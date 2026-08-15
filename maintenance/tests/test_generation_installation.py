from datetime import timedelta
from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone
from assets.models import (
    Installation,
    InstallationMaintenance,
    InstallationEvent,
    InstallationHourReading,
    ModeDeclenchement,
)
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

    def test_mode_les_deux_retient_echeance_la_plus_proche(self):
        """Mode "le premier des deux" : la branche calendaire (échéance dans 5 jours)
        et la branche compteur (seuil déjà atteint, donc échéance aujourd'hui) sont
        toutes deux éligibles. Une seule occurrence doit être créée, avec la date la
        plus proche des deux (aujourd'hui, côté compteur)."""
        maintenance = InstallationMaintenance.objects.create(
            installation=self.installation,
            periodicity="5 jours ou 500h",
            title="Contrôle mixte",
            mode_declenchement=ModeDeclenchement.LES_DEUX,
            intervalle=5,
            unite_intervalle="J",
            seuil_heures=500,
            derniere_echeance_heures=0,
        )
        # Branche calendaire : dernier événement aujourd'hui, prochaine échéance dans 5 jours.
        InstallationEvent.objects.create(
            installation=self.installation, label="Contrôle mixte", date=timezone.now()
        )
        # Branche compteur : seuil déjà dépassé, échéance constatée aujourd'hui.
        InstallationHourReading.objects.create(installation=self.installation, hours=520)

        call_command("generate_installation_occurrences")

        self.assertEqual(
            MaintenanceOccurrence.objects.filter(installation_maintenance=maintenance).count(), 1
        )
        occ = MaintenanceOccurrence.objects.get(installation_maintenance=maintenance)
        self.assertEqual(occ.scheduled_for, timezone.localdate())

    def test_mode_les_deux_aucune_generation_si_aucune_branche_eligible(self):
        """Mode "le premier des deux" : ni la branche calendaire (échéance trop
        lointaine, hors fenêtre de 90 jours) ni la branche compteur (seuil non
        atteint) ne sont éligibles. Aucune occurrence ne doit être créée."""
        InstallationMaintenance.objects.create(
            installation=self.installation,
            periodicity="200 jours ou 500h",
            title="Contrôle mixte lointain",
            mode_declenchement=ModeDeclenchement.LES_DEUX,
            intervalle=200,
            unite_intervalle="J",
            seuil_heures=500,
            derniere_echeance_heures=0,
        )
        InstallationEvent.objects.create(
            installation=self.installation, label="Contrôle mixte lointain", date=timezone.now()
        )
        InstallationHourReading.objects.create(installation=self.installation, hours=100)

        call_command("generate_installation_occurrences")

        self.assertFalse(MaintenanceOccurrence.objects.exists())
