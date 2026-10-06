"""API comptes : périmètre vide, champs d'un profil qu'un tiers ne doit pas
pouvoir réécrire (compte lié, secteurs autorisés hors périmètre), création et
suppression de profil par l'API."""
from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient

from accounts.models import UserProfile
from org.models import Sector, Service, Ship


class ApiComptesChampsProprietaireTests(TestCase):
    def setUp(self):
        self.ship_a = Ship.objects.create(name="Navire A champs", code="NA-CHP")
        self.service_a = Service.objects.create(ship=self.ship_a, name="Service A champs")
        self.sector_a = Sector.objects.create(service=self.service_a, name="Secteur A champs")
        self.ship_b = Ship.objects.create(name="Navire B champs", code="NB-CHP")
        self.service_b = Service.objects.create(ship=self.ship_b, name="Service B champs")
        self.sector_b = Sector.objects.create(service=self.service_b, name="Secteur B champs")

        self.sans_perimetre = self._marin("sans_perimetre_chp", "CHEF_SERVICE")
        self.equipier_a = self._marin("equipier_a_chp", "EQUIPIER", ship=self.ship_a)
        self.equipier_b = self._marin("equipier_b_chp", "EQUIPIER", ship=self.ship_b)
        self.commandant_a = self._marin("commandant_a_chp", "COMMANDANT", ship=self.ship_a)
        self.admin_a = self._marin("admin_a_chp", "ADMIN_NAVIRE", ship=self.ship_a)

    def _marin(self, username, role, **perimetre):
        user = User.objects.create_user(username=username, password="pass")
        UserProfile.objects.update_or_create(user=user, defaults={"role": role, **perimetre})
        return user

    def _client(self, username):
        client = APIClient()
        client.login(username=username, password="pass")
        return client

    def test_perimetre_vide_ne_donne_pas_la_flotte_via_users(self):
        r = self._client("sans_perimetre_chp").get("/api/accounts/users/")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(list(r.data), [])

    def test_perimetre_vide_ne_donne_pas_la_flotte_via_profiles(self):
        r = self._client("sans_perimetre_chp").get("/api/accounts/profiles/")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(list(r.data), [])

    def test_patch_ne_modifie_pas_le_compte_lie(self):
        r = self._client("commandant_a_chp").patch(
            f"/api/accounts/profiles/{self.equipier_a.profile.pk}/",
            {"role": "EQUIPIER", "user": {"id": self.equipier_b.pk, "username": "pirate"}},
            format="json",
        )
        self.assertEqual(r.status_code, 200)
        self.equipier_a.profile.refresh_from_db()
        self.assertEqual(self.equipier_a.profile.user_id, self.equipier_a.pk)
        self.equipier_a.refresh_from_db()
        self.assertEqual(self.equipier_a.username, "equipier_a_chp")

    def test_commandant_ne_peut_pas_donner_un_secteur_hors_perimetre(self):
        r = self._client("commandant_a_chp").patch(
            f"/api/accounts/profiles/{self.equipier_a.profile.pk}/",
            {"role": "EQUIPIER", "allowed_sectors": [self.sector_b.pk]},
            format="json",
        )
        self.assertEqual(r.status_code, 400)
        self.assertFalse(self.equipier_a.profile.allowed_sectors.exists())

    def test_commandant_peut_donner_un_secteur_de_son_navire(self):
        r = self._client("commandant_a_chp").patch(
            f"/api/accounts/profiles/{self.equipier_a.profile.pk}/",
            {"role": "EQUIPIER", "allowed_sectors": [self.sector_a.pk]},
            format="json",
        )
        self.assertEqual(r.status_code, 200)
        self.assertEqual(self.equipier_a.profile.allowed_sectors.count(), 1)

    def test_creation_de_profil_par_api_interdite(self):
        r = self._client("commandant_a_chp").post(
            "/api/accounts/profiles/", {"role": "EQUIPIER", "user": self.equipier_b.pk}, format="json"
        )
        self.assertEqual(r.status_code, 405)

    def test_suppression_de_profil_par_api_interdite(self):
        r = self._client("admin_a_chp").delete(f"/api/accounts/profiles/{self.equipier_a.profile.pk}/")
        self.assertEqual(r.status_code, 405)
        self.assertTrue(UserProfile.objects.filter(pk=self.equipier_a.profile.pk).exists())
