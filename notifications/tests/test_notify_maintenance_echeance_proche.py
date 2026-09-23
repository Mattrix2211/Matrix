from datetime import timedelta

from django.conf import settings
from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone

from assets.models import Asset, AssetType
from maintenance.models import MaintenanceOccurrence, MaintenancePlan
from notifications.models import Notification, NotificationLevel
from notifications.tasks import JOURS_ALERTE_ECHEANCE_MAINTENANCE, notify_maintenance_echeance_proche
from org.models import Sector, Service, Ship


class NotifyMaintenanceEcheanceProcheTests(TestCase):
    """Rappel préventif d'échéance de maintenance, AVANT le retard (WARNING) —
    complément de notify_overdue_occurrences (DANGER, une fois l'échéance
    dépassée)."""

    def setUp(self):
        ship = Ship.objects.create(name="Navire Échéance", code="ECH")
        service = Service.objects.create(ship=ship, name="Tech")
        sector = Sector.objects.create(service=service, name="Elec")
        asset_type = AssetType.objects.create(name="TypeA", category="Cat", sector=sector)
        self.asset = Asset.objects.create(
            asset_type=asset_type, ship=ship, service=service, sector=sector
        )
        self.plan = MaintenancePlan.objects.create(
            scope="ASSET", asset=self.asset, name="Plan A", every_n_days=30
        )
        self.marin = User.objects.create_user(username="marin_ech", password="pass")

    def _creer_occurrence(self, dans_combien_de_jours, status="ASSIGNED"):
        occ = MaintenanceOccurrence.objects.create(
            plan=self.plan,
            asset=self.asset,
            scheduled_for=timezone.localdate() + timedelta(days=dans_combien_de_jours),
            status=status,
        )
        return occ

    def test_notifie_les_assignes_dune_occurrence_a_echeance_proche(self):
        occ = self._creer_occurrence(JOURS_ALERTE_ECHEANCE_MAINTENANCE)
        occ.assignees.add(self.marin)

        notify_maintenance_echeance_proche()

        notif = Notification.objects.get(user=self.marin)
        self.assertEqual(notif.level, NotificationLevel.WARNING)
        self.assertIn(str(self.asset), notif.verb)

    def test_aucune_notification_sans_assigne(self):
        occ = self._creer_occurrence(JOURS_ALERTE_ECHEANCE_MAINTENANCE)
        self.assertEqual(occ.assignees.count(), 0)

        notify_maintenance_echeance_proche()

        self.assertFalse(Notification.objects.exists())

    def test_aucune_notification_hors_fenetre(self):
        occ = self._creer_occurrence(JOURS_ALERTE_ECHEANCE_MAINTENANCE + 5)
        occ.assignees.add(self.marin)

        notify_maintenance_echeance_proche()

        self.assertFalse(Notification.objects.exists())

    def test_occurrence_deja_terminee_ignoree(self):
        occ = self._creer_occurrence(JOURS_ALERTE_ECHEANCE_MAINTENANCE, status="DONE")
        occ.assignees.add(self.marin)

        notify_maintenance_echeance_proche()

        self.assertFalse(Notification.objects.exists())

    def test_pas_de_doublon_si_tache_executee_plusieurs_fois(self):
        occ = self._creer_occurrence(JOURS_ALERTE_ECHEANCE_MAINTENANCE)
        occ.assignees.add(self.marin)

        notify_maintenance_echeance_proche()
        notify_maintenance_echeance_proche()

        self.assertEqual(Notification.objects.filter(user=self.marin).count(), 1)

    def test_referencee_dans_celery_beat_schedule(self):
        entry = settings.CELERY_BEAT_SCHEDULE.get("notify_maintenance_echeance_proche_daily")
        self.assertIsNotNone(entry, "Aucune entrée Celery Beat pour notify_maintenance_echeance_proche")
        self.assertEqual(entry["task"], "notifications.tasks.notify_maintenance_echeance_proche")
