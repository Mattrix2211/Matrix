"""Vérifie la correction des N+1 sévères sur la page Installations et la liste
Matériel : le nombre de requêtes ne doit plus dépendre du nombre d'installations
ou de matériels affichés (requêtes groupées / prefetch_related), et les valeurs
affichées doivent rester identiques à avant la correction.

Les vues sont invoquées directement (RequestFactory + get_context_data), sans
passer par le rendu complet du template ni par les context processors globaux
(ex: matrix.context_processors.installations_notifications), afin d'isoler
précisément le comportement des vues corrigées."""
from decimal import Decimal

from django.contrib.auth.models import User
from django.db import connection
from django.test import RequestFactory, TestCase
from django.test.utils import CaptureQueriesContext

from org.models import Ship, Service, Sector
from assets.models import (
    Asset,
    AssetDocument,
    AssetType,
    Installation,
    InstallationHourReading,
    InstallationIsolationReading,
    InstallationVibrationReading,
)
from assets.web_views import AssetListView, InstallationListView


class InstallationListNPlusUnTests(TestCase):
    """InstallationListView.get_context_data faisait 3 requêtes séparées par
    installation affichée (dernier relevé vibration, somme des heures, dernier
    relevé isolement) : 3N+1 requêtes minimum. Doit désormais utiliser des
    requêtes groupées (installation_id__in=...)."""

    def setUp(self):
        self.ship = Ship.objects.create(name="Navire A")
        self.service = Service.objects.create(name="Srv", ship=self.ship)
        self.sector = Sector.objects.create(name="Sec", service=self.service)
        self.user = User.objects.create_user(username="u1", password="pass")
        self.factory = RequestFactory()

    def _creer_installations_avec_releves(self, n):
        installations = []
        for i in range(n):
            inst = Installation.objects.create(
                designation=f"Installation {i}", ship=self.ship, service=self.service, sector=self.sector,
            )
            InstallationHourReading.objects.create(installation=inst, date="2026-01-01", hours=Decimal("10.0"), is_visit=True)
            InstallationHourReading.objects.create(installation=inst, date="2026-02-01", hours=Decimal("5.0"))
            InstallationVibrationReading.objects.create(installation=inst, date="2026-02-01", state="B")
            InstallationIsolationReading.objects.create(installation=inst, date="2026-02-01", ohms=Decimal("100.00"))
            installations.append(inst)
        return installations

    def _construire_contexte(self):
        """Construit le contexte de InstallationListView directement, pour isoler
        les requêtes faites par la vue elle-même (pas celles d'un context processor
        global indépendant de cette tâche)."""
        request = self.factory.get("/installations/")
        request.user = self.user
        view = InstallationListView()
        view.request = request
        view.kwargs = {}
        view.object_list = view.get_queryset()
        return view.get_context_data()

    def test_nombre_de_requetes_ne_depend_pas_du_nombre_dinstallations(self):
        self._creer_installations_avec_releves(2)
        with CaptureQueriesContext(connection) as petit_lot:
            self._construire_contexte()

        self._creer_installations_avec_releves(8)
        with CaptureQueriesContext(connection) as grand_lot:
            self._construire_contexte()

        self.assertEqual(
            len(petit_lot.captured_queries), len(grand_lot.captured_queries),
            "Le nombre de requêtes ne doit pas augmenter avec le nombre d'installations affichées.",
        )

    def test_valeurs_affichees_restent_correctes(self):
        installations = self._creer_installations_avec_releves(1)
        inst = installations[0]
        # Relevés plus récents : doivent être ceux retenus comme "derniers".
        InstallationVibrationReading.objects.create(installation=inst, date="2026-03-01", state="A")
        InstallationIsolationReading.objects.create(installation=inst, date="2026-03-01", ohms=Decimal("250.00"))

        ctx = self._construire_contexte()
        page = list(ctx["installations"])
        self.assertEqual(len(page), 1)
        it = page[0]
        self.assertEqual(it.vibration_last_state_card, "A")
        self.assertEqual(it.isolation_last_ohms_card, Decimal("250.00"))
        self.assertEqual(it.hours_total_card, 15.0)
        self.assertEqual(it.hours_last_visit_card, 5.0)


class AssetListNPlusUnTests(TestCase):
    """AssetListView.get_queryset ne préchargeait pas les documents : le template
    boucle sur a.documents.all pour chaque matériel affiché (une requête
    AssetDocument par matériel). Doit désormais utiliser prefetch_related('documents')."""

    def setUp(self):
        self.ship = Ship.objects.create(name="Navire A")
        self.service = Service.objects.create(name="Srv", ship=self.ship)
        self.sector = Sector.objects.create(name="Sec", service=self.service)
        self.asset_type = AssetType.objects.create(name="Extincteur", category="EPI", sector=self.sector)
        self.user = User.objects.create_user(username="u2", password="pass")
        self.factory = RequestFactory()

    def _creer_materiels_avec_documents(self, n):
        for i in range(n):
            asset = Asset.objects.create(
                asset_type=self.asset_type, ship=self.ship, service=self.service, sector=self.sector,
                serial_number=f"SN-{i}", internal_id=f"INT-{i}",
            )
            AssetDocument.objects.create(asset=asset, file="asset_docs/fiche.pdf", name="Fiche technique")

    def _obtenir_queryset(self):
        request = self.factory.get("/assets/")
        request.user = self.user
        view = AssetListView()
        view.request = request
        view.kwargs = {}
        return view.get_queryset()

    def test_nombre_de_requetes_ne_depend_pas_du_nombre_de_materiels(self):
        self._creer_materiels_avec_documents(2)
        with CaptureQueriesContext(connection) as petit_lot:
            for a in self._obtenir_queryset():
                list(a.documents.all())

        self._creer_materiels_avec_documents(8)
        with CaptureQueriesContext(connection) as grand_lot:
            for a in self._obtenir_queryset():
                list(a.documents.all())

        self.assertEqual(
            len(petit_lot.captured_queries), len(grand_lot.captured_queries),
            "Le nombre de requêtes ne doit pas augmenter avec le nombre de matériels affichés.",
        )

    def test_documents_toujours_accessibles_correctement(self):
        self._creer_materiels_avec_documents(1)
        assets = list(self._obtenir_queryset())
        self.assertEqual(len(assets), 1)
        documents = list(assets[0].documents.all())
        self.assertEqual(len(documents), 1)
        self.assertEqual(documents[0].name, "Fiche technique")
