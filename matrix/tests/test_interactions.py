"""Tests UX-0.4 : niveaux d'interaction (docs/UX.md §5.1) et contraste du rouge plein."""
from pathlib import Path

from django.template import Context, Template, TemplateSyntaxError
from django.test import SimpleTestCase

RACINE = Path(__file__).resolve().parents[1] / "static"
CSS = RACINE / "css" / "matrix.css"


def rendre(source, **contexte):
    return Template("{% load composants %}" + source).render(Context(contexte))


def inclure(gabarit, **p):
    return Template('{% include "components/' + gabarit + '" %}').render(Context(p))


class PopoverTests(SimpleTestCase):
    def test_popover_accessible_et_echappe(self):
        html = inclure("popover.html", libelle="Dernier relevé", texte='"><script>x</script>', icone="information")
        self.assertIn('data-bs-toggle="popover"', html)
        self.assertIn("<button", html)
        self.assertIn("bi-info-circle", html)
        self.assertIn('data-bs-title="Dernier relevé"', html)
        self.assertNotIn("<script>", html)


class MenuContextuelTests(SimpleTestCase):
    def test_menu_nomme_et_entrees(self):
        html = rendre(
            '{% menu_contextuel libelle="Actions sur la pompe" %}'
            '{% include "components/menu_item.html" with libelle="Imprimer" url="/i/" icone="impression" %}'
            '{% include "components/menu_item.html" with libelle="Supprimer" hx_post="/s/" danger=True %}'
            "{% fin_menu_contextuel %}"
        )
        self.assertIn('aria-label="Actions sur la pompe"', html)
        self.assertIn("bi-three-dots", html)
        self.assertIn('aria-haspopup="true"', html)
        self.assertIn('href="/i/"', html)
        self.assertIn('hx-post="/s/"', html)
        self.assertIn("mx-menu__item--danger", html)
        self.assertNotIn("btn-primary", html)

    def test_libelle_echappe(self):
        html = rendre('{% menu_contextuel libelle=l %}{% fin_menu_contextuel %}', l='"><b>')
        self.assertNotIn("<b>", html)


class ModaleTests(SimpleTestCase):
    def test_modale_accessible(self):
        html = rendre('{% modale id="m1" titre="Archiver ?" %}<p>Corps</p>{% fin_modale %}')
        self.assertIn('id="m1"', html)
        self.assertIn('aria-labelledby="m1-titre"', html)
        self.assertIn('id="m1-titre"', html)
        self.assertIn('aria-label="Fermer"', html)
        self.assertIn("<p>Corps</p>", html)
        self.assertIn("Annuler", html)
        self.assertNotIn("data-bs-keyboard", html)
        self.assertNotIn("hx-get", html)

    def test_modale_chargee_par_htmx(self):
        html = rendre('{% modale id="m2" titre="T" url="/c/" %}{% fin_modale %}')
        self.assertIn('hx-get="/c/"', html)
        self.assertIn('hx-trigger="show.bs.modal from:#m2"', html)
        self.assertIn("Chargement", html)

    def test_titre_echappe(self):
        html = rendre('{% modale id="m3" titre=t %}{% fin_modale %}', t="<script>")
        self.assertNotIn("<script>", html)


class PanneauTests(SimpleTestCase):
    def test_panneau_accessible(self):
        html = rendre('{% panneau_lateral id="disc" titre="Discussion" icone="discussion" %}Fil{% fin_panneau_lateral %}')
        self.assertIn("offcanvas-end", html)
        self.assertIn('aria-labelledby="disc-titre"', html)
        self.assertIn('aria-label="Fermer"', html)
        self.assertIn("bi-chat-left-text", html)
        self.assertIn("Fil", html)

    def test_panneau_gauche_et_htmx(self):
        html = rendre('{% panneau_lateral id="f" titre="Filtres" cote="start" url="/f/" %}{% fin_panneau_lateral %}')
        self.assertIn("offcanvas-start", html)
        self.assertIn('hx-trigger="show.bs.offcanvas from:#f"', html)

    def test_contenu_echappe(self):
        html = rendre('{% panneau_lateral id="p" titre="T" %}{{ x }}{% fin_panneau_lateral %}', x="<i>")
        self.assertIn("&lt;i&gt;", html)


