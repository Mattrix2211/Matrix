"""API exécutions de maintenance : exécutant et signature de validation sont
posés par le serveur, le rattachement reste dans le périmètre de l'appelant."""
from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.models import UserProfile
from assets.models import Asset, AssetType
from maintenance.models import MaintenanceExecution, MaintenanceOccurrence, MaintenancePlan
from org.models import Sector, Service, Ship


class ApiExecutionsChampsProprietaireTests(TestCase):
    def setUp(self):
        self.occ_a, self.occ_b = (self._occurrence(n) for n in ("A", "B"))
        self.chef_a = User.objects.create_user(username="chef_a_mex", password="pass")
        UserProfile.objects.update_or_create(
            user=self.chef_a, defaults={"role": "CHEF_SECTION", "ship": self.occ_a.asset.ship}
        )
        self.autre = User.objects.create_user(username="autre_mex", password="pass")
        self.client = APIClient()
        self.client.login(username="chef_a_mex", password="pass")

    def _occurrence(self, nom):
        navire = Ship.objects.create(name=f"Navire {nom} mex", code=f"{nom}-MEX")
        service = Service.objects.create(ship=navire, name=f"Service {nom}")
        secteur = Sector.objects.create(service=service, name=f"Secteur {nom}")
        type_ = AssetType.objects.create(name=f"Type {nom}", category="Cat", sector=secteur)
        asset = Asset.objects.create(asset_type=type_, ship=navire, service=service, sector=secteur)
        plan = MaintenancePlan.objects.create(scope="ASSET", asset=asset, name=f"Plan {nom}", every_n_days=30)
        return MaintenanceOccurrence.objects.create(
            plan=plan, asset=asset, scheduled_for=timezone.now().date(), status="PLANNED"
        )

    def test_executant_et_signature_non_choisis_par_l_appelant(self):
        r = self.client.post(
            "/api/maintenance/executions/",
            {"occurrence": self.occ_a.pk, "executed_by": self.autre.pk, "valide_par": self.autre.pk,
             "date_validation": "2026-01-01T00:00:00Z", "created_by": self.autre.pk},
            format="json",
        )
        self.assertEqual(r.status_code, 201)
        execution = MaintenanceExecution.objects.get(pk=r.data["id"])
        self.assertEqual(execution.executed_by, self.chef_a)
        self.assertIsNone(execution.valide_par)
        self.assertIsNone(execution.date_validation)
        self.assertEqual(execution.created_by, self.chef_a)

    def test_modification_ne_forge_pas_la_signature(self):
        execution = MaintenanceExecution.objects.create(occurrence=self.occ_a, executed_by=self.chef_a)
        r = self.client.patch(
            f"/api/maintenance/executions/{execution.pk}/",
            {"valide_par": self.autre.pk, "executed_by": self.autre.pk},
            format="json",
        )
        self.assertEqual(r.status_code, 200)
        execution.refresh_from_db()
        self.assertIsNone(execution.valide_par)
        self.assertEqual(execution.executed_by, self.chef_a)

    def test_execution_sur_une_occurrence_hors_perimetre_refusee(self):
        r = self.client.post("/api/maintenance/executions/", {"occurrence": self.occ_b.pk}, format="json")
        self.assertEqual(r.status_code, 400)
        self.assertFalse(MaintenanceExecution.objects.exists())
