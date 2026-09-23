from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient

from accounts.models import UserProfile
from assets.models import AssetType, ChecklistTemplate, Location
from org.models import Sector, Section, Service, Ship


class ScopeLeakAssetsReferentielsTests(TestCase):
    """LocationViewSet, AssetTypeViewSet et ChecklistTemplateViewSet
    n'ont pas de champ ship/service/sector/section direct pour tous les
    niveaux de périmètre. Un utilisateur scopé (chef de secteur, de
    service, ou commandant) doit pouvoir consulter ces référentiels sans
    provoquer d'erreur serveur, et ne doit voir que ceux de son navire
    (cf. tâche [SEC] ScopedQuerySetMixin : ne plus s'annuler silencieusement,
    refus Tech Lead sur assets/views.py)."""

    def setUp(self):
        # Navire A
        self.ship_a = Ship.objects.create(name="Navire A", code="NA")
        self.service_a = Service.objects.create(ship=self.ship_a, name="Service A")
        self.sector_a = Sector.objects.create(service=self.service_a, name="Secteur A")
        self.section_a = Section.objects.create(sector=self.sector_a, name="Section A")
        self.location_a = Location.objects.create(ship=self.ship_a, name="Local A")
        self.asset_type_a = AssetType.objects.create(name="TypeA", category="Cat", sector=self.sector_a)
        self.checklist_a = ChecklistTemplate.objects.create(name="Checklist A", sector=self.sector_a)

        # Navire B
        self.ship_b = Ship.objects.create(name="Navire B", code="NB")
        self.service_b = Service.objects.create(ship=self.ship_b, name="Service B")
        self.sector_b = Sector.objects.create(service=self.service_b, name="Secteur B")
        self.location_b = Location.objects.create(ship=self.ship_b, name="Local B")
        self.asset_type_b = AssetType.objects.create(name="TypeB", category="Cat", sector=self.sector_b)
        self.checklist_b = ChecklistTemplate.objects.create(name="Checklist B", sector=self.sector_b)

        # Un utilisateur par niveau de périmètre, tous rattachés au navire A
        self.user_secteur = User.objects.create_user(username="chef_secteur_a", password="pass")
        UserProfile.objects.update_or_create(
            user=self.user_secteur, defaults={"role": "CHEF_SECTEUR", "sector": self.sector_a}
        )
        self.user_service = User.objects.create_user(username="chef_service_a", password="pass")
        UserProfile.objects.update_or_create(
            user=self.user_service, defaults={"role": "CHEF_SERVICE", "service": self.service_a}
        )
        self.user_commandant = User.objects.create_user(username="commandant_a", password="pass")
        UserProfile.objects.update_or_create(
            user=self.user_commandant, defaults={"role": "COMMANDANT", "ship": self.ship_a}
        )
        self.user_section = User.objects.create_user(username="chef_section_a", password="pass")
        UserProfile.objects.update_or_create(
            user=self.user_section, defaults={"role": "CHEF_SECTION", "section": self.section_a}
        )

    def _login(self, user):
        client = APIClient()
        client.login(username=user.username, password="pass")
        return client

    def test_locations_visibles_sans_erreur_pour_chaque_niveau_de_perimetre(self):
        for user in (self.user_secteur, self.user_service, self.user_commandant, self.user_section):
            client = self._login(user)
            r = client.get("/api/assets/locations/")
            self.assertEqual(r.status_code, 200, user.username)
            ids = {loc["id"] for loc in r.data}
            self.assertIn(self.location_a.id, ids, user.username)
            self.assertNotIn(self.location_b.id, ids, user.username)

    def test_asset_types_visibles_sans_erreur_pour_secteur_service_navire(self):
        for user in (self.user_secteur, self.user_service, self.user_commandant):
            client = self._login(user)
            r = client.get("/api/assets/types/")
            self.assertEqual(r.status_code, 200, user.username)
            ids = {t["id"] for t in r.data}
            self.assertIn(self.asset_type_a.id, ids, user.username)
            self.assertNotIn(self.asset_type_b.id, ids, user.username)

    def test_asset_types_vide_mais_sans_erreur_pour_un_chef_de_section(self):
        # Un secteur n'est jamais découpé par section : un chef de section
        # ne voit aucun type d'actif via ce filtre, mais la requête ne
        # doit pas planter pour autant (choix assumé, cf. commentaire
        # AssetTypeViewSet.get_scoped_filters).
        client = self._login(self.user_section)
        r = client.get("/api/assets/types/")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.data), 0)

    def test_checklist_templates_visibles_sans_erreur_pour_secteur_service_navire(self):
        for user in (self.user_secteur, self.user_service, self.user_commandant):
            client = self._login(user)
            r = client.get("/api/assets/checklist-templates/")
            self.assertEqual(r.status_code, 200, user.username)
            ids = {c["id"] for c in r.data}
            self.assertIn(self.checklist_a.id, ids, user.username)
            self.assertNotIn(self.checklist_b.id, ids, user.username)
