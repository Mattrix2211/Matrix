"""Inventaire exact des anciens documents (arborescences, rapports, PDF) concernés par le basculement V3.
Lecture seule : aucun fichier n'est déplacé. Usage : python inventorier_anciens.py <sortie.csv>"""
import csv
import hashlib
import re
import subprocess
import sys
from pathlib import Path

DT = Path(__file__).resolve().parents[2]
RACINE = DT.parents[1]
suivis = subprocess.run(["git", "ls-files", "docs/dossier-technique"], capture_output=True, text=True, check=True, cwd=RACINE).stdout.split("\n")
suivis = [f.removeprefix("docs/dossier-technique/") for f in suivis if f]

# texte rendu des sources de la révision 2 (hors commentaires de correspondance)
rendu = ""
for p in sorted((DT / "refonte").glob("[1-5]_*/*.md")):
    rendu += "\n".join(l for l in p.read_text(encoding="utf-8").split("\n") if "<!--" not in l and "](" not in l) + "\n"
rendu = re.sub(r"\s+", "", rendu)

ARCHIVE = "archive_G0_initial"
EN_PLACE = ("restreint/ECARTS_DECISIONS_CODE.md",)
EN_PLACE_PREFIXES = ("restreint/annexes/",)
CONSERVES = ("couverture/", "audit_preuves/", "outils/")
CONSERVES_FICHIERS = ("AUDIT_GLOBAL_G0.md", "PLAN_EXECUTION_REFONTE_G0.md")
RAPPORTS = ("BILAN_FINAL_G0.md", "G0_PROPOSITION.md", "G0_SOMMAIRE_DETAILLE.md", "RAPPORT_CLOTURE_G0.md", "RAPPORT_E1.md", "RAPPORT_E2.md", "RAPPORT_E3.md", "RAPPORT_E4.md",
            "RAPPORT_QUALIFICATION_FINALE_G0.md", "REVUE_INDEPENDANTE_G0_2026-11-12.md", "SYNTHESE_ECARTS_PAR_CRITICITE.md")
REMPLACES = ("00_LISEZ-MOI.md", "GUIDE_DE_LECTURE.md")


def classer(f):
    """(catégorie, destination option A recommandée, destination option B)"""
    if f.startswith(("refonte/", "audit_preuves/", "couverture/", "outils/")) or f in CONSERVES_FICHIERS:
        if f.startswith("refonte/"):
            return None
        return ("conservé en place", f, f)
    arch = f"{ARCHIVE}/{f}"
    if f.startswith("pdf/"):
        return ("ancien PDF diffusable (retrait soumis à autorisation explicite du PO)", arch, arch)
    if f.startswith("guide-visuel/pdf/"):
        return ("ancien PDF (guide visuel de 39 pages)", arch, arch)
    if f in EN_PLACE or f.startswith(EN_PLACE_PREFIXES):
        return ("ancienne arborescence — citée par les PDF définitifs", f, arch)
    if f.startswith(("diffusable/", "restreint/", "schemas/", "guide-visuel/")):
        return ("ancienne arborescence", arch, arch)
    if f in REMPLACES:
        return ("ancien point d'entrée remplacé par refonte/README_DOSSIER.md", arch, arch)
    if f in RAPPORTS:
        return ("ancien rapport ou proposition", f"{ARCHIVE}/rapports/{f}", f"{ARCHIVE}/rapports/{f}")
    return ("non classé", "à arbitrer", "à arbitrer")


lignes = []
for f in sorted(suivis):
    c = classer(f)
    if c is None:
        continue
    d = (DT / f).read_bytes()
    nom = f if "/" not in f else f
    cite = "oui" if re.sub(r"\s+", "", f) in rendu or (("/" not in f) and re.sub(r"\s+", "", f.removesuffix(".md")) in rendu) else "non"
    lignes.append([f, len(d), hashlib.sha256(d).hexdigest(), c[0], c[1], c[2], cite])
with open(sys.argv[1], "w", encoding="utf-8-sig", newline="") as fh:
    w = csv.writer(fh, delimiter=";")
    w.writerow(["chemin (depuis docs/dossier-technique)", "taille_octets", "sha256", "categorie", "destination_option_A_recommandee", "destination_option_B", "cite_par_les_documents_de_la_revision_2"])
    w.writerows(lignes)
from collections import Counter
print(len(lignes), "fichiers")
for k, v in sorted(Counter(l[3] for l in lignes).items()): print(v, k)
print(Counter(l[6] for l in lignes))
print("non classés:", [l[0] for l in lignes if l[3] == "non classé"])
