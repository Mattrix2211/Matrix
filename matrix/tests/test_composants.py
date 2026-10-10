"""Tests UX-0.3 : rendu des composants « cards » (docs/UX.md §14 et §26)."""
from pathlib import Path

from django.template import Context, Template, TemplateSyntaxError
from django.test import SimpleTestCase

CSS = Path(__file__).resolve().parents[1] / "static" / "css" / "matrix.css"


def rendre(source, **contexte):
    return Template("{% load composants %}" + source).render(Context(contexte))


class SurfaceTests(SimpleTestCase):
    def test_surface_avec_titre_icone_et_contenu(self):
        html = rendre('{% surface titre="Mesures" icone="maintenance" %}<p>Corps</p>{% fin_surface %}')
        self.assertIn("mx-surface", html)
        self.assertIn("Mesures", html)
        self.assertIn("bi-tools", html)
        self.assertIn("<p>Corps</p>", html)

    def test_surface_sans_survol_ni_lien(self):
        html = rendre("{% surface %}x{% fin_surface %}")
        self.assertNotIn("<a ", html)
        self.assertNotIn("interactive", html)

    def test_titre_echappe(self):
        html = rendre('{% surface titre=t %}x{% fin_surface %}', t="<script>")
        self.assertNotIn("<script>", html)

    def test_parametre_positionnel_refuse(self):
        with self.assertRaises(TemplateSyntaxError):
            rendre('{% surface "titre" %}x{% fin_surface %}')


class CartesTests(SimpleTestCase):
    def test_carte_interactive_est_un_lien(self):
        html = rendre('{% carte_interactive url="/x/" titre="Pompe" sous_titre="Salle 2" icone="piece" %}{% fin_carte_interactive %}')
        self.assertIn('<a href="/x/"', html)
        self.assertIn("mx-carte--interactive", html)
        self.assertIn("Salle 2", html)
        self.assertIn("bi-chevron-right", html)

    def test_carte_action_secondaire_par_defaut(self):
        html = rendre('{% carte_action titre="Signer" libelle="Ouvrir" url="/s/" %}{% fin_carte_action %}')
        self.assertIn("btn-outline-primary", html)
        self.assertNotIn("btn-primary", html.replace("btn-outline-primary", ""))

    def test_carte_action_principale(self):
        html = rendre('{% carte_action titre="Signer" libelle="Ouvrir" url="/s/" principale=True %}{% fin_carte_action %}')
        self.assertIn("btn btn-sm btn-primary", html)


class AttentionTests(SimpleTestCase):
    def test_danger_alerte_et_libelle_explicite(self):
        html = rendre('{% attention niveau="danger" titre="Vibration C" icone="retard" %}Détail{% fin_attention %}')
        self.assertIn("mx-attention--danger", html)
        self.assertIn('role="alert"', html)
        self.assertIn("Danger :", html)
        self.assertIn("bi-alarm", html)
        self.assertIn("Détail", html)

    def test_attention_par_defaut(self):
        html = rendre('{% attention titre="Péremption proche" %}{% fin_attention %}')
        self.assertIn("mx-attention--attention", html)
        self.assertIn('role="status"', html)
        self.assertIn("bi-exclamation-triangle", html)


class MetricTests(SimpleTestCase):
    def rendre(self, **p):
        return Template('{% include "components/metric.html" %}').render(Context(p))

    def test_metric_statique(self):
        html = self.rendre(libelle="Heures de marche", valeur="1 248", unite="h", etat="ok", detail="+42 h / mois")
        self.assertIn("1 248", html)
        self.assertIn("Conforme", html)
        self.assertIn("mx-metric--ok", html)
        self.assertNotIn("<button", html)
        self.assertNotIn("interactif", html)

    def test_metric_avec_popover_devient_bouton(self):
        html = self.rendre(libelle="Isolement", valeur="72", unite="MΩ", popover="Dernier relevé : 72 MΩ")
        self.assertIn("<button", html)
        self.assertIn('data-bs-toggle="popover"', html)
        self.assertIn("mx-metric--interactif", html)


