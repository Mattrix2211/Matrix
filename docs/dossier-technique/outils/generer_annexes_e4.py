"""Génère les annexes C (routes), D (modèles), E (tâches planifiées, commandes, variables), H (schémas) et le registre des ⚪ de l'annexe F.

Usage : python generer_annexes_e4.py <dossier_dossier_technique> <racine_etat_B>
Lecture seule sur le code : aucune exécution de l'application, analyse syntaxique des fichiers Python.
"""
import ast
import json
import re
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

D = Path(sys.argv[1]).resolve()
B = Path(sys.argv[2]).resolve()
inv = json.loads((D / "couverture/etat_B/inventaire.json").read_text(encoding="utf-8"))
ENTETE = ("> Diffusion restreinte. Généré par `outils/generer_annexes_e4.py` depuis l'inventaire de l'état B "
          "(`6d6d0be`, non fusionné dans `main`). Ne pas éditer à la main.")
chapitres = {p.name: p.read_text(encoding="utf-8") for p in sorted(list(D.glob("diffusable/[0-9]*.md")) + list(D.glob("restreint/[0-9]*.md")))}


def num(nom):
    return int(nom[:2])


def lire_ast(chemin):
    try:
        return ast.parse(chemin.read_text(encoding="utf-8"))
    except (OSError, SyntaxError):
        return None


_cache = {}


def arbre(module):
    if module not in _cache:
        base = B / module.replace(".", "/")
        _cache[module] = lire_ast(base.with_suffix(".py")) or lire_ast(base / "__init__.py")
    return _cache[module]


def gabarits(vue):
    """Gabarits HTML cités dans la classe ou la fonction de la vue."""
    if "." not in vue:
        return ""
    module, _, nom = vue.rpartition(".")
    tree = arbre(module)
    if tree is None:
        return ""
    for noeud in ast.walk(tree):
        if isinstance(noeud, (ast.ClassDef, ast.FunctionDef)) and noeud.name == nom:
            trouves = []
            for sous in ast.walk(noeud):
                if isinstance(sous, ast.Constant) and isinstance(sous.value, str) and sous.value.endswith(".html"):
                    if sous.value not in trouves:
                        trouves.append(sous.value)
            return ", ".join(f"`matrix/templates/{t}`" for t in trouves[:3] if (B / "matrix/templates" / t).is_file())
    return ""


# ---------- Annexe C ----------
routes = inv["routes"]
admin = [r for r in routes if r["route"].startswith("admin/")]
api = [r for r in routes if r["route"].startswith("api/")]
web = [r for r in routes if not r["route"].startswith(("admin/", "api/"))]
L = ["# Annexe C — Index des routes web et API (généré, état B)", "", ENTETE, "",
     f"**{len(routes)} routes** : {len(web)} pages et fichiers, {len(api)} routes d'API, {len(admin)} routes d'administration Django (résumées). "
     "Lecture : chemin, nom, vue, gabarit HTML cité dans la vue (quand il y en a un). Chapitres : voir la matrice (annexe G).", "",
     "## C.1 Pages web, fichiers et recherche", "", "| Chemin | Nom | Vue | Gabarit |", "|---|---|---|---|"]
for r in sorted(web, key=lambda r: r["route"]):
    L.append(f"| `{r['route'] or '/'}` | {r['nom'] or '—'} | `{r['vue']}` | {gabarits(r['vue']) or '—'} |")
L += ["", "## C.2 API REST (`/api/…`)", "",
      "Les routes avec suffixe de format (`.json`) et les racines d'API sont omises ; chaque ressource expose liste, détail, création, modification, suppression selon ses droits (chapitre 20).", "",
      "| Chemin | Nom | Vue |", "|---|---|---|"]
for r in sorted(api, key=lambda r: r["route"]):
    if "format" in r["route"] or r["nom"] == "api-root":
        continue
    L.append(f"| `{r['route']}` | {r['nom'] or '—'} | `{r['vue']}` |")
L += ["", "## C.3 Administration Django (résumé)", "", "| Application | Routes |", "|---|---|"]
par_admin = defaultdict(int)
for r in admin:
    morceaux = r["route"].split("/")
    par_admin[morceaux[1] if len(morceaux) > 2 and morceaux[1] else "(racine)"] += 1
for k in sorted(par_admin):
    L.append(f"| `{k}` | {par_admin[k]} |")
L += ["", "Ces routes servent aux comptes techniques ; elles ne sont pas un parcours métier (chapitre 20).", ""]
(D / "restreint/annexes/C_index_routes.md").write_text("\n".join(L), encoding="utf-8")

