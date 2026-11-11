"""Inventaire du code de Matrix, en lecture seule.

Usage : python inventaire.py <racine_du_code> <dossier_de_sortie>

Charge Django sur la copie du code indiquée (jamais sur ce dépôt de documentation),
sans accès base de données, et produit des fichiers Markdown et JSON.
"""
import ast
import json
import os
import re
import sys
from collections import defaultdict
from pathlib import Path

RACINE = Path(sys.argv[1]).resolve()
SORTIE = Path(sys.argv[2]).resolve()
SORTIE.mkdir(parents=True, exist_ok=True)

os.chdir(RACINE)
sys.path.insert(0, str(RACINE))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "matrix.settings")
os.environ["DJANGO_DEBUG"] = "1"

import django  # noqa: E402

django.setup()

from django.apps import apps  # noqa: E402
from django.conf import settings  # noqa: E402
from django.contrib.contenttypes.fields import GenericForeignKey  # noqa: E402
from django.urls import URLPattern, URLResolver, get_resolver  # noqa: E402

PAQUETS = [c.label for c in apps.get_app_configs() if c.name.split(".")[0] in {
    "accounts", "org", "assets", "maintenance", "logistics", "training", "quarts", "absences", "taches",
    "demandes", "annonces", "programme", "postes", "documentation", "retex", "rondes", "threads",
    "notifications", "dashboard", "calendar_app", "reports", "matrix"}]


def cible_nom(champ):
    rel = champ.related_model
    return rel._meta.label if rel and not isinstance(rel, str) else str(rel)


def inventaire_modeles():
    sortie = []
    for modele in apps.get_models():
        if modele._meta.app_label not in PAQUETS:
            continue
        champs, relations, generiques = [], [], []
        for f in modele._meta.get_fields():
            if getattr(f, "auto_created", False) and not f.concrete:
                continue
            if isinstance(f, GenericForeignKey):
                generiques.append(f.name)
                continue
            if f.is_relation and f.related_model is not None:
                cle = {"ForeignKey": "FK", "OneToOneField": "1-1", "ManyToManyField": "N-N"}.get(
                    type(f).__name__, type(f).__name__)
                od = getattr(getattr(f, "remote_field", None), "on_delete", None)
                relations.append({"champ": f.name, "type": cle, "vers": cible_nom(f),
                                  "on_delete": od.__name__ if od else None, "null": bool(f.null)})
            else:
                champs.append(f.name)
        sortie.append({"app": modele._meta.app_label, "modele": modele.__name__, "champs": champs,
                       "relations": relations, "generiques": generiques,
                       "uuid": any(type(f).__name__ == "UUIDField" for f in modele._meta.get_fields()
                                   if hasattr(f, "get_internal_type"))})
    return sortie


def parcourir(resolveur, prefixe=""):
    for p in resolveur.url_patterns:
        if isinstance(p, URLResolver):
            yield from parcourir(p, prefixe + str(p.pattern))
        elif isinstance(p, URLPattern):
            cb = p.callback
            vue = getattr(cb, "view_class", None) or cb
            yield {"route": prefixe + str(p.pattern), "nom": p.name,
                   "vue": f"{vue.__module__}.{vue.__name__}"}


def inventaire_routes():
    return list(parcourir(get_resolver()))


def inventaire_beat():
    sortie = []
    for nom, cfg in getattr(settings, "CELERY_BEAT_SCHEDULE", {}).items():
        sortie.append({"nom": nom, "tache": cfg.get("task"), "planification": str(cfg.get("schedule"))})
    return sortie


def inventaire_commandes():
    sortie = []
    for chemin in sorted(RACINE.glob("**/management/commands/*.py")):
        if chemin.name != "__init__.py" and "venv" not in chemin.parts:
            sortie.append(str(chemin.relative_to(RACINE)))
    return sortie


