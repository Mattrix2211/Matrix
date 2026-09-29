"""Double équipage, tranche 4 : une occurrence de maintenance appartient au
bâtiment (visible des deux équipages), mais ne s'assigne qu'à des marins de
l'équipage de l'appelant ; même règle pour les tickets correctifs."""
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.models import UserProfile
from assets.models import Asset, AssetType
from logistics.models import CorrectiveTicket
from maintenance.models import MaintenanceOccurrence, MaintenancePlan
from org.models import Equipage, Sector, Service, Ship

User = get_user_model()


def marin(nom, role, ship, equipage=None):
    user = User.objects.create_user(username=nom, password="pass")
    UserProfile.objects.update_or_create(user=user, defaults={"role": role, "ship": ship, "equipage": equipage})
    return User.objects.get(pk=user.pk)


class AssignationsParEquipageTests(TestCase):
    def setUp(self):
        self.ship = Ship.objects.create(name="BSAM Test", code="BT", classe_navire="BSAM", double_equipage=True)
        self.bleu = Equipage.objects.create(ship=self.ship, nom="Bleu")
        self.rouge = Equipage.objects.create(ship=self.ship, nom="Rouge")
        self.ship.equipage_a_bord = self.bleu
        self.ship.save()
        service = Service.objects.create(ship=self.ship, name="Pont")
        secteur = Sector.objects.create(service=service, name="Manœuvre")
        type_actif = AssetType.objects.create(name="Extincteur", category="Incendie", sector=secteur)
        self.asset = Asset.objects.create(asset_type=type_actif, ship=self.ship, service=service, sector=secteur)
        plan = MaintenancePlan.objects.create(scope="ASSET", asset=self.asset, name="Plan", every_n_days=30)
        self.occurrence = MaintenanceOccurrence.objects.create(
            plan=plan, asset=self.asset, scheduled_for=timezone.localdate(), status="PLANNED",
        )
        self.cdt_bleu = marin("cdt_bleu", "COMMANDANT", self.ship, self.bleu)
        self.m_bleu = marin("m_bleu", "EQUIPIER", self.ship, self.bleu)
        self.m_rouge = marin("m_rouge", "EQUIPIER", self.ship, self.rouge)

    def _assigner_occurrence(self, marin_cible):
        client = APIClient()
        client.force_authenticate(self.cdt_bleu)
        return client.patch(
            f"/api/maintenance/occurrences/{self.occurrence.pk}/", {"assignees": [marin_cible.pk]}, format="json"
        )

    def test_occurrence_non_assignable_a_l_autre_equipage(self):
        reponse = self._assigner_occurrence(self.m_rouge)
        self.assertEqual(reponse.status_code, 400)
        self.assertFalse(self.occurrence.assignees.exists())

    def test_occurrence_assignable_a_son_equipage(self):
        reponse = self._assigner_occurrence(self.m_bleu)
        self.assertEqual(reponse.status_code, 200, reponse.content)
        self.assertEqual(list(self.occurrence.assignees.all()), [self.m_bleu])

    def test_ticket_web_n_assigne_que_l_equipage_de_l_appelant(self):
        ticket = CorrectiveTicket.objects.create(asset=self.asset, description="Fuite")
        self.client.force_login(self.cdt_bleu)
        self.client.post(
            reverse("ticket-assign", args=[ticket.pk]), {"assignees": [self.m_bleu.pk, self.m_rouge.pk]}
        )
        self.assertEqual(list(ticket.assignees.all()), [self.m_bleu])

    def test_ticket_api_refuse_l_autre_equipage(self):
        ticket = CorrectiveTicket.objects.create(asset=self.asset, description="Fuite")
        client = APIClient()
        client.force_authenticate(self.cdt_bleu)
        reponse = client.patch(f"/api/logistics/tickets/{ticket.pk}/", {"assignees": [self.m_rouge.pk]}, format="json")
        self.assertEqual(reponse.status_code, 400)
        self.assertFalse(ticket.assignees.exists())
