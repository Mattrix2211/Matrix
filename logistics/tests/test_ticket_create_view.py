from django.contrib.auth.models import User
from django.test import TestCase

from accounts.models import UserProfile
from assets.models import Asset, AssetType
from logistics.models import CorrectiveTicket
from org.models import Sector, Service, Ship


class TicketCreateViewTests(TestCase):
    """Signalement rapide d'une anomalie depuis la fiche d'un matériel mobile
    (bouton « Signaler une anomalie » du scan QR ou de la fiche équipement).
    """

    def setUp(self):
        self.ship_a = Ship.objects.create(name="Navire A", code="NA")
        self.service_a = Service.objects.create(ship=self.ship_a, name="Service A")
        self.sector_a = Sector.objects.create(service=self.service_a, name="Secteur A")
        self.asset_type_a = AssetType.objects.create(name="TypeA", category="Cat", sector=self.sector_a)
        self.asset_a = Asset.objects.create(
            asset_type=self.asset_type_a, ship=self.ship_a, service=self.service_a, sector=self.sector_a,
        )

        self.ship_b = Ship.objects.create(name="Navire B", code="NB")
        self.service_b = Service.objects.create(ship=self.ship_b, name="Service B")
        self.sector_b = Sector.objects.create(service=self.service_b, name="Secteur B")
        self.asset_type_b = AssetType.objects.create(name="TypeB", category="Cat", sector=self.sector_b)
        self.asset_b = Asset.objects.create(
            asset_type=self.asset_type_b, ship=self.ship_b, service=self.service_b, sector=self.sector_b,
        )

        self.marin = User.objects.create_user(username="marin_a", password="pass")
        UserProfile.objects.update_or_create(
            user=self.marin, defaults={"role": "EQUIPIER", "ship": self.ship_a}
        )
        self.client.login(username="marin_a", password="pass")

    def test_signalement_cree_un_ticket_et_redirige_vers_le_detail(self):
        response = self.client.post(
            f"/logistics/tickets/creer/{self.asset_a.id}/",
            {"description": "Fuite constatée", "severity": "4"},
        )
        ticket = CorrectiveTicket.objects.get(asset=self.asset_a)
        self.assertRedirects(response, f"/logistics/tickets/{ticket.id}/")
        self.assertEqual(ticket.description, "Fuite constatée")
        self.assertEqual(ticket.severity, 4)
        self.assertEqual(ticket.status, "REPORTED")
        self.assertIn(self.marin, ticket.assignees.all())

    def test_signalement_sans_description_est_refuse(self):
        self.client.post(f"/logistics/tickets/creer/{self.asset_a.id}/", {"description": "  "})
        self.assertFalse(CorrectiveTicket.objects.filter(asset=self.asset_a).exists())

    def test_signalement_sur_materiel_hors_perimetre_rejete(self):
        response = self.client.post(
            f"/logistics/tickets/creer/{self.asset_b.id}/", {"description": "Anomalie"}
        )
        self.assertEqual(response.status_code, 400)
        self.assertFalse(CorrectiveTicket.objects.filter(asset=self.asset_b).exists())
