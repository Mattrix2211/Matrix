"""Vérifie la faille corrigée sur org/views.py : avant correction, seul ADMIN_NAVIRE
était restreint à son navire dans ShipViewSet/ServiceViewSet/SectorViewSet/SectionViewSet ;
tout autre rôle (CHEF_SECTION compris, dès lors que RolePermission.min_level_write =
CHEF_SECTION) pouvait créer/modifier des services, secteurs et sections sur n'importe
quel navire de la flotte. La restriction de périmètre par navire est désormais
généralisée à tous les rôles non administrateur général (cf. _is_master_admin).
"""
from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient
from accounts.models import UserProfile
from org.models import Ship, Service, Sector, Section


class ScopeNavireTests(TestCase):
    def setUp(self):
        self.navire_a = Ship.objects.create(name="Navire A", code="A")
        self.navire_b = Ship.objects.create(name="Navire B", code="B")

        self.service_a = Service.objects.create(ship=self.navire_a, name="Service A")
        self.service_b = Service.objects.create(ship=self.navire_b, name="Service B")

        self.secteur_a = Sector.objects.create(service=self.service_a, name="Secteur A")
        self.secteur_b = Sector.objects.create(service=self.service_b, name="Secteur B")

        self.section_a = Section.objects.create(sector=self.secteur_a, name="Section A")
        self.section_b = Section.objects.create(sector=self.secteur_b, name="Section B")

        # Un profil est déjà auto-créé par le signal post_save sur User : on met à jour
        # le rôle et le navire plutôt que de recréer un profil.
        self.chef_section_a = User.objects.create_user(username="chef_a", password="pass")
        UserProfile.objects.update_or_create(
            user=self.chef_section_a, defaults={"role": "CHEF_SECTION", "ship": self.navire_a}
        )

        self.admin_navire_a = User.objects.create_user(username="admin_a", password="pass")
        UserProfile.objects.update_or_create(
            user=self.admin_navire_a, defaults={"role": "ADMIN_NAVIRE", "ship": self.navire_a}
        )

        self.master_admin = User.objects.create_user(username="master", password="pass")
        UserProfile.objects.update_or_create(
            user=self.master_admin, defaults={"role": "MASTER_ADMIN"}
        )

        self.client = APIClient()

    # --- CHEF_SECTION du navire A rejeté sur le navire B ---------------------------

    def test_chef_section_ne_voit_que_les_services_de_son_navire(self):
        self.client.login(username="chef_a", password="pass")
        resp = self.client.get("/api/org/services/")
        self.assertEqual(resp.status_code, 200)
        noms = {s["name"] for s in resp.data["results"]} if "results" in resp.data else {s["name"] for s in resp.data}
        self.assertIn("Service A", noms)
        self.assertNotIn("Service B", noms)

    def test_chef_section_ne_peut_pas_creer_un_service_sur_un_autre_navire(self):
        self.client.login(username="chef_a", password="pass")
        resp = self.client.post(
            "/api/org/services/", {"ship": self.navire_b.id, "name": "Intrus"}, format="json"
        )
        self.assertEqual(resp.status_code, 403)
        self.assertFalse(Service.objects.filter(name="Intrus").exists())

    def test_chef_section_ne_peut_pas_creer_un_secteur_sur_un_autre_navire(self):
        self.client.login(username="chef_a", password="pass")
        resp = self.client.post(
            "/api/org/sectors/", {"service": self.service_b.id, "name": "Intrus"}, format="json"
        )
        self.assertEqual(resp.status_code, 403)
        self.assertFalse(Sector.objects.filter(name="Intrus").exists())

    def test_chef_section_ne_peut_pas_modifier_une_section_dun_autre_navire(self):
        self.client.login(username="chef_a", password="pass")
        resp = self.client.patch(
            f"/api/org/sections/{self.section_b.id}/", {"name": "Renommée"}, format="json"
        )
        # 404 : la section d'un autre navire est hors du périmètre visible du chef de
        # section (get_queryset filtré), donc introuvable avant même perform_update.
        self.assertIn(resp.status_code, (403, 404))
        self.section_b.refresh_from_db()
        self.assertEqual(self.section_b.name, "Section B")

    def test_chef_section_ne_voit_pas_le_navire_dun_autre_batiment(self):
        self.client.login(username="chef_a", password="pass")
        resp = self.client.get("/api/org/ships/")
        self.assertEqual(resp.status_code, 200)
        ids = {s["id"] for s in resp.data["results"]} if "results" in resp.data else {s["id"] for s in resp.data}
        self.assertIn(self.navire_a.id, ids)
        self.assertNotIn(self.navire_b.id, ids)

    # --- ADMIN_NAVIRE reste limité à son propre navire (comportement déjà existant) -

    def test_admin_navire_reste_limite_a_son_propre_navire(self):
        self.client.login(username="admin_a", password="pass")
        resp = self.client.get("/api/org/ships/")
        self.assertEqual(resp.status_code, 200)
        ids = {s["id"] for s in resp.data["results"]} if "results" in resp.data else {s["id"] for s in resp.data}
        self.assertIn(self.navire_a.id, ids)
        self.assertNotIn(self.navire_b.id, ids)

    # --- MASTER_ADMIN garde l'accès multi-navires -----------------------------------

    def test_master_admin_a_un_acces_multi_navires(self):
        self.client.login(username="master", password="pass")
        resp = self.client.get("/api/org/ships/")
        self.assertEqual(resp.status_code, 200)
        ids = {s["id"] for s in resp.data["results"]} if "results" in resp.data else {s["id"] for s in resp.data}
        self.assertIn(self.navire_a.id, ids)
        self.assertIn(self.navire_b.id, ids)
