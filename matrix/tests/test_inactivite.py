"""Déconnexion automatique après inactivité (docs/UX.md §2.3) : session expirée côté serveur,
requêtes automatiques, « Rester connecté », htmx, API, page de connexion."""
import shutil
import subprocess
import time
import unittest
from pathlib import Path

from django.contrib.auth import get_user_model
from django.test import Client, SimpleTestCase, TestCase, override_settings
from django.urls import reverse

from accounts.models import AuditLog
from matrix.core.inactivite import (
    AVERTISSEMENT_DEFAUT, CLE_SESSION, DELAI_DEFAUT, DELAI_MAX, DELAI_MIN, delai_avertissement, delai_inactivite,
)

TESTS = Path(__file__).resolve().parent
AUTOMATIQUE = {"HTTP_X_MX_AUTOMATIQUE": "1"}


class InactiviteTestCase(TestCase):
    def setUp(self):
        self.marin = get_user_model().objects.create_user("marin", password="x")
        self.client.force_login(self.marin)

    def vieillir(self, secondes):
        """Simule une dernière activité vieille de N secondes."""
        session = self.client.session
        session[CLE_SESSION] = int(time.time()) - secondes
        session.save()

    def derniere_activite(self):
        return self.client.session.get(CLE_SESSION)


class ReglageDelaiTests(SimpleTestCase):
    def test_defaut_et_valeurs_valides(self):
        self.assertEqual(delai_inactivite(), DELAI_DEFAUT)
        with override_settings(INACTIVITE_DELAI_SECONDES="300"):
            self.assertEqual(delai_inactivite(), 300)

    def test_valeur_invalide_ou_hors_bornes_revient_au_defaut(self):
        for brut in ("abc", "", None, "0", "-5", str(DELAI_MIN - 1), str(DELAI_MAX + 1), "1.5"):
            with override_settings(INACTIVITE_DELAI_SECONDES=brut):
                self.assertEqual(delai_inactivite(), DELAI_DEFAUT, brut)

    def test_avertissement_borne_par_le_delai(self):
        self.assertEqual(delai_avertissement(), AVERTISSEMENT_DEFAUT)
        with override_settings(INACTIVITE_DELAI_SECONDES="60", INACTIVITE_AVERTISSEMENT_SECONDES="45"):
            self.assertEqual(delai_avertissement(), 30)
        with override_settings(INACTIVITE_AVERTISSEMENT_SECONDES="x"):
            self.assertEqual(delai_avertissement(), AVERTISSEMENT_DEFAUT)


class ExpirationTests(InactiviteTestCase):
    def test_session_recente_reste_ouverte_et_est_datee(self):
        self.assertEqual(self.client.get(reverse("home")).status_code, 200)
        self.assertIsNotNone(self.derniere_activite())

    def test_session_inactive_redirige_vers_la_connexion_avec_le_message(self):
        self.client.get(reverse("home"))
        self.vieillir(DELAI_DEFAUT + 5)
        reponse = self.client.get(reverse("user-directory") + "?q=a")
        self.assertEqual(reponse.status_code, 302)
        self.assertEqual(reponse["Location"], "/accounts/login/?expire=1&next=%2Fusers%2F%3Fq%3Da")
        self.assertNotIn("_auth_user_id", self.client.session)
        page = self.client.get(reponse["Location"])
        self.assertContains(page, "Votre session a expiré par inactivité")

    def test_connexion_sans_parametre_ne_montre_pas_le_message(self):
        self.client.logout()
        self.assertNotContains(self.client.get("/login/"), "expiré par inactivité")

    def test_delai_configurable(self):
        with override_settings(INACTIVITE_DELAI_SECONDES="120"):
            self.client.get(reverse("home"))
            self.vieillir(100)
            self.assertEqual(self.client.get(reverse("home")).status_code, 200)
            self.vieillir(130)
            self.assertEqual(self.client.get(reverse("home")).status_code, 302)

    def test_expiration_tracee(self):
        self.client.get(reverse("home"))
        self.vieillir(DELAI_DEFAUT + 5)
        self.client.get(reverse("home"))
        self.assertTrue(AuditLog.objects.filter(actor=self.marin, action="session_expiree").exists())

    def test_anonyme_non_concerne(self):
        anonyme = Client()
        reponse = anonyme.get(reverse("home"))
        self.assertEqual(reponse.status_code, 302)
        self.assertNotIn("expire", reponse["Location"])
        self.assertFalse(AuditLog.objects.filter(action="session_expiree").exists())

    def test_requete_post_expiree_sans_retour_vers_une_page_en_lecture_seule(self):
        self.client.get(reverse("home"))
        self.vieillir(DELAI_DEFAUT + 5)
        reponse = self.client.post(reverse("basculer-theme"))
        self.assertEqual(reponse["Location"], "/accounts/login/?expire=1")


