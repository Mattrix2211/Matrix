"""Tests du service de bilan PDF — Mode Période (T9).

Suit le même schéma de scoping/périmètre que le Mode Instantané (test_services.py, T8) :
un chef de secteur ne peut générer le bilan que de son propre secteur.
"""
import unittest
from datetime import datetime, timedelta

from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone

from accounts.models import UserProfile
from assets.models import (
    Asset,
    AssetType,
    Installation,
    InstallationHourReading,
    InstallationIsolationReading,
    InstallationMaintenance,
    InstallationVibrationReading,
    ModeDeclenchement,
)
from logistics.models import CorrectiveTicket, PartLineItem, PartRequest
from maintenance.models import MaintenanceExecution, MaintenanceOccurrence
from org.models import Sector, Service, Ship
from reports.services import (
    PerimetreNonAutorise,
    construire_contexte_periode,
    generer_bilan_periode_pdf,
    pdf_disponible,
)
from training.models import TrainingCourse, TrainingRecord


class BilanPeriodeTests(TestCase):
    def setUp(self):
        self.navire = Ship.objects.create(name="Navire T9", code="T9")
        self.service = Service.objects.create(ship=self.navire, name="Service T9")
        self.secteur = Sector.objects.create(service=self.service, name="Secteur T9")
        # Un secteur "voisin", hors périmètre du chef de secteur testé.
        self.autre_secteur = Sector.objects.create(service=self.service, name="Autre secteur")

        self.chef = User.objects.create_user(username="chef", password="pass")
        UserProfile.objects.filter(user=self.chef).update(
            role="CHEF_SECTEUR", sector=self.secteur
        )
        self.chef.refresh_from_db()

        self.installation = Installation.objects.create(
            designation="Pompe principale",
            ship=self.navire,
            service=self.service,
            sector=self.secteur,
        )
        self.installation_hors_perimetre = Installation.objects.create(
            designation="Pompe voisine",
            ship=self.navire,
            service=self.service,
            sector=self.autre_secteur,
        )

        self.date_debut = timezone.localdate() - timedelta(days=30)
        self.date_fin = timezone.localdate()

    def _creer_maintenance(self, installation):
        return InstallationMaintenance.objects.create(
            installation=installation,
            periodicity="1 mois",
            title="Graissage",
            mode_declenchement=ModeDeclenchement.CALENDRIER,
            intervalle=1,
            unite_intervalle="M",
        )

    def test_perimetre_non_autorise_leve_une_erreur(self):
        with self.assertRaises(PerimetreNonAutorise):
            construire_contexte_periode(
                "sector", self.autre_secteur.id, self.chef, self.date_debut, self.date_fin
            )

    def test_date_debut_apres_date_fin_leve_une_erreur(self):
        with self.assertRaises(ValueError):
            construire_contexte_periode(
                "sector", self.secteur.id, self.chef, self.date_fin, self.date_debut
            )

    def test_aucune_donnee_sur_la_periode(self):
        contexte = construire_contexte_periode(
            "sector", self.secteur.id, self.chef, self.date_debut, self.date_fin
        )

        self.assertEqual(contexte["nb_maintenances_planifiees"], 0)
        self.assertIsNone(contexte["taux_conformite"])
        self.assertEqual(contexte["tickets_ouverts_periode"], [])
        self.assertEqual(contexte["tickets_fermes_periode"], [])
        self.assertIsNone(contexte["delai_moyen_resolution"])
        self.assertEqual(contexte["releves_heures"], [])
        self.assertEqual(contexte["pieces_consommees"], [])
        self.assertEqual(contexte["qualifications_obtenues"], [])

    def test_taux_conformite_maintenance(self):
        maintenance = self._creer_maintenance(self.installation)

        # Réalisée à temps : exécution achevée la veille de la date prévue.
        date_prevue_a_temps = self.date_debut + timedelta(days=5)
        occ_a_temps = MaintenanceOccurrence.objects.create(
            installation_maintenance=maintenance,
            scheduled_for=date_prevue_a_temps,
            status="DONE",
        )
        MaintenanceExecution.objects.create(
            occurrence=occ_a_temps,
            completed_at=timezone.make_aware(
                datetime.combine(date_prevue_a_temps - timedelta(days=1), datetime.min.time())
            ),
            conformity="CONFORME",
        )

        # Réalisée en retard : exécution achevée après la date prévue.
        date_prevue_en_retard = self.date_debut + timedelta(days=10)
        occ_en_retard = MaintenanceOccurrence.objects.create(
            installation_maintenance=maintenance,
            scheduled_for=date_prevue_en_retard,
            status="DONE",
        )
        MaintenanceExecution.objects.create(
            occurrence=occ_en_retard,
            completed_at=timezone.make_aware(
                datetime.combine(date_prevue_en_retard + timedelta(days=3), datetime.min.time())
            ),
            conformity="CONFORME",
        )

        # Annulée : exclue du décompte.
        MaintenanceOccurrence.objects.create(
            installation_maintenance=maintenance,
            scheduled_for=self.date_debut + timedelta(days=15),
            status="CANCELLED",
        )

        contexte = construire_contexte_periode(
            "sector", self.secteur.id, self.chef, self.date_debut, self.date_fin
        )

        self.assertEqual(contexte["nb_maintenances_planifiees"], 2)
        self.assertEqual(contexte["nb_maintenances_realisees_a_temps"], 1)
        self.assertEqual(contexte["taux_conformite"], 50.0)

    def test_maintenance_hors_perimetre_exclue(self):
        maintenance_voisine = self._creer_maintenance(self.installation_hors_perimetre)
        MaintenanceOccurrence.objects.create(
            installation_maintenance=maintenance_voisine,
            scheduled_for=self.date_debut + timedelta(days=5),
            status="DONE",
        )

        contexte = construire_contexte_periode(
            "sector", self.secteur.id, self.chef, self.date_debut, self.date_fin
        )

        self.assertEqual(contexte["nb_maintenances_planifiees"], 0)

    def test_tickets_periode_a_cheval_sur_un_changement_de_statut(self):
        asset_type = AssetType.objects.create(name="Extincteur", category="Sécu", sector=self.secteur)
        asset = Asset.objects.create(
            asset_type=asset_type, ship=self.navire, service=self.service, sector=self.secteur,
        )

        # Ouvert avant la période, toujours ouvert à la fin de la période : ne
        # compte ni comme "ouvert" ni comme "fermé" sur la fenêtre, mais apparaît
        # dans les tickets encore ouverts en fin de période.
        ticket_ancien_toujours_ouvert = CorrectiveTicket.objects.create(
            asset=asset,
            description="Fuite ancienne",
            status="REPORTED",
            reported_at=timezone.now() - timedelta(days=60),
        )

        # Ouvert avant la période, fermé pendant la période.
        ticket_ferme_pendant = CorrectiveTicket.objects.create(
            asset=asset,
            description="Panne résolue",
            status="REPORTED",
            reported_at=timezone.now() - timedelta(days=45),
        )
        CorrectiveTicket.objects.filter(pk=ticket_ferme_pendant.pk).update(
            status="CLOSED",
            updated_at=timezone.now() - timedelta(days=10),
        )

        # Ouvert pendant la période, toujours ouvert.
        ticket_ouvert_pendant = CorrectiveTicket.objects.create(
            asset=asset,
            description="Nouveau signalement",
            status="REPORTED",
            reported_at=timezone.now() - timedelta(days=5),
        )

        contexte = construire_contexte_periode(
            "sector", self.secteur.id, self.chef, self.date_debut, self.date_fin
        )

        ids_ouverts_periode = {t.id for t in contexte["tickets_ouverts_periode"]}
        ids_fermes_periode = {t.id for t in contexte["tickets_fermes_periode"]}
        ids_encore_ouverts = {t.id for t in contexte["tickets_encore_ouverts_fin_periode"]}

        self.assertEqual(ids_ouverts_periode, {ticket_ouvert_pendant.id})
        self.assertEqual(ids_fermes_periode, {ticket_ferme_pendant.id})
        self.assertEqual(
            ids_encore_ouverts, {ticket_ancien_toujours_ouvert.id, ticket_ouvert_pendant.id}
        )
        self.assertEqual(contexte["delai_moyen_resolution"], 35.0)

    def test_releves_scopes_sur_la_periode(self):
        InstallationHourReading.objects.create(
            installation=self.installation,
            date=self.date_debut + timedelta(days=1),
            hours=100,
        )
        # Hors fenêtre : ne doit pas apparaître.
        InstallationHourReading.objects.create(
            installation=self.installation,
            date=self.date_debut - timedelta(days=5),
            hours=90,
        )
        InstallationVibrationReading.objects.create(
            installation=self.installation, date=self.date_debut + timedelta(days=2), state="B"
        )
        InstallationIsolationReading.objects.create(
            installation=self.installation, date=self.date_debut + timedelta(days=3), ohms=500
        )
        # Relevé hors périmètre.
        InstallationHourReading.objects.create(
            installation=self.installation_hors_perimetre,
            date=self.date_debut + timedelta(days=1),
            hours=200,
        )

        contexte = construire_contexte_periode(
            "sector", self.secteur.id, self.chef, self.date_debut, self.date_fin
        )

        self.assertEqual(len(contexte["releves_heures"]), 1)
        self.assertEqual(contexte["releves_heures"][0].hours, 100)
        self.assertEqual(len(contexte["releves_vibration"]), 1)
        self.assertEqual(len(contexte["releves_isolement"]), 1)

    def test_pieces_consommees_sur_la_periode(self):
        asset_type = AssetType.objects.create(name="Extincteur", category="Sécu", sector=self.secteur)
        asset = Asset.objects.create(
            asset_type=asset_type, ship=self.navire, service=self.service, sector=self.secteur,
        )
        ticket = CorrectiveTicket.objects.create(asset=asset, description="Panne", status="IN_REPAIR")
        demande = PartRequest.objects.create(ticket=ticket)
        piece_consommee = PartLineItem.objects.create(
            part_request=demande,
            reference="REF-001",
            description="Joint torique",
            status="CONSUMED",
            received_at=self.date_debut + timedelta(days=2),
        )
        # Pas encore consommée : exclue.
        PartLineItem.objects.create(
            part_request=demande,
            reference="REF-002",
            description="Filtre",
            status="RECEIVED",
            received_at=self.date_debut + timedelta(days=2),
        )

        contexte = construire_contexte_periode(
            "sector", self.secteur.id, self.chef, self.date_debut, self.date_fin
        )

        self.assertEqual(len(contexte["pieces_consommees"]), 1)
        self.assertEqual(contexte["pieces_consommees"][0].id, piece_consommee.id)

    def test_qualifications_obtenues_et_expirees_sur_la_periode(self):
        equipier = User.objects.create_user(username="marin", password="pass")
        UserProfile.objects.filter(user=equipier).update(sector=self.secteur)
        equipier_hors_perimetre = User.objects.create_user(username="marin2", password="pass")
        UserProfile.objects.filter(user=equipier_hors_perimetre).update(
            sector=self.autre_secteur
        )

        cours = TrainingCourse.objects.create(title="Sécurité incendie")
        qualification_obtenue = TrainingRecord.objects.create(
            user=equipier, course=cours,
            completed_at=self.date_debut + timedelta(days=3),
            expires_at=self.date_fin + timedelta(days=300),
        )
        qualification_expiree = TrainingRecord.objects.create(
            user=equipier, course=cours,
            completed_at=self.date_debut - timedelta(days=300),
            expires_at=self.date_debut + timedelta(days=10),
        )
        # Hors périmètre : exclue malgré des dates dans la fenêtre.
        TrainingRecord.objects.create(
            user=equipier_hors_perimetre, course=cours,
            completed_at=self.date_debut + timedelta(days=3),
            expires_at=self.date_fin + timedelta(days=300),
        )

        contexte = construire_contexte_periode(
            "sector", self.secteur.id, self.chef, self.date_debut, self.date_fin
        )

        self.assertEqual(len(contexte["qualifications_obtenues"]), 1)
        self.assertEqual(contexte["qualifications_obtenues"][0].id, qualification_obtenue.id)
        self.assertEqual(len(contexte["qualifications_expirees"]), 1)
        self.assertEqual(contexte["qualifications_expirees"][0].id, qualification_expiree.id)

    @unittest.skipUnless(pdf_disponible(), "WeasyPrint indisponible sur cette machine")
    def test_generation_pdf_periode(self):
        pdf = generer_bilan_periode_pdf(
            "sector", self.secteur.id, self.chef, self.date_debut, self.date_fin
        )
        self.assertTrue(pdf.startswith(b"%PDF"))
