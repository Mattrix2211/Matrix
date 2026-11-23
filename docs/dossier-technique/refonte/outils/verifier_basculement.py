"""Vérifications du basculement V3 (lecture seule) : aucun fichier perdu ni modifié, citations des PDF résolues, liens relatifs.
Usage : python verifier_basculement.py [--liens-avant <racine docs/dossier-technique d'avant>]   (code retour 1 au moindre écart)"""
import argparse
import csv
import hashlib
import re
import sys
from pathlib import Path

R = Path(__file__).resolve().parent.parent
DT = R.parent
ap = argparse.ArgumentParser()
ap.add_argument("--liens-avant")
a = ap.parse_args()
erreurs = []

# 1. inventaire : chaque ancien fichier retrouvé à sa destination (option A), même SHA-256
lignes = list(csv.reader(open(R / "baseline/inventaire_anciens_documents.csv", encoding="utf-8-sig"), delimiter=";"))[1:]
for chemin, taille, sha, cat, dest_a, dest_b, cite in lignes:
    d = DT / dest_a
    if not d.is_file():
        erreurs.append(f"absent : {dest_a}")
    elif hashlib.sha256(d.read_bytes()).hexdigest() != sha:
        erreurs.append(f"contenu différent : {dest_a}")
print(f"1. inventaire : {len(lignes)} fichiers attendus à leur destination, empreintes identiques")

# 2. aucun ancien chemin déplacé ne subsiste à l'ancien endroit
for chemin, taille, sha, cat, dest_a, dest_b, cite in lignes:
    if dest_a != chemin and (DT / chemin).exists():
        erreurs.append(f"présent aux deux endroits : {chemin}")

# 3. chemins anciens cités par les documents de la révision 2 : à l'endroit cité, ou à la destination décrite par la table de correspondance
table = (DT / "archive_G0_initial/LISEZ-MOI.md").read_text(encoding="utf-8")
cites = [l for l in lignes if l[6] == "oui"]
for chemin, taille, sha, cat, dest_a, *_r in cites:
    if not (DT / dest_a).exists():
        erreurs.append(f"citation sans cible : {chemin}")
    elif dest_a != chemin and not any(x in table for x in (chemin, chemin.split("/")[0] + "/", Path(chemin).stem)):
        erreurs.append(f"citation déplacée absente de la table de correspondance : {chemin}")
print(f"3. {len(cites)} chemins cités : chacun existe à l'endroit cité ou à la destination décrite par la table de correspondance")

# 4. liens relatifs des fichiers Markdown
def liens_casses(racine):
    casses = set()
    for md in racine.rglob("*.md"):
        if "node_modules" in md.parts:
            continue
        t = md.read_text(encoding="utf-8", errors="ignore")
        t = re.sub(r"```.*?```", "", t, flags=re.S)
        for m in re.finditer(r"\]\(([^)\s#]+)(?:#[^)]*)?\)", t):
            cible = m.group(1)
            if re.match(r"[a-z]+:", cible) or cible.startswith("/"):
                continue
            if not (md.parent / cible).resolve().exists():
                casses.add((str(md.relative_to(racine)), cible))
    return casses


apres = liens_casses(DT)
if a.liens_avant:
    avant = liens_casses(Path(a.liens_avant))
    def normaliser(s):
        return {(f.replace("archive_G0_initial/", "").replace("refonte/archives/", "refonte/").replace("refonte/pdf/", "refonte/pdf_candidats/"), c) for f, c in s}
    nouveaux = normaliser(apres) - normaliser(avant)
    for f, c in sorted(nouveaux):
        erreurs.append(f"lien nouvellement cassé : {f} -> {c}")
    print(f"4. liens relatifs cassés : {len(avant)} avant, {len(apres)} après, {len(nouveaux)} nouveau(x)")
else:
    print(f"4. liens relatifs cassés : {len(apres)}")

# 5. aucun fichier suivi ne subsiste à l'ancien nom des dossiers renommés
for ancien in ("refonte/pdf_candidats", "refonte/apercus_V1", "diffusable", "schemas", "guide-visuel", "pdf"):
    if (DT / ancien).exists():
        erreurs.append(f"ancien dossier encore présent : {ancien}")
print(f"{len(erreurs)} écart(s)")
for e in erreurs:
    print(" -", e)
sys.exit(1 if erreurs else 0)
