from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient
from django.utils import timezone
from org.models import Ship, Service, Sector
from assets.models import Asset, AssetType
from maintenance.models import MaintenancePlan, MaintenanceOccurrence


class MaintenanceRBACTests(TestCase):
    def test_assignee_can_start_occurrence(self):
        # Mise en place minimale : org + matériel + plan + occurrence
        ship = Ship.objects.create(name="S1")
        service = Service.objects.create(name="Srv", ship=ship)
        sector = Sector.objects.create(name="Sec", service=service)
        at = AssetType.objects.create(name="TypeA", category="Cat", sector=sector)
        asset = Asset.objects.create(asset_type=at, ship=ship, service=service, sector=sector)

        plan = MaintenancePlan.objects.create(scope="ASSET", asset=asset, name="Plan A", every_n_days=30)
        occ = MaintenanceOccurrence.objects.create(
            plan=plan,
            asset=asset,
            scheduled_for=timezone.now().date(),
            status="PLANNED",
        )

        assignee = User.objects.create_user(username="tech", password="pass")
        occ.assignees.add(assignee)

        other = User.objects.create_user(username="other", password="pass")

        client = APIClient()
        # un utilisateur non assigné ne peut pas démarrer l'occurrence
        client.login(username="other", password="pass")
        url = f"/api/maintenance/occurrences/{occ.id}/start/"
        r1 = client.post(url, {})
        self.assertIn(r1.status_code, (403, 401))

        # l'assigné peut démarrer l'occurrence
        client.logout()
        client.login(username="tech", password="pass")
        r2 = client.post(url, {})
        self.assertEqual(r2.status_code, 200)
