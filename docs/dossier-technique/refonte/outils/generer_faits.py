"""Génère refonte/faits.yaml : registre unique des chiffres cités dans les documents.

Usage : python generer_faits.py <racine_etat_B> <dossier-technique> <sortie.yaml>
Chaque fait porte sa valeur, sa méthode et sa source. Les documents ne recopient jamais un chiffre : ils l'appellent
par {{fait:nom}} ; le contrôle C3 refuse un chiffre en dur qui contredit ce registre. Lecture seule sur l'état B.
"""
import json
import re
import sys
from pathlib import Path

import yaml

B = Path(sys.argv[1]).resolve()
D = Path(sys.argv[2]).resolve()
SORTIE = Path(sys.argv[3])
inv = json.loads((D / "couverture/etat_B/inventaire.json").read_text(encoding="utf-8"))
routes = [r["route"] for r in inv["routes"]]
tests_def = 0
for f in list(B.glob("*/tests/*.py")) + list(B.glob("*/tests.py")):
    tests_def += len(re.findall(r"^\s+def test_", f.read_text(encoding="utf-8"), re.M))
migrations = len(list(B.glob("*/migrations/0*.py")))
settings = (B / "matrix/settings.py").read_text(encoding="utf-8")
variables = set(re.findall(r"(?:getenv|environ\.get|env\.get)\(\s*[\"']([A-Z_0-9]+)[\"']", settings)) | set(re.findall(r"(?:environ|env)\[\s*[\"']([A-Z_0-9]+)[\"']\s*\]", settings)) | set(re.findall(r"[\"']([A-Z_0-9]{4,})[\"']\s+in\s+(?:os\.)?(?:environ|env)", settings))
roles = re.findall(r"^\s+([A-Z_]+) = \d$", (B / "matrix/core/roles.py").read_text(encoding="utf-8"), re.M)

F = {
    "n_modeles": (len(inv["modeles"]), "comptage des modèles Django du projet", "couverture/etat_B/inventaire.json"),
    "n_routes": (len(routes), "routes résolues par l'URLconf", "couverture/etat_B/inventaire.json"),
    "n_routes_pages": (sum(1 for r in routes if not r.startswith(("admin/", "api/"))), "routes hors admin/ et api/", "inventaire.json"),
    "n_routes_api": (sum(1 for r in routes if r.startswith("api/")), "routes préfixées api/", "inventaire.json"),
    "n_routes_admin": (sum(1 for r in routes if r.startswith("admin/")), "routes préfixées admin/", "inventaire.json"),
    "n_taches_planifiees": (len(inv["beat"]), "entrées CELERY_BEAT_SCHEDULE", "inventaire.json"),
    "n_commandes": (len(inv["commandes"]), "fichiers management/commands", "inventaire.json"),
    "n_actions_seuil": (len(inv["actions_seuils"]), "entrées de REGISTRE_ACTIONS", "inventaire.json"),
    "n_modules_activables": (len(inv["registres_modules"]["REGISTRE_MODULES"]), "entrées de REGISTRE_MODULES", "inventaire.json"),
    "n_signaux": (len(inv["signaux"]), "récepteurs @receiver", "inventaire.json"),
    "n_migrations": (migrations, "fichiers 0*.py sous */migrations", "arborescence de l'état B"),
    "n_variables_environnement": (len(variables), "variables lues par matrix/settings.py", "settings.py"),
    "n_roles": (len(roles), "membres de RoleLevel", "matrix/core/roles.py"),
    "n_fonctions_test_indentees": (tests_def, "def test_ indentés sous */tests", "arborescence de l'état B ; n'est pas le nombre de tests exécutés"),
    "n_tests_executes_rapportes": (3963, "rapporté par les comptes rendus de lots (suite complète SQLite) — non rejoué", "source antérieure [R]"),
    "n_decisions_v12": (125, "décisions du dossier V1.2", "branche du dossier V1.2 (accès restreint)"),
    "n_ecarts_registre": (26, "écarts A1 à A26", "5_registre/registre.json"),
    "n_points_a_confirmer": (8, "points B1 à B8", "5_registre/registre.json"),
    "n_propositions": (7, "propositions D1 à D7", "5_registre/registre.json"),
    "n_schemas": (42, "sources Mermaid", "schemas/src"),
    "n_applications": (21, "applications fonctionnelles (hors noyau)", "INSTALLED_APPS"),
}
sortie = {k: {"valeur": v[0], "methode": v[1], "source": v[2]} for k, v in F.items()}
SORTIE.write_text("# Généré par refonte/outils/generer_faits.py — ne pas éditer à la main.\n" + yaml.safe_dump(sortie, allow_unicode=True, sort_keys=False), encoding="utf-8")
for k, v in F.items():
    print(f"{k:32s} {v[0]}")
