"""Tests de la couche Python qui prépare les nouvelles visualisations ajoutées
au principe fondamental n°5 de CLAUDE.md (« Priorité au visuel ») : courbe de
tendance de l'isolement (Chart.js) et frise de l'évolution des vibrations
(SVG/CSS). Le rendu JS/Chart.js lui-même n'est pas testé ici, seul le contexte
transmis par InstallationDetailView (assets/web_views.py)."""
import json
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from assets.models import Installation, InstallationIsolationReading, InstallationVibrationReading
from org.models import Sector, Service, Ship


class CourbeIsolementTests(TestCase):
    """InstallationDetailView doit transmettre les données nécessaires à la
    courbe Chart.js de l'onglet Isolement (_onglet_isolement.html)."""

    def setUp(self):
        self.ship = Ship.objects.create(name="Navire A", code="NA-ISO")
        self.service = Service.objects.create(ship=self.ship, name="Srv")
        self.sector = Sector.objects.create(service=self.service, name="Sec")
        self.installation = Installation.objects.create(
            designation="Moteur bâbord", ship=self.ship, service=self.service, sector=self.sector,
            isolation_seuil_ohms=100,
        )
        self.user = User.objects.create_user(username="u1", password="pass")
        self.client.login(username="u1", password="pass")
        self.url = reverse("installation-detail", args=[self.installation.pk])

    def test_labels_et_valeurs_dans_lordre_chronologique(self):
        # Créés dans le désordre pour vérifier que le contexte les remet dans
        # l'ordre chronologique (du plus ancien au plus récent), condition
        # nécessaire pour une courbe lisible de gauche à droite.
        InstallationIsolationReading.objects.create(installation=self.installation, date="2026-01-15", ohms=Decimal("130.00"))
        InstallationIsolationReading.objects.create(installation=self.installation, date="2026-01-01", ohms=Decimal("200.00"))
        InstallationIsolationReading.objects.create(installation=self.installation, date="2026-01-08", ohms=Decimal("150.00"))

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        labels = json.loads(response.context["isolation_chart_labels_json"])
        valeurs = json.loads(response.context["isolation_chart_values_json"])
        self.assertEqual(labels, ["01/01/2026", "08/01/2026", "15/01/2026"])
        self.assertEqual(valeurs, [200.0, 150.0, 130.0])

    def test_seuil_transmis_au_contexte(self):
        response = self.client.get(self.url)
        self.assertEqual(response.context["isolation_seuil_ohms"], 100)

    def test_pas_de_seuil_pas_de_derive_calculee(self):
        self.installation.isolation_seuil_ohms = None
        self.installation.save(update_fields=["isolation_seuil_ohms"])
        InstallationIsolationReading.objects.create(installation=self.installation, date="2026-01-01", ohms=Decimal("200.00"))

        response = self.client.get(self.url)

        self.assertIsNone(response.context["isolation_jours_avant_seuil"])

    def test_derive_a_la_baisse_estimee_via_regression_lineaire(self):
        # Réutilise assets/trend.py::jours_avant_franchissement_seuil (déjà
        # utilisé par notifications/tasks.py) — tendance à la baisse claire,
        # seuil pas encore franchi : une estimation en jours doit être renvoyée.
        InstallationIsolationReading.objects.create(installation=self.installation, date="2026-01-01", ohms=Decimal("300.00"))
        InstallationIsolationReading.objects.create(installation=self.installation, date="2026-01-08", ohms=Decimal("250.00"))
        InstallationIsolationReading.objects.create(installation=self.installation, date="2026-01-15", ohms=Decimal("200.00"))

        response = self.client.get(self.url)

        jours = response.context["isolation_jours_avant_seuil"]
        self.assertIsNotNone(jours)
        self.assertGreater(jours, 0)

    def test_aucune_mesure_ne_plante_pas_la_page(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(json.loads(response.context["isolation_chart_labels_json"]), [])
        self.assertEqual(json.loads(response.context["isolation_chart_values_json"]), [])


class FriseVibrationTests(TestCase):
    """InstallationDetailView doit transmettre la frise chronologique des
    relevés de vibration (_onglet_vibration.html), limitée aux 20 plus
    récents pour rester lisible."""

    def setUp(self):
        self.ship = Ship.objects.create(name="Navire B", code="NB-VIB")
        self.service = Service.objects.create(ship=self.ship, name="Srv")
        self.sector = Sector.objects.create(service=self.service, name="Sec")
        self.installation = Installation.objects.create(
            designation="Pompe tribord", ship=self.ship, service=self.service, sector=self.sector,
        )
        self.user = User.objects.create_user(username="u2", password="pass")
        self.client.login(username="u2", password="pass")
        self.url = reverse("installation-detail", args=[self.installation.pk])

    def test_ordre_chronologique_du_plus_ancien_au_plus_recent(self):
        InstallationVibrationReading.objects.create(installation=self.installation, date="2026-01-03", state="C")
        InstallationVibrationReading.objects.create(installation=self.installation, date="2026-01-01", state="A")
        InstallationVibrationReading.objects.create(installation=self.installation, date="2026-01-02", state="B")

        response = self.client.get(self.url)

        timeline = response.context["vibration_timeline"]
        self.assertEqual([v.state for v in timeline], ["A", "B", "C"])

    def test_limitee_aux_20_releves_les_plus_recents(self):
        for i in range(1, 23):
            InstallationVibrationReading.objects.create(
                installation=self.installation, date=f"2026-01-{i:02}", state="A",
            )

        response = self.client.get(self.url)

        timeline = response.context["vibration_timeline"]
        self.assertEqual(len(timeline), 20)
        # Les 2 relevés les plus anciens (01 et 02 janvier) doivent être exclus.
        dates = [v.date.isoformat() for v in timeline]
        self.assertEqual(dates[0], "2026-01-03")
        self.assertEqual(dates[-1], "2026-01-22")

    def test_liste_vide_sans_releve(self):
        response = self.client.get(self.url)
        self.assertEqual(response.context["vibration_timeline"], [])