def inventaire_registres():
    from matrix.core.role_thresholds import REGISTRE_ACTIONS
    from matrix.core import modules as mod

    actions = [{"cle": a.cle, "libelle": a.libelle, "categorie": a.categorie, "portee": a.portee,
                "defaut": a.defaut.name, "ouverte_au_second": a.ouverte_au_second}
               for a in REGISTRE_ACTIONS]
    registre_modules = [m for m in dir(mod) if m.isupper() and not m.startswith("_")]
    contenu = {}
    for nom in registre_modules:
        valeur = getattr(mod, nom)
        if isinstance(valeur, (list, tuple, dict, set)):
            contenu[nom] = [str(v) for v in (valeur if not isinstance(valeur, dict) else valeur.items())]
    return actions, contenu


def dependances():
    """Imports d'un paquet vers un autre (niveau module et dans les fonctions), hors tests et migrations."""
    noms = {p for p in PAQUETS if p != "matrix"}
    matrice = defaultdict(lambda: defaultdict(int))
    for chemin in RACINE.rglob("*.py"):
        rel = chemin.relative_to(RACINE)
        if rel.parts[0] not in noms or "tests" in rel.parts or "migrations" in rel.parts \
                or rel.name.startswith("test"):
            continue
        try:
            arbre = ast.parse(chemin.read_text(encoding="utf-8"))
        except SyntaxError:
            continue
        for n in ast.walk(arbre):
            cibles = []
            if isinstance(n, ast.ImportFrom) and n.module and n.level == 0:
                cibles.append(n.module.split(".")[0])
            elif isinstance(n, ast.Import):
                cibles.extend(a.name.split(".")[0] for a in n.names)
            for c in cibles:
                if c in noms and c != rel.parts[0]:
                    matrice[rel.parts[0]][c] += 1
    return {a: dict(b) for a, b in matrice.items()}


def signaux():
    sortie = []
    for chemin in RACINE.rglob("*.py"):
        rel = chemin.relative_to(RACINE)
        if "tests" in rel.parts or "migrations" in rel.parts or rel.parts[0] in {"venv", "design"}:
            continue
        for i, ligne in enumerate(chemin.read_text(encoding="utf-8").splitlines(), 1):
            if re.match(r"\s*@receiver\(", ligne):
                sortie.append(f"{rel}:{i} {ligne.strip()}")
    return sortie


def fichiers_par_paquet():
    sortie = {}
    for p in PAQUETS:
        if p == "matrix":
            continue
        base = RACINE / p
        def nb(motif):
            return len([f for f in base.glob(motif) if f.is_file()])
        tests = list(base.glob("tests/**/test*.py")) + list(base.glob("test*.py"))
        nb_tests = sum(len(re.findall(r"^\s+def test_", t.read_text(encoding="utf-8"), re.M)) for t in tests)
        sortie[p] = {"fichiers_py": len(list(base.rglob("*.py"))), "migrations": nb("migrations/0*.py"),
                     "services": sorted(f.name for f in base.glob("*services*.py")),
                     "fichiers_de_test": len(tests), "tests": nb_tests,
                     "gabarits": len(list(base.rglob("templates/**/*.html")))}
    return sortie