class BadgeJaugeVideTests(SimpleTestCase):
    def inclure(self, gabarit, **p):
        return Template('{% include "components/' + gabarit + '" %}').render(Context(p))

    def test_badge_etat_icone_et_libelle(self):
        html = self.inclure("badge_etat.html", etat="danger", libelle="En retard")
        self.assertIn("mx-badge--danger", html)
        self.assertIn("bi-alarm", html)
        self.assertIn("En retard", html)

    def test_badge_neutre_par_defaut_sans_icone(self):
        html = self.inclure("badge_etat.html", libelle="Terminé")
        self.assertIn("mx-badge--neutre", html)
        self.assertNotIn("<i ", html)

    def test_jauge_accessible_et_valeur_ecrite(self):
        html = self.inclure("jauge.html", libelle="Stock", valeur=72, etat="attention")
        self.assertIn('role="progressbar"', html)
        self.assertIn('aria-valuenow="72"', html)
        self.assertIn("width: 72%", html)
        self.assertIn("72 %", html)

    def test_etat_vide_avec_action(self):
        html = self.inclure("etat_vide.html", titre="Aucune tâche", icone="maintenance", url="/n/", libelle="Créer")
        self.assertIn("Aucune tâche", html)
        self.assertIn('href="/n/"', html)

    def test_etat_vide_sans_action(self):
        html = self.inclure("etat_vide.html", titre="Rien")
        self.assertNotIn("<a ", html)


class SecuriteEtLimitesTests(SimpleTestCase):
    def inclure(self, gabarit, **p):
        return Template('{% include "components/' + gabarit + '" %}').render(Context(p))

    def test_contenu_de_bloc_non_sur_echappe(self):
        html = rendre("{% surface %}{{ x }}{% fin_surface %}", x="<b>")
        self.assertIn("&lt;b&gt;", html)
        self.assertNotIn("<b>", html)

    def test_popover_echappe(self):
        html = self.inclure("metric.html", libelle="L", valeur="1", popover='"><script>x</script>')
        self.assertNotIn("<script>", html)
        self.assertIn("hover focus", html)

    def test_carte_action_avec_contenu_et_icone(self):
        html = rendre('{% carte_action titre="T" libelle="Go" url="/a/" icone="ticket" %}{{ x }}{% fin_carte_action %}', x="<i>")
        self.assertIn("bi-wrench", html)
        self.assertIn("&lt;i&gt;", html)

    def test_carte_interactive_avec_contenu(self):
        html = rendre('{% carte_interactive url="/a/" titre="T" %}{{ x }}{% fin_carte_interactive %}', x="<u>")
        self.assertIn("mx-carte__contenu", html)
        self.assertIn("&lt;u&gt;", html)

    def test_jauge_valeurs_limites(self):
        for valeur, attendu in ((-5, 0), (250, 100), ("abc", 0), ('50%;"><x', 0), (None, 0), ("42.7", 42)):
            html = self.inclure("jauge.html", libelle="J", valeur=valeur)
            self.assertIn(f"width: {attendu}%", html, valeur)
            self.assertIn(f'aria-valuenow="{attendu}"', html, valeur)
            self.assertNotIn("<x", html)


class CssComposantsTests(SimpleTestCase):
    def test_classes_definies_et_sans_couleur_en_dur(self):
        css = CSS.read_text(encoding="utf-8")
        bloc = css[css.index("Composants « cards »"):]
        for classe in (".mx-surface", ".mx-carte--interactive", ".mx-carte--action", ".mx-metric", ".mx-attention", ".mx-badge", ".mx-jauge", ".mx-vide"):
            self.assertIn(classe, bloc)
        self.assertNotRegex(bloc, r"#[0-9a-fA-F]{3,8}\b")
        self.assertNotIn("--shadow-glow", bloc)