# ---------- Annexe D ----------
def a_gfk(app, modele):
    tree = arbre(f"{app}.models")
    if tree is None:
        return False
    for noeud in ast.walk(tree):
        if isinstance(noeud, ast.ClassDef) and noeud.name == modele:
            return any(isinstance(s, ast.Call) and getattr(s.func, "id", getattr(s.func, "attr", "")) == "GenericForeignKey" for s in ast.walk(noeud))
    return False


def a_uuid(app, modele):
    tree = arbre(f"{app}.models")
    if tree is None:
        return False
    for noeud in ast.walk(tree):
        if isinstance(noeud, ast.ClassDef) and noeud.name == modele:
            for s in ast.walk(noeud):
                if isinstance(s, ast.Call) and getattr(s.func, "attr", "") == "UUIDField":
                    return any(k.arg == "primary_key" for k in s.keywords)
    return False


L = ["# Annexe D — Index des modèles (généré, état B)", "", ENTETE, "",
     f"**{len(inv['modeles'])} modèles**. Colonnes : paquet, modèle, nombre de champs, clé primaire (UUID ou entier ; un modèle à clé entière peut porter par ailleurs un champ UUID, voir le dictionnaire), relation générique (`GenericForeignKey`), chapitres où le modèle est expliqué. Dictionnaire des champs : `couverture/etat_B/MODELES.md`.", "",
     "| Paquet | Modèle | Champs | Clé primaire | Relation générique | Chapitres |", "|---|---|---|---|---|---|"]
for m in sorted(inv["modeles"], key=lambda m: (m["app"], m["modele"])):
    chs = sorted({num(n) for n, t in chapitres.items() if not n.startswith("19_") and re.search(rf"\b{m['modele']}\b", t)})
    L.append(f"| `{m['app']}` | `{m['modele']}` | {len(m['champs'])} | {'UUID' if a_uuid(m['app'], m['modele']) else 'entier'} | "
             f"{'oui' if a_gfk(m['app'], m['modele']) else 'non'} | {', '.join(map(str, chs)) or '19'} |")
L.append("")
(D / "restreint/annexes/D_index_modeles.md").write_text("\n".join(L), encoding="utf-8")

# ---------- Annexe E ----------
def rythme(p):
    p = str(p)
    if p.isdigit():
        s = int(p)
        return {60: "chaque minute", 900: "tous les quarts d'heure", 3600: "chaque heure", 86400: "chaque jour"}.get(s, f"toutes les {s} s")
    m = re.match(r"<crontab: (\S+) (\S+) (\S+) (\S+) (\S+)", p)
    if m:
        mi, h = m.group(1), m.group(2)
        if mi == "*" and h == "*":
            return "chaque minute (la tâche filtre selon l'heure de chaque marin)"
        if mi.isdigit() and h.isdigit():
            return f"chaque jour à {int(h):02d}:{int(mi):02d}"
    return p


def doc_tache(chemin_complet):
    module, _, fonc = chemin_complet.rpartition(".")
    tree = arbre(module)
    if tree:
        for n in ast.walk(tree):
            if isinstance(n, ast.FunctionDef) and n.name == fonc:
                d = ast.get_docstring(n) or ""
                return d.split("\n")[0].strip()
    return ""


L = ["# Annexe E — Tâches planifiées, commandes de gestion et variables (généré, état B)", "", ENTETE, "",
     "## E.1 Tâches planifiées (Celery beat)", "",
     f"{len(inv['beat'])} tâches. **Sans worker ni beat, aucune n'est exécutée** (chapitres 21 et 23).", "",
     "| Nom | Tâche | Rythme | Rôle (première ligne de la documentation du code) |", "|---|---|---|---|"]
for b in inv["beat"]:
    L.append(f"| `{b['nom']}` | `{b['tache']}` | {rythme(b['planification'])} | {doc_tache(b['tache']) or '—'} |")
L += ["", "## E.2 Commandes de gestion", "", f"{len(inv['commandes'])} commandes (`python manage.py <nom>`).", "",
      "| Commande | Paquet | Rôle (texte d'aide du code) |", "|---|---|---|"]
for c in inv["commandes"]:
    chemin = B / c
    aide = ""
    tree = lire_ast(chemin)
    if tree:
        for n in ast.walk(tree):
            if isinstance(n, ast.Assign) and any(getattr(t, "id", "") == "help" for t in n.targets):
                try:
                    aide = ast.literal_eval(n.value)
                except ValueError:
                    aide = ""
    aide = re.sub(r"\s+", " ", aide).strip()
    demo = " **Démonstration : refuse de s'exécuter hors d'une base de démonstration.**" if Path(c).stem.startswith("seed_demo") else ""
    L.append(f"| `{Path(c).stem}` | `{c.split('/')[0]}` | {aide or '—'}{demo} |")
