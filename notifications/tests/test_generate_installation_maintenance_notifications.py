from datetime import timedelta
from django.contrib.auth.models import User
from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone
from accounts.models import UserProfile
from assets.models import Installation, InstallationMaintenance, InstallationHourReading, ModeDeclenchement
from notifications.models import Notification
from org.models import Ship, Service, Sector


class GenerateInstallationMaintenanceNotificationsTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="u1", password="pass")
        # Aligne la préférence de notification sur l'heure courante pour que la commande déclenche.
        now = timezone.localtime(timezone.now()).time().replace(second=0, microsecond=0)
        UserProfile.objects.update_or_create(user=self.user, defaults={"notification_time": now})

        ship = Ship.objects.create(name="Navire test", code="NT1")
        service = Service.objects.create(ship=ship, name="Service test")
        sector = Sector.objects.create(service=service, name="Secteur test")
        self.installation = Installation.objects.create(
            designation="Pompe test", ship=ship, service=service, sector=sector,
        )

    def test_notification_branche_compteur(self):
        maintenance = InstallationMaintenance.objects.create(
            installation=self.installation,
            periodicity="500h",
            title="Vidange",
            mode_declenchement=ModeDeclenchement.COMPTEUR,
            seuil_heures=500,
            derniere_echeance_heures=0,
        )
        InstallationHourReading.objects.create(installation=self.installation, hours=520)

        call_command("generate_installation_maintenance_notifications")

        self.assertTrue(
            Notification.objects.filter(user=self.user, verb__icontains="Vidange").exists()
        )
        self.assertTrue(maintenance.pk)

    def test_notification_branche_calendrier(self):
        InstallationMaintenance.objects.create(
            installation=self.installation,
            periodicity="1 mois",
            title="Graissage",
            mode_declenchement=ModeDeclenchement.CALENDRIER,
            intervalle=1,
            unite_intervalle="M",
        )
        # Aucun InstallationEvent : la base de calcul est la date de création (aujourd'hui),
        # donc pas d'échéance dans la fenêtre par défaut de 7 jours.
        call_command("generate_installation_maintenance_notifications")
        self.assertFalse(
            Notification.objects.filter(user=self.user, verb__icontains="Graissage").exists()
        )

    def test_pas_de_notification_si_seuil_non_atteint(self):
        InstallationMaintenance.objects.create(
            installation=self.installation,
            periodicity="500h",
            title="Contrôle filtre",
            mode_declenchement=ModeDeclenchement.COMPTEUR,
            seuil_heures=500,
            derniere_echeance_heures=0,
        )
        InstallationHourReading.objects.create(installation=self.installation, hours=100)

        call_command("generate_installation_maintenance_notifications")

        self.assertFalse(
            Notification.objects.filter(user=self.user, verb__icontains="Contrôle filtre").exists()
        )
