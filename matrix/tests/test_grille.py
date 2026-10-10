"""Tests UX-0.5 : grille de saisie façon tableur (docs/UX.md §5.2)."""
import shutil
import subprocess
import unittest
from pathlib import Path

from django.template import Context, Template
from django.test import SimpleTestCase

TESTS = Path(__file__).resolve().parent

COLONNES = [
    {"nom": "serie", "libelle": "N° de série"},
    {"nom": "controle", "libelle": "Date de contrôle", "type": "date"},
    {"nom": "etat", "libelle": "État", "type": "conformite"},
]
LIGNES = [
    {"cle": "1", "libelle": "Extincteur 1", "valeurs": {"serie": "A1", "etat": "conforme"}},
    {"cle": "2", "libelle": "Extincteur 2", "valeurs": {"serie": '"><script>x</script>'},
     "erreurs": {"controle": "Date invalide"}},
]


def rendre(**extra):
    contexte = {"colonnes": COLONNES, "lignes": LIGNES}
    contexte.update(extra)
    return Template(
        '{% load composants %}{% grille id="g1" libelle="Contrôle des extincteurs" '
        "colonnes=colonnes lignes=lignes lecture_seule=ro %}<p>Observations</p>{% fin_grille %}"
    ).render(Context(contexte))


class GrilleRenduTests(SimpleTestCase):
    def test_accessibilite(self):
        html = rendre(ro=False)
        self.assertIn('role="grid"', html)
        self.assertIn('aria-label="Contrôle des extincteurs"', html)
        self.assertIn('scope="col"', html)
        self.assertIn('role="rowheader"', html)
        self.assertIn('aria-label="N° de série : Extincteur 1"', html)
        self.assertNotIn("aria-readonly", html)

    def test_champs_et_conformite(self):
        html = rendre(ro=False)
        self.assertIn('name="1__serie"', html)
        self.assertIn('name="2__etat"', html)
        self.assertIn('<option value="conforme" selected>Conforme</option>', html)
        self.assertIn("Non conforme", html)
        self.assertIn('placeholder="JJ/MM/AAAA"', html)
        self.assertIn("Observations", html)

    def test_action_principale_unique_et_outils(self):
        html = rendre(ro=False)
        self.assertEqual(html.count("btn-primary"), 1)
        self.assertIn("Tout conforme", html)
        self.assertIn("Recopier vers le bas", html)
        self.assertIn("Ctrl+D", html)
        self.assertIn('type="submit"', html)
        self.assertIn("Aucune modification", html)

    def test_erreur_dans_la_cellule(self):
        html = rendre(ro=False)
        self.assertIn('aria-invalid="true"', html)
        self.assertIn("Date invalide", html)
        self.assertIn('aria-describedby="g1-2-controle-erreur"', html)

    def test_echappement(self):
        html = rendre(ro=False)
        self.assertNotIn("<script>", html)

    def test_barre_masquee_sans_js(self):
        self.assertIn("data-grille-barre hidden", rendre(ro=False))

    def test_valeur_none_donne_chaine_vide(self):
        lignes = [{"cle": "1", "libelle": "L", "valeurs": {"serie": None}}]
        html = rendre(ro=False, lignes=lignes)
        self.assertNotIn("None", html)
        self.assertIn('value=""', html)

    def test_initiale_hors_liste_coherente(self):
        lignes = [{"cle": "1", "libelle": "L", "valeurs": {"etat": "inconnu"}}]
        html = rendre(ro=False, lignes=lignes)
        self.assertNotIn('data-initial="inconnu"', html)
        self.assertIn('data-initial=""', html)

    def test_lecture_seule(self):
        html = rendre(ro=True)
        self.assertIn('aria-readonly="true"', html)
        self.assertNotIn("<input", html)
        self.assertNotIn("<select", html)
        self.assertNotIn("<button", html)
        self.assertIn("Conforme", html)
        self.assertIn("A1", html)


@unittest.skipUnless(shutil.which("node"), "node absent : logique JS vérifiée par le QA dans le navigateur")
class GrilleJsTests(SimpleTestCase):
    def test_logique_pure(self):
        resultat = subprocess.run(
            ["node", str(TESTS / "grille.test.js")], capture_output=True, text=True, timeout=30
        )
        self.assertEqual(resultat.returncode, 0, resultat.stderr)