reglages = (B / "matrix/settings.py").read_text(encoding="utf-8")
vars_ = {}
for m in re.finditer(r'(?:os\.getenv|env\.get|os\.environ\.get)\(\s*"([A-Z_0-9]+)"(?:\s*,\s*([^)]*))?\)', reglages):
    vars_.setdefault(m.group(1), (m.group(2) or "").strip())
L += ["", "## E.3 Variables d'environnement lues par `matrix/settings.py`", "",
      f"{len(vars_)} variables. Signification et valeurs recommandées : chapitre 23 (§23.3).", "",
      "| Variable | Valeur par défaut dans le code |", "|---|---|"]
for k in sorted(vars_):
    defaut = vars_[k]
    defaut = defaut + ")" * max(0, defaut.count("(") - defaut.count(")"))
    defaut = defaut.replace("|", "\\|") or "—"
    L.append(f"| `{k}` | `{defaut}` |" if defaut != "—" else f"| `{k}` | — |")
L.append("")
(D / "restreint/annexes/E_taches_commandes_variables.md").write_text("\n".join(L), encoding="utf-8")

# ---------- Annexe H ----------
def ligne_schema(svg):
    sid = svg.stem
    chs, titre, diff = set(), "", set()
    noms_diff = {p.name for p in D.glob("diffusable/*.md")}
    for n, t in chapitres.items():
        if f"{sid}.svg" in t:
            chs.add(num(n))
            diff.add("générale" if n in noms_diff else "restreinte")
            m = re.search(rf"\*Sch[ée]ma {sid[:3]} — ([^*]+?)\*", t)
            if m and not titre:
                titre = re.split(r"\. ", m.group(1).strip())[0].rstrip(".")
    titre = titre or sid[4:].replace("_", " ")
    return sid, titre, sorted(chs), diff


EN_TETE_H = ["| N° | Titre | Source | Export | Chapitres |", "|---|---|---|---|---|"]
diffusables, restreints = [], []
for svg in sorted((D / "schemas/svg").glob("S*.svg")):
    sid, titre, chs, diff = ligne_schema(svg)
    ligne = f"| {sid[:3]} | {titre} | `schemas/src/{sid}.mmd` | `schemas/svg/{sid}.svg` | {', '.join(map(str, chs)) or '—'} |"
    (diffusables if "générale" in diff else restreints).append(ligne)
(D / "diffusable/annexes/H_index_schemas.md").write_text("\n".join(
    ["# Annexe H — Index des schémas (généré)", "",
     "> Diffusion générale. Généré par `outils/generer_annexes_e4.py`. Cet index ne liste que les schémas des chapitres diffusables ; l'index des schémas des chapitres restreints est dans la partie restreinte du dossier. Sources Mermaid conservées dans `schemas/src/`, exports lisibles hors ligne dans `schemas/svg/`.", "",
     f"**{len(diffusables)} schémas diffusables.**", ""] + EN_TETE_H + diffusables + [""]), encoding="utf-8")
(D / "restreint/annexes/H_bis_schemas_restreints.md").write_text("\n".join(
    ["# Annexe H bis — Index des schémas des chapitres restreints (généré)", "", ENTETE, "",
     f"**{len(restreints)} schémas restreints.**", ""] + EN_TETE_H + restreints + [""]), encoding="utf-8")

# ---------- Registre des ⚪ (pour l'annexe F) ----------
L = ["## F.5 Registre des éléments non vérifiés (⚪), par chapitre (généré)", "",
     "Chaque ligne reprend, à l'identique, un passage marqué ⚪ dans un chapitre. Aucune ligne n'a été ajoutée ni retirée à la main.", ""]
total = 0
for n, t in chapitres.items():
    lignes = [re.sub(r"\s+", " ", l).strip() for l in t.splitlines() if "⚪" in l and not l.lstrip().startswith(("> **Pour", "> **État", "> **Diffusion", "Légende", "#"))]
    lignes = [l for l in lignes if "Légende" not in l and "ne pas vérifié" not in l]
    if lignes:
        L.append(f"### {n}")
        for l in lignes:
            L.append("- " + (l[:330] + "…" if len(l) > 330 else l))
            total += 1
        L.append("")
L.insert(2, f"**{total} passages** répartis sur {sum(1 for n,t in chapitres.items() if '⚪' in t)} fichiers.")
(D / "couverture/F5_registre_non_verifies.generated.md").write_text("\n".join(L), encoding="utf-8")
print("annexes C, D, E, H et registre F.5 générés ; ⚪ :", total)
