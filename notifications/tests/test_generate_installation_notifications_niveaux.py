from datetime import timedelta

from django.contrib.auth.models import User
from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone

from accounts.models import UserProfile
from assets.models import Installation, InstallationVibrationReading
from notifications.models import Notification, NotificationLevel
from org.models import Sector, Service, Ship


class GenerateInstallationNotificationsNiveauxTests(TestCase):
    """Le niveau d'une notification d'échéance vibration/isolement dépend de si
    l'échéance est déjà dépassée (DANGER) ou à venir (WARNING)."""

    def setUp(self):
        self.user = User.objects.create_user(username="u1", password="pass")
        now = timezone.localtime(timezone.now()).time().replace(second=0, microsecond=0)
        UserProfile.objects.update_or_create(user=self.user, defaults={"notification_time": now})

        ship = Ship.objects.create(name="Navire test", code="NT2")
        service = Service.objects.create(ship=ship, name="Service test")
        sector = Sector.objects.create(service=service, name="Secteur test")
        self.installation = Installation.objects.create(
            designation="Propulseur", ship=ship, service=service, sector=sector, vib_days_a=10,
        )

    def test_echeance_vibration_deja_depassee_est_critique(self):
        InstallationVibrationReading.objects.create(
            installation=self.installation, date=timezone.localdate() - timedelta(days=20), state="A",
        )

        call_command("generate_installation_notifications")

        notif = Notification.objects.filter(user=self.user, verb__icontains="Vibration").first()
        self.assertIsNotNone(notif)
        self.assertEqual(notif.level, NotificationLevel.DANGER)

    def test_echeance_vibration_a_venir_est_une_simple_attention(self):
        InstallationVibrationReading.objects.create(
            installation=self.installation, date=timezone.localdate() - timedelta(days=5), state="A",
        )

        call_command("generate_installation_notifications")

        notif = Notification.objects.filter(user=self.user, verb__icontains="Vibration").first()
        self.assertIsNotNone(notif)
        self.assertEqual(notif.level, NotificationLevel.WARNING)
