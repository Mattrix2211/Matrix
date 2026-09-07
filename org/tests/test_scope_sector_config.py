"""Vérifie la faille corrigée sur SectorConfigViewSet (org/views.py) : avant
correction, aucun filtre de périmètre n'était appliqué sur ce ViewSet — un
utilisateur authentifié pouvait lire, et tout utilisateur au seuil
d'écriture générique (CHEF_SECTION+) modifier ou supprimer, la configuration
d'un secteur (préférences d'affichage, seuils d'alerte, widgets du tableau
de bord) appartenant à un AUTRE navire. La restriction par navire est
désormais alignée sur celle déjà appliquée à Ship/Service/Sector/Section
(cf. org/tests/test_scope_navire.py)."""
from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient

from accounts.models import UserProfile
from org.models import Sector, SectorConfig, Section, Service, Ship


class ScopeSectorConfigTests(TestCase):
    def setUp(self):
        self.navire_a = Ship.objects.create(name="Navire Config A", code="CFA")
        self.navire_b = Ship.objects.create(name="Navire Config B", code="CFB")

        self.service_a = Service.objects.create(ship=self.navire_a, name="Service A")
        self.service_b = Service.objects.create(ship=self.navire_b, name="Service B")

        self.secteur_a = Sector.objects.create(service=self.service_a, name="Secteur A")
        self.secteur_b = Sector.objects.create(service=self.service_b, name="Secteur B")

        self.config_a = SectorConfig.objects.create(sector=self.secteur_a, ui_preferences={"a": 1})
        self.config_b = SectorConfig.objects.create(sector=self.secteur_b, ui_preferences={"b": 2})

        self.chef_section_a = User.objects.create_user(username="chef_cfg_a", password="pass")
        UserProfile.objects.update_or_create(
            user=self.chef_section_a, defaults={"role": "CHEF_SECTION", "ship": self.navire_a}
        )

        self.master_admin = User.objects.create_user(username="master_cfg", password="pass")
        UserProfile.objects.update_or_create(user=self.master_admin, defaults={"role": "MASTER_ADMIN"})

        self.client = APIClient()
        self.client.login(username="chef_cfg_a", password="pass")

    def test_liste_ne_contient_pas_la_config_dun_autre_navire(self):
        r = self.client.get("/api/org/sector-configs/")
        self.assertEqual(r.status_code, 200)
        ids = {c["id"] for c in r.data}
        self.assertIn(self.config_a.id, ids)
        self.assertNotIn(self.config_b.id, ids)

    def test_ne_peut_pas_lire_la_config_dun_autre_navire_par_pk(self):
        r = self.client.get(f"/api/org/sector-configs/{self.config_b.id}/")
        self.assertEqual(r.status_code, 404)

    def test_ne_peut_pas_modifier_la_config_dun_autre_navire(self):
        r = self.client.patch(
            f"/api/org/sector-configs/{self.config_b.id}/",
            {"ui_preferences": {"hack": True}},
            format="json",
        )
        self.assertEqual(r.status_code, 404)
        self.config_b.refresh_from_db()
        self.assertEqual(self.config_b.ui_preferences, {"b": 2})

    def test_ne_peut_pas_supprimer_la_config_dun_autre_navire(self):
        r = self.client.delete(f"/api/org/sector-configs/{self.config_b.id}/")
        self.assertEqual(r.status_code, 404)
        self.assertTrue(SectorConfig.objects.filter(pk=self.config_b.id).exists())

    def test_master_admin_voit_les_configs_de_toute_la_flotte(self):
        self.client.logout()
        self.client.login(username="master_cfg", password="pass")
        r = self.client.get("/api/org/sector-configs/")
        self.assertEqual(r.status_code, 200)
        ids = {c["id"] for c in r.data}
        self.assertIn(self.config_a.id, ids)
        self.assertIn(self.config_b.id, ids)
