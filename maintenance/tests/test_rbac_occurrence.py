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

    def test_suppression_occurrence_interdite_via_api(self):
        """Une occurrence n'est jamais créée à la main (seule generate_occurrences
        le fait) et porte l'historique de statuts ainsi que la signature de
        validation d'une installation critique : sa suppression via l'API est
        donc interdite pour tout utilisateur, même un administrateur général
        (SuppressionInterditeMixin, matrix/core/mixins.py — même audit que la
        correction de CorrectiveTicketViewSet, tâche Notion « Matrice de tests de
        permissions »)."""
        ship = Ship.objects.create(name="S2")
        service = Service.objects.create(name="Srv2", ship=ship)
        sector = Sector.objects.create(name="Sec2", service=service)
        at = AssetType.objects.create(name="TypeB", category="Cat", sector=sector)
        asset = Asset.objects.create(asset_type=at, ship=ship, service=service, sector=sector)
        plan = MaintenancePlan.objects.create(scope="ASSET", asset=asset, name="Plan B", every_n_days=30)
        occ = MaintenanceOccurrence.objects.create(
            plan=plan, asset=asset, scheduled_for=timezone.now().date(), status="PLANNED",
        )
        admin = User.objects.create_superuser(username="admin_mtx", password="pass", email="a@a.fr")

        client = APIClient()
        client.login(username="admin_mtx", password="pass")
        r = client.delete(f"/api/maintenance/occurrences/{occ.id}/")
        self.assertEqual(r.status_code, 405)
        self.assertTrue(MaintenanceOccurrence.objects.filter(pk=occ.id).exists())
