from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient
from org.models import Ship, Service, Sector
from assets.models import AssetType, Asset
from logistics.models import CorrectiveTicket, TicketStatusLog


class LogisticsRBACTests(TestCase):
    def test_only_chef_section_can_transition_ticket(self):
        ship = Ship.objects.create(name="S1")
        service = Service.objects.create(name="Srv", ship=ship)
        sector = Sector.objects.create(name="Sec", service=service)
        at = AssetType.objects.create(name="TypeA", category="Cat", sector=sector)
        asset = Asset.objects.create(asset_type=at, ship=ship, service=service, sector=sector)

        # Création du ticket
        ticket = CorrectiveTicket.objects.create(asset=asset, description="Pb")

        # Utilisateurs
        equipier = User.objects.create_user(username="equ", password="pass")
        chef = User.objects.create_user(username="chef", password="pass")

        # Un profil est déjà auto-créé par le signal post_save sur User (rôle EQUIPIER
        # par défaut) : on met à jour le rôle plutôt que de recréer un profil.
        from accounts.models import UserProfile
        UserProfile.objects.update_or_create(user=equipier, defaults={"role": "EQUIPIER"})
        UserProfile.objects.update_or_create(user=chef, defaults={"role": "CHEF_SECTION"})

        client = APIClient()
        # L'équipier ne peut pas faire transiter le ticket
        client.login(username="equ", password="pass")
        url = f"/api/logistics/tickets/{ticket.pk}/transition/"
        resp = client.post(url, {"status": "DIAGNOSED"}, format="json")
        self.assertIn(resp.status_code, (403, 404))

        # Le chef peut faire transiter le ticket
        client.logout()
        client.login(username="chef", password="pass")
        resp3 = client.post(url, {"status": "DIAGNOSED"}, format="json")
        self.assertIn(resp3.status_code, (200, 202))

    def test_transition_api_refuse_la_fermeture_sans_diagnostic_ni_solution(self):
        """Régression : l'action 'transition' de l'API DRF fermait un ticket sans
        exiger le retour d'expérience (diagnostic + solution), contrairement à
        TicketTransitionView (interface web) qui applique déjà cette règle
        (CLAUDE.md : « REX obligatoire à CLOSED »)."""
        ship = Ship.objects.create(name="S2")
        service = Service.objects.create(name="Srv2", ship=ship)
        sector = Sector.objects.create(name="Sec2", service=service)
        at = AssetType.objects.create(name="TypeB", category="Cat", sector=sector)
        asset = Asset.objects.create(asset_type=at, ship=ship, service=service, sector=sector)
        ticket = CorrectiveTicket.objects.create(asset=asset, description="Fuite")

        from accounts.models import UserProfile
        chef = User.objects.create_user(username="chef_rex_api", password="pass")
        UserProfile.objects.update_or_create(user=chef, defaults={"role": "CHEF_SECTION"})

        client = APIClient()
        client.login(username="chef_rex_api", password="pass")
        url = f"/api/logistics/tickets/{ticket.pk}/transition/"

        resp = client.post(url, {"status": "CLOSED"}, format="json")
        self.assertEqual(resp.status_code, 400)
        ticket.refresh_from_db()
        self.assertNotEqual(ticket.status, "CLOSED")
        self.assertEqual(TicketStatusLog.objects.filter(ticket=ticket).count(), 0)

        # Une fois le diagnostic et la solution renseignés (sur le ticket, comme le
        # ferait l'interface web via TicketTransitionView), la fermeture est acceptée.
        ticket.diagnostic_final = "Joint usé"
        ticket.solution = "Joint remplacé"
        ticket.save(update_fields=["diagnostic_final", "solution"])
        resp2 = client.post(url, {"status": "CLOSED"}, format="json")
        self.assertIn(resp2.status_code, (200, 202))
        ticket.refresh_from_db()
        self.assertEqual(ticket.status, "CLOSED")
