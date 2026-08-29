from django.test import TestCase
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from org.models import Ship, Service, Sector
from assets.models import AssetType, Asset
from logistics.models import CorrectiveTicket, TicketStatusLog

class TicketTransitionTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="u", password="p")
        ship = Ship.objects.create(name="Ship A", code="A")
        service = Service.objects.create(ship=ship, name="Tech")
        sector = Sector.objects.create(service=service, name="Elec")
        at = AssetType.objects.create(name="Extincteur", category="Fire", sector=sector)
        self.asset = Asset.objects.create(asset_type=at, ship=ship, service=service, sector=sector, status="OK")

    def test_transition_logs(self):
        t = CorrectiveTicket.objects.create(asset=self.asset, description="Panne")
        old = t.status
        t.status = "DIAGNOSED"
        t.save()
        TicketStatusLog.objects.create(ticket=t, old_status=old, new_status=t.status, user=self.user)
        self.assertEqual(TicketStatusLog.objects.filter(ticket=t).count(), 1)

    def test_saut_direct_reported_vers_closed_actuellement_accepte(self):
        """Test de non-régression (pas une validation de règle métier) : constate
        que CorrectiveTicketViewSet.transition() n'impose aujourd'hui AUCUN ordre
        entre les statuts du cycle de vie. Un ticket "Signalé" (REPORTED) peut donc
        être fermé (CLOSED) en un seul appel, sans passer par les étapes
        intermédiaires (DIAGNOSED, WAITING_PARTS, PLANNED, IN_REPAIR, TESTING,
        RETURNED_TO_SERVICE).

        Ce point a été remonté à l'utilisateur lors de l'audit de couverture de
        tests (tâche Notion issue de l'ecc:pr-test-analyzer du 2026-08-29) : il
        s'agit potentiellement d'un choix métier Marine Nationale (traçabilité
        réglementaire du cycle de vie d'une panne), pas d'une décision technique
        anodine. Ce test documente donc le comportement CONSTATÉ, sans en changer
        le comportement — imposer ou non un ordre de transition est une question
        métier qui reste à trancher par l'utilisateur, pas par le développeur."""
        from accounts.models import UserProfile

        chef = User.objects.create_user(username="chef_ordre_transitions", password="pass")
        UserProfile.objects.update_or_create(user=chef, defaults={"role": "CHEF_SECTION"})
        ticket = CorrectiveTicket.objects.create(asset=self.asset, description="Fuite huile")
        self.assertEqual(ticket.status, "REPORTED")

        client = APIClient()
        client.login(username="chef_ordre_transitions", password="pass")
        url = f"/api/logistics/tickets/{ticket.pk}/transition/"
        # Le REX (diagnostic + solution) est une exigence distincte, déjà testée
        # ailleurs (test_rbac_transitions.py) : on la renseigne ici pour isoler
        # uniquement le comportement lié à l'ORDRE des statuts.
        ticket.diagnostic_final = "Joint défectueux"
        ticket.solution = "Joint remplacé"
        ticket.save(update_fields=["diagnostic_final", "solution"])

        resp = client.post(url, {"status": "CLOSED"}, format="json")

        self.assertIn(resp.status_code, (200, 202))
        ticket.refresh_from_db()
        self.assertEqual(ticket.status, "CLOSED")
        self.assertEqual(
            list(TicketStatusLog.objects.filter(ticket=ticket).values_list("old_status", "new_status")),
            [("REPORTED", "CLOSED")],
        )
