from django.conf import settings
from django.test import TestCase
from assets.models import Installation, InstallationHourReading, InstallationMaintenance, ModeDeclenchement
from maintenance.models import MaintenanceOccurrence
from maintenance.tasks import generate_installation_occurrences
from org.models import Sector, Service, Ship


class CeleryBeatInstallationOccurrencesTests(TestCase):
    """Vérifie que la génération des occurrences de maintenance pour les
    installations fixes est bien planifiée dans Celery Beat (jusqu'ici oubliée,
    contrairement à son équivalent pour le matériel mobile)."""

    def test_tache_referencee_dans_celery_beat_schedule(self):
        entry = settings.CELERY_BEAT_SCHEDULE.get("generate_installation_occurrences_daily")
        self.assertIsNotNone(entry, "Aucune entrée Celery Beat pour generate_installation_occurrences")
        self.assertEqual(entry["task"], "maintenance.tasks.generate_installation_occurrences")

    def test_tache_celery_genere_bien_une_occurrence(self):
        """La tâche Celery doit produire le même résultat que la commande qu'elle enveloppe."""
        ship = Ship.objects.create(name="Navire test", code="NT3")
        service = Service.objects.create(ship=ship, name="Service test")
        sector = Sector.objects.create(service=service, name="Secteur test")
        installation = Installation.objects.create(
            designation="Pompe test", ship=ship, service=service, sector=sector,
        )
        maintenance = InstallationMaintenance.objects.create(
            installation=installation,
            periodicity="500h",
            title="Vidange",
            mode_declenchement=ModeDeclenchement.COMPTEUR,
            seuil_heures=500,
            derniere_echeance_heures=0,
        )
        InstallationHourReading.objects.create(installation=installation, hours=520)

        generate_installation_occurrences()

        self.assertTrue(
            MaintenanceOccurrence.objects.filter(installation_maintenance=maintenance).exists()
        )
