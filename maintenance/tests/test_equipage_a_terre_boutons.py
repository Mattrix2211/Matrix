"""Équipage à terre : boutons d'écriture refusés masqués, et refus serveur maintenu (403)."""
from django.urls import reverse
from django.utils import timezone

from assets.models import Asset, AssetType
from maintenance.models import MaintenanceOccurrence, MaintenancePlan
from org.models import Sector, Service
from taches.tests.test_taches import TachesBase


class BoutonsEquipageATerreTests(TachesBase):
    def setUp(self):
        super().setUp()
        service = self.secteur.service
        type_ = AssetType.objects.create(name="Pompe", category="Cat", sector=self.secteur)
        asset = Asset.objects.create(asset_type=type_, ship=self.navire, service=service, sector=self.secteur)
        plan = MaintenancePlan.objects.create(scope="ASSET", asset=asset, name="Plan", every_n_days=30)
        self.occ = MaintenanceOccurrence.objects.create(
            plan=plan, asset=asset, scheduled_for=timezone.localdate(), status="PLANNED",
        )
        self.chef_b = self._marin("chef_b", self.secteur, "CHEF_SECTION", "B")

    def _liste(self, user):
        self.client.force_login(user)
        return self.client.get(reverse("maintenance-occurrences")).content.decode()

    def test_a_terre_ni_assigner_ni_executer_mais_ouvrir_et_bandeau(self):
        page = self._liste(self.chef_b)
        self.assertNotIn("M'assigner", page)
        self.assertNotIn("Me désister", page)
        self.assertNotIn("Exécuter", page)
        self.assertIn("Ouvrir", page)
        self.assertIn("Lecture seule — Équipage B à terre", page)
        self.assertIn("feuille de service de votre équipage", page)

    def test_a_bord_inchange(self):
        page = self._liste(self.chef)
        self.assertIn("M'assigner", page)
        self.assertIn("Exécuter", page)
        self.assertNotIn("Lecture seule", page)

    def test_serveur_refuse_toujours_a_terre(self):
        self.client.force_login(self.chef_b)
        self.assertEqual(self.client.post(reverse("occurrence-self-assign", args=[self.occ.pk])).status_code, 403)
        self.assertEqual(
            self.client.post(reverse("occurrence-execute", args=[self.occ.pk]), {"notes": "x"}).status_code, 403
        )
        self.assertFalse(self.occ.assignees.exists())
