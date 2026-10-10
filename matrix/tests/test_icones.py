"""Tests UX-0.2 : polices et icônes auto-hébergées, aucun emoji, aucun lien externe.

Référence : docs/UX.md §16 (iconographie) et CLAUDE.md (principe 4 : Internet
n'existe pas, aucun CDN).
"""
import re
from pathlib import Path

from django.template import Context, Template
from django.test import SimpleTestCase

from matrix.core.icones import ICONES, classe_icone

RACINE = Path(__file__).resolve().parents[2]
STATIC = RACINE / "matrix" / "static"
DOSSIERS_EXCLUS = {"venv", ".git", "node_modules", "vendor", "design", "archive", "staticfiles", "__pycache__", "docs"}

# Émoticônes et pictogrammes colorés (hors flèches typographiques → et ↔,
# autorisées dans le texte).
MOTIF_EMOJI = re.compile(
    r"[\u2300-\u23ff\u2600-\u27bf\u2b00-\u2bff\ufe0f\u200d\U0001F000-\U0001FAFF]"
)
MOTIF_URL_EXTERNE = re.compile(r"""(?:src|href|url\()\s*=?\s*["']?https?://""")


def _fichiers(suffixes, racines=None):
    for racine in racines or [RACINE]:
        for chemin in racine.rglob("*"):
            if chemin.is_file() and chemin.suffix in suffixes and not (set(chemin.relative_to(RACINE).parts) & DOSSIERS_EXCLUS):
                yield chemin


class SansEmojiTests(SimpleTestCase):
    def test_aucun_emoji_dans_gabarits_code_et_scripts(self):
        trouves = []
        for chemin in _fichiers({".html", ".py", ".js", ".css"}):
            for numero, ligne in enumerate(chemin.read_text(encoding="utf-8").splitlines(), 1):
                if MOTIF_EMOJI.search(ligne):
                    trouves.append(f"{chemin.relative_to(RACINE)}:{numero}")
        self.assertEqual(trouves, [], "Emoji interdits (utiliser une icône Bootstrap Icons) : " + ", ".join(trouves))


class SansLienExterneTests(SimpleTestCase):
    def test_aucun_lien_externe_dans_les_gabarits(self):
        trouves = []
        for chemin in _fichiers({".html"}):
            if MOTIF_URL_EXTERNE.search(chemin.read_text(encoding="utf-8")):
                trouves.append(str(chemin.relative_to(RACINE)))
        self.assertEqual(trouves, [], "Lien http(s) externe (CDN) interdit : " + ", ".join(trouves))

    def test_aucune_reference_cdn_dans_les_feuilles_de_style_du_projet(self):
        for nom in ("fonts.css", "matrix.css"):
            contenu = (STATIC / "css" / nom).read_text(encoding="utf-8")
            self.assertNotRegex(contenu, r"https?://", nom)


class PolicesAutoHebergeesTests(SimpleTestCase):
    def test_fichiers_references_par_fonts_css_existent(self):
        contenu = (STATIC / "css" / "fonts.css").read_text(encoding="utf-8")
        references = re.findall(r'url\("\.\./([^"]+)"\)', contenu)
        self.assertTrue(references)
        for ref in references:
            fichier = STATIC / ref
            self.assertTrue(fichier.is_file() and fichier.stat().st_size > 1000, ref)

    def test_trois_familles_declarees(self):
        contenu = (STATIC / "css" / "fonts.css").read_text(encoding="utf-8")
        for famille in ("Space Grotesk", "Inter", "JetBrains Mono"):
            self.assertIn(f'font-family: "{famille}"', contenu)

    def test_bootstrap_icons_auto_heberge(self):
        css = STATIC / "vendor" / "bootstrap-icons" / "bootstrap-icons.min.css"
        self.assertTrue(css.is_file())
        self.assertNotRegex(css.read_text(encoding="utf-8"), r"url\(\s*[\"']?https?://")
        self.assertTrue((STATIC / "vendor" / "bootstrap-icons" / "fonts" / "bootstrap-icons.woff2").is_file())


class TableDesIconesTests(SimpleTestCase):
    def test_icones_du_chapitre_16(self):
        attendu = {
            "anomalie": "bi-exclamation-triangle", "calendrier": "bi-calendar3", "maintenance": "bi-tools",
            "parametres": "bi-gear", "utilisateur": "bi-person", "suppression": "bi-trash",
            "modification": "bi-pencil", "piece": "bi-box", "historique": "bi-clock-history",
            "discussion": "bi-chat-left-text", "impression": "bi-printer",
        }
        for concept, classe in attendu.items():
            self.assertEqual(classe_icone(concept), classe)

    def test_chaque_icone_existe_dans_bootstrap_icons(self):
        css = (STATIC / "vendor" / "bootstrap-icons" / "bootstrap-icons.min.css").read_text(encoding="utf-8")
        for concept, classe in ICONES.items():
            self.assertIn(f".{classe}::before", css, concept)

    def test_balise_de_gabarit(self):
        rendu = Template('{% load icones %}{% icone "suppression" "me-1" %}').render(Context())
        self.assertEqual(rendu, '<i class="bi bi-trash me-1" aria-hidden="true"></i>')

    def test_concept_inconnu_leve_une_erreur(self):
        with self.assertRaises(KeyError):
            classe_icone("inexistant")
