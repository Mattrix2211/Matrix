"""Un ADMIN_NAVIRE ne touche jamais au rôle MASTER_ADMIN, côté API comme côté web."""
from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient

from accounts.models import UserProfile
from org.models import Ship


class AdminNavireLimitesTests(TestCase):
    def setUp(self):
        self.navire = Ship.objects.create(name="Navire limites", code="NV-LIM")
        self.admin = self._marin("admin_lim", "ADMIN_NAVIRE")
        self.equipier = self._marin("equipier_lim", "EQUIPIER")
        self.maitre = self._marin("maitre_lim", "MASTER_ADMIN")

    def _marin(self, username, role):
        user = User.objects.create_user(username=username, password="pass")
        UserProfile.objects.update_or_create(user=user, defaults={"role": role, "ship": self.navire})
        return user

    def _api(self):
        client = APIClient()
        client.login(username="admin_lim", password="pass")
        return client

    def test_api_refuse_dattribuer_master_admin(self):
        r = self._api().patch(f"/api/accounts/profiles/{self.equipier.profile.pk}/", {"role": "MASTER_ADMIN"}, format="json")
        self.assertEqual(r.status_code, 403)
        self.equipier.profile.refresh_from_db()
        self.assertEqual(self.equipier.profile.role, "EQUIPIER")

    def test_api_refuse_de_modifier_un_profil_master_admin(self):
        r = self._api().patch(f"/api/accounts/profiles/{self.maitre.profile.pk}/", {"role": "EQUIPIER"}, format="json")
        self.assertEqual(r.status_code, 403)
        self.maitre.profile.refresh_from_db()
        self.assertEqual(self.maitre.profile.role, "MASTER_ADMIN")

    def test_api_refuse_de_modifier_un_master_admin_sans_changer_son_role(self):
        r = self._api().patch(f"/api/accounts/profiles/{self.maitre.profile.pk}/", {"ship": self.navire.pk}, format="json")
        self.assertEqual(r.status_code, 403)

    def test_api_autorise_un_role_inferieur_ou_egal(self):
        for role in ("COMMANDANT", "ADMIN_NAVIRE"):
            r = self._api().patch(f"/api/accounts/profiles/{self.equipier.profile.pk}/", {"role": role}, format="json")
            self.assertEqual(r.status_code, 200)

    def test_api_modification_sans_role_dans_le_payload_reste_possible(self):
        r = self._api().patch(f"/api/accounts/profiles/{self.equipier.profile.pk}/", {"ship": self.navire.pk}, format="json")
        self.assertEqual(r.status_code, 200)

    def test_web_refuse_dattribuer_master_admin(self):
        self.client.login(username="admin_lim", password="pass")
        self.client.post("/users/", {
            "action": "bulk_update_role", "selected_ids": [self.equipier.id], "role": "MASTER_ADMIN",
        })
        self.equipier.profile.refresh_from_db()
        self.assertEqual(self.equipier.profile.role, "EQUIPIER")

    def test_web_refuse_de_modifier_un_profil_master_admin(self):
        self.client.login(username="admin_lim", password="pass")
        self.client.post("/users/", {
            "action": "bulk_update_role", "selected_ids": [self.maitre.id], "role": "EQUIPIER",
        })
        self.maitre.profile.refresh_from_db()
        self.assertEqual(self.maitre.profile.role, "MASTER_ADMIN")
        self.client.post("/users/", {"action": "set_password", "pk": self.maitre.id, "password": "NouveauMotDePasse123!"})
        self.maitre.refresh_from_db()
        self.assertTrue(self.maitre.check_password("pass"))
