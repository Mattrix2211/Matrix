from datetime import timedelta

from django.contrib.auth.models import User
from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.utils import timezone
from rest_framework.test import APIClient

from assets.models import Asset, AssetType
from logistics.models import CorrectiveTicket
from maintenance.models import MaintenanceOccurrence, MaintenancePlan
from org.models import Sector, Service, Ship


class PreventiveWeekChartViewTests(TestCase):
    """Vérifie que le graphique hebdomadaire de maintenance préventive agrège les
    occurrences en une seule requête par métrique, sans changer les valeurs
    renvoyées par rapport à l'ancienne implémentation (boucle de .count())."""

    def setUp(self):
        ship = Ship.objects.create(name="Ship A", code="A")
        service = Service.objects.create(ship=ship, name="Tech")
        sector = Sector.objects.create(service=service, name="Elec")
        asset_type = AssetType.objects.create(name="TypeA", category="Cat", sector=sector)
        self.asset = Asset.objects.create(
            asset_type=asset_type, ship=ship, service=service, sector=sector
        )
        self.plan = MaintenancePlan.objects.create(
            scope="ASSET", asset=self.asset, name="Plan A", every_n_days=30
        )
        self.user = User.objects.create_user(username="marin", password="pass")
        self.client = APIClient()
        self.client.login(username="marin", password="pass")

        self.today = timezone.localdate()

        # 2 occurrences planifiées aujourd'hui, dont 1 terminée.
        MaintenanceOccurrence.objects.create(
            plan=self.plan, asset=self.asset, scheduled_for=self.today, status="DONE"
        )
        MaintenanceOccurrence.objects.create(
            plan=self.plan, asset=self.asset, scheduled_for=self.today, status="PLANNED"
        )
        # 1 occurrence terminée demain.
        MaintenanceOccurrence.objects.create(
            plan=self.plan,
            asset=self.asset,
            scheduled_for=self.today + timedelta(days=1),
            status="DONE",
        )
        # 1 occurrence hors de la fenêtre affichée (ne doit pas être comptée).
        MaintenanceOccurrence.objects.create(
            plan=self.plan,
            asset=self.asset,
            scheduled_for=self.today + timedelta(days=30),
            status="DONE",
        )

    def test_valeurs_retournees_correctes(self):
        response = self.client.get("/api/dashboard/preventive_week/")
        self.assertEqual(response.status_code, 200)
        data = response.json()

        labels = data["labels"]
        planned = data["datasets"][0]["data"]
        done = data["datasets"][1]["data"]

        idx_today = labels.index(self.today.strftime("%d/%m"))
        idx_demain = labels.index((self.today + timedelta(days=1)).strftime("%d/%m"))

        self.assertEqual(planned[idx_today], 2)
        self.assertEqual(done[idx_today], 1)
        self.assertEqual(planned[idx_demain], 1)
        self.assertEqual(done[idx_demain], 1)

    def test_nombre_de_requetes_borne(self):
        # Avant correction : 2 requêtes .count() par jour affiché (7 jours -> 14
        # requêtes), plus l'authentification. Désormais, une seule requête agrégée
        # doit suffire pour les deux métriques (planifié + réalisé), quel que soit
        # le nombre de jours affichés.
        with CaptureQueriesContext(connection) as ctx:
            response = self.client.get("/api/dashboard/preventive_week/")
        self.assertEqual(response.status_code, 200)

        requetes_maintenance_occurrence = [
            q for q in ctx.captured_queries if "maintenance_maintenanceoccurrence" in q["sql"].lower()
        ]
        self.assertEqual(
            len(requetes_maintenance_occurrence),
            1,
            "Une seule requête agrégée doit interroger MaintenanceOccurrence",
        )


class CorrectiveOpenChartViewTests(TestCase):
    """Vérifie que le graphique des tickets correctifs ouverts agrège les tickets
    en une seule requête, sans changer les valeurs renvoyées par rapport à
    l'ancienne implémentation (boucle de .count() par statut)."""

    def setUp(self):
        ship = Ship.objects.create(name="Ship A", code="A")
        service = Service.objects.create(ship=ship, name="Tech")
        sector = Sector.objects.create(service=service, name="Elec")
        asset_type = AssetType.objects.create(name="TypeA", category="Cat", sector=sector)
        self.asset = Asset.objects.create(
            asset_type=asset_type, ship=ship, service=service, sector=sector
        )
        self.user = User.objects.create_user(username="marin", password="pass")
        self.client = APIClient()
        self.client.login(username="marin", password="pass")

        CorrectiveTicket.objects.create(asset=self.asset, description="Panne 1", status="REPORTED")
        CorrectiveTicket.objects.create(asset=self.asset, description="Panne 2", status="REPORTED")
        CorrectiveTicket.objects.create(asset=self.asset, description="Panne 3", status="IN_REPAIR")
        # Statut fermé : ne doit pas être compté (hors liste des statuts ouverts).
        CorrectiveTicket.objects.create(asset=self.asset, description="Panne 4", status="CLOSED")

    def test_valeurs_retournees_correctes(self):
        response = self.client.get("/api/dashboard/corrective_open/")
        self.assertEqual(response.status_code, 200)
        data = response.json()

        labels = data["labels"]
        values = data["datasets"][0]["data"]

        self.assertEqual(values[labels.index("REPORTED")], 2)
        self.assertEqual(values[labels.index("IN_REPAIR")], 1)
        self.assertEqual(values[labels.index("WAITING_PARTS")], 0)

    def test_nombre_de_requetes_borne(self):
        # Avant correction : 1 requête .count() par statut ouvert (6 statuts -> 6
        # requêtes). Désormais, une seule requête agrégée doit suffire.
        with CaptureQueriesContext(connection) as ctx:
            response = self.client.get("/api/dashboard/corrective_open/")
        self.assertEqual(response.status_code, 200)

        requetes_ticket = [
            q for q in ctx.captured_queries if "logistics_correctiveticket" in q["sql"].lower()
        ]
        self.assertEqual(
            len(requetes_ticket),
            1,
            "Une seule requête agrégée doit interroger CorrectiveTicket",
        )
