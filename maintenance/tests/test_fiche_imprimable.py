"""Fiche de maintenance imprimable (parcours « papier puis saisie »)."""
from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import UserProfile
from assets.models import Asset, AssetType, ChecklistItemTemplate, ChecklistTemplate
from maintenance.models import MaintenanceOccurrence, MaintenancePlan
from org.models import Sector, Service, Ship


def _navire(suffixe):
    ship = Ship.objects.create(name=f"Navire {suffixe} fiche", code=f"N{suffixe}-FICHE")
    service = Service.objects.create(ship=ship, name=f"Service {suffixe} fiche")
    sector = Sector.objects.create(service=service, name=f"Secteur {suffixe} fiche")
    type_ = AssetType.objects.create(name=f"Type {suffixe} fiche", category="Cat", sector=sector)
    asset = Asset.objects.create(asset_type=type_, ship=ship, service=service, sector=sector)
    modele = ChecklistTemplate.objects.create(name=f"Modèle {suffixe}", sector=sector)
    ChecklistItemTemplate.objects.create(template=modele, label=f"Contrôler le niveau {suffixe}", order=1)
    ChecklistItemTemplate.objects.create(
        template=modele, label=f"Pression huile {suffixe}", field_type="number", unit="bar", order=2,
    )
    plan = MaintenancePlan.objects.create(
        scope="ASSET", asset=asset, name=f"Plan {suffixe}", every_n_days=30, checklist_template=modele,
    )
    occ = MaintenanceOccurrence.objects.create(
        plan=plan, asset=asset, scheduled_for=timezone.localdate(), status="PLANNED",
    )
    return sector, occ


class FicheImprimableTests(TestCase):
    def setUp(self):
        self.sector_a, self.occ_a = _navire("A")
        _, self.occ_b = _navire("B")
        user = User.objects.create_user(username="chef_fiche", password="pass")
        UserProfile.objects.update_or_create(user=user, defaults={"role": "CHEF_SERVICE", "sector": self.sector_a})
        self.client.login(username="chef_fiche", password="pass")

    def test_anonyme_redirige(self):
        self.client.logout()
        r = self.client.get(reverse("occurrence-imprimer", args=[self.occ_a.pk]))
        self.assertEqual(r.status_code, 302)

    def test_contenu_de_la_fiche(self):
        r = self.client.get(reverse("occurrence-imprimer", args=[self.occ_a.pk]))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, f"FM-{self.occ_a.pk:06d}")
        self.assertContains(r, "Plan A")
        self.assertContains(r, "Contrôler le niveau A")
        self.assertContains(r, "fiche-case")
        self.assertContains(r, "Pression huile A")
        self.assertContains(r, "bar")
        self.assertContains(r, "Exécutant")
        self.assertContains(r, "Contrôle")
        self.assertContains(r, "data:image/png;base64,")

    def test_case_fait_seulement_sur_les_points_a_cocher(self):
        r = self.client.get(reverse("occurrence-imprimer", args=[self.occ_a.pk]))
        self.assertContains(r, 'class="fiche-case" aria-hidden="true"', count=1)

    def test_hors_perimetre_refuse(self):
        r = self.client.get(reverse("occurrence-imprimer", args=[self.occ_b.pk]))
        self.assertEqual(r.status_code, 404)

    def test_lot_filtre_le_perimetre(self):
        r = self.client.get(reverse("occurrences-imprimer"), {"ids": f"{self.occ_a.pk},{self.occ_b.pk}"})
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Plan A")
        self.assertNotContains(r, "Plan B")

    def test_lot_vide_ou_hors_perimetre_404(self):
        r = self.client.get(reverse("occurrences-imprimer"), {"ids": str(self.occ_b.pk)})
        self.assertEqual(r.status_code, 404)
        r = self.client.get(reverse("occurrences-imprimer"), {"ids": "abc"})
        self.assertEqual(r.status_code, 404)

    def test_lien_depuis_la_liste(self):
        r = self.client.get(reverse("maintenance-occurrences"))
        self.assertContains(r, reverse("occurrence-imprimer", args=[self.occ_a.pk]))
