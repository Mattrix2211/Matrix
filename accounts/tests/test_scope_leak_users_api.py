"""Exposition API utilisateurs : UserViewSet/UserProfileViewSet doivent
appliquer le même périmètre que UserDirectoryView (accounts/web_views.py) —
seul MASTER_ADMIN (ou un superutilisateur) voit la flotte entière, tous les
autres rôles (ADMIN_NAVIRE et COMMANDANT compris, cf.
matrix/core/scopes.py::is_master_admin) sont rattachés à un navire précis et
la lecture est restreinte à leur périmètre hiérarchique.

Avant correction (audit sécurité du 2026-08-29), un COMMANDANT (et tout rôle
au-dessus) voyait le personnel de TOUS les navires de la flotte, y compris
via une simple requête d'API sur un autre navire que le sien (fuite de
données inter-navire). Cf. tâche « Sécurité : restreindre un COMMANDANT (et
rôles supérieurs) à son propre navire dans l'annuaire du personnel ».
"""
from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient

from accounts.models import UserProfile
from org.models import Sector, Service, Ship


class ScopeLeakUsersAPITests(TestCase):
    def setUp(self):
        # Navire A
        self.ship_a = Ship.objects.create(name="Navire A comptes", code="NA-CPT")
        self.service_a = Service.objects.create(ship=self.ship_a, name="Service A comptes")
        self.sector_a = Sector.objects.create(service=self.service_a, name="Secteur A comptes")

        # Navire B
        self.ship_b = Ship.objects.create(name="Navire B comptes", code="NB-CPT")
        self.service_b = Service.objects.create(ship=self.ship_b, name="Service B comptes")
        self.sector_b = Sector.objects.create(service=self.service_b, name="Secteur B comptes")

        self.equipier_a = User.objects.create_user(username="equipier_a_cpt", password="pass")
        UserProfile.objects.update_or_create(
            user=self.equipier_a, defaults={"role": "EQUIPIER", "sector": self.sector_a}
        )
        self.equipier_b = User.objects.create_user(username="equipier_b_cpt", password="pass")
        UserProfile.objects.update_or_create(
            user=self.equipier_b, defaults={"role": "EQUIPIER", "sector": self.sector_b}
        )
        self.commandant_a = User.objects.create_user(username="commandant_a_cpt", password="pass")
        UserProfile.objects.update_or_create(
            user=self.commandant_a, defaults={"role": "COMMANDANT", "ship": self.ship_a}
        )
        self.admin_navire_a = User.objects.create_user(username="admin_navire_a_cpt", password="pass")
        UserProfile.objects.update_or_create(
            user=self.admin_navire_a, defaults={"role": "ADMIN_NAVIRE", "ship": self.ship_a}
        )
        self.master_admin = User.objects.create_superuser(
            username="master_admin_cpt", password="pass", email="master_admin_cpt@example.com"
        )

    def _login(self, username):
        client = APIClient()
        client.login(username=username, password="pass")
        return client

    def test_equipier_ne_voit_que_les_comptes_de_son_perimetre_via_users(self):
        client = self._login("equipier_a_cpt")
        r = client.get("/api/accounts/users/")
        self.assertEqual(r.status_code, 200)
        usernames = {u["username"] for u in r.data}
        self.assertIn("equipier_a_cpt", usernames)
        self.assertNotIn("equipier_b_cpt", usernames)

    def test_equipier_ne_voit_que_les_profils_de_son_perimetre_via_profiles(self):
        client = self._login("equipier_a_cpt")
        r = client.get("/api/accounts/profiles/")
        self.assertEqual(r.status_code, 200)
        user_ids = {p["user"]["id"] for p in r.data}
        self.assertIn(self.equipier_a.id, user_ids)
        self.assertNotIn(self.equipier_b.id, user_ids)

    def test_commandant_ne_voit_que_son_propre_navire_via_users(self):
        client = self._login("commandant_a_cpt")
        r = client.get("/api/accounts/users/")
        self.assertEqual(r.status_code, 200)
        usernames = {u["username"] for u in r.data}
        self.assertIn("equipier_a_cpt", usernames)
        self.assertNotIn("equipier_b_cpt", usernames)

    def test_commandant_ne_voit_que_son_propre_navire_via_profiles(self):
        client = self._login("commandant_a_cpt")
        r = client.get("/api/accounts/profiles/")
        self.assertEqual(r.status_code, 200)
        user_ids = {p["user"]["id"] for p in r.data}
        self.assertIn(self.equipier_a.id, user_ids)
        self.assertNotIn(self.equipier_b.id, user_ids)

    def test_admin_navire_ne_voit_que_son_propre_navire_via_users(self):
        """ADMIN_NAVIRE est, comme COMMANDANT, rattaché à un navire précis
        (matrix/core/scopes.py::is_master_admin) : seul MASTER_ADMIN a une
        vue flotte entière."""
        client = self._login("admin_navire_a_cpt")
        r = client.get("/api/accounts/users/")
        self.assertEqual(r.status_code, 200)
        usernames = {u["username"] for u in r.data}
        self.assertIn("equipier_a_cpt", usernames)
        self.assertNotIn("equipier_b_cpt", usernames)

    def test_master_admin_voit_la_flotte_entiere_via_users(self):
        client = self._login("master_admin_cpt")
        r = client.get("/api/accounts/users/")
        self.assertEqual(r.status_code, 200)
        usernames = {u["username"] for u in r.data}
        self.assertIn("equipier_a_cpt", usernames)
        self.assertIn("equipier_b_cpt", usernames)

    def test_master_admin_voit_la_flotte_entiere_via_profiles(self):
        client = self._login("master_admin_cpt")
        r = client.get("/api/accounts/profiles/")
        self.assertEqual(r.status_code, 200)
        user_ids = {p["user"]["id"] for p in r.data}
        self.assertIn(self.equipier_a.id, user_ids)
        self.assertIn(self.equipier_b.id, user_ids)
