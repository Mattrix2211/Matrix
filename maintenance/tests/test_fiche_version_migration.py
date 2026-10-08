"""Les exécutions d'installation déjà saisies sont figées sur la version validée à leur date."""
from datetime import date
from importlib import import_module

from django.apps import apps
from django.test import TestCase

from assets.models import ChecklistTemplate, Installation, InstallationMaintenance
from maintenance.models import MaintenanceExecution, MaintenanceOccurrence
from org.models import Sector, Service, Ship

migration = import_module("maintenance.migrations.0006_executions_version_fiche_existantes")


class FigerVersionsTests(TestCase):
    def test_execution_existante_garde_sa_version_et_rejeu_sans_effet(self):
        navire = Ship.objects.create(name="N", code="N1")
        service = Service.objects.create(ship=navire, name="S")
        secteur = Sector.objects.create(service=service, name="Se")
        installation = Installation.objects.create(designation="Pompe", ship=navire, service=service, sector=secteur)
        fiche = InstallationMaintenance.objects.create(installation=installation, periodicity="1 an", title="Annuel")
        v1 = ChecklistTemplate.objects.create(fiche=fiche, numero=1, name="Annuel", sector=secteur, valide_le="2020-01-01T00:00:00Z")
        occurrence = MaintenanceOccurrence.objects.create(installation_maintenance=fiche, scheduled_for=date.today())
        execution = MaintenanceExecution.objects.create(occurrence=occurrence)
        MaintenanceExecution.objects.filter(pk=execution.pk).update(version_fiche=None)
        ChecklistTemplate.objects.create(fiche=fiche, numero=2, name="Annuel", sector=secteur, valide_le="2999-01-01T00:00:00Z")
        migration.figer_versions(apps, None)
        migration.figer_versions(apps, None)
        execution.refresh_from_db()
        self.assertEqual(execution.version_fiche, v1)
