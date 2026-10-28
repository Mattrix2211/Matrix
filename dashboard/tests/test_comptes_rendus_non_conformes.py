"""Accueil du chef : bloc « Mon périmètre » et libellés des comptes rendus non conformes (aucun geste « Valider »)."""
from django.test import TestCase
from django.urls import reverse

from dashboard.aujourdhui import supervision
from dashboard.tests.test_supervision import SupervisionTests
from maintenance.models import InstallationMaintenance, MaintenanceOccurrence
from assets.models import Installation


class ComptesRendusNonConformesTests(TestCase):
    # Réutilise les fabriques de SupervisionTests sans en rejouer les tests.
    setUp = SupervisionTests.setUp
    _marin = SupervisionTests._marin
    _asset = SupervisionTests._asset
    _occurrence = SupervisionTests._occurrence
    _page = SupervisionTests._page

    def test_libelles_et_lien_vers_le_compte_rendu(self):
        attente = self._occurrence(self.asset_a, 1, "WAITING_VALIDATION")
        r = self._page(self.chef_a)
        self.assertContains(r, "<h2 class=\"h5 mt-5 mb-3\">Mon périmètre</h2>", html=True)
        self.assertContains(r, "Comptes rendus non conformes à traiter")
        self.assertContains(r, "Non conforme : un ticket correctif est ouvert")
        self.assertContains(r, reverse("occurrence-execute", args=[attente.pk]))
        self.assertNotContains(r, "Valider")
        self.assertNotContains(r, "Rien à traiter")

    def test_aucun_changement_de_statut_en_consultant_l_accueil(self):
        attente = self._occurrence(self.asset_a, 1, "WAITING_VALIDATION")
        self._page(self.chef_a)
        attente.refresh_from_db()
        self.assertEqual(attente.status, "WAITING_VALIDATION")

    def test_installation_sans_promesse_de_ticket(self):
        installation = Installation.objects.create(
            designation="Groupe", ship=self.navire, service=self.service, sector=self.secteur_a,
        )
        fiche = InstallationMaintenance.objects.create(installation=installation, periodicity="3 mois", title="Révision")
        MaintenanceOccurrence.objects.create(
            installation_maintenance=fiche, scheduled_for=self.aujourdhui, status="WAITING_VALIDATION",
        )
        ligne = supervision(self.chef_a, self.aujourdhui)["validations"][0]
        self.assertTrue(ligne["detail"].endswith("Non conforme"))
        self.assertNotIn("ticket", ligne["detail"])

    def test_sans_compte_rendu_etat_vide_unique(self):
        r = self._page(self.chef_a)
        self.assertContains(r, "Rien à traiter")
        self.assertNotContains(r, "Comptes rendus non conformes à traiter")
