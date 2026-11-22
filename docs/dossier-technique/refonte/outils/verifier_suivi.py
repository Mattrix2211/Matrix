"""Cohérence des documents de suivi : empreintes, pages et tailles des PDF cités = fichiers réels ; compteurs, état de la phase 13 et nombre de pages identiques partout.
Lecture seule. Usage : python verifier_suivi.py   (code retour 1 au moindre écart)"""
import csv
import hashlib
import re
import sys
from pathlib import Path

import pypdfium2 as pdfium

R = Path(__file__).resolve().parent.parent
PDFS = R / "pdf_candidats"
NOMS = {"GU": "1_Guide_utilisateur", "RF": "2_Referentiel_fonctionnel", "DT": "3_Dossier_technique_reprise", "RE": "5_Registre_ecarts_decisions"}
SUIVI = [R / "README_DOSSIER.md", R / "REPRISE.md", R / "RAPPORT_RECETTE_REFONTE.md", R / "INVENTAIRE_LIVRABLES.md", R / "baseline/PLAN_BASCULEMENT_V3.md", R / "baseline/RAPPORT_V2_FINAL.md"]
textes = {p: p.read_text(encoding="utf-8") for p in SUIVI}
erreurs = []
total = 0
for code, nom in NOMS.items():
    f = PDFS / f"Matrix_G0R2_{nom}_PROVISOIRE_RESTREINT.pdf"
    h = hashlib.sha256(f.read_bytes()).hexdigest()
    n = len(pdfium.PdfDocument(str(f)))
    total += n
    inv = textes[R / "INVENTAIRE_LIVRABLES.md"]
    ligne = [l for l in inv.split("\n") if f.name in l]
    if not ligne or h not in ligne[0] or f"| {n} |" not in ligne[0] or f"{f.stat().st_size:,}".replace(",", " ") not in ligne[0].replace(" ", " "):
        erreurs.append(f"INVENTAIRE_LIVRABLES.md : ligne de {code} différente du fichier réel (pages {n}, SHA-256 {h[:12]}…)")
# toute empreinte de 64 caractères citée doit être celle d'un PDF actuel ou d'un ancien fichier de l'inventaire
actuelles = {hashlib.sha256((PDFS / f"Matrix_G0R2_{n}_PROVISOIRE_RESTREINT.pdf").read_bytes()).hexdigest() for n in NOMS.values()}
actuelles |= {l[2] for l in csv.reader(open(R / "baseline/inventaire_anciens_documents.csv", encoding="utf-8-sig"), delimiter=";")}
for p, t in textes.items():
    for h in set(re.findall(r"\b[0-9a-f]{64}\b", t)):
        if h not in actuelles:
            erreurs.append(f"{p.name} : empreinte {h[:12]}… ne correspond à aucun PDF actuel")
# journal final : une ligne par page, aucune page sans méthode
lignes = list(csv.DictReader(open(PDFS / "JOURNAL_INSPECTION_FINAL.csv", encoding="utf-8-sig"), delimiter=";"))
if len(lignes) != total:
    erreurs.append(f"JOURNAL_INSPECTION_FINAL.csv : {len(lignes)} lignes pour {total} pages")
if any(not l["methode"] for l in lignes):
    erreurs.append("JOURNAL_INSPECTION_FINAL.csv : page sans méthode")
# état annoncé partout
for p in (R / "README_DOSSIER.md", R / "REPRISE.md", R / "RAPPORT_RECETTE_REFONTE.md"):
    t = textes[p]
    if re.search(r"ne sont pas encore construits|phases? 10 à 13[^.]*non (commenc|engag)", t):
        erreurs.append(f"{p.name} : état obsolète (PDF non construits ou phases 10 à 13 non commencées)")
    if "22/11/2026" not in t:
        erreurs.append(f"{p.name} : date de validation de V2 absente")
for p in (R / "README_DOSSIER.md", R / "REPRISE.md", R / "baseline/PLAN_BASCULEMENT_V3.md"):
    if not re.search(r"basculement[^.]*n'est pas fait|non exécuté|rien n'est déplacé|aucun fichier n'est déplacé", textes[p], re.I):
        erreurs.append(f"{p.name} : n'indique pas que le basculement n'est pas fait")
# compteurs de reconstruction identiques
for p in (R / "REPRISE.md", R / "RAPPORT_RECETTE_REFONTE.md", R / "baseline/RAPPORT_V2_FINAL.md"):
    t = textes[p]
    if not re.search(r"guide 5, référentiel 9, dossier technique 5, registre 3|GU 5, \*\*RF 9\*\*, \*\*DT 5\*\*, RE 3", t):
        erreurs.append(f"{p.name} : compteurs de reconstruction différents de 5 / 9 / 5 / 3")
print(f"{len(SUIVI)} documents de suivi, {total} pages, {len(erreurs)} écart(s)")
for e in erreurs:
    print(" -", e)
sys.exit(1 if erreurs else 0)
