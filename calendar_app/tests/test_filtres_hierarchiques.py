"""Filtres du calendrier : cascade service > secteur > section, bornée au périmètre du compte."""
from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from accounts.models import UserProfile
from calendar_app.evenements_sources import filtres_organisation_coherents
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

    def test_l_api_ignore_un_service_hors_perimetre(self):
        self.client.force_login(self.chef_secteur)
        reponse = self.client.get(reverse("calendar-events"), {"service": self.ops.pk, "view": "month", "date": "2026-11-02"})
        self.assertEqual(reponse.status_code, 200)