def main():
    modeles = inventaire_modeles()
    routes = inventaire_routes()
    beat = inventaire_beat()
    commandes = inventaire_commandes()
    actions, registres_modules = inventaire_registres()
    deps = dependances()
    sigs = signaux()
    fich = fichiers_par_paquet()

    donnees = {"modeles": modeles, "routes": routes, "beat": beat, "commandes": commandes,
               "actions_seuils": actions, "registres_modules": registres_modules, "dependances": deps,
               "signaux": sigs, "paquets": fich}
    (SORTIE / "inventaire.json").write_text(json.dumps(donnees, ensure_ascii=False, indent=1), encoding="utf-8")

    par_app = defaultdict(list)
    for m in modeles:
        par_app[m["app"]].append(m)
    routes_par_paquet = defaultdict(int)
    for r in routes:
        routes_par_paquet[r["vue"].split(".")[0]] += 1

    L = ["# Inventaire mesuré de l'état B (généré)", "",
         f"Généré par `outils/inventaire.py` sur la copie du code `{RACINE.name}`. Ne pas éditer à la main.", "",
         "## Synthèse par paquet", "",
         "| Paquet | Modèles | Relations | Relations génériques | Routes | Migrations | Tests (fonctions) | Services |",
         "|---|---|---|---|---|---|---|---|"]
    for p in sorted(par_app):
        ms = par_app[p]
        rel = sum(len(m["relations"]) for m in ms)
        gen = sum(len(m["generiques"]) for m in ms)
        f = fich.get(p, {})
        L.append(f"| `{p}` | {len(ms)} | {rel} | {gen} | {routes_par_paquet.get(p, 0)} | "
                 f"{f.get('migrations', '—')} | {f.get('tests', '—')} | {', '.join(f.get('services', [])) or '—'} |")
    L.append(f"| **Total** | **{len(modeles)}** | **{sum(len(m['relations']) for m in modeles)}** | "
             f"**{sum(len(m['generiques']) for m in modeles)}** | **{len(routes)}** | "
             f"**{sum(f.get('migrations', 0) for f in fich.values())}** | "
             f"**{sum(f.get('tests', 0) for f in fich.values())}** | |")
    L += ["", "Paquets sans modèle : " + ", ".join(sorted(set(PAQUETS) - set(par_app))) + ".", "",
          "## Tâches planifiées (Celery beat)", "", "| Nom | Tâche | Planification |", "|---|---|---|"]
    L += [f"| `{b['nom']}` | `{b['tache']}` | {b['planification']} |" for b in beat]
    L += ["", "## Commandes de gestion", ""] + [f"- `{c}`" for c in commandes]
    L += ["", "## Actions à seuil de rôle configurable", "",
          "| Clé | Catégorie | Portée | Seuil par défaut | Second |", "|---|---|---|---|---|"]
    L += [f"| `{a['cle']}` | {a['categorie']} | {a['portee']} | {a['defaut']} | "
          f"{'oui' if a['ouverte_au_second'] else ''} |" for a in actions]
    L += ["", "## Dépendances entre paquets (nombre d'imports, hors tests)", "",
          "| De → vers | Imports |", "|---|---|"]
    for a in sorted(deps):
        L.append(f"| `{a}` → " + ", ".join(f"`{b}` ({n})" for b, n in sorted(deps[a].items())) + " | |")
    L += ["", "## Signaux (`@receiver`)", ""] + [f"- `{s}`" for s in sigs]
    L += ["", "## Relations génériques", ""]
    for m in modeles:
        if m["generiques"]:
            L.append(f"- `{m['app']}.{m['modele']}` : {', '.join(m['generiques'])}")
    (SORTIE / "INVENTAIRE.md").write_text("\n".join(L) + "\n", encoding="utf-8")

    D = ["# Dictionnaire des modèles de l'état B (généré)", ""]
    for p in sorted(par_app):
        D += [f"## `{p}`", ""]
        for m in sorted(par_app[p], key=lambda x: x["modele"]):
            D.append(f"### {m['modele']}")
            D.append("- Champs : " + (", ".join(f"`{c}`" for c in m["champs"]) or "—"))
            for r in m["relations"]:
                od = f", `{r['on_delete']}`" if r["on_delete"] else ""
                D.append(f"- {r['type']} `{r['champ']}` → `{r['vers']}`{od}{' (facultatif)' if r['null'] else ''}")
            for g in m["generiques"]:
                D.append(f"- Relation générique `{g}`")
            D.append("")
    (SORTIE / "MODELES.md").write_text("\n".join(D), encoding="utf-8")

    R = ["# Routes de l'état B (généré)", "", "| Route | Nom | Vue |", "|---|---|---|"]
    R += [f"| `{r['route']}` | {r['nom'] or ''} | `{r['vue']}` |" for r in sorted(routes, key=lambda x: x['route'])]
    (SORTIE / "ROUTES.md").write_text("\n".join(R) + "\n", encoding="utf-8")
    print(f"{len(modeles)} modèles, {len(routes)} routes, {len(beat)} tâches planifiées, {len(commandes)} commandes")


main()