class RenouvellementTests(InactiviteTestCase):
    def test_requete_normale_renouvelle(self):
        self.client.get(reverse("home"))
        self.vieillir(300)
        self.client.get(reverse("home"))
        self.assertGreater(self.derniere_activite(), int(time.time()) - 10)

    def test_requetes_automatiques_ne_renouvellent_pas(self):
        self.client.get(reverse("home"))
        self.vieillir(300)
        ancienne = self.derniere_activite()
        for url in (reverse("notifications-compteur"), reverse("brouillon") + "?cle=x"):
            self.assertLess(self.client.get(url, **AUTOMATIQUE).status_code, 400)
        self.assertEqual(self.derniere_activite(), ancienne)

    def test_requete_automatique_sur_session_expiree_renvoie_401_sans_page(self):
        self.client.get(reverse("home"))
        self.vieillir(DELAI_DEFAUT + 5)
        reponse = self.client.get(reverse("notifications-compteur"), **AUTOMATIQUE)
        self.assertEqual(reponse.status_code, 401)
        self.assertNotIn(b"<html", reponse.content)

    def test_rester_connecte_renouvelle(self):
        self.client.get(reverse("home"))
        self.vieillir(DELAI_DEFAUT - 20)
        reponse = self.client.post(reverse("session-inactivite"), HTTP_ACCEPT="application/json")
        self.assertEqual(reponse.json()["restant"], DELAI_DEFAUT)
        self.assertGreater(self.derniere_activite(), int(time.time()) - 5)

    def test_consulter_le_temps_restant_ne_prolonge_pas(self):
        self.client.get(reverse("home"))
        self.vieillir(300)
        reponse = self.client.get(reverse("session-inactivite"), **AUTOMATIQUE)
        self.assertAlmostEqual(reponse.json()["restant"], DELAI_DEFAUT - 300, delta=3)
        self.assertLess(self.derniere_activite(), int(time.time()) - 290)

    def test_rester_connecte_sur_session_expiree_renvoie_401(self):
        self.client.get(reverse("home"))
        self.vieillir(DELAI_DEFAUT + 5)
        reponse = self.client.post(reverse("session-inactivite"), HTTP_ACCEPT="application/json")
        self.assertEqual(reponse.status_code, 401)

    def test_anonyme_ne_peut_pas_prolonger(self):
        reponse = Client().post(reverse("session-inactivite"), HTTP_ACCEPT="application/json")
        self.assertEqual(reponse.status_code, 401)


class HtmxTests(InactiviteTestCase):
    def test_htmx_session_expiree_renvoie_hx_redirect_et_pas_de_page(self):
        self.client.get(reverse("home"))
        self.vieillir(DELAI_DEFAUT + 5)
        reponse = self.client.get(
            reverse("notifications-panneau"), HTTP_HX_REQUEST="true", HTTP_HX_CURRENT_URL="http://testserver/formations/?p=2"
        )
        self.assertEqual(reponse.status_code, 200)
        self.assertEqual(reponse["HX-Redirect"], "/accounts/login/?expire=1&next=%2Fformations%2F%3Fp%3D2")
        self.assertEqual(reponse.content, b"")

    def test_htmx_anonyme_renvoie_hx_redirect(self):
        reponse = Client().get(
            reverse("recherche-rapide") + "?q=ab", HTTP_HX_REQUEST="true", HTTP_HX_CURRENT_URL="http://testserver/"
        )
        self.assertEqual(reponse["HX-Redirect"], "/accounts/login/?next=%2F")
        self.assertNotIn(b"<html", reponse.content)

    def test_htmx_page_courante_sans_hote_ou_avec_controle_ignoree(self):
        for courante in ("//evil.example", "http://testserver/" + "a" * 2100):
            reponse = Client().get(
                reverse("recherche-rapide") + "?q=ab", HTTP_HX_REQUEST="true", HTTP_HX_CURRENT_URL=courante
            )
            self.assertEqual(reponse["HX-Redirect"], "/accounts/login/", courante[:30])

    def test_htmx_page_courante_etrangere_ignoree(self):
        reponse = Client().get(
            reverse("recherche-rapide") + "?q=ab", HTTP_HX_REQUEST="true", HTTP_HX_CURRENT_URL="http://evil.example/x"
        )
        self.assertEqual(reponse["HX-Redirect"], "/accounts/login/")

    def test_htmx_connecte_non_modifie(self):
        reponse = self.client.get(reverse("notifications-panneau"), HTTP_HX_REQUEST="true")
        self.assertEqual(reponse.status_code, 200)
        self.assertNotIn("HX-Redirect", reponse)

    def test_page_normale_anonyme_garde_la_redirection_habituelle(self):
        reponse = Client().get(reverse("user-directory"))
        self.assertEqual(reponse["Location"], "/accounts/login/?next=/users/")


