"""Contrastes WCAG AA des jetons de couleur de matrix.css, en clair et en sombre : texte 4,5:1, composants d'interface 3:1."""
import re
from pathlib import Path

from django.test import SimpleTestCase

CSS = Path(__file__).resolve().parents[1] / "static" / "css" / "matrix.css"


def _luminance(hexa):
    r, g, b = (int(hexa.lstrip("#")[i:i + 2], 16) / 255 for i in (0, 2, 4))
    lin = lambda c: c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    return 0.2126 * lin(r) + 0.7152 * lin(g) + 0.0722 * lin(b)


def _contraste(a, b):
    la, lb = sorted((_luminance(a), _luminance(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def _jetons(bloc):
    return dict(re.findall(r"--([\w-]+):\s*(#[0-9A-Fa-f]{6}|var\(--[\w-]+\))", bloc))


def _resoudre(jetons):
    """Remplace les références var(--x) par leur couleur."""
    def valeur(nom):
        v = jetons[nom]
        return valeur(v[6:-1]) if v.startswith("var(") else v
    return {nom: valeur(nom) for nom in jetons}


class ContrastesTests(SimpleTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        css = CSS.read_text(encoding="utf-8")
        debut_sombre = css.index('\n[data-theme="sombre"] {')
        racine = css[css.index(":root {"):debut_sombre]
        sombre = css[debut_sombre:]
        sombre = sombre[:sombre.index("}")]
        cls.clair = _resoudre(_jetons(racine))
        cls.sombre = _resoudre({**_jetons(racine), **_jetons(sombre)})

    def _verifier(self, jetons, textes, fonds, seuil, composants=False):
        for fond in fonds:
            for nom in textes:
                ratio = _contraste(jetons[nom], jetons[fond])
                self.assertGreaterEqual(ratio, seuil, f"{nom} sur {fond} : {ratio:.2f}:1 < {seuil}:1")

    def test_textes_clair(self):
        self._verifier(self.clair, ("text", "text-sec", "text-ter", "lien", "attention-texte", "ok-texte", "red-texte"), ("bg", "surface"), 4.5)

    def test_textes_sombre(self):
        self._verifier(self.sombre, ("text", "text-sec", "text-ter", "signal", "amber", "green-tech", "red-texte"), ("bg", "surface"), 4.5)

    def test_composants_d_interface(self):
        self._verifier(self.clair, ("signal-ui", "focus"), ("bg", "surface"), 3.0)
