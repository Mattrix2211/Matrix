"""Tests de la confirmation explicite sur le passage en "Terminée" (DONE)
d'une exécution de maintenance sur une installation critique.

Vérifie : refus sans confirmation (aucune exécution enregistrée, occurrence
inchangée), acceptation avec confirmation (valide_par/date_validation posés par
le serveur, audit avec texte et version), ancien champ mot de passe sans effet,
et absence de régression sur les installations non critiques et le matériel mobile.
"""
from django.contrib.auth.models import User
from django.test import TestCase

from accounts.models import AuditLog
from matrix.core.confirmations import texte_confirmation
from django.urls import reverse
from rest_framework.test import APIClient

from assets.models import Asset, AssetType, Installation, InstallationMaintenance, ModeDeclenchement
from maintenance.models import MaintenanceExecution, MaintenanceOccurrence, MaintenancePlan
from accounts.models import UserProfile
from org.models import Sector, Service, Ship
from django.utils import timezone


class SignatureValidationExecutionTests(TestCase):
    def setUp(self):
        self.ship = Ship.objects.create(name="Navire test signature exec", code="NT-SIGX")
        self.service = Service.objects.create(ship=self.ship, name="Service test signature exec")
        self.sector = Sector.objects.create(service=self.service, name="Secteur test signature exec")
        self.installation_critique = Installation.objects.create(
            designation="Groupe électrogène critique",
            ship=self.ship, service=self.service, sector=self.sector,
            critique=True,
        )
        self.installation_normale = Installation.objects.create(
            designation="Groupe électrogène standard",
            ship=self.ship, service=self.service, sector=self.sector,
            critique=False,
        )
        self.tech = User.objects.create_user(username="tech_signature", password="MotDePasseCorrect1")
        UserProfile.objects.update_or_create(user=self.tech, defaults={"ship": self.ship})

    def _creer_occurrence(self, installation, mode=ModeDeclenchement.CALENDRIER):
        maintenance = InstallationMaintenance.objects.create(
            installation=installation,
            periodicity="1 mois",
            title="Contrôle général",
            mode_declenchement=mode,
            intervalle=1,
            unite_intervalle="M",
        )
        occ = MaintenanceOccurrence.objects.create(
            installation_maintenance=maintenance, scheduled_for=timezone.localdate(), status="ASSIGNED",
        )
        occ.assignees.add(self.tech)
        return occ

    def test_page_affiche_identite_et_texte_non_precoche(self):
        occ = self._creer_occurrence(self.installation_critique)
        self.client.login(username="tech_signature", password="MotDePasseCorrect1")
        r = self.client.get(reverse("occurrence-execute", args=[occ.id]))
        self.assertContains(r, "Vous validez en tant que")
        self.assertContains(r, "tech_signature")
        self.assertContains(r, texte_confirmation("maintenance_critique")[1])
        self.assertContains(r, 'name="confirmation"')
        self.assertNotRegex(r.content.decode(), r'name="confirmation"[^>]*checked')
        self.assertNotContains(r, 'name="mot_de_passe"')

    def test_validation_refusee_sans_confirmation(self):
        occ = self._creer_occurrence(self.installation_critique)
        self.client.login(username="tech_signature", password="MotDePasseCorrect1")
        url = reverse("occurrence-execute", args=[occ.id])
        r = self.client.post(url, {"conformity": "CONFORME"})
        self.assertContains(r, "Confirmation requise")
        occ.refresh_from_db()
        self.assertEqual(occ.status, "ASSIGNED")
        self.assertFalse(MaintenanceExecution.objects.filter(occurrence=occ).exists())
        self.assertTrue(AuditLog.objects.filter(action="validation_critique_refusee").exists())
        self.assertFalse(AuditLog.objects.filter(action="occurrence_validation_critique").exists())

    def test_ancien_mot_de_passe_ne_vaut_pas_confirmation(self):
        occ = self._creer_occurrence(self.installation_critique)
        self.client.login(username="tech_signature", password="MotDePasseCorrect1")
        url = reverse("occurrence-execute", args=[occ.id])
        self.client.post(url, {"conformity": "CONFORME", "mot_de_passe": "MotDePasseCorrect1"})
        occ.refresh_from_db()
        self.assertEqual(occ.status, "ASSIGNED")

    def test_validation_refusee_sans_droit(self):
        # Un marin non assigné et hors périmètre est refusé avant toute logique de confirmation.
        occ = self._creer_occurrence(self.installation_critique)
        autre = User.objects.create_user(username="autre_signature", password="MotDePasseCorrect1")
        autre_navire = Ship.objects.create(name="Autre navire signature", code="NT-SIGX2")
        UserProfile.objects.update_or_create(user=autre, defaults={"ship": autre_navire})
        self.client.login(username="autre_signature", password="MotDePasseCorrect1")
        r = self.client.post(reverse("occurrence-execute", args=[occ.id]), {"conformity": "CONFORME", "confirmation": "1"})
        self.assertIn(r.status_code, (400, 403, 404))
        occ.refresh_from_db()
        self.assertEqual(occ.status, "ASSIGNED")
        self.assertFalse(AuditLog.objects.filter(action="validation_critique_refusee").exists())

    def test_validation_acceptee_avec_confirmation(self):
        occ = self._creer_occurrence(self.installation_critique)
        self.client.login(username="tech_signature", password="MotDePasseCorrect1")
        url = reverse("occurrence-execute", args=[occ.id])
        self.client.post(url, {"conformity": "CONFORME", "confirmation": "1", "valide_par": "999"})
        occ.refresh_from_db()
        self.assertEqual(occ.status, "DONE")
        execution = MaintenanceExecution.objects.get(occurrence=occ)
        self.assertEqual(execution.valide_par, self.tech)
        self.assertIsNotNone(execution.date_validation)
        version, texte = texte_confirmation("maintenance_critique")
        entree = AuditLog.objects.get(action="occurrence_validation_critique")
        self.assertIn("canal=web", entree.details)
        self.assertIn(f"confirmation_version={version}", entree.details)
        self.assertIn(texte, entree.details)

    def test_installation_non_critique_ne_necessite_pas_de_confirmation(self):
        occ = self._creer_occurrence(self.installation_normale)
        self.client.login(username="tech_signature", password="MotDePasseCorrect1")
        url = reverse("occurrence-execute", args=[occ.id])
        self.client.post(url, {"conformity": "CONFORME"})
        occ.refresh_from_db()
        self.assertEqual(occ.status, "DONE")
        execution = MaintenanceExecution.objects.get(occurrence=occ)
        self.assertIsNone(execution.valide_par)

    def test_non_conforme_sur_installation_critique_ne_necessite_pas_de_confirmation(self):
        # NON_CONFORME fait passer l'occurrence en WAITING_VALIDATION, pas DONE :
        # la confirmation ne concerne que le passage en "Terminée".
        occ = self._creer_occurrence(self.installation_critique)
        self.client.login(username="tech_signature", password="MotDePasseCorrect1")
        url = reverse("occurrence-execute", args=[occ.id])
        self.client.post(url, {"conformity": "NON_CONFORME"})
        occ.refresh_from_db()
        self.assertEqual(occ.status, "WAITING_VALIDATION")

    def test_materiel_mobile_ne_necessite_pas_de_confirmation(self):
        asset_type = AssetType.objects.create(name="Extincteur signature", category="Incendie", sector=self.sector)
        asset = Asset.objects.create(asset_type=asset_type, ship=self.ship, service=self.service, sector=self.sector)
        plan = MaintenancePlan.objects.create(scope="ASSET", asset=asset, name="Contrôle annuel", every_n_days=365)
        occ = MaintenanceOccurrence.objects.create(
            plan=plan, asset=asset, scheduled_for=timezone.localdate(), status="ASSIGNED",
        )
        occ.assignees.add(self.tech)
        self.client.login(username="tech_signature", password="MotDePasseCorrect1")
        url = reverse("occurrence-execute", args=[occ.id])
        self.client.post(url, {"conformity": "CONFORME"})
        occ.refresh_from_db()
        self.assertEqual(occ.status, "DONE")


