from decimal import Decimal
from django.contrib.auth.models import User
from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from org.models import Ship, Service, Sector
from assets.models import (
    Asset,
    AssetType,
    Installation,
    InstallationMaintenance,
    InstallationHourReading,
    ModeDeclenchement,
)
from maintenance.models import MaintenanceOccurrence, MaintenanceExecution, MaintenancePlan
from maintenance.management.commands.generate_installation_occurrences import add_interval


class ExecutionInstallationTests(TestCase):
    """Vérifie la remise à zéro de l'échéance d'une InstallationMaintenance à la
    validation du formulaire de fin de maintenance (branches compteur et calendaire),
    ainsi que la non-régression du flux d'exécution existant pour le matériel mobile."""

    def setUp(self):
        self.ship = Ship.objects.create(name="Navire test", code="NT4")
        self.service = Service.objects.create(ship=self.ship, name="Service test")
        self.sector = Sector.objects.create(service=self.service, name="Secteur test")
        self.installation = Installation.objects.create(
            designation="Groupe électrogène", ship=self.ship, service=self.service, sector=self.sector,
        )
        self.tech = User.objects.create_user(username="tech", password="pass")
        self.client = APIClient()
        self.client.login(username="tech", password="pass")

    def test_validation_branche_compteur_met_a_jour_derniere_echeance(self):
        maintenance = InstallationMaintenance.objects.create(
            installation=self.installation,
            periodicity="500h",
            title="Vidange",
            mode_declenchement=ModeDeclenchement.COMPTEUR,
            seuil_heures=500,
            derniere_echeance_heures=0,
        )
        InstallationHourReading.objects.create(installation=self.installation, hours=520)
        occ = MaintenanceOccurrence.objects.create(
            installation_maintenance=maintenance, scheduled_for=timezone.localdate(), status="ASSIGNED",
        )
        occ.assignees.add(self.tech)

        r = self.client.post(f"/api/maintenance/occurrences/{occ.id}/complete/", {"conformity": "CONFORME"})
        self.assertEqual(r.status_code, 200)

        maintenance.refresh_from_db()
        self.assertEqual(maintenance.derniere_echeance_heures, Decimal("520.00"))

    def test_validation_branche_calendaire_sert_de_reference_pour_prochaine_echeance(self):
        maintenance = InstallationMaintenance.objects.create(
            installation=self.installation,
            periodicity="1 mois",
            title="Contrôle général",
            mode_declenchement=ModeDeclenchement.CALENDRIER,
            intervalle=1,
            unite_intervalle="M",
        )
        occ = MaintenanceOccurrence.objects.create(
            installation_maintenance=maintenance, scheduled_for=timezone.localdate(), status="ASSIGNED",
        )
        occ.assignees.add(self.tech)

        r = self.client.post(f"/api/maintenance/occurrences/{occ.id}/complete/", {"conformity": "CONFORME"})
        self.assertEqual(r.status_code, 200)
        occ.refresh_from_db()
        self.assertEqual(occ.status, "DONE")

        # La prochaine génération doit se baser sur la date de cette exécution
        # structurée (aujourd'hui), pas sur l'ancienne heuristique InstallationEvent
        # (aucun InstallationEvent n'existe ici).
        call_command("generate_installation_occurrences")
        nouvelle = (
            MaintenanceOccurrence.objects.filter(installation_maintenance=maintenance)
            .exclude(pk=occ.pk)
            .first()
        )
        self.assertIsNotNone(nouvelle)
        attendue = add_interval(timezone.localdate(), "M", 1)
        self.assertEqual(nouvelle.scheduled_for, attendue)

    def test_non_conforme_ne_declenche_pas_la_mise_a_jour(self):
        maintenance = InstallationMaintenance.objects.create(
            installation=self.installation,
            periodicity="500h",
            title="Vidange",
            mode_declenchement=ModeDeclenchement.COMPTEUR,
            seuil_heures=500,
            derniere_echeance_heures=0,
        )
        InstallationHourReading.objects.create(installation=self.installation, hours=520)
        occ = MaintenanceOccurrence.objects.create(
            installation_maintenance=maintenance, scheduled_for=timezone.localdate(), status="ASSIGNED",
        )
        occ.assignees.add(self.tech)

        r = self.client.post(f"/api/maintenance/occurrences/{occ.id}/complete/", {"conformity": "NON_CONFORME"})
        self.assertEqual(r.status_code, 200)
        occ.refresh_from_db()
        self.assertEqual(occ.status, "WAITING_VALIDATION")

        maintenance.refresh_from_db()
        self.assertEqual(maintenance.derniere_echeance_heures, Decimal("0.00"))

    def test_non_regression_flux_asset_existant(self):
        asset_type = AssetType.objects.create(name="Extincteur", category="Incendie", sector=self.sector)
        asset = Asset.objects.create(asset_type=asset_type, ship=self.ship, service=self.service, sector=self.sector)
        plan = MaintenancePlan.objects.create(scope="ASSET", asset=asset, name="Contrôle annuel", every_n_days=365)
        occ = MaintenanceOccurrence.objects.create(
            plan=plan, asset=asset, scheduled_for=timezone.localdate(), status="ASSIGNED",
        )
        occ.assignees.add(self.tech)

        r = self.client.post(f"/api/maintenance/occurrences/{occ.id}/complete/", {"conformity": "CONFORME"})
        self.assertEqual(r.status_code, 200)
        occ.refresh_from_db()
        self.assertEqual(occ.status, "DONE")
        self.assertTrue(MaintenanceExecution.objects.filter(occurrence=occ).exists())
