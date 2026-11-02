"""Filtres du calendrier : cascade service > secteur > section, bornée au périmètre du compte."""
from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import UserProfile
from assets.models import Asset, AssetType
from calendar_app.evenements_sources import filtres_organisation_coherents
from maintenance.models import MaintenanceOccurrence, MaintenancePlan
from org.models import Section, Sector, Service, Ship


class FiltresHierarchiquesTests(TestCase):
    def setUp(self):
        self.navire = Ship.objects.create(name="Bretagne cal", code="BC")
        self.autre_navire = Ship.objects.create(name="Autre cal", code="AC")
        self.prop = Service.objects.create(ship=self.navire, name="Propulsion")
        self.ops = Service.objects.create(ship=self.navire, name="Opérations")
        self.moteurs = Sector.objects.create(service=self.prop, name="Moteurs")
        self.aux = Sector.objects.create(service=self.prop, name="Auxiliaires")
        self.passerelle = Sector.objects.create(service=self.ops, name="Passerelle")
        self.sec_m1 = Section.objects.create(sector=self.moteurs, name="Moteurs 1")
        self.sec_p1 = Section.objects.create(sector=self.passerelle, name="Passerelle 1")
        self.etranger = Service.objects.create(ship=self.autre_navire, name="Ailleurs")
        self.chef_secteur = self._marin("chef_secteur", "CHEF_SECTEUR", service=self.prop, sector=self.moteurs)
        self.commandant = self._marin("cdt", "COMMANDANT")

    def _marin(self, nom, role, **rattachement):
        user = User.objects.create_user(username=nom, password="pass")
        UserProfile.objects.update_or_create(user=user, defaults={"role": role, "ship": self.navire, **rattachement})
        return User.objects.get(pk=user.pk)

    def test_les_listes_se_limitent_a_la_hierarchie_du_compte(self):
        self.client.force_login(self.chef_secteur)
        page = self.client.get(reverse("calendar-index"))
        self.assertEqual([s.name for s in page.context["services"]], ["Propulsion"])
        self.assertEqual([s.name for s in page.context["sectors"]], ["Moteurs"])
        self.assertEqual([s.name for s in page.context["sections"]], ["Moteurs 1"])
        self.assertNotContains(page, "Passerelle")
        self.assertNotContains(page, "Ailleurs")

    def test_le_commandant_voit_tout_son_batiment_mais_pas_les_autres(self):
        self.client.force_login(self.commandant)
        page = self.client.get(reverse("calendar-index"))
        self.assertEqual({s.name for s in page.context["services"]}, {"Propulsion", "Opérations"})
        self.assertNotContains(page, "Ailleurs")

    def test_les_options_portent_leur_parent_pour_la_cascade(self):
        self.client.force_login(self.commandant)
        page = self.client.get(reverse("calendar-index"))
        self.assertContains(page, f'data-service="{self.prop.pk}"')
        self.assertContains(page, f'data-sector="{self.moteurs.pk}"')

    def test_un_filtre_hors_perimetre_n_est_pas_elargi_a_tous(self):
        filtres = filtres_organisation_coherents(self.chef_secteur, {
            "ship": None, "service": str(self.ops.pk), "sector": str(self.passerelle.pk), "section": str(self.sec_p1.pk)})
        self.assertEqual(filtres["service"], str(self.ops.pk))

    def test_un_parent_incompatible_invalide_les_enfants(self):
        filtres = filtres_organisation_coherents(self.commandant, {
            "service": str(self.ops.pk), "sector": str(self.moteurs.pk), "section": str(self.sec_m1.pk)})
        self.assertEqual(filtres["service"], str(self.ops.pk))
        self.assertIsNone(filtres["sector"])
        self.assertIsNone(filtres["section"])

    def _occurrence(self, service, secteur, designation):
        type_asset = AssetType.objects.create(name=f"Type {designation}", category="MCO", sector=secteur)
        asset = Asset.objects.create(
            asset_type=type_asset, ship=self.navire, service=service, sector=secteur, designation=designation,
            internal_id=designation[:12],
        )
        plan = MaintenancePlan.objects.create(scope="ASSET", asset=asset, name=f"Plan {designation}", every_n_days=30)
        return MaintenanceOccurrence.objects.create(plan=plan, asset=asset, scheduled_for=timezone.localdate(), status="PLANNED")

    def _titres(self, user, **filtres):
        self.client.force_login(user)
        reponse = self.client.get(reverse("calendar-events"), {"view": "month", "date": str(timezone.localdate()), **filtres})
        self.assertEqual(reponse.status_code, 200)
        return " | ".join(evenement["title"] for evenement in reponse.json())

    def test_un_service_hors_perimetre_ne_renvoie_rien_et_n_elargit_pas_a_tous(self):
        self._occurrence(self.prop, self.moteurs, "Pompe MOTEURS")
        self._occurrence(self.ops, self.passerelle, "Radar PASSERELLE")
        sans_filtre = self._titres(self.chef_secteur)
        self.assertIn("Pompe MOTEURS", sans_filtre)
        self.assertNotIn("Radar PASSERELLE", sans_filtre)
        hors = self._titres(self.chef_secteur, service=self.ops.pk)
        self.assertNotIn("Radar PASSERELLE", hors)  # jamais de données hors périmètre
        self.assertNotIn("Pompe MOTEURS", hors)  # et pas d'élargissement à « Tous »
        propre = self._titres(self.chef_secteur, service=self.prop.pk)
        self.assertIn("Pompe MOTEURS", propre)

    def test_le_commandant_filtre_service_par_service(self):
        self._occurrence(self.prop, self.moteurs, "Pompe MOTEURS")
        self._occurrence(self.ops, self.passerelle, "Radar PASSERELLE")
        self.assertIn("Radar PASSERELLE", self._titres(self.commandant, service=self.ops.pk))
        self.assertNotIn("Pompe MOTEURS", self._titres(self.commandant, service=self.ops.pk))
