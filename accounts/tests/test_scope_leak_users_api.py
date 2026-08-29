"""Exposition API utilisateurs : UserViewSet/UserProfileViewSet doivent
appliquer le même périmètre et le même seuil de rôle que UserDirectoryView
(accounts/web_views.py) — COMMANDANT et au-dessus voient la flotte entière,
en-dessous la lecture est restreinte au périmètre hiérarchique de l'appelant.
Avant correction, l'API exposait tous les comptes à tout utilisateur connecté,
y compris un simple équipier. Cf. tâche [SEC] Exposition API utilisateurs.
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

    def test_commandant_voit_la_flotte_entiere_via_users(self):
        client = self._login("commandant_a_cpt")
        r = client.get("/api/accounts/users/")
        self.assertEqual(r.status_code, 200)
        usernames = {u["username"] for u in r.data}
        self.assertIn("equipier_a_cpt", usernames)
        self.assertIn("equipier_b_cpt", usernames)
