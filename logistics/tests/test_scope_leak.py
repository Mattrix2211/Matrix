from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient

from accounts.models import UserProfile
from assets.models import Asset, AssetType
from logistics.models import CorrectiveTicket, PartLineItem, PartRequest
from org.models import Sector, Service, Ship


class ScopeLeakLogisticsTests(TestCase):
    """Un utilisateur scopé sur le navire A ne doit ni voir ni modifier les
    tickets correctifs, demandes de pièces et lignes de pièces du navire B
    via l'API (cf. tâche [SEC] ScopedQuerySetMixin : ne plus s'annuler
    silencieusement)."""

    def setUp(self):
        # Navire A
        self.ship_a = Ship.objects.create(name="Navire A", code="NA")
        self.service_a = Service.objects.create(ship=self.ship_a, name="Service A")
        self.sector_a = Sector.objects.create(service=self.service_a, name="Secteur A")
        self.asset_type_a = AssetType.objects.create(name="TypeA", category="Cat", sector=self.sector_a)
        self.asset_a = Asset.objects.create(
            asset_type=self.asset_type_a, ship=self.ship_a, service=self.service_a, sector=self.sector_a,
        )

        # Navire B
        self.ship_b = Ship.objects.create(name="Navire B", code="NB")
        self.service_b = Service.objects.create(ship=self.ship_b, name="Service B")
        self.sector_b = Sector.objects.create(service=self.service_b, name="Secteur B")
        self.asset_type_b = AssetType.objects.create(name="TypeB", category="Cat", sector=self.sector_b)
        self.asset_b = Asset.objects.create(
            asset_type=self.asset_type_b, ship=self.ship_b, service=self.service_b, sector=self.sector_b,
        )

        self.ticket_a = CorrectiveTicket.objects.create(asset=self.asset_a, description="Panne A")
        self.ticket_b = CorrectiveTicket.objects.create(asset=self.asset_b, description="Panne B")

        self.part_request_a = PartRequest.objects.create(ticket=self.ticket_a)
        self.part_request_b = PartRequest.objects.create(ticket=self.ticket_b)

        self.part_line_a = PartLineItem.objects.create(
            part_request=self.part_request_a, reference="REF-A", description="Pièce A"
        )
        self.part_line_b = PartLineItem.objects.create(
            part_request=self.part_request_b, reference="REF-B", description="Pièce B"
        )

        # Utilisateur scopé uniquement sur le secteur A
        self.user_a = User.objects.create_user(username="chef_a", password="pass")
        UserProfile.objects.update_or_create(
            user=self.user_a, defaults={"role": "CHEF_SECTION", "sector": self.sector_a}
        )

        self.client = APIClient()
        self.client.login(username="chef_a", password="pass")

    def test_tickets_scope_leak(self):
        r = self.client.get("/api/logistics/tickets/")
        self.assertEqual(r.status_code, 200)
        ids = {str(t["id"]) for t in r.data}
        self.assertIn(str(self.ticket_a.id), ids)
        self.assertNotIn(str(self.ticket_b.id), ids)

    def test_part_requests_scope_leak(self):
        r = self.client.get("/api/logistics/part-requests/")
        self.assertEqual(r.status_code, 200)
        ids = {pr["id"] for pr in r.data}
        self.assertIn(self.part_request_a.id, ids)
        self.assertNotIn(self.part_request_b.id, ids)

    def test_part_lines_scope_leak(self):
        r = self.client.get("/api/logistics/part-lines/")
        self.assertEqual(r.status_code, 200)
        ids = {pl["id"] for pl in r.data}
        self.assertIn(self.part_line_a.id, ids)
        self.assertNotIn(self.part_line_b.id, ids)

    def test_ne_peut_pas_transitionner_un_ticket_dun_autre_navire(self):
        """Un CHEF_SECTION du navire A ne doit pas pouvoir faire transitionner
        un ticket du navire B, même si son rôle le lui permettrait sur son
        propre périmètre : l'objet doit d'abord être absent de son queryset
        scopé (404)."""
        url = f"/api/logistics/tickets/{self.ticket_b.id}/transition/"
        r = self.client.post(url, {"status": "DIAGNOSED"}, format="json")
        self.assertEqual(r.status_code, 404)

    def test_ne_peut_pas_lire_une_demande_de_pieces_dun_autre_navire_par_pk(self):
        r = self.client.get(f"/api/logistics/part-requests/{self.part_request_b.id}/")
        self.assertEqual(r.status_code, 404)
