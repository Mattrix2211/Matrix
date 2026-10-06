"""API demandes de pièces : demandeur et rattachement ne sont pas choisis par l'appelant."""
from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient

from accounts.models import UserProfile
from assets.models import Asset, AssetType
from logistics.models import CorrectiveTicket, PartLineItem, PartRequest
from org.models import Sector, Service, Ship


class ApiPiecesChampsProprietaireTests(TestCase):
    def setUp(self):
        self.ticket_a, self.ticket_b = (self._ticket(n) for n in ("A", "B"))
        self.demande_a = PartRequest.objects.create(ticket=self.ticket_a)
        self.demande_b = PartRequest.objects.create(ticket=self.ticket_b)
        self.chef_a = User.objects.create_user(username="chef_a_prc", password="pass")
        UserProfile.objects.update_or_create(
            user=self.chef_a, defaults={"role": "CHEF_SECTION", "ship": self.ticket_a.asset.ship}
        )
        self.autre = User.objects.create_user(username="autre_prc", password="pass")
        self.client = APIClient()
        self.client.login(username="chef_a_prc", password="pass")

    def _ticket(self, nom):
        navire = Ship.objects.create(name=f"Navire {nom} prc", code=f"{nom}-PRC")
        service = Service.objects.create(ship=navire, name=f"Service {nom}")
        secteur = Sector.objects.create(service=service, name=f"Secteur {nom}")
        type_ = AssetType.objects.create(name=f"Type {nom}", category="Cat", sector=secteur)
        asset = Asset.objects.create(asset_type=type_, ship=navire, service=service, sector=secteur)
        return CorrectiveTicket.objects.create(asset=asset, description=f"Panne {nom}")

    def test_demandeur_force_a_l_appelant(self):
        r = self.client.post(
            "/api/logistics/part-requests/",
            {"ticket": self.ticket_a.pk, "requested_by": self.autre.pk, "created_by": self.autre.pk},
            format="json",
        )
        self.assertEqual(r.status_code, 201)
        demande = PartRequest.objects.get(pk=r.data["id"])
        self.assertEqual(demande.requested_by, self.chef_a)
        self.assertEqual(demande.created_by, self.chef_a)

    def test_demande_sur_un_ticket_hors_perimetre_refusee(self):
        nb = PartRequest.objects.count()
        r = self.client.post("/api/logistics/part-requests/", {"ticket": self.ticket_b.pk}, format="json")
        self.assertEqual(r.status_code, 400)
        self.assertEqual(PartRequest.objects.count(), nb)

    def test_demande_ne_peut_pas_etre_deplacee_hors_perimetre(self):
        r = self.client.patch(
            f"/api/logistics/part-requests/{self.demande_a.pk}/", {"ticket": self.ticket_b.pk}, format="json"
        )
        self.assertEqual(r.status_code, 400)
        self.demande_a.refresh_from_db()
        self.assertEqual(self.demande_a.ticket, self.ticket_a)

    def test_ligne_sur_une_demande_hors_perimetre_refusee(self):
        r = self.client.post(
            "/api/logistics/part-lines/",
            {"part_request": self.demande_b.pk, "reference": "X", "description": "Intrus"},
            format="json",
        )
        self.assertEqual(r.status_code, 400)
        self.assertFalse(PartLineItem.objects.exists())

    def test_ligne_sur_sa_propre_demande_acceptee(self):
        r = self.client.post(
            "/api/logistics/part-lines/",
            {"part_request": self.demande_a.pk, "reference": "X", "description": "Ok"},
            format="json",
        )
        self.assertEqual(r.status_code, 201)
