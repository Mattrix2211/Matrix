"""Tests UX-0.7 : page de démonstration des composants (docs/UX.md §26.1)."""
import re

from unittest import mock

from django.contrib.auth.models import User
from django.template import TemplateDoesNotExist
from django.test import SimpleTestCase, TestCase

from accounts.models import Roles, UserProfile
from matrix.core.icones import ICONES
from matrix.tests.test_icones import MOTIF_EMOJI
from matrix.styleguide import COMPOSANTS, lire_parametres, rapport_contraste, tableau_contrastes, variables_css

URL = "/styleguide/"


def creer(nom, role=None, **extra):
    utilisateur = User.objects.create_user(nom, password="x", **extra)
    if role:
        UserProfile.objects.update_or_create(user=utilisateur, defaults={"role": role})
        utilisateur.refresh_from_db()
    return utilisateur


class AccesTests(TestCase):
    def test_anonyme_redirige_vers_connexion(self):
        reponse = self.client.get(URL)
        self.assertEqual(reponse.status_code, 302)
        self.assertIn("/login/", reponse["Location"])

    def test_roles_non_administrateurs_refuses(self):
        for role in (Roles.EQUIPIER, Roles.CHEF_SERVICE, Roles.COMMANDANT):
            with self.subTest(role=role):
                self.client.force_login(creer(f"u_{role}", role))
                self.assertEqual(self.client.get(URL).status_code, 403)

    def test_administrateurs_autorises(self):
        self.client.force_login(creer("an", Roles.ADMIN_NAVIRE))
        self.assertEqual(self.client.get(URL).status_code, 200)
        self.client.force_login(creer("root", is_superuser=True))
        self.assertEqual(self.client.get(URL).status_code, 200)


class ContenuTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = creer("an", Roles.ADMIN_NAVIRE)

    def setUp(self):
        self.client.force_login(self.admin)
        self.html = self.client.get(URL).content.decode()

    def test_chaque_composant_est_present_et_rendu(self):
        for composant in COMPOSANTS:
            with self.subTest(composant=composant["nom"]):
                self.assertIn(f'id="composant-{composant["nom"]}"', self.html)
                self.assertTrue(lire_parametres(composant["nom"]), "paramètres non lus dans le gabarit")
        for classe in ("mx-surface", "mx-carte--interactive", "mx-carte--action", "mx-metric", "mx-attention--danger",
                       "mx-badge--ok", "mx-jauge", "mx-vide", "mx-popover__declencheur", "mx-menu", "mx-menu__item--danger",
                       "mx-modale", "mx-panneau", "mx-assistant", "data-grille", "data-grille-lecture-seule",
                       "mx-grille__cellule--erreur"):
            self.assertIn(classe, self.html)

    def test_code_d_appel_affiche_et_pas_de_brouillon(self):
        self.assertIn("{% grille id=&quot;sg-grille&quot;", self.html)
        self.assertNotIn("data-brouillon", self.html)

    def test_aucune_erreur_de_rendu(self):
        self.assertNotIn("{%", re.sub(r"<pre.*?</pre>|<code>.*?</code>", "", self.html, flags=re.S))
        self.assertNotIn("TemplateSyntaxError", self.html)

    def test_sections_couleurs_icones_typographies_espacements(self):
        for ancre in ("couleurs", "icones", "typographies", "espacements"):
            self.assertIn(f'id="{ancre}"', self.html)
        for concept in ICONES:
            self.assertIn(f"<code>{concept}</code>", self.html)
        for nom in ("Space Grotesk", "Inter", "JetBrains Mono", "--red-plein", "--red-texte", "--signal"):
            self.assertIn(nom, self.html)

    def test_bascule_de_theme_presente(self):
        self.assertIn('name="next" value="/styleguide/"', self.html)
        self.assertIn('action="/users/theme/"', self.html)
        self.assertIn("Passer en mode sombre", self.html)

    def test_aucun_emoji_ni_url_externe(self):
        self.assertIsNone(MOTIF_EMOJI.search(self.html))
        self.assertNotRegex(self.html, r'(?:src|href|action)="https?://')
        self.assertNotRegex(self.html, r"url\(\s*['\"]?https?://")


class CalculTests(SimpleTestCase):
    def test_rapport_de_contraste_connu(self):
        self.assertAlmostEqual(rapport_contraste("#000000", "#FFFFFF"), 21.0, places=2)
        self.assertAlmostEqual(rapport_contraste("#FFFFFF", "#FFFFFF"), 1.0, places=2)

    def test_variables_des_deux_themes(self):
        clair, sombre = variables_css()
        self.assertEqual(clair["bg"], "#F0F4F8")
        self.assertEqual(sombre["bg"], "#0B1929")
        self.assertEqual(clair["red-plein"], "#D62839")
        self.assertEqual(sombre["red-texte"], "#FF7F8A")
        self.assertEqual(sombre["signal"], clair["signal"])


class RobustesseTests(TestCase):
    def test_gabarit_absent_ne_casse_pas_la_page(self):
        self.client.force_login(creer("an", Roles.ADMIN_NAVIRE))
        with mock.patch("matrix.styleguide.get_template", side_effect=TemplateDoesNotExist("components/x.html")):
            self.assertEqual(lire_parametres("surface"), [])
            self.assertEqual(self.client.get(URL).status_code, 200)

    def test_gabarit_sans_commentaire(self):
        faux = mock.Mock()
        faux.template.source = "<p>sans commentaire</p>"
        with mock.patch("matrix.styleguide.get_template", return_value=faux):
            self.assertEqual(lire_parametres("surface"), [])

    def test_variable_css_absente_ne_casse_pas_la_page(self):
        self.client.force_login(creer("an", Roles.ADMIN_NAVIRE))
        clair, sombre = variables_css()
        for couleurs in (clair, sombre):
            del couleurs["red-texte"]
        with mock.patch("matrix.styleguide.variables_css", return_value=(clair, sombre)):
            self.assertEqual(self.client.get(URL).status_code, 200)
            usages = [ligne["usage"] for ligne in tableau_contrastes()]
        self.assertNotIn("Texte rouge sur une surface", usages)
        self.assertIn("Texte principal sur le fond", usages)
