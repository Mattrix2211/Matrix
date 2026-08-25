from datetime import time, timedelta
from unittest.mock import patch

from celery.schedules import crontab
from django.conf import settings
from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone
from accounts.models import UserProfile
from assets.models import (
    Installation,
    InstallationHourReading,
    InstallationMaintenance,
    InstallationVibrationReading,
    ModeDeclenchement,
)
from notifications.models import Notification
from notifications.tasks import generate_installation_maintenance_notifications, generate_installation_notifications
from org.models import Sector, Service, Ship


class CeleryBeatInstallationNotificationsTests(TestCase):
    """Vérifie que les notifications d'échéances vibration/isolement et d'entretien
    des installations fixes sont bien planifiées dans Celery Beat, et que la tâche
    Celery produit le même résultat que la commande qu'elle enveloppe."""

    def setUp(self):
        self.user = User.objects.create_user(username="marin1", password="pass")
        # Aligne la préférence de notification sur l'heure courante pour que la tâche déclenche.
        now = timezone.localtime(timezone.now()).time().replace(second=0, microsecond=0)
        UserProfile.objects.update_or_create(user=self.user, defaults={"notification_time": now})

        ship = Ship.objects.create(name="Navire test", code="NT4")
        service = Service.objects.create(ship=ship, name="Service test")
        sector = Sector.objects.create(service=service, name="Secteur test")
        self.installation = Installation.objects.create(
            designation="Pompe test", ship=ship, service=service, sector=sector,
        )

    def test_generate_installation_notifications_referencee_dans_celery_beat_schedule(self):
        entry = settings.CELERY_BEAT_SCHEDULE.get("generate_installation_notifications_daily")
        self.assertIsNotNone(entry, "Aucune entrée Celery Beat pour generate_installation_notifications")
        self.assertEqual(entry["task"], "notifications.tasks.generate_installation_notifications")

    def test_generate_installation_maintenance_notifications_referencee_dans_celery_beat_schedule(self):
        entry = settings.CELERY_BEAT_SCHEDULE.get("generate_installation_maintenance_notifications_daily")
        self.assertIsNotNone(entry, "Aucune entrée Celery Beat pour generate_installation_maintenance_notifications")
        self.assertEqual(entry["task"], "notifications.tasks.generate_installation_maintenance_notifications")

    def test_planification_toutes_les_minutes_pour_respecter_lheure_choisie_par_chaque_marin(self):
        """Les deux tâches comparent en interne l'heure courante à la préférence
        de CHAQUE marin (UserProfile.notification_time). Un horaire fixe unique
        (ex: crontab(hour=8, minute=0)) ne déclenche la tâche qu'une fois par
        jour et ne notifie donc que les marins ayant gardé la préférence par
        défaut (08:00) : tout marin ayant personnalisé son horaire n'était
        jamais notifié. La planification doit donc être toutes les minutes,
        comme pour notify_ma_journee_minute."""
        entry_echeances = settings.CELERY_BEAT_SCHEDULE.get("generate_installation_notifications_daily")
        entry_entretien = settings.CELERY_BEAT_SCHEDULE.get("generate_installation_maintenance_notifications_daily")
        self.assertEqual(entry_echeances["schedule"], crontab(minute="*"))
        self.assertEqual(entry_entretien["schedule"], crontab(minute="*"))

    def test_marin_avec_horaire_personnalise_different_de_08h00_est_bien_notifie(self):
        """Reproduit le scénario du bug: avant le correctif, seule l'exécution
        fixe à 08:00 déclenchait la tâche, donc un marin ayant personnalisé son
        horaire (ici volontairement différent de 08:00) n'était jamais notifié.
        On simule l'heure d'exécution de la tâche (03:17) plutôt que l'heure
        réelle de la machine de test, pour ne pas dépendre du moment où les
        tests tournent."""
        UserProfile.objects.filter(user=self.user).update(notification_time=time(3, 17))
        InstallationVibrationReading.objects.create(
            installation=self.installation,
            date=timezone.localdate() - timedelta(days=25),
            state="C",
        )
        heure_execution = timezone.localtime().replace(hour=3, minute=17, second=0, microsecond=0)

        with patch("django.utils.timezone.localtime", return_value=heure_execution):
            generate_installation_notifications()

        self.assertTrue(
            Notification.objects.filter(user=self.user, verb__icontains="Vibration").exists()
        )

    def test_tache_maintenance_notifications_genere_bien_une_alerte(self):
        maintenance = InstallationMaintenance.objects.create(
            installation=self.installation,
            periodicity="500h",
            title="Vidange",
            mode_declenchement=ModeDeclenchement.COMPTEUR,
            seuil_heures=500,
            derniere_echeance_heures=0,
        )
        InstallationHourReading.objects.create(installation=self.installation, hours=520)

        generate_installation_maintenance_notifications()

        self.assertTrue(
            Notification.objects.filter(user=self.user, verb__icontains="Vidange").exists()
        )
        self.assertTrue(maintenance.pk)

    def test_tache_vibration_isolement_genere_bien_une_alerte(self):
        # État "C" : échéance à 30 jours, mesure vieille de 25 jours -> échéance dans 5 jours (< fenêtre de 7 j).
        InstallationVibrationReading.objects.create(
            installation=self.installation,
            date=timezone.localdate() - timedelta(days=25),
            state="C",
        )

        generate_installation_notifications()

        self.assertTrue(
            Notification.objects.filter(user=self.user, verb__icontains="Vibration").exists()
        )

    def test_pas_de_doublon_meme_execution_multiple_meme_jour(self):
        """Le déduplicateur en mémoire (remplaçant le .exists() par combinaison
        installation x utilisateur) ne doit pas laisser passer de doublon si la tâche
        est exécutée plusieurs fois le même jour."""
        InstallationMaintenance.objects.create(
            installation=self.installation,
            periodicity="500h",
            title="Vidange",
            mode_declenchement=ModeDeclenchement.COMPTEUR,
            seuil_heures=500,
            derniere_echeance_heures=0,
        )
        InstallationHourReading.objects.create(installation=self.installation, hours=520)

        generate_installation_maintenance_notifications()
        generate_installation_maintenance_notifications()

        self.assertEqual(
            Notification.objects.filter(user=self.user, verb__icontains="Vidange").count(), 1
        )
