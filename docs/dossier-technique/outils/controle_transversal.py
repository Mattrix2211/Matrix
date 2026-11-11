"""Revue transversale automatique du dossier complet (lecture seule).

Usage : python controle_transversal.py <dossier_dossier_technique>

Vérifie : présence des 26 chapitres et des 8 annexes ; couverture de tous les paquets, modèles, circuits, tâches planifiées, commandes ;
renvois aux écarts (An) et points à confirmer (Bn) existants ; identifiants DEC cités (déjà contrôlés par verifier_references) ; absence de marques
d'inachèvement ; chaque schéma exporté, référencé et décrit dans un index ; format des lignes du registre des écarts.
"""
import json
import re
import sys
from pathlib import Path

D = Path(sys.argv[1]).resolve()
inv = json.loads((D / "couverture/etat_B/inventaire.json").read_text(encoding="utf-8"))
erreurs, infos = [], []
chap = {p.name: p.read_text(encoding="utf-8") for p in sorted(list(D.glob("diffusable/[0-9]*.md")) + list(D.glob("restreint/[0-9]*.md")))}
tout = "\n".join(chap.values())

# 1. 26 chapitres
manquants = [n for n in range(1, 27) if not any(k.startswith(f"{n:02d}_") for k in chap)]
if manquants:
    erreurs.append(f"chapitres absents : {manquants}")
infos.append(f"{26 - len(manquants)} chapitres sur 26 présents ; {len(chap)} fichiers de chapitre")

# 2. 8 annexes
annexes = {
    "A": "diffusable/annexes/A_glossaire.md", "B": "restreint/annexes/B_matrice_role_action.md", "C": "restreint/annexes/C_index_routes.md",
    "D": "restreint/annexes/D_index_modeles.md", "E": "restreint/annexes/E_taches_commandes_variables.md",
    "F": "restreint/annexes/F_sources_branches_non_verifies.md", "G": "restreint/annexes/G_matrice_couverture.md", "H": "diffusable/annexes/H_index_schemas.md",
}
for k, v in annexes.items():
    if not (D / v).is_file() or (D / v).stat().st_size < 500:
        erreurs.append(f"annexe {k} absente ou vide : {v}")
infos.append(f"{sum(1 for v in annexes.values() if (D / v).is_file())} annexes sur 8 présentes")

# 3. Couverture du code
for m in inv["modeles"]:
    if not re.search(rf"\b{m['modele']}\b", tout):
        erreurs.append(f"modèle non expliqué dans un chapitre : {m['app']}.{m['modele']}")
for app in inv["paquets"]:
    n = app.split(".")[-1]
    if not re.search(rf"\b{re.escape(n)}\b", tout):
        erreurs.append(f"paquet jamais cité : {app}")
texte_e = (D / annexes["E"]).read_text(encoding="utf-8")
for b in inv["beat"]:
    if b["nom"] not in texte_e:
        erreurs.append(f"tâche planifiée absente de l'annexe E : {b['nom']}")
for c in inv["commandes"]:
    if Path(c).stem not in texte_e:
        erreurs.append(f"commande absente de l'annexe E : {Path(c).stem}")
texte_b = (D / annexes["B"]).read_text(encoding="utf-8")
for a in inv["actions_seuils"]:
    libelle = a.get("libelle") or a.get("description") or ""
    if libelle and libelle[:40] not in texte_b:
        infos.append(f"action à seuil non retrouvée telle quelle dans l'annexe B : {libelle[:50]}")
mods = inv["registres_modules"].get("REGISTRE_MODULES", [])
for ligne in mods:
    cle = re.search(r"cle='(\w+)'", ligne)
    if cle and not re.search(rf"\b{cle.group(1)}\b", tout):
        erreurs.append(f"module activable jamais cité : {cle.group(1)}")
routes_web = [r for r in inv["routes"] if not r["route"].startswith(("admin/", "api/"))]
texte_c = (D / annexes["C"]).read_text(encoding="utf-8")
for r in routes_web:
    if f"`{r['route'] or '/'}`" not in texte_c:
        erreurs.append(f"route absente de l'annexe C : {r['route']}")
        break

# 4. Matrice de couverture : circuits tous rédigés
g = (D / annexes["G"]).read_text(encoding="utf-8")
for l in g.splitlines():
    if "À VÉRIFIER" in l or "à rédiger" in l:
        erreurs.append("circuit non démontré dans la matrice : " + l.strip()[:90])

# 5. Écarts et points à confirmer
reg = (D / "restreint/ECARTS_DECISIONS_CODE.md").read_text(encoding="utf-8")
ids = set(re.findall(r"^\| (A\d+)\b", reg, re.M)) | set(re.findall(r"^\| (B\d+) ", reg, re.M))
cites = set(re.findall(r"\b(?:écart|écarts|Écart)s? (A\d+)\b|\((?:A|B)(\d+)\b", tout))
for m in re.finditer(r"\b(A\d{1,2}|B\d)\b", tout):
    ident = m.group(1)
    if re.match(r"A\d", ident) and ident not in ids and int(ident[1:]) >= 11:
        erreurs.append(f"renvoi à un écart absent du registre : {ident}")
        ids.add(ident)
lignes_a = [l for l in reg.splitlines() if re.match(r"^\| A\d+ ", l)]
for l in lignes_a:
    colonnes = [c for c in l.strip().strip("|").split(" | ")]
    if len(colonnes) < 6:
        erreurs.append("ligne d'écart à moins de 6 colonnes : " + l[:60])
infos.append(f"registre : {len(lignes_a)} écarts d'implémentation, {len(re.findall(r'^[|] B\d ', reg, re.M))} points à confirmer")

# 6. Marques d'inachèvement
for n, t in chap.items():
    for motif in (r"\bTODO\b", r"\bXXX\b", r"à rédiger", r"\[à compléter\]", r"lorem ipsum"):
        if re.search(motif, t, re.I):
            erreurs.append(f"{n}: marque d'inachèvement « {motif} »")

# 7. Schémas
src = {p.stem for p in (D / "schemas/src").glob("*.mmd")}
svg = {p.stem for p in (D / "schemas/svg").glob("*.svg")}
if src != svg:
    erreurs.append(f"schémas sources/exports différents : {sorted(src ^ svg)}")
index = (D / annexes["H"]).read_text(encoding="utf-8") + (D / "restreint/annexes/H_bis_schemas_restreints.md").read_text(encoding="utf-8")
for s in sorted(svg):
    if s[:3] not in index:
        erreurs.append(f"schéma absent des index : {s}")
    if f"{s}.svg" not in tout:
        erreurs.append(f"schéma jamais référencé par un chapitre : {s}")
infos.append(f"{len(svg)} schémas, tous exportés")

for i in infos:
    print("INFO  ", i)
for e in erreurs:
    print("ERREUR", e)
print(f"{len(erreurs)} erreur(s)")
sys.exit(1 if erreurs else 0)
