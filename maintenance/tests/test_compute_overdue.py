from datetime import timedelta

from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone

from assets.models import Asset, AssetType
from maintenance.models import MaintenanceOccurrence, MaintenancePlan
from maintenance.tasks import compute_overdue
from org.models import Sector, Service, Ship


class ComputeOverdueTaskTests(TestCase):
    """Vérifie le comportement réel de la tâche Celery horaire compute_overdue,
    jusqu'ici jamais invoquée directement dans les tests (les occurrences en
    retard étaient créées avec status="OVERDUE" en dur, sans jamais passer par
    la tâche elle-même)."""

    def setUp(self):
        self.user = User.objects.create_user(username="u_overdue", password="p")
        ship = Ship.objects.create(name="Ship overdue", code="OV1")
        service = Service.objects.create(ship=ship, name="Tech")
        sector = Sector.objects.create(service=service, name="Elec")
        asset_type = AssetType.objects.create(name="Extincteur", category="Fire", sector=sector)
        self.asset = Asset.objects.create(
            asset_type=asset_type, ship=ship, service=service, sector=sector, status="OK"
        )
        self.plan = MaintenancePlan.objects.create(
            scope="ASSET", asset=self.asset, name="Contrôle visuel", every_n_days=30
        )
        self.hier = timezone.localdate() - timedelta(days=1)
        self.demain = timezone.localdate() + timedelta(days=1)

    def _cree_occurrence(self, status, scheduled_for):
        return MaintenanceOccurrence.objects.create(
            plan=self.plan, asset=self.asset, scheduled_for=scheduled_for, status=status
        )

    def test_occurrences_planned_ou_assigned_echues_passent_en_overdue(self):
        occ_planned = self._cree_occurrence("PLANNED", self.hier)
        occ_assigned = self._cree_occurrence("ASSIGNED", self.hier)

        compute_overdue()

        occ_planned.refresh_from_db()
        occ_assigned.refresh_from_db()
        self.assertEqual(occ_planned.status, "OVERDUE")
        self.assertEqual(occ_assigned.status, "OVERDUE")

    def test_occurrences_en_cours_ou_terminees_ne_sont_pas_touchees(self):
        """Une occurrence déjà prise en charge (en cours, en validation ou
        terminée) ne doit jamais être basculée en retard, même si sa date
        planifiée est dépassée."""
        occ_in_progress = self._cree_occurrence("IN_PROGRESS", self.hier)
        occ_waiting = self._cree_occurrence("WAITING_VALIDATION", self.hier)
        occ_done = self._cree_occurrence("DONE", self.hier)

        compute_overdue()

        occ_in_progress.refresh_from_db()
        occ_waiting.refresh_from_db()
        occ_done.refresh_from_db()
        self.assertEqual(occ_in_progress.status, "IN_PROGRESS")
        self.assertEqual(occ_waiting.status, "WAITING_VALIDATION")
        self.assertEqual(occ_done.status, "DONE")

    def test_occurrences_non_echues_ne_sont_pas_touchees(self):
        """Une occurrence planifiée ou assignée mais pas encore échue (date dans
        le futur) ne doit pas être marquée en retard."""
        occ_planned_futur = self._cree_occurrence("PLANNED", self.demain)
        occ_assigned_futur = self._cree_occurrence("ASSIGNED", self.demain)

        compute_overdue()

        occ_planned_futur.refresh_from_db()
        occ_assigned_futur.refresh_from_db()
        self.assertEqual(occ_planned_futur.status, "PLANNED")
        self.assertEqual(occ_assigned_futur.status, "ASSIGNED")
