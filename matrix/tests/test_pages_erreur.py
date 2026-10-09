"""Passe finale : pages 403/404/500 en français, champs date, heure locale des brouillons, lecture seule."""
from datetime import datetime, timezone as tz

from django.contrib.auth.models import User
from django.template.loader import render_to_string
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import UserProfile
from assets.models import Installation
from matrix.core.models import Brouillon
from org.models import Sector, Service, Ship
from training.models import TrainingCourse


class PagesErreurTests(TestCase):
    def setUp(self):
        self.navire = Ship.objects.create(name="FREMM", code="FR-ER", double_equipage=True, equipage_a_bord="A")
        self.service = Service.objects.create(ship=self.navire, name="Énergie")
        self.secteur = Sector.objects.create(service=self.service, name="Propulsion")
        self.terre = self._marin("terre", "COMMANDANT", "B")
        self.bord = self._marin("bord", "COMMANDANT", "A")

    def _marin(self, nom, role, equipage):
        user = User.objects.create_user(username=nom, password="pass")
        UserProfile.objects.update_or_create(user=user, defaults={"role": role, "ship": self.navire, "equipage": equipage})
        return user

    def test_403_lecture_seule_habille(self):
        self.client.login(username="terre", password="pass")
        r = self.client.post(reverse("asset-import"), {})
        self.assertEqual(r.status_code, 403)
        self.assertTemplateUsed(r, "403.html")
        self.assertContains(r, "Accès refusé", status_code=403)
        self.assertContains(r, "équipage est à terre", status_code=403)
        self.assertContains(r, 'class="mx-coque"', status_code=403)

    def test_404_habille(self):
        self.client.login(username="bord", password="pass")
        r = self.client.get(reverse("formation-detail", args=[999999]))
        self.assertEqual(r.status_code, 404)
        self.assertTemplateUsed(r, "404.html")
        self.assertContains(r, "Page introuvable", status_code=404)

    def test_403_gabarit_ne_montre_pas_le_texte_de_l_exception(self):
        html = render_to_string("403.html", {"exception": "secret interne"})
        self.assertIn("Accès refusé", html)
        self.assertNotIn("secret interne", html)

    def test_500_autonome_en_francais(self):
        html = render_to_string("500.html")
        self.assertIn("Une erreur est survenue", html)
        self.assertNotIn("<script", html)

    def test_champs_personnalises_masques_a_terre(self):
        install = Installation.objects.create(designation="Groupe", ship=self.navire, service=self.service, sector=self.secteur)
        url = reverse("installation-detail", args=[install.pk])
        self.client.login(username="terre", password="pass")
        self.assertNotContains(self.client.get(url), 'data-bs-target="#editInstallationModal"><i')
        self.client.login(username="bord", password="pass")
        self.assertContains(self.client.get(url), 'data-bs-target="#editInstallationModal"><i')

    def test_date_de_validation_au_format_iso(self):
        TrainingCourse.objects.create(title="Incendie")
        self.client.login(username="bord", password="pass")
        r = self.client.get(reverse("formation-list"))
        self.assertContains(r, f'name="completed_at" value="{timezone.localdate():%Y-%m-%d}"')

    def test_brouillon_renvoye_en_heure_locale(self):
        b = Brouillon.objects.create(user=self.bord, cle="cr:1", contenu={"note": "x"})
        Brouillon.objects.filter(pk=b.pk).update(updated_at=datetime(2026, 7, 7, 17, 23, tzinfo=tz.utc))
        self.client.login(username="bord", password="pass")
        d = self.client.get(reverse("brouillon"), {"cle": "cr:1"}).json()
        self.assertTrue(d["mis_a_jour"].startswith("2026-07-07T19:23"))
