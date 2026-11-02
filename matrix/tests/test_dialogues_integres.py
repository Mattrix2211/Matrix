"""Aucune boîte de dialogue native du navigateur : les confirmations passent par le dialogue intégré de Matrix."""
import re
from pathlib import Path

from django.conf import settings
from django.test import SimpleTestCase

NATIF = re.compile(r"(?<![\w.])(confirm|alert|prompt)\s*\(")


class DialoguesNatifsTests(SimpleTestCase):
    def _fichiers(self):
        racine = Path(settings.BASE_DIR)
        for dossier, motif in (("matrix/templates", "*.html"), ("matrix/static/js", "*.js")):
            for chemin in (racine / dossier).rglob(motif):
                if "vendor" not in chemin.parts:
                    yield chemin

    def test_aucun_appel_natif_dans_les_gabarits_et_scripts(self):
        trouves = []
        for chemin in self._fichiers():
            for numero, ligne in enumerate(chemin.read_text(encoding="utf-8").splitlines(), start=1):
                if NATIF.search(ligne) and "remplace confirm()" not in ligne:
                    trouves.append(f"{chemin.name}:{numero}")
        self.assertEqual(trouves, [])

    def test_aucun_onsubmit_ni_onclick_de_confirmation(self):
        trouves = []
        for chemin in self._fichiers():
            texte = chemin.read_text(encoding="utf-8")
            if re.search(r'on(submit|click)="return (?!false)', texte) or "hx-confirm" in texte:
                trouves.append(chemin.name)
        self.assertEqual(trouves, [])
