from django.conf import settings
from django.test import TestCase


class CeleryBeatGenerationOccurrencesTests(TestCase):
    """Vérifie que la génération quotidienne des occurrences de maintenance
    (matériel mobile) et le calcul horaire des retards sont bien planifiés
    dans Celery Beat, même pattern que CeleryBeatInstallationOccurrencesTests
    (test_celery_beat_installations.py) pour leurs équivalents installations."""

    def test_generate_occurrences_referencee_dans_celery_beat_schedule(self):
        entry = settings.CELERY_BEAT_SCHEDULE.get("generate_occurrences_daily")
        self.assertIsNotNone(entry, "Aucune entrée Celery Beat pour generate_occurrences")
        self.assertEqual(entry["task"], "maintenance.tasks.generate_occurrences")

    def test_compute_overdue_referencee_dans_celery_beat_schedule(self):
        entry = settings.CELERY_BEAT_SCHEDULE.get("compute_overdue_hourly")
        self.assertIsNotNone(entry, "Aucune entrée Celery Beat pour compute_overdue")
        self.assertEqual(entry["task"], "maintenance.tasks.compute_overdue")
