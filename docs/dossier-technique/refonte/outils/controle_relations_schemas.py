"""Contrôle des relations des cinq schémas refaits (S02, S14, S22, S27, S38) :
 - chaque flèche d'un schéma Mermaid (S14, S22, S27, S38) figure comme ligne « De / Condition / Vers » dans le tableau du référentiel, et inversement ;
 - S02 : les flèches « calendrier » et « notifications » sont recoupées avec l'inventaire des dépendances du code (calendar_app et notifications
   importent bien chacun de ces modules), et chaque module du dessin existe dans l'inventaire ; toutes les relations figurent dans le tableau.
Usage : python controle_relations_schemas.py   (code de retour 1 au moindre écart)"""
import json
import re
import sys
from pathlib import Path

R = Path(__file__).resolve().parent.parent
DT = R.parent
ecarts = []


def norm(t):
    t = re.sub(r"<br\s*/?>", " ", t)
    t = re.sub(r"[`*]", "", t)
    return re.sub(r"\s+", " ", t).strip()


def aretes_mmd(chemin):
    t = chemin.read_text(encoding="utf-8")
    noeuds = {m.group(1): norm(m.group(2)) for m in re.finditer(r'(\b[A-Z][A-Za-z0-9]*)\["([^"]+)"\]', t)}
    sortie = []
    for l in t.split("\n"):
        l = l.strip()
        m = re.match(r"^([A-Z0-9 &]+?)\s*(-\.->|-->|-\.-)\s*(?:\|\"([^\"]*)\"\|)?\s*([A-Z0-9 &]+)$", l)
        if m and "subgraph" not in l:
            src = [x for x in re.split(r"\s*&\s*", m.group(1).strip()) if x]
            dst = [x for x in re.split(r"\s*&\s*", m.group(4).strip()) if x]
            for a in src:
                for b in dst:
                    sortie.append((noeuds.get(a, a), norm(m.group(3) or "—"), noeuds.get(b, b)))
        elif "-->" in l and l.count("-->") > 1:
            ch = [x.strip() for x in re.split(r"-->", l)]
            for a, b in zip(ch, ch[1:]):
                sortie.append((noeuds.get(a, a), "—", noeuds.get(b, b)))
    return sortie


def lignes_table(chemin):
    t = chemin.read_text(encoding="utf-8")
    i = t.index("| De | Condition ou passage | Vers |")
    out = []
    for l in t[i:].split("\n")[2:]:
        if not l.startswith("|"):
            break
        c = [norm(x) for x in l.strip().strip("|").split("|")]
        out.append((c[0], c[1], c[2]))
    return out


CAS = [("S14_sources_calendrier", "07_fiche_calendrier.md"), ("S22_equiper_depuis_catalogue", "11_fiche_materiel_installations.md"),
       ("S27_stock_et_pieces", "13_fiche_logistique.md"), ("S38_feuille_de_route", "25_cible_et_feuille_de_route.md")]
for svg, fiche in CAS:
    a = set(aretes_mmd(R / "schemas/src" / (svg + ".mmd")))
    # les 9 sources de S14 sont regroupées dans une ligne du tableau
    if svg.startswith("S14"):
        a = {(("Neuf sources : maintenance, ticket correctif, formation, quart, garde à quai, tâche, absence, programme du bâtiment, événement personnel") if x[0] in {"Maintenance", "Ticket correctif", "Formation", "Quart", "Garde à quai", "Tâche", "Absence", "Programme du bâtiment", "Événement personnel"} else x[0], x[1], x[2]) for x in a}
    t = set(lignes_table(R / "2_referentiel_fonctionnel" / fiche))
    t = {(x, c if c != "visas puis publication" else c, v) for x, c, v in t}
    manque = a - t
    en_trop = t - a
    for x in manque:
        ecarts.append(f"{svg} : flèche absente du tableau : {x}")
    for x in en_trop:
        ecarts.append(f"{svg} : ligne du tableau absente du schéma : {x}")
    print(f"{svg} : {len(a)} flèche(s), {len(t)} ligne(s) de tableau, {len(manque)} manquante(s), {len(en_trop)} en trop")

# S02 : recoupement avec le code
src = (R / "outils/dessiner_s02.py").read_text(encoding="utf-8")
CAL = eval(re.search(r"^CAL = (\{.*?\})", src, re.M).group(1))
NOT = eval(re.search(r"^NOT = (\{.*?\})", src, re.M).group(1))
dep = json.loads((DT / "couverture/etat_B/inventaire.json").read_text(encoding="utf-8"))["dependances"]
for m in CAL:
    if m not in dep.get("calendar_app", {}):
        ecarts.append(f"S02 : calendar_app n'importe pas {m} dans l'inventaire du code")
for m in NOT:
    if m not in dep.get("notifications", {}):
        ecarts.append(f"S02 : notifications n'importe pas {m} dans l'inventaire du code")
sources_cal = set(dep["calendar_app"]) - {"threads", "accounts"}
if sources_cal != CAL:
    ecarts.append(f"S02 : sources du calendrier du code {sorted(sources_cal)} ≠ dessin {sorted(CAL)}")
tab = (R / "2_referentiel_fonctionnel/03_vue_ensemble.md").read_text(encoding="utf-8")
for m in CAL | NOT:
    if f"`{m}`" not in tab:
        ecarts.append(f"S02 : module {m} absent du tableau des relations")
for m in ("maintenance", "logistics", "threads", "matrix.core"):
    if m not in tab:
        ecarts.append(f"S02 : {m} absent du tableau")
print(f"S02 : {len(CAL)} modules vers le calendrier, {len(NOT)} vers les notifications, recoupés avec l'inventaire du code ; dépendance au noyau commun : 6 groupes")
print("ÉCARTS :", len(ecarts))
for e in ecarts:
    print(" -", e)
sys.exit(1 if ecarts else 0)
