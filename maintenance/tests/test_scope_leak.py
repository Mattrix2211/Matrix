from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.models import UserProfile
from assets.models import (
    Asset,
    AssetType,
    Installation,
    InstallationMaintenance,
    ModeDeclenchement,
)
from maintenance.models import MaintenanceExecution, MaintenanceOccurrence, MaintenancePlan
from org.models import Sector, Service, Ship


class ScopeLeakMaintenanceTests(TestCase):
    """Un utilisateur scopé sur le navire A ne doit ni voir ni modifier les
    plans/occurrences/exécutions du navire B via l'API (cf. tâche [SEC]
    ScopedQuerySetMixin : ne plus s'annuler silencieusement)."""

    def setUp(self):
        # Navire A
        self.ship_a = Ship.objects.create(name="Navire A", code="NA")
        self.service_a = Service.objects.create(ship=self.ship_a, name="Service A")
        self.sector_a = Sector.objects.create(service=self.service_a, name="Secteur A")
        self.asset_type_a = AssetType.objects.create(name="TypeA", category="Cat", sector=self.sector_a)
        self.asset_a = Asset.objects.create(
            asset_type=self.asset_type_a, ship=self.ship_a, service=self.service_a, sector=self.sector_a,
        )
        self.installation_a = Installation.objects.create(
            designation="Pompe A", ship=self.ship_a, service=self.service_a, sector=self.sector_a,
        )

        # Navire B
        self.ship_b = Ship.objects.create(name="Navire B", code="NB")
        self.service_b = Service.objects.create(ship=self.ship_b, name="Service B")
        self.sector_b = Sector.objects.create(service=self.service_b, name="Secteur B")
        self.asset_type_b = AssetType.objects.create(name="TypeB", category="Cat", sector=self.sector_b)
        self.asset_b = Asset.objects.create(
            asset_type=self.asset_type_b, ship=self.ship_b, service=self.service_b, sector=self.sector_b,
        )
        self.installation_b = Installation.objects.create(
            designation="Pompe B", ship=self.ship_b, service=self.service_b, sector=self.sector_b,
        )

        # Plans scopés par actif (ASSET) sur les deux navires
        self.plan_a = MaintenancePlan.objects.create(scope="ASSET", asset=self.asset_a, name="Plan A", every_n_days=30)
        self.plan_b = MaintenancePlan.objects.create(scope="ASSET", asset=self.asset_b, name="Plan B", every_n_days=30)

        # Plan scopé par type d'actif (ASSET_TYPE) sur le navire B, pour couvrir
        # le second chemin de traduction (asset_type__sector__...)
        self.plan_type_b = MaintenancePlan.objects.create(
            scope="ASSET_TYPE", asset_type=self.asset_type_b, name="Plan type B", every_n_days=30
        )

        # Occurrences liées à du matériel mobile sur les deux navires
        self.occ_asset_a = MaintenanceOccurrence.objects.create(
            plan=self.plan_a, asset=self.asset_a, scheduled_for=timezone.now().date(), status="PLANNED",
        )
        self.occ_asset_b = MaintenanceOccurrence.objects.create(
            plan=self.plan_b, asset=self.asset_b, scheduled_for=timezone.now().date(), status="PLANNED",
        )

        # Occurrences liées à une installation fixe sur les deux navires (second
        # chemin XOR du modèle MaintenanceOccurrence)
        self.installation_maintenance_a = InstallationMaintenance.objects.create(
            installation=self.installation_a, periodicity="Mensuel", title="Graissage",
            mode_declenchement=ModeDeclenchement.CALENDRIER,
        )
        self.installation_maintenance_b = InstallationMaintenance.objects.create(
            installation=self.installation_b, periodicity="Mensuel", title="Graissage",
            mode_declenchement=ModeDeclenchement.CALENDRIER,
        )
        self.occ_install_a = MaintenanceOccurrence.objects.create(
            installation_maintenance=self.installation_maintenance_a,
            scheduled_for=timezone.now().date(), status="PLANNED",
        )
        self.occ_install_b = MaintenanceOccurrence.objects.create(
            installation_maintenance=self.installation_maintenance_b,
            scheduled_for=timezone.now().date(), status="PLANNED",
        )

        # Exécutions liées aux occurrences des deux chemins, sur les deux navires
        self.exec_asset_a = MaintenanceExecution.objects.create(occurrence=self.occ_asset_a)
        self.exec_asset_b = MaintenanceExecution.objects.create(occurrence=self.occ_asset_b)
        self.exec_install_a = MaintenanceExecution.objects.create(occurrence=self.occ_install_a)
        self.exec_install_b = MaintenanceExecution.objects.create(occurrence=self.occ_install_b)

        # Utilisateur scopé uniquement sur le secteur A
        self.user_a = User.objects.create_user(username="chef_a", password="pass")
        UserProfile.objects.update_or_create(
            user=self.user_a, defaults={"role": "CHEF_SECTION", "sector": self.sector_a}
        )

        self.client = APIClient()
        self.client.login(username="chef_a", password="pass")

    def test_plans_scope_leak(self):
        r = self.client.get("/api/maintenance/plans/")
        self.assertEqual(r.status_code, 200)
        ids = {p["id"] for p in r.data}
        self.assertIn(self.plan_a.id, ids)
        self.assertNotIn(self.plan_b.id, ids)
        self.assertNotIn(self.plan_type_b.id, ids)

    def test_occurrences_scope_leak(self):
        r = self.client.get("/api/maintenance/occurrences/")
        self.assertEqual(r.status_code, 200)
        ids = {o["id"] for o in r.data}
        self.assertIn(self.occ_asset_a.id, ids)
        self.assertIn(self.occ_install_a.id, ids)
        self.assertNotIn(self.occ_asset_b.id, ids)
        self.assertNotIn(self.occ_install_b.id, ids)

    def test_executions_scope_leak(self):
        r = self.client.get("/api/maintenance/executions/")
        self.assertEqual(r.status_code, 200)
        ids = {e["id"] for e in r.data}
        self.assertIn(self.exec_asset_a.id, ids)
        self.assertIn(self.exec_install_a.id, ids)
        self.assertNotIn(self.exec_asset_b.id, ids)
        self.assertNotIn(self.exec_install_b.id, ids)

    def test_ne_peut_pas_modifier_une_occurrence_dun_autre_navire(self):
        """Un CHEF_SECTION du navire A ne doit pas pouvoir démarrer une
        occurrence du navire B, même si son rôle suffit en écriture
        (min_role_level_write=EQUIPIER) : l'objet doit d'abord être absent
        de son queryset scopé (404), pas seulement bloqué par le rôle."""
        url = f"/api/maintenance/occurrences/{self.occ_asset_b.id}/start/"
        r = self.client.post(url, {})
        self.assertEqual(r.status_code, 404)

        url_install = f"/api/maintenance/occurrences/{self.occ_install_b.id}/start/"
        r_install = self.client.post(url_install, {})
        self.assertEqual(r_install.status_code, 404)

    def test_ne_peut_pas_lire_un_plan_dun_autre_navire_par_pk(self):
        r = self.client.get(f"/api/maintenance/plans/{self.plan_b.id}/")
        self.assertEqual(r.status_code, 404)
