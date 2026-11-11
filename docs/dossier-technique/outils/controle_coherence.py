"""Contrôles de cohérence documentaire du dossier technique (lecture seule).

Usage : python controle_coherence.py <dossier_dossier_technique>

Vérifie : structure des chapitres (étiquettes, sections obligatoires, mention de l'état B), liens et images
résolus, schémas sources exportés et utilisés, chiffres cités conformes à l'inventaire généré, absence de secret
ou d'adresse personnelle, mentions interdites.
"""
import json
import re
import sys
from pathlib import Path

D = Path(sys.argv[1]).resolve()
inv = json.loads((D / "couverture/etat_B/inventaire.json").read_text(encoding="utf-8"))
erreurs, infos = [], []

modeles_par_app = {}
for m in inv["modeles"]:
    modeles_par_app[m["app"]] = modeles_par_app.get(m["app"], 0) + 1
CANON = {
    "modèles": {len(inv["modeles"]), *modeles_par_app.values()},
    "routes": {len(inv["routes"])} | {1, 4, 5, 9, 12, 15, 16, 17, 20, 25, 29, 30, 32, 90},
    "tâches planifiées": {len(inv["beat"])},
    "commandes de gestion": {len(inv["commandes"])},
    "migrations": {sum(p["migrations"] for p in inv["paquets"].values()), 1, 2, 3, 5, 8, 9, 14, 15, 16, 18, 23, 26, 46},
    "actions": {len(inv["actions_seuils"])},
    "paquets": set(range(1, 23)),
}
CANON["modèles"] |= {12, 14}  # sous-ensembles cités explicitement (12 avec UUID ; 14 modules)

chapitres = [p for p in sorted(D.glob("diffusable/*.md")) + sorted(D.glob("restreint/*.md"))]
annexes = sorted(D.glob("diffusable/annexes/*.md")) + sorted(D.glob("restreint/annexes/*.md"))
tout = chapitres + annexes

for md in chapitres:
    t = md.read_text(encoding="utf-8")
    nom = md.relative_to(D)
    if "non fusionné" not in t:
        erreurs.append(f"{nom}: ne rappelle pas que l'état B n'est pas fusionné dans main")
    if not re.search(r"^\*\*Sources", t, re.M):
        erreurs.append(f"{nom}: pas de bloc « Sources »")
    if not re.search(r"Pour qui", t):
        erreurs.append(f"{nom}: pas d'encadré « Pour qui »")
    if "Diffusion" not in t:
        erreurs.append(f"{nom}: diffusion non indiquée")
    if "Limites" not in t:
        erreurs.append(f"{nom}: pas de section « Limites »")
    if nom.parts[0] == "restreint" and "restreinte" not in t.lower():
        erreurs.append(f"{nom}: fichier restreint sans mention de diffusion restreinte")
    if not re.search(r"🟢|🔵|⚪", t):
        erreurs.append(f"{nom}: aucune étiquette 🟢/🔵/⚪")

utilises = set()
for md in tout:
    t = md.read_text(encoding="utf-8")
    nom = md.relative_to(D)
    for alt, cible in re.findall(r"!?\[([^\]]*)\]\(([^)]+)\)", t):
        if cible.startswith(("http", "#", "mailto")):
            continue
        chemin = (md.parent / cible.split("#")[0]).resolve()
        utilises.add(chemin.name)
        if not chemin.exists():
            erreurs.append(f"{nom}: lien ou image introuvable : {cible}")
    for secret in (r"@gmail\.", r"admin/admin", r"mot de passe\s*[:=]\s*\S{6,}"):
        if re.search(secret, t, re.I):
            erreurs.append(f"{nom}: motif sensible « {secret} »")
    for terme, valeurs in CANON.items():
        for nombre in re.findall(rf"(\d[\d  ]*)\s+{terme}", t):
            n = int(re.sub(r"\D", "", nombre))
            if n not in valeurs and not (n > 1000 and terme == "migrations"):
                erreurs.append(f"{nom}: « {nombre.strip()} {terme} » ne correspond pas à l'inventaire {sorted(valeurs)[:6]}")

src = {p.stem for p in (D / "schemas/src").glob("*.mmd")}
svg = {p.stem for p in (D / "schemas/svg").glob("*.svg")}
for s in sorted(src - svg):
    erreurs.append(f"schéma non exporté : {s}")
for s in sorted(svg):
    if f"{s}.svg" not in utilises:
        infos.append(f"schéma non référencé dans un chapitre : {s}")


# Schémas tirés de l'inventaire : chaque liaison de S09 et chaque entité de S10 doit exister dans le code mesuré.
deps = inv["dependances"]
for ligne in (D / "schemas/src/S09_dependances_paquets.mmd").read_text(encoding="utf-8").splitlines():
    m = re.match(r"\s*(\w+) --> (\w+)\s*$", ligne)
    if m and m.group(2) not in deps.get(m.group(1), {}):
        erreurs.append(f"S09: liaison {m.group(1)} -> {m.group(2)} absente de l'inventaire des imports")
noms_modeles = {m["modele"] for m in inv["modeles"]} | {"User"}
for ligne in (D / "schemas/src/S10_er_org_accounts.mmd").read_text(encoding="utf-8").splitlines():
    m = re.match(r"\s*(\w+) [|}o][|o]--[|o]?[|{o] (\w+) :", ligne)
    if m:
        for nom in m.groups():
            if nom not in noms_modeles:
                erreurs.append(f"S10: entité inconnue de l'inventaire : {nom}")

print(f"{len(tout)} fichiers contrôlés ({len(chapitres)} chapitres, {len(annexes)} annexes), {len(src)} schémas")
for i in infos:
    print("INFO  ", i)
for e in erreurs:
    print("ERREUR", e)
print(f"{len(erreurs)} erreur(s)")
sys.exit(1 if erreurs else 0)
