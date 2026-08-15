from datetime import timedelta
from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone
from assets.models import Installation, InstallationMaintenance, InstallationHourReading, ModeDeclenchement
from maintenance.models import MaintenanceOccurrence
from org.models import Ship, Service, Sector


class GenerateInstallationOccurrencesTests(TestCase):
    """Vérifie la génération des occurrences de maintenance pour les installations
    fixes, en réutilisant le même style que OccurrenceGenerationTests (matériel
    mobile) et GenerateInstallationMaintenanceNotificationsTests (détection d'échéance)."""

    def setUp(self):
        ship = Ship.objects.create(name="Navire test", code="NT2")
        service = Service.objects.create(ship=ship, name="Service test")
        sector = Sector.objects.create(service=service, name="Secteur test")
        self.installation = Installation.objects.create(
            designation="Pompe test", ship=ship, service=service, sector=sector,
        )

    def test_generation_branche_calendrier(self):
        maintenance = InstallationMaintenance.objects.create(
            installation=self.installation,
            periodicity="1 mois",
            title="Graissage",
            mode_declenchement=ModeDeclenchement.CALENDRIER,
            intervalle=1,
            unite_intervalle="M",
        )
        # Aucun InstallationEvent : la base de calcul est la date de création
        # (aujourd'hui), donc l'échéance dans 1 mois entre bien dans la fenêtre de 90 jours.
        call_command("generate_installation_occurrences")

        occ = MaintenanceOccurrence.objects.get(installation_maintenance=maintenance)
        self.assertEqual(occ.status, "PLANNED")
        self.assertIsNone(occ.plan)
        self.assertIsNone(occ.asset)

    def test_generation_branche_compteur(self):
        maintenance = InstallationMaintenance.objects.create(
            installation=self.installation,
            periodicity="500h",
            title="Vidange",
            mode_declenchement=ModeDeclenchement.COMPTEUR,
            seuil_heures=500,
            derniere_echeance_heures=0,
        )
        InstallationHourReading.objects.create(installation=self.installation, hours=520)

        call_command("generate_installation_occurrences")

        occ = MaintenanceOccurrence.objects.get(installation_maintenance=maintenance)
        self.assertEqual(occ.status, "PLANNED")
        self.assertEqual(occ.scheduled_for, timezone.localdate())

    def test_pas_de_generation_si_seuil_non_atteint(self):
        InstallationMaintenance.objects.create(
            installation=self.installation,
            periodicity="500h",
            title="Contrôle filtre",
            mode_declenchement=ModeDeclenchement.COMPTEUR,
            seuil_heures=500,
            derniere_echeance_heures=0,
        )
        InstallationHourReading.objects.create(installation=self.installation, hours=100)

        call_command("generate_installation_occurrences")

        self.assertFalse(MaintenanceOccurrence.objects.exists())

    def test_pas_de_doublon_si_occurrence_deja_en_cours(self):
        maintenance = InstallationMaintenance.objects.create(
            installation=self.installation,
            periodicity="500h",
            title="Vidange",
            mode_declenchement=ModeDeclenchement.COMPTEUR,
            seuil_heures=500,
            derniere_echeance_heures=0,
        )
        InstallationHourReading.objects.create(installation=self.installation, hours=520)

        call_command("generate_installation_occurrences")
        call_command("generate_installation_occurrences")

        self.assertEqual(
            MaintenanceOccurrence.objects.filter(installation_maintenance=maintenance).count(), 1
        )

    def test_occurrence_terminee_permet_une_nouvelle_generation(self):
        maintenance = InstallationMaintenance.objects.create(
            installation=self.installation,
            periodicity="500h",
            title="Vidange",
            mode_declenchement=ModeDeclenchement.COMPTEUR,
            seuil_heures=500,
            derniere_echeance_heures=0,
        )
        InstallationHourReading.objects.create(installation=self.installation, hours=520)

        MaintenanceOccurrence.objects.create(
            installation_maintenance=maintenance,
            scheduled_for=timezone.localdate() - timedelta(days=1),
            status="DONE",
        )

        call_command("generate_installation_occurrences")

        self.assertEqual(
            MaintenanceOccurrence.objects.filter(installation_maintenance=maintenance).count(), 2
        )
