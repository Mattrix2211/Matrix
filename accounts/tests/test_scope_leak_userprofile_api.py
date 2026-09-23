"""UserProfileViewSet (API DRF) doit valider que le navire/service/secteur/
section de DESTINATION d'une écriture (PATCH/PUT) appartient au périmètre
navire de l'appelant — même règle que celle déjà appliquée côté web via
matrix/core/scopes.py::resoudre_affectation_dans_perimetre (cf. create_user,
edit_user, bulk_update_* dans accounts/web_views.py).

Avant correction, UserProfileViewSet acceptait n'importe quel id de navire/
service/secteur/section transmis dans le payload sans vérifier qu'il
appartenait au périmètre de l'appelant : un COMMANDANT ou un ADMIN_NAVIRE
pouvait ainsi, en forgeant une requête API, rattacher un utilisateur de son
navire à un navire d'un AUTRE bâtiment (faille signalée par le QA, cf. tâche
« Sécurité : valider le périmètre navire de destination... dans
UserProfileViewSet »)."""
from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient

from accounts.models import UserProfile
from org.models import Ship


class ScopeLeakUserProfileAPIDestinationTests(TestCase):
    def setUp(self):
        self.ship_a = Ship.objects.create(name="Navire A profil API", code="NA-PAPI")
        self.ship_b = Ship.objects.create(name="Navire B profil API", code="NB-PAPI")

        self.equipier_a = User.objects.create_user(username="equipier_a_papi", password="pass")
        UserProfile.objects.update_or_create(
            user=self.equipier_a, defaults={"role": "EQUIPIER", "ship": self.ship_a}
        )

        self.commandant_a = User.objects.create_user(username="commandant_a_papi", password="pass")
        UserProfile.objects.update_or_create(
            user=self.commandant_a, defaults={"role": "COMMANDANT", "ship": self.ship_a}
        )
        self.admin_navire_a = User.objects.create_user(username="admin_navire_a_papi", password="pass")
        UserProfile.objects.update_or_create(
            user=self.admin_navire_a, defaults={"role": "ADMIN_NAVIRE", "ship": self.ship_a}
        )
        self.master_admin = User.objects.create_superuser(
            username="master_admin_papi", password="pass", email="master_admin_papi@example.com"
        )

    def _login(self, username):
        client = APIClient()
        client.login(username=username, password="pass")
        return client

    def _url(self, profile):
        return f"/api/accounts/profiles/{profile.pk}/"

    def test_commandant_ne_peut_pas_affecter_un_utilisateur_a_un_navire_hors_perimetre(self):
        client = self._login("commandant_a_papi")
        r = client.patch(
            self._url(self.equipier_a.profile),
            {"role": "EQUIPIER", "ship": self.ship_b.pk},
            format="json",
        )
        self.assertEqual(r.status_code, 400)
        self.equipier_a.profile.refresh_from_db()
        self.assertEqual(self.equipier_a.profile.ship_id, self.ship_a.pk)

    def test_admin_navire_ne_peut_pas_affecter_un_utilisateur_a_un_navire_hors_perimetre(self):
        client = self._login("admin_navire_a_papi")
        r = client.patch(
            self._url(self.equipier_a.profile),
            {"role": "EQUIPIER", "ship": self.ship_b.pk},
            format="json",
        )
        self.assertEqual(r.status_code, 400)
        self.equipier_a.profile.refresh_from_db()
        self.assertEqual(self.equipier_a.profile.ship_id, self.ship_a.pk)

    def test_commandant_peut_affecter_un_utilisateur_a_son_propre_navire(self):
        """Non-régression : une destination DANS le périmètre reste acceptée."""
        client = self._login("commandant_a_papi")
        r = client.patch(
            self._url(self.equipier_a.profile),
            {"role": "EQUIPIER", "ship": self.ship_a.pk},
            format="json",
        )
        self.assertEqual(r.status_code, 200)
        self.equipier_a.profile.refresh_from_db()
        self.assertEqual(self.equipier_a.profile.ship_id, self.ship_a.pk)

    def test_master_admin_garde_une_liberte_totale_dassignation(self):
        client = self._login("master_admin_papi")
        r = client.patch(
            self._url(self.equipier_a.profile),
            {"role": "EQUIPIER", "ship": self.ship_b.pk},
            format="json",
        )
        self.assertEqual(r.status_code, 200)
        self.equipier_a.profile.refresh_from_db()
        self.assertEqual(self.equipier_a.profile.ship_id, self.ship_b.pk)