class SignatureValidationAPIExecutionTests(TestCase):
    """Mêmes règles que SignatureValidationExecutionTests ci-dessus, mais via
    l'action DRF MaintenanceOccurrenceViewSet.complete : l'API ne doit pas
    offrir un moyen de contourner la confirmation exigée par l'interface web."""

    def setUp(self):
        self.ship = Ship.objects.create(name="Navire test signature exec API", code="NT-SIGX-API")
        self.service = Service.objects.create(ship=self.ship, name="Service test signature exec API")
        self.sector = Sector.objects.create(service=self.service, name="Secteur test signature exec API")
        self.installation_critique = Installation.objects.create(
            designation="Groupe électrogène critique API",
            ship=self.ship, service=self.service, sector=self.sector,
            critique=True,
        )
        self.tech = User.objects.create_user(username="tech_signature_api", password="MotDePasseCorrect1")
        UserProfile.objects.update_or_create(user=self.tech, defaults={"ship": self.ship})
        maintenance = InstallationMaintenance.objects.create(
            installation=self.installation_critique,
            periodicity="1 mois",
            title="Contrôle général",
            mode_declenchement=ModeDeclenchement.CALENDRIER,
            intervalle=1,
            unite_intervalle="M",
        )
        self.occ = MaintenanceOccurrence.objects.create(
            installation_maintenance=maintenance, scheduled_for=timezone.localdate(), status="ASSIGNED",
        )
        self.occ.assignees.add(self.tech)
        self.client = APIClient()
        self.client.login(username="tech_signature_api", password="MotDePasseCorrect1")
        self.url = f"/api/maintenance/occurrences/{self.occ.id}/complete/"

    def test_refusee_sans_confirmation_ou_non_booleenne(self):
        for charge in ({}, {"confirmation": False}, {"confirmation": "true"}, {"confirmation": 1}, {"mot_de_passe": "MotDePasseCorrect1"}):
            with self.subTest(charge=charge):
                r = self.client.post(self.url, {"conformity": "CONFORME", **charge}, format="json")
                self.assertEqual(r.status_code, 400)
                self.assertIn("Confirmation requise", r.json()["detail"])
                self.occ.refresh_from_db()
                self.assertEqual(self.occ.status, "ASSIGNED")
                self.assertFalse(MaintenanceExecution.objects.filter(occurrence=self.occ).exists())
        self.assertFalse(AuditLog.objects.filter(action="occurrence_validation_critique").exists())

    def test_refusee_sans_droit_avant_la_confirmation(self):
        autre = User.objects.create_user(username="autre_signature_api", password="MotDePasseCorrect1")
        autre_navire = Ship.objects.create(name="Autre navire signature API", code="NT-SIGX-API2")
        UserProfile.objects.update_or_create(user=autre, defaults={"ship": autre_navire})
        client = APIClient()
        client.login(username="autre_signature_api", password="MotDePasseCorrect1")
        r = client.post(self.url, {"conformity": "CONFORME", "confirmation": True}, format="json")
        self.assertIn(r.status_code, (403, 404))
        r = client.post(self.url, {"conformity": "CONFORME"}, format="json")
        self.assertIn(r.status_code, (403, 404))
        self.occ.refresh_from_db()
        self.assertEqual(self.occ.status, "ASSIGNED")

    def test_acceptee_avec_confirmation(self):
        r = self.client.post(
            self.url, {"conformity": "CONFORME", "confirmation": True, "valide_par": 999}, format="json"
        )
        self.assertEqual(r.status_code, 200)
        self.occ.refresh_from_db()
        self.assertEqual(self.occ.status, "DONE")
        execution = MaintenanceExecution.objects.get(occurrence=self.occ)
        self.assertEqual(execution.valide_par, self.tech)
        self.assertIsNotNone(execution.date_validation)
        version, texte = texte_confirmation("maintenance_critique")
        entree = AuditLog.objects.get(action="occurrence_validation_critique")
        self.assertIn("canal=api", entree.details)
        self.assertIn(f"confirmation_version={version}", entree.details)
        self.assertIn(texte, entree.details)

    def test_patch_generique_ne_permet_pas_de_contourner_la_confirmation(self):
        """Régression (contre-vérification sécurité) : le statut ne doit pas
        pouvoir être modifié via le endpoint générique du ViewSet, qui ne passe
        pas par complete() et donc pas par la confirmation."""
        detail_url = f"/api/maintenance/occurrences/{self.occ.id}/"
        r = self.client.patch(detail_url, {"status": "DONE"}, format="json")
        self.assertEqual(r.status_code, 400)
        self.occ.refresh_from_db()
        self.assertEqual(self.occ.status, "ASSIGNED")
        self.assertFalse(MaintenanceExecution.objects.filter(occurrence=self.occ).exists())
