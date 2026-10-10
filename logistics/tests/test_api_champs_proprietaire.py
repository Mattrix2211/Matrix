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


class ApiTicketsAssignationTests(TestCase):
    def setUp(self):
        self.ticket_a, self.ticket_b = (self._ticket(n) for n in ("A", "B"))
        self.chef_a = self._marin("chef_a_tka", "CHEF_SECTION", self.ticket_a.asset.ship)
        self.equipier_a = self._marin("equipier_a_tka", "EQUIPIER", self.ticket_a.asset.ship)
        self.equipier_b = self._marin("equipier_b_tka", "EQUIPIER", self.ticket_b.asset.ship)
        self.client = APIClient()
        self.client.login(username="chef_a_tka", password="pass")

    def _marin(self, username, role, navire):
        user = User.objects.create_user(username=username, password="pass")
        UserProfile.objects.update_or_create(user=user, defaults={"role": role, "ship": navire})
        return user

    def _ticket(self, nom):
        navire = Ship.objects.create(name=f"Navire {nom} tka", code=f"{nom}-TKA")
        service = Service.objects.create(ship=navire, name=f"Service {nom}")
        secteur = Sector.objects.create(service=service, name=f"Secteur {nom}")
        type_ = AssetType.objects.create(name=f"Type {nom}", category="Cat", sector=secteur)
        asset = Asset.objects.create(asset_type=type_, ship=navire, service=service, sector=secteur)
        return CorrectiveTicket.objects.create(asset=asset, description=f"Panne {nom}")

    def test_assignation_d_un_marin_hors_perimetre_refusee(self):
        r = self.client.patch(
            f"/api/logistics/tickets/{self.ticket_a.pk}/", {"assignees": [self.equipier_b.pk]}, format="json"
        )
        self.assertEqual(r.status_code, 400)
        self.assertFalse(self.ticket_a.assignees.exists())

    def test_assignation_d_un_marin_du_perimetre_acceptee(self):
        r = self.client.patch(
            f"/api/logistics/tickets/{self.ticket_a.pk}/", {"assignees": [self.equipier_a.pk]}, format="json"
        )
        self.assertEqual(r.status_code, 200)
        self.assertEqual(list(self.ticket_a.assignees.all()), [self.equipier_a])

    def test_creation_sur_un_materiel_hors_perimetre_refusee(self):
        nb = CorrectiveTicket.objects.count()
        r = self.client.post(
            "/api/logistics/tickets/", {"asset": self.ticket_b.asset.pk, "description": "Intrus"}, format="json"
        )
        self.assertEqual(r.status_code, 400)
        self.assertEqual(CorrectiveTicket.objects.count(), nb)

    def test_auteur_pose_par_le_serveur(self):
        r = self.client.post(
            "/api/logistics/tickets/",
            {"asset": self.ticket_a.asset.pk, "description": "Ok", "created_by": self.equipier_b.pk},
            format="json",
        )
        self.assertEqual(r.status_code, 201)
        self.assertEqual(CorrectiveTicket.objects.get(pk=r.data["id"]).created_by, self.chef_a)
        r = self.client.patch(
            f"/api/logistics/tickets/{r.data['id']}/", {"updated_by": self.equipier_b.pk, "description": "Maj"}, format="json"
        )
        self.assertEqual(CorrectiveTicket.objects.get(pk=r.data["id"]).updated_by, self.chef_a)