class AssistantTests(SimpleTestCase):
    ETAPES = ["Catégorie", "Exemplaires", "Synthèse"]

    def test_etape_intermediaire(self):
        html = rendre('{% assistant titre="Ajout" etapes=e etape=2 %}Corps{% fin_assistant %}', e=self.ETAPES)
        self.assertIn("Étape 2 sur 3", html)
        self.assertEqual(html.count('aria-current="step"'), 1)
        self.assertEqual(html.count("mx-assistant__etape--faite"), 1)
        self.assertIn('value="precedent"', html)
        self.assertIn("Suivant", html)
        self.assertEqual(html.count("btn-primary"), 1)

    def test_suivant_est_le_premier_submit_du_dom(self):
        html = rendre('{% assistant titre="A" etapes=e etape=2 %}{% fin_assistant %}', e=self.ETAPES)
        self.assertLess(html.index('value="suivant"'), html.index('value="precedent"'))

    def test_id_du_titre_configurable(self):
        defaut = rendre('{% assistant titre="A" etapes=e %}{% fin_assistant %}', e=self.ETAPES)
        self.assertIn('id="assistant-titre"', defaut)
        perso = rendre('{% assistant titre="A" etapes=e id="ajout-titre" %}{% fin_assistant %}', e=self.ETAPES)
        self.assertIn('aria-labelledby="ajout-titre"', perso)
        self.assertIn('id="ajout-titre"', perso)

    def test_premiere_etape_sans_precedent(self):
        html = rendre('{% assistant titre="A" etapes=e %}{% fin_assistant %}', e=self.ETAPES)
        self.assertNotIn('value="precedent"', html)

    def test_derniere_etape_valide(self):
        html = rendre('{% assistant titre="A" etapes=e etape=3 %}{% fin_assistant %}', e=self.ETAPES)
        self.assertIn(">Valider<", html)
        self.assertNotIn("Suivant", html)

    def test_libelles_echappes(self):
        html = rendre('{% assistant titre="A" etapes=e %}{% fin_assistant %}', e=["<b>"])
        self.assertNotIn("<b>", html)

    def test_parametre_positionnel_refuse(self):
        with self.assertRaises(TemplateSyntaxError):
            rendre('{% modale "m" %}{% fin_modale %}')


class ContrasteRougeTests(SimpleTestCase):
    @staticmethod
    def luminance(hexa):
        canaux = [int(hexa[i:i + 2], 16) / 255 for i in (1, 3, 5)]
        lin = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in canaux]
        return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]

    def test_texte_blanc_sur_rouge_plein_au_moins_aa(self):
        import re
        css = CSS.read_text(encoding="utf-8")
        rouge = re.search(r"--red-plein:\s*(#[0-9A-Fa-f]{6})", css).group(1)
        clair, fonce = sorted((self.luminance("#FFFFFF"), self.luminance(rouge)), reverse=True)
        self.assertGreaterEqual((clair + 0.05) / (fonce + 0.05), 4.5)

    def test_rouge_texte_au_moins_aa_dans_les_deux_themes(self):
        import re
        css = CSS.read_text(encoding="utf-8")
        sombre = css[css.index('[data-theme="sombre"] {'):]
        clair = css[:css.index('[data-theme="sombre"] {')]
        fonds = {"clair": ("#F0F4F8", "#FFFFFF"), "sombre": ("#0B1929", "#12263A")}
        for theme, bloc in (("clair", clair), ("sombre", sombre)):
            texte = re.search(r"--red-texte:\s*(#[0-9A-Fa-f]{6})", bloc).group(1)
            for fond in fonds[theme]:
                haut, bas = sorted((self.luminance(texte), self.luminance(fond)), reverse=True)
                self.assertGreaterEqual((haut + 0.05) / (bas + 0.05), 4.5, (theme, fond))
        self.assertIn(".mx-menu__item--danger:hover { color: var(--red-texte); }", css)

    def test_pastilles_rouges_utilisent_le_rouge_plein(self):
        css = CSS.read_text(encoding="utf-8")
        self.assertIn(".mx-badge--danger { background: var(--red-plein); color: var(--paper); }", css)
        self.assertIn("background-color: var(--red-plein) !important;", css)
        self.assertNotIn("background: var(--red); color: var(--ink)", css)


class CssInteractionsTests(SimpleTestCase):
    def test_bloc_sans_couleur_en_dur(self):
        import re
        css = CSS.read_text(encoding="utf-8")
        bloc = css[css.index("Niveaux d'interaction"):]
        for classe in (".mx-modale", ".mx-panneau", ".mx-menu", ".mx-assistant__etape--actuelle"):
            self.assertIn(classe, bloc)
        self.assertNotRegex(bloc, r"#[0-9a-fA-F]{3,8}\b")

    def test_echap_ferme_les_popovers(self):
        js = (RACINE / "js" / "matrix.js").read_text(encoding="utf-8")
        self.assertIn("'Escape'", js)
