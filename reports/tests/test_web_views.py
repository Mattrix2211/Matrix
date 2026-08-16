"""Tests de la vue web du bilan PDF (T10) — bouton "Générer le bilan".

Vérifie l'accès selon le rôle, le périmètre automatique (pas de drill-down),
la génération du PDF en téléchargement et la gestion de PerimetreNonAutorise.
"""
from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import UserProfile
from org.models import Sector, Service, Ship
from reports.services import PerimetreNonAutorise


class GenererBilanViewTests(TestCase):
    def setUp(self):
        self.navire = Ship.objects.create(name="Navire T10", code="T10")
        self.service = Service.objects.create(ship=self.navire, name="Service T10")
        self.secteur = Sector.objects.create(service=self.service, name="Secteur T10")
        self.autre_secteur = Sector.objects.create(service=self.service, name="Autre secteur")

        self.chef = User.objects.create_user(username="chef", password="pass")
        UserProfile.objects.filter(user=self.chef).update(
            role="CHEF_SECTEUR", sector=self.secteur
        )
        self.chef.refresh_from_db()

        self.equipier = User.objects.create_user(username="equipier", password="pass")
        UserProfile.objects.filter(user=self.equipier).update(
            role="EQUIPIER", sector=self.secteur
        )
        self.equipier.refresh_from_db()

        self.chef_sans_perimetre = User.objects.create_user(username="chef2", password="pass")
        UserProfile.objects.filter(user=self.chef_sans_perimetre).update(role="CHEF_SECTION")
        self.chef_sans_perimetre.refresh_from_db()

        self.url = reverse("rapport-bilan")

    def test_equipier_refuse(self):
        self.client.login(username="equipier", password="pass")
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 403)

    def test_utilisateur_non_authentifie_redirige_vers_login(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response.url)

    def test_chef_sans_perimetre_est_redirige_avec_message(self):
        self.client.login(username="chef2", password="pass")
        response = self.client.get(self.url, follow=True)
        self.assertEqual(response.status_code, 200)
        messages = [str(m) for m in response.context["messages"]]
        self.assertTrue(any("périmètre" in m for m in messages))

    def test_mode_instantane_renvoie_un_pdf_en_telechargement(self):
        self.client.login(username="chef", password="pass")
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/pdf")
        self.assertIn("attachment; filename=", response["Content-Disposition"])
        self.assertTrue(response.content.startswith(b"%PDF"))

    def test_mode_periode_avec_dates_renvoie_un_pdf(self):
        self.client.login(username="chef", password="pass")
        aujourdhui = timezone.localdate()
        response = self.client.get(
            self.url,
            {
                "date_debut": (aujourdhui - timedelta(days=30)).isoformat(),
                "date_fin": aujourdhui.isoformat(),
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/pdf")
        self.assertTrue(response.content.startswith(b"%PDF"))

    def test_dates_invalides_redirige_avec_message(self):
        self.client.login(username="chef", password="pass")
        response = self.client.get(
            self.url, {"date_debut": "pas-une-date", "date_fin": "2026-01-01"}, follow=True
        )
        self.assertEqual(response.status_code, 200)
        messages = [str(m) for m in response.context["messages"]]
        self.assertTrue(any("Dates invalides" in m for m in messages))

    def test_perimetre_non_autorise_ne_leve_pas_une_erreur_500(self):
        """Le service peut lever PerimetreNonAutorise (garde-fou de scope_filters_for_user) :
        la vue doit l'intercepter proprement (message + redirection), jamais une 500."""
        self.client.login(username="chef", password="pass")
        with patch(
            "reports.web_views.generer_bilan_instantane_pdf",
            side_effect=PerimetreNonAutorise("Le périmètre demandé ne correspond pas."),
        ):
            response = self.client.get(self.url, follow=True)
        self.assertEqual(response.status_code, 200)
        messages = [str(m) for m in response.context["messages"]]
        self.assertTrue(any("autorisé" in m for m in messages))
