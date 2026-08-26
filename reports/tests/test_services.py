"""Tests du service de bilan PDF — Mode Instantané (T8 + section stock T11).

Le Mode Période (dates) est testé séparément dans test_services_periode.py (T9).
"""
import unittest
from datetime import timedelta

from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone

from accounts.models import UserProfile
from assets.models import (
    Installation,
    InstallationHourReading,
    InstallationIsolationReading,
    InstallationMaintenance,
    InstallationVibrationReading,
    ModeDeclenchement,
    Asset,
    AssetType,
)
from logistics.models import CorrectiveTicket, StockPiece
from maintenance.models import MaintenanceOccurrence
from org.models import Sector, Service, Ship
from reports.services import (
    PerimetreNonAutorise,
    construire_contexte_instantane,
    generer_bilan_instantane_pdf,
    pdf_disponible,
)
from training.models import TrainingCourse, TrainingRecord


class BilanInstantaneTests(TestCase):
    def setUp(self):
        self.navire = Ship.objects.create(name="Navire T8", code="T8")
        self.service = Service.objects.create(ship=self.navire, name="Service T8")
        self.secteur = Sector.objects.create(service=self.service, name="Secteur T8")
        # Un secteur "voisin", hors périmètre du chef de secteur testé.
        self.autre_secteur = Sector.objects.create(service=self.service, name="Autre secteur")

        self.chef = User.objects.create_user(username="chef", password="pass")
        UserProfile.objects.filter(user=self.chef).update(
            role="CHEF_SECTEUR", sector=self.secteur
        )
        # Invalide le cache de la relation profile déjà chargée par le signal de
        # création automatique, pour que la lecture suivante voie le secteur affecté.
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

    def test_perimetre_non_autorise_leve_une_erreur(self):
        with self.assertRaises(PerimetreNonAutorise):
            construire_contexte_instantane("sector", self.autre_secteur.id, self.chef)

    def test_contexte_ne_contient_que_le_perimetre_du_secteur(self):
        InstallationHourReading.objects.create(
            installation=self.installation, hours=120, is_visit=True
        )
        InstallationHourReading.objects.create(
            installation=self.installation_hors_perimetre, hours=999, is_visit=True
        )

        contexte = construire_contexte_instantane("sector", self.secteur.id, self.chef)

        designations = [ligne["installation"].designation for ligne in contexte["installations"]]
        self.assertIn("Pompe principale", designations)
        self.assertNotIn("Pompe voisine", designations)

    def test_derniers_releves_et_derniere_visite(self):
        InstallationHourReading.objects.create(
            installation=self.installation, date=timezone.localdate() - timedelta(days=10),
            hours=100, is_visit=True,
        )
        InstallationHourReading.objects.create(
            installation=self.installation, date=timezone.localdate(), hours=150, is_visit=False
        )
        InstallationVibrationReading.objects.create(installation=self.installation, state="B")
        InstallationIsolationReading.objects.create(installation=self.installation, ohms=500)

        contexte = construire_contexte_instantane("sector", self.secteur.id, self.chef)
        ligne = next(
            l for l in contexte["installations"] if l["installation"] == self.installation
        )

        self.assertEqual(ligne["dernier_releve_heures"].hours, 150)
        self.assertEqual(ligne["derniere_visite"].hours, 100)
        self.assertEqual(ligne["dernier_releve_vibration"].state, "B")
        self.assertEqual(ligne["dernier_releve_isolement"].ohms, 500)

    def test_echeance_en_retard_marque_installation_en_retard(self):
        maintenance = InstallationMaintenance.objects.create(
            installation=self.installation,
            periodicity="1 mois",
            title="Graissage",
            mode_declenchement=ModeDeclenchement.CALENDRIER,
            intervalle=1,
            unite_intervalle="M",
        )
        MaintenanceOccurrence.objects.create(
            installation_maintenance=maintenance,
            scheduled_for=timezone.localdate() - timedelta(days=3),
            status="OVERDUE",
        )

        contexte = construire_contexte_instantane("sector", self.secteur.id, self.chef)

        ligne = next(
            l for l in contexte["installations"] if l["installation"] == self.installation
        )
        self.assertEqual(ligne["statut"], "En retard")
        self.assertEqual(len(contexte["echeances"]), 1)
        self.assertTrue(contexte["echeances"][0]["en_retard"])

    def test_echeance_terminee_exclue(self):
        maintenance = InstallationMaintenance.objects.create(
            installation=self.installation,
            periodicity="1 mois",
            title="Graissage",
            mode_declenchement=ModeDeclenchement.CALENDRIER,
            intervalle=1,
            unite_intervalle="M",
        )
        MaintenanceOccurrence.objects.create(
            installation_maintenance=maintenance,
            scheduled_for=timezone.localdate() - timedelta(days=3),
            status="DONE",
        )

        contexte = construire_contexte_instantane("sector", self.secteur.id, self.chef)

        self.assertEqual(contexte["echeances"], [])
        ligne = next(
            l for l in contexte["installations"] if l["installation"] == self.installation
        )
        self.assertEqual(ligne["statut"], "À jour")

    def test_tickets_ouverts_scopes_et_fermes_exclus(self):
        asset_type = AssetType.objects.create(name="Extincteur", category="Sécu", sector=self.secteur)
        asset = Asset.objects.create(
            asset_type=asset_type, ship=self.navire, service=self.service, sector=self.secteur,
        )
        asset_hors_perimetre = Asset.objects.create(
            asset_type=AssetType.objects.create(
                name="Extincteur2", category="Sécu", sector=self.autre_secteur
            ),
            ship=self.navire, service=self.service, sector=self.autre_secteur,
        )
        ticket_ouvert = CorrectiveTicket.objects.create(
            asset=asset, description="Fuite détectée", status="REPORTED"
        )
        CorrectiveTicket.objects.create(asset=asset, description="Déjà résolu", status="CLOSED")
        CorrectiveTicket.objects.create(
            asset=asset_hors_perimetre, description="Hors périmètre", status="REPORTED"
        )

        contexte = construire_contexte_instantane("sector", self.secteur.id, self.chef)

        self.assertEqual(len(contexte["tickets_ouverts"]), 1)
        self.assertEqual(contexte["tickets_ouverts"][0].id, ticket_ouvert.id)
        self.assertGreaterEqual(contexte["tickets_ouverts"][0].anciennete_jours, 0)

    def test_qualifications_proches_expiration_scopees_par_profil_marin(self):
        equipier = User.objects.create_user(username="marin", password="pass")
        UserProfile.objects.filter(user=equipier).update(sector=self.secteur)
        equipier_hors_perimetre = User.objects.create_user(username="marin2", password="pass")
        UserProfile.objects.filter(user=equipier_hors_perimetre).update(
            sector=self.autre_secteur
        )

        cours = TrainingCourse.objects.create(title="Sécurité incendie")
        TrainingRecord.objects.create(
            user=equipier, course=cours,
            completed_at=timezone.localdate() - timedelta(days=300),
            expires_at=timezone.localdate() + timedelta(days=30),
        )
        # Hors fenêtre d'alerte (trop lointain).
        TrainingRecord.objects.create(
            user=equipier, course=cours,
            completed_at=timezone.localdate(),
            expires_at=timezone.localdate() + timedelta(days=300),
        )
        # Bonne échéance mais hors périmètre.
        TrainingRecord.objects.create(
            user=equipier_hors_perimetre, course=cours,
            completed_at=timezone.localdate() - timedelta(days=300),
            expires_at=timezone.localdate() + timedelta(days=30),
        )

        contexte = construire_contexte_instantane("sector", self.secteur.id, self.chef)

        self.assertEqual(len(contexte["qualifications_proches_expiration"]), 1)
        self.assertEqual(contexte["qualifications_proches_expiration"][0].user, equipier)

    def test_stock_sous_seuil_scope_et_stock_suffisant_exclu(self):
        piece_sous_seuil = StockPiece.objects.create(
            reference="REF-001", designation="Joint torique", quantite=1, quantite_minimale=5,
            ship=self.navire, service=self.service, sector=self.secteur,
        )
        StockPiece.objects.create(
            reference="REF-002", designation="Roulement", quantite=10, quantite_minimale=5,
            ship=self.navire, service=self.service, sector=self.secteur,
        )
        StockPiece.objects.create(
            reference="REF-003", designation="Joint hors périmètre", quantite=0, quantite_minimale=5,
            ship=self.navire, service=self.service, sector=self.autre_secteur,
        )

        contexte = construire_contexte_instantane("sector", self.secteur.id, self.chef)

        self.assertEqual(len(contexte["stock_alerte"]), 1)
        self.assertEqual(contexte["stock_alerte"][0].id, piece_sous_seuil.id)

    @unittest.skipUnless(pdf_disponible(), "WeasyPrint indisponible sur cette machine")
    def test_generation_pdf_instantane(self):
        pdf = generer_bilan_instantane_pdf("sector", self.secteur.id, self.chef)
        self.assertTrue(pdf.startswith(b"%PDF"))
