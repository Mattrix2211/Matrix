from datetime import date, timedelta

from django.conf import settings
from django.contrib.auth.models import User
from django.test import TestCase

from accounts.models import Roles, UserProfile
from assets.models import (
    Installation,
    InstallationHourReading,
    InstallationIsolationReading,
    InstallationMaintenance,
    ModeDeclenchement,
)
from notifications.models import Notification, NotificationLevel
from notifications.tasks import detect_installation_drift
from org.models import Sector, Section, Service, Ship


class DetectInstallationDriftTests(TestCase):
    """Vérifie la détection de dérive sur les relevés techniques (isolement,
    heures de marche) avant le franchissement effectif du seuil : cf. tâche
    Notion [FEAT] Détecter une dérive sur les relevés techniques."""

    def setUp(self):
        self.ship = Ship.objects.create(name="Navire dérive", code="ND1")
        self.service = Service.objects.create(ship=self.ship, name="Service test")
        self.sector = Sector.objects.create(service=self.service, name="Secteur test")
        self.section = Section.objects.create(sector=self.sector, name="Section test")

        self.chef_service = User.objects.create_user(username="chef_service", password="pass")
        UserProfile.objects.filter(user=self.chef_service).update(
            role=Roles.CHEF_SERVICE, service=self.service
        )
        self.chef_secteur = User.objects.create_user(username="chef_secteur", password="pass")
        UserProfile.objects.filter(user=self.chef_secteur).update(
            role=Roles.CHEF_SECTEUR, sector=self.sector
        )

        # Chef d'un autre secteur : ne doit jamais être notifié (test de périmètre).
        autre_service = Service.objects.create(ship=self.ship, name="Autre service")
        autre_sector = Sector.objects.create(service=autre_service, name="Autre secteur")
        self.chef_hors_perimetre = User.objects.create_user(username="chef_hors_perimetre", password="pass")
        UserProfile.objects.filter(user=self.chef_hors_perimetre).update(
            role=Roles.CHEF_SECTEUR, sector=autre_sector
        )

        self.installation = Installation.objects.create(
            designation="Groupe électrogène",
            ship=self.ship,
            service=self.service,
            sector=self.sector,
            isolation_seuil_ohms=500_000,
        )

    def _ajoute_releves_isolement_en_baisse(self):
        depart = date(2026, 1, 1)
        for i in range(5):
            InstallationIsolationReading.objects.create(
                installation=self.installation,
                date=depart + timedelta(days=i),
                ohms=1_000_000 - i * 100_000,
            )

    def test_beat_schedule_reference_bien_la_tache(self):
        entry = settings.CELERY_BEAT_SCHEDULE.get("detect_installation_drift_daily")
        self.assertIsNotNone(entry, "Aucune entrée Celery Beat pour detect_installation_drift")
        self.assertEqual(entry["task"], "notifications.tasks.detect_installation_drift")

    def test_notification_creee_si_derive_isolement_detectee(self):
        self._ajoute_releves_isolement_en_baisse()

        detect_installation_drift()

        notif = Notification.objects.filter(user=self.chef_service, verb__icontains="isolement").first()
        self.assertIsNotNone(notif)
        self.assertIn("Groupe électrogène", notif.verb)
        self.assertIn("seuil estimé atteint dans", notif.verb)
        # Dérive détectée AVANT le franchissement réel : simple attention (WARNING),
        # pas encore une alerte critique (pas de push pour ce niveau).
        self.assertEqual(notif.level, NotificationLevel.WARNING)

    def test_aucune_notification_si_isolement_stable(self):
        depart = date(2026, 1, 1)
        for i in range(5):
            InstallationIsolationReading.objects.create(
                installation=self.installation, date=depart + timedelta(days=i), ohms=900_000,
            )

        detect_installation_drift()

        self.assertFalse(
            Notification.objects.filter(user=self.chef_service, verb__icontains="isolement").exists()
        )

    def test_aucune_notification_sans_seuil_configure(self):
        self.installation.isolation_seuil_ohms = None
        self.installation.save()
        self._ajoute_releves_isolement_en_baisse()

        detect_installation_drift()

        self.assertFalse(
            Notification.objects.filter(user=self.chef_service, verb__icontains="isolement").exists()
        )

    def test_pas_de_doublon_si_tache_relancee(self):
        self._ajoute_releves_isolement_en_baisse()

        detect_installation_drift()
        detect_installation_drift()

        self.assertEqual(
            Notification.objects.filter(user=self.chef_service, verb__icontains="isolement").count(), 1
        )

    def test_derive_resolue_puis_recreee(self):
        self._ajoute_releves_isolement_en_baisse()
        detect_installation_drift()
        self.assertTrue(
            Notification.objects.filter(
                user=self.chef_service, verb__icontains="isolement", is_read=False
            ).exists()
        )

        # L'isolement redevient stable/s'améliore : la dérive doit être résolue.
        InstallationIsolationReading.objects.create(
            installation=self.installation, date=date(2026, 1, 10), ohms=2_000_000,
        )
        InstallationIsolationReading.objects.create(
            installation=self.installation, date=date(2026, 1, 11), ohms=2_000_000,
        )
        detect_installation_drift()
        self.assertFalse(
            Notification.objects.filter(
                user=self.chef_service, verb__icontains="isolement", is_read=False
            ).exists(),
            "La dérive résolue doit être marquée lue",
        )

        # Nouvelle dérive : une nouvelle alerte active doit être recréée.
        depart = date(2026, 2, 1)
        for i in range(5):
            InstallationIsolationReading.objects.create(
                installation=self.installation, date=depart + timedelta(days=i), ohms=1_000_000 - i * 100_000,
            )
        detect_installation_drift()
        self.assertTrue(
            Notification.objects.filter(
                user=self.chef_service, verb__icontains="isolement", is_read=False
            ).exists(),
            "Une nouvelle dérive doit recréer une alerte active",
        )

    def test_seul_le_perimetre_de_l_installation_est_notifie(self):
        self._ajoute_releves_isolement_en_baisse()

        detect_installation_drift()

        for u in (self.chef_service, self.chef_secteur):
            self.assertTrue(
                Notification.objects.filter(user=u, verb__icontains="isolement").exists(),
                f"Notification attendue pour {u.username}",
            )
        self.assertFalse(
            Notification.objects.filter(user=self.chef_hors_perimetre, verb__icontains="isolement").exists(),
            "Un chef hors périmètre ne doit jamais être notifié",
        )

    def test_derive_detectee_sur_heures_de_marche_vers_seuil_entretien(self):
        maintenance = InstallationMaintenance.objects.create(
            installation=self.installation,
            periodicity="500h",
            title="Vidange moteur",
            mode_declenchement=ModeDeclenchement.COMPTEUR,
            seuil_heures=500,
            derniere_echeance_heures=0,
        )
        depart = date(2026, 1, 1)
        for i in range(5):
            InstallationHourReading.objects.create(
                installation=self.installation, date=depart + timedelta(days=i), hours=300 + i * 40,
            )

        detect_installation_drift()

        notif = Notification.objects.filter(user=self.chef_service, verb__icontains="Vidange moteur").first()
        self.assertIsNotNone(notif)
        self.assertIn("heures de marche", notif.verb)
        self.assertTrue(maintenance.pk)

    def test_aucune_notification_heures_si_seuil_deja_atteint(self):
        # Cas déjà couvert par generate_installation_maintenance_notifications
        # (échéance atteinte) : ne doit pas être redoublé ici par une dérive.
        InstallationMaintenance.objects.create(
            installation=self.installation,
            periodicity="500h",
            title="Vidange moteur",
            mode_declenchement=ModeDeclenchement.COMPTEUR,
            seuil_heures=500,
            derniere_echeance_heures=0,
        )
        depart = date(2026, 1, 1)
        for i in range(5):
            InstallationHourReading.objects.create(
                installation=self.installation, date=depart + timedelta(days=i), hours=500 + i * 40,
            )

        detect_installation_drift()

        self.assertFalse(
            Notification.objects.filter(user=self.chef_service, verb__icontains="Vidange moteur").exists()
        )
