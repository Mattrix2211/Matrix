"""Garde : l'équipage à bord ne se lit que par l'accesseur unique de `matrix/core/equipage.py`."""
import re
from pathlib import Path

from django.conf import settings
from django.test import SimpleTestCase

MODULE_D_ACCES = "matrix/core/equipage.py"
DOSSIERS_IGNORES = {"venv", ".venv", "node_modules", ".git", "migrations", "tests", "__pycache__", "design", "docs", "media"}
# Lecture ou écriture d'attribut, saut de relation ORM, getattr et requêtes ORM nommant le champ.
MOTIF = re.compile(
    r"\.equipage_a_bord\b|__equipage_a_bord\b|getattr\([^)]*equipage_a_bord"
    r"|\b(?:values|values_list|only|defer|F|order_by|filter|exclude)\([^)]*equipage_a_bord"
)


def lectures_directes(texte):
    return [ligne.strip() for ligne in texte.splitlines() if MOTIF.search(ligne)]


class AccesseurUniqueEquipageTests(SimpleTestCase):
    def test_le_motif_reconnait_les_lectures_directes(self):
        for ligne in (
            "navire.equipage_a_bord", "{{ ship.equipage_a_bord }}", "Q(ship__equipage_a_bord='A')",
            "getattr(navire, 'equipage_a_bord')", "Ship.objects.values('equipage_a_bord')",
        ):
            self.assertTrue(lectures_directes(ligne), ligne)
        self.assertFalse(lectures_directes("equipage_a_bord(navire)"))

    def test_aucune_lecture_directe_hors_du_module_d_acces(self):
        racine = Path(settings.BASE_DIR)
        fautes = []
        for chemin in racine.rglob("*"):
            relatif = chemin.relative_to(racine)
            if (
                chemin.suffix not in (".py", ".html") or DOSSIERS_IGNORES & set(relatif.parts)
                or chemin.name.startswith("test_") or relatif.as_posix() == MODULE_D_ACCES
            ):
                continue
            for ligne in lectures_directes(chemin.read_text(encoding="utf-8")):
                fautes.append(f"{relatif.as_posix()} : {ligne}")
        self.assertEqual(fautes, [], "Utilisez equipage_a_bord(navire) de matrix.core.equipage.")
