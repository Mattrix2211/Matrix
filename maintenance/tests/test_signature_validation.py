"""Tests de la signature de validation sur le passage en "Terminée" (DONE)
d'une exécution de maintenance sur une installation critique.

Geste engageant : exige une ré-authentification légère (mot de passe courant
de l'appelant) avant d'être appliqué. Vérifie : refus si le mot de passe est
incorrect (aucune exécution enregistrée, occurrence inchangée), acceptation si
le mot de passe est correct (valide_par/date_validation renseignés), et
absence de régression sur les installations non critiques et sur le matériel
mobile (aucun mot de passe exigé).
"""
from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from assets.models import Asset, AssetType, Installation, InstallationMaintenance, ModeDeclenchement
from maintenance.models import MaintenanceExecution, MaintenanceOccurrence, MaintenancePlan
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

    def test_validation_refusee_avec_mauvais_mot_de_passe(self):
        occ = self._creer_occurrence(self.installation_critique)
        self.client.login(username="tech_signature", password="MotDePasseCorrect1")
        url = reverse("occurrence-execute", args=[occ.id])
        self.client.post(url, {"conformity": "CONFORME", "mot_de_passe": "faux-mot-de-passe"})
        occ.refresh_from_db()
        self.assertEqual(occ.status, "ASSIGNED")
        self.assertFalse(MaintenanceExecution.objects.filter(occurrence=occ).exists())

    def test_validation_refusee_sans_mot_de_passe(self):
        occ = self._creer_occurrence(self.installation_critique)
        self.client.login(username="tech_signature", password="MotDePasseCorrect1")
        url = reverse("occurrence-execute", args=[occ.id])
        self.client.post(url, {"conformity": "CONFORME"})
        occ.refresh_from_db()
        self.assertEqual(occ.status, "ASSIGNED")
        self.assertFalse(MaintenanceExecution.objects.filter(occurrence=occ).exists())

    def test_validation_acceptee_avec_bon_mot_de_passe(self):
        occ = self._creer_occurrence(self.installation_critique)
        self.client.login(username="tech_signature", password="MotDePasseCorrect1")
        url = reverse("occurrence-execute", args=[occ.id])
        self.client.post(url, {"conformity": "CONFORME", "mot_de_passe": "MotDePasseCorrect1"})
        occ.refresh_from_db()
        self.assertEqual(occ.status, "DONE")
        execution = MaintenanceExecution.objects.get(occurrence=occ)
        self.assertEqual(execution.valide_par, self.tech)
        self.assertIsNotNone(execution.date_validation)

    def test_installation_non_critique_ne_necessite_pas_de_mot_de_passe(self):
        occ = self._creer_occurrence(self.installation_normale)
        self.client.login(username="tech_signature", password="MotDePasseCorrect1")
        url = reverse("occurrence-execute", args=[occ.id])
        self.client.post(url, {"conformity": "CONFORME"})
        occ.refresh_from_db()
        self.assertEqual(occ.status, "DONE")
        execution = MaintenanceExecution.objects.get(occurrence=occ)
        self.assertIsNone(execution.valide_par)

    def test_non_conforme_sur_installation_critique_ne_necessite_pas_de_mot_de_passe(self):
        # NON_CONFORME fait passer l'occurrence en WAITING_VALIDATION, pas DONE :
        # la validation par mot de passe ne concerne que le passage en "Terminée".
        occ = self._creer_occurrence(self.installation_critique)
        self.client.login(username="tech_signature", password="MotDePasseCorrect1")
        url = reverse("occurrence-execute", args=[occ.id])
        self.client.post(url, {"conformity": "NON_CONFORME"})
        occ.refresh_from_db()
        self.assertEqual(occ.status, "WAITING_VALIDATION")

    def test_materiel_mobile_ne_necessite_pas_de_mot_de_passe(self):
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
    l'action DRF MaintenanceOccurrenceViewSet.complete (tâche [SEC] Signature
    mot de passe contournable via l'API) : l'API ne doit pas offrir un moyen
    de contourner la ré-authentification exigée par l'interface web."""

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

    def test_refusee_avec_mauvais_mot_de_passe(self):
        r = self.client.post(self.url, {"conformity": "CONFORME", "mot_de_passe": "faux-mot-de-passe"}, format="json")
        self.assertEqual(r.status_code, 403)
        self.occ.refresh_from_db()
        self.assertEqual(self.occ.status, "ASSIGNED")
        self.assertFalse(MaintenanceExecution.objects.filter(occurrence=self.occ).exists())

    def test_refusee_sans_mot_de_passe(self):
        r = self.client.post(self.url, {"conformity": "CONFORME"}, format="json")
        self.assertEqual(r.status_code, 403)
        self.occ.refresh_from_db()
        self.assertEqual(self.occ.status, "ASSIGNED")
        self.assertFalse(MaintenanceExecution.objects.filter(occurrence=self.occ).exists())

    def test_acceptee_avec_bon_mot_de_passe(self):
        r = self.client.post(
            self.url, {"conformity": "CONFORME", "mot_de_passe": "MotDePasseCorrect1"}, format="json"
        )
        self.assertEqual(r.status_code, 200)
        self.occ.refresh_from_db()
        self.assertEqual(self.occ.status, "DONE")
        execution = MaintenanceExecution.objects.get(occurrence=self.occ)
        self.assertEqual(execution.valide_par, self.tech)
        self.assertIsNotNone(execution.date_validation)

    def test_patch_generique_ne_permet_pas_de_contourner_la_signature(self):
        """Régression (contre-vérification sécurité) : le statut ne doit pas
        pouvoir être modifié via le endpoint générique du ViewSet, qui ne passe
        pas par complete() et donc pas par le contrôle mot de passe."""
        detail_url = f"/api/maintenance/occurrences/{self.occ.id}/"
        r = self.client.patch(detail_url, {"status": "DONE"}, format="json")
        self.assertEqual(r.status_code, 400)
        self.occ.refresh_from_db()
        self.assertEqual(self.occ.status, "ASSIGNED")
        self.assertFalse(MaintenanceExecution.objects.filter(occurrence=self.occ).exists())