class ApiTests(InactiviteTestCase):
    def test_api_anonyme_garde_son_code_sans_redirection(self):
        reponse = Client().get("/api/accounts/users/")
        self.assertIn(reponse.status_code, (401, 403))
        self.assertNotIn("Location", reponse)

    def test_api_session_expiree_garde_son_code_sans_redirection(self):
        self.client.get(reverse("home"))
        self.vieillir(DELAI_DEFAUT + 5)
        reponse = self.client.get("/api/accounts/users/")
        self.assertIn(reponse.status_code, (401, 403))
        self.assertNotIn("Location", reponse)


class DeconnexionNavigateurTests(InactiviteTestCase):
    def test_vraie_expiration_tracee_une_fois_avec_message_et_retour(self):
        self.client.get(reverse("home"))
        self.vieillir(DELAI_DEFAUT + 5)
        reponse = self.client.post(reverse("logout"), {"next": "/formations/"})
        self.assertEqual(reponse["Location"], "/accounts/login/?expire=1&next=%2Fformations%2F")
        self.assertEqual(AuditLog.objects.filter(actor=self.marin, action="session_expiree").count(), 1)

    def test_champ_forge_sur_session_fraiche_ne_trace_rien(self):
        self.client.get(reverse("home"))
        reponse = self.client.post(reverse("logout"), {"inactivite": "1", "next": "/formations/"})
        self.assertEqual(reponse["Location"], "/accounts/login/?next=%2Fformations%2F")
        self.assertFalse(AuditLog.objects.filter(action="session_expiree").exists())

    def test_deconnexion_volontaire_sans_message_ni_trace(self):
        self.client.get(reverse("home"))
        reponse = self.client.post(reverse("logout"))
        self.assertEqual(reponse["Location"], "/login/")
        self.assertNotContains(self.client.get(reponse["Location"]), "expiré par inactivité")
        self.assertFalse(AuditLog.objects.filter(action="session_expiree").exists())

    def test_retour_invalide_refuse(self):
        invalides = ("https://evil.example/", "//evil.example/", "javascript:alert(1)", "/a\x00b", "/" + "a" * 2000)
        for suivant in invalides:
            self.client.force_login(self.marin)
            self.client.get(reverse("home"))
            self.vieillir(DELAI_DEFAUT + 5)
            reponse = self.client.post(reverse("logout"), {"next": suivant})
            self.assertEqual(reponse["Location"], "/accounts/login/?expire=1", repr(suivant)[:30])

    def test_retour_limite_accepte(self):
        self.client.get(reverse("home"))
        reponse = self.client.post(reverse("logout"), {"next": "/" + "a" * 1990})
        self.assertIn("next=", reponse["Location"])


class PageTests(InactiviteTestCase):
    def test_delais_injectes_sans_valeur_codee_en_dur(self):
        with override_settings(INACTIVITE_DELAI_SECONDES="321", INACTIVITE_AVERTISSEMENT_SECONDES="17"):
            page = self.client.get(reverse("home"))
        self.assertContains(page, 'data-delai="321"')
        self.assertContains(page, 'data-avertissement="17"')
        self.assertContains(page, 'role="alertdialog"')
        self.assertContains(page, "js/inactivite.js")

    def test_dialogue_lie_au_marin_de_la_page(self):
        page = self.client.get(reverse("home"))
        self.assertContains(page, f'data-utilisateur="{self.marin.pk}"')
        self.client.get(reverse("home"))
        reponse = self.client.get(reverse("session-inactivite"), **AUTOMATIQUE)
        self.assertEqual(reponse.json()["utilisateur"], self.marin.pk)

    def test_aucun_jeton_dans_les_data_attributs(self):
        page = self.client.get(reverse("home")).content.decode()
        debut = page.index('id="mx-inactivite"')
        balise = page[debut:page.index(">", debut)]
        self.assertNotIn("csrf", balise.lower())
        self.assertNotIn("token", balise.lower())

    def test_anonyme_sans_dialogue(self):
        self.assertNotContains(Client().get("/login/"), "mx-inactivite")

    def test_script_sans_delai_en_dur(self):
        source = (Path(__file__).resolve().parents[1] / "static" / "js" / "inactivite.js").read_text(encoding="utf-8")
        self.assertNotRegex(source, r"\b(900|60000|15\s*\*\s*60)\b")


@unittest.skipUnless(shutil.which("node"), "node absent : logique JS vérifiée par le QA dans le navigateur")
class InactiviteJsTests(SimpleTestCase):
    def test_logique_pure(self):
        resultat = subprocess.run(
            ["node", str(TESTS / "inactivite.test.js")], capture_output=True, text=True, timeout=30
        )
        self.assertEqual(resultat.returncode, 0, resultat.stderr)
