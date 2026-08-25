"""Vérifie le digest calendrier quotidien « Ma journée »/« Ma journée de
demain » : notification résumée créée seulement si le marin a bien quelque
chose ce jour-là, à l'heure qu'il a choisie, sans doublon en cas d'exécutions
répétées."""
from datetime import time, timedelta

from django.conf import settings
from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone

from accounts.models import UserProfile
from assets.models import Asset, AssetType
from calendar_app.models import PersonalEvent
from maintenance.models import MaintenanceOccurrence, MaintenancePlan
from notifications.models import Notification
from notifications.tasks import notify_ma_journee, notify_ma_journee_demain
from org.models import Sector, Service, Ship
from training.models import TrainingCourse, TrainingSession


class MaJourneeTests(TestCase):
    def setUp(self):
        self.marin = User.objects.create_user(username="marin1", password="pass")
        # Aligne les deux préférences sur l'heure courante pour que les tâches déclenchent.
        now = timezone.localtime(timezone.now()).time().replace(second=0, microsecond=0)
        UserProfile.objects.update_or_create(
            user=self.marin,
            defaults={"notification_time": now, "notification_time_soir": now},
        )

        self.ship = Ship.objects.create(name="Navire test", code="NT5")
        self.service = Service.objects.create(ship=self.ship, name="Service test")
        self.sector = Sector.objects.create(service=self.service, name="Secteur test")
        self.asset_type = AssetType.objects.create(name="TypeA", category="Cat", sector=self.sector)
        self.asset = Asset.objects.create(
            asset_type=self.asset_type, ship=self.ship, service=self.service, sector=self.sector
        )
        self.plan = MaintenancePlan.objects.create(
            scope="ASSET", asset=self.asset, name="Plan A", every_n_days=30
        )
        self.today = timezone.localdate()
        self.tomorrow = self.today + timedelta(days=1)

    def test_pas_de_notification_si_journee_vide(self):
        notify_ma_journee()
        self.assertFalse(Notification.objects.filter(user=self.marin).exists())

    def test_ma_journee_resume_maintenance_assignee(self):
        occ = MaintenanceOccurrence.objects.create(
            plan=self.plan, asset=self.asset, scheduled_for=self.today, status="ASSIGNED"
        )
        occ.assignees.set([self.marin])

        notify_ma_journee()

        notif = Notification.objects.get(user=self.marin)
        self.assertIn("Ma journée", notif.verb)
        self.assertIn("1 maintenance(s)", notif.verb)
        self.assertIn(self.today.strftime("%d/%m/%Y"), notif.verb)

    def test_ma_journee_ignore_les_evenements_dun_autre_jour(self):
        MaintenanceOccurrence.objects.create(
            plan=self.plan, asset=self.asset, scheduled_for=self.tomorrow, status="ASSIGNED"
        ).assignees.set([self.marin])

        notify_ma_journee()

        self.assertFalse(Notification.objects.filter(user=self.marin).exists())

    def test_ma_journee_demain_resume_le_lendemain(self):
        course = TrainingCourse.objects.create(sector=self.sector, title="Sécurité incendie")
        session = TrainingSession.objects.create(
            course=course,
            scheduled_at=timezone.make_aware(
                timezone.datetime.combine(self.tomorrow, timezone.datetime.min.time().replace(hour=9))
            ),
        )
        session.attendees.set([self.marin])
        PersonalEvent.objects.create(
            owner=self.marin,
            title="Rappel personnel",
            starts_at=timezone.make_aware(
                timezone.datetime.combine(self.tomorrow, timezone.datetime.min.time().replace(hour=14))
            ),
        )

        notify_ma_journee_demain()

        notif = Notification.objects.get(user=self.marin)
        self.assertIn("Ma journée de demain", notif.verb)
        self.assertIn("1 formation(s)", notif.verb)
        self.assertIn("1 événement(s) personnel(s)", notif.verb)
        self.assertIn(self.tomorrow.strftime("%d/%m/%Y"), notif.verb)

    def test_pas_de_doublon_meme_execution_multiple_meme_jour(self):
        MaintenanceOccurrence.objects.create(
            plan=self.plan, asset=self.asset, scheduled_for=self.today, status="ASSIGNED"
        ).assignees.set([self.marin])

        notify_ma_journee()
        notify_ma_journee()

        self.assertEqual(Notification.objects.filter(user=self.marin).count(), 1)

    def test_aucune_notification_hors_de_lheure_choisie(self):
        now = timezone.localtime(timezone.now()).time()
        autre_heure = time((now.hour + 2) % 24, now.minute)
        UserProfile.objects.filter(user=self.marin).update(notification_time=autre_heure)
        MaintenanceOccurrence.objects.create(
            plan=self.plan, asset=self.asset, scheduled_for=self.today, status="ASSIGNED"
        ).assignees.set([self.marin])

        notify_ma_journee()

        self.assertFalse(Notification.objects.filter(user=self.marin).exists())

    def test_taches_referencees_dans_celery_beat_schedule(self):
        entry_matin = settings.CELERY_BEAT_SCHEDULE.get("notify_ma_journee_minute")
        entry_soir = settings.CELERY_BEAT_SCHEDULE.get("notify_ma_journee_demain_minute")
        self.assertIsNotNone(entry_matin, "Aucune entrée Celery Beat pour notify_ma_journee")
        self.assertIsNotNone(entry_soir, "Aucune entrée Celery Beat pour notify_ma_journee_demain")
        self.assertEqual(entry_matin["task"], "notifications.tasks.notify_ma_journee")
        self.assertEqual(entry_soir["task"], "notifications.tasks.notify_ma_journee_demain")
