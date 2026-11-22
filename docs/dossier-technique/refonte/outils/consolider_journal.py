"""Journal d'inspection consolidé : une ligne par page des quatre PDF définitifs, sans nouvelle inspection ni reconstruction.
Chaque page est rattachée à une inspection directe réellement effectuée, par une chaîne de preuves recalculée ici :
identité binaire du document, ou identité graphique (100 ppp, niveaux de gris, pied de page exclu, mêmes dimensions) avec une page déjà inspectée.
Usage : python consolider_journal.py <dossier_pdf_definitifs> <sortie.csv>   (lit les anciens PDF dans l'historique git)"""
import csv
import hashlib
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

import pypdfium2 as pdfium

RACINE = Path(__file__).resolve().parent.parent
PDFS = Path(sys.argv[1])
NOMS = {"GU": "1_Guide_utilisateur", "RF": "2_Referentiel_fonctionnel", "DT": "3_Dossier_technique_reprise", "RE": "5_Registre_ecarts_decisions"}
fichier = lambda c: f"Matrix_G0R2_{NOMS[c]}_PROVISOIRE_RESTREINT.pdf"
inspections = json.load(open(PDFS / "inspections_directes_par_passe.json", encoding="utf-8"))["passes"]
zoom = inspections["63e9be2"].get("grossissement_140_ppp", {})
tmp = Path(tempfile.mkdtemp())


def ancien(rev, code):
    chemin = f"docs/dossier-technique/refonte/pdf_candidats/{fichier(code)}"
    sortie = tmp / f"{rev}_{code}.pdf"
    sortie.write_bytes(subprocess.run(["git", "show", f"{rev}:{chemin}"], capture_output=True, check=True, cwd=RACINE).stdout)
    return sortie


def empreintes(chemin):
    pdf = pdfium.PdfDocument(str(chemin))
    sortie = {}
    for i in range(len(pdf)):
        im = pdf[i].render(scale=100 / 72).to_pil().convert("L")
        w, h = im.size
        sortie[i + 1] = (hashlib.sha256(im.crop((0, 0, w, int(h * 0.93))).tobytes()).hexdigest(), w, h)
    return sortie


def sha(chemin):
    return hashlib.sha256(Path(chemin).read_bytes()).hexdigest()


def lire(nom):
    return list(csv.DictReader(open(PDFS / nom, encoding="utf-8-sig"), delimiter=";"))


j2 = {(r["document"], int(r["page"])): r for r in lire("JOURNAL_INSPECTION_V2.csv")}
j3 = {(r["document"], int(r["page"])): r for r in lire("JOURNAL_INSPECTION_V3.csv")}
faibles = {}
for code in NOMS:
    t = (PDFS / f"controles_{code}.md").read_text(encoding="utf-8")
    faibles[code] = {int(p): int(x) for p, x in re.findall(r"p\.(\d+) remplie à (\d+) %", t)}


def trouver(emp, cible, pages=None):
    """Pages de `emp` pixel pour pixel identiques à `cible` (hash, w, h) ; la plus proche en numéro d'abord."""
    return sorted((p for p, v in emp.items() if v == cible and (pages is None or p in pages)))


def origine_v2(code, p):
    r = j2[(code, p)]
    return f"V2 p.{p} ({r['base_inspection']})", r


lignes = []
for code in ("GU", "RF", "DT", "RE"):
    final = PDFS / fichier(code)
    n = len(pdfium.PdfDocument(str(final)))
    h_final = sha(final)
    if code == "GU":
        v2 = ancien("574a374", "GU")
        assert sha(v2) == h_final, "GU différent de la V2"
        for p in range(1, n + 1):
            o, r = origine_v2("GU", p)
            lignes.append([code, p, "identité binaire du document", f"SHA-256 identique au PDF de la V2 (commit 574a374) : {h_final}", o, r["verdict"], r["observation"]])
        continue
    emp_f = empreintes(final)
    if code == "RE":
        ref = ancien("636bf6b", "RE")
        assert sha(ref) == h_final, "RE différent de la version inspectée"
        e2 = empreintes(ancien("574a374", "RE"))
        for p in range(1, n + 1):
            if p in inspections["636bf6b"]["RE"]:
                lignes.append([code, p, "identité binaire du document", f"SHA-256 identique au PDF du commit 636bf6b : {h_final}", f"inspection directe p.{p} du PDF du commit 636bf6b (relecture à 100 ppp)", "conforme", "constat A25 corrigé ; état inchangé"])
                continue
            q = trouver(e2, emp_f[p])
            assert q, f"RE p.{p} sans page inspectée identique"
            o, r = origine_v2("RE", q[0])
            lignes.append([code, p, "identité binaire du document", f"SHA-256 identique au PDF du commit 636bf6b : {h_final} ; page identique (100 ppp) à la p.{q[0]} de la V2", o, r["verdict"], r["observation"]])
        continue
    e4 = empreintes(ancien("636bf6b", code))
    e3 = empreintes(ancien("5a9885e", code))
    e2 = empreintes(ancien("574a374", code))
    direct_final = set(inspections["63e9be2"][code])
    direct_4 = set(inspections["636bf6b"][code])
    direct_3 = {p for (c, p), r in j3.items() if c == code and r["statut"] == "inspectée"}
    for p in range(1, n + 1):
        if p in direct_final:
            suffixe = " ; grossissement à 140 ppp" if p in zoom.get(code, []) else ""
            lignes.append([code, p, "inspection directe", f"relecture à 100 ppp{suffixe}", "PDF définitif (commit 63e9be2)", "conforme", ""])
            continue
        q = trouver(e4, emp_f[p])
        assert q, f"{code} p.{p} sans page identique dans la version du commit 636bf6b"
        q = min(q, key=lambda x: (x != p, abs(x - p)))
        preuve = f"identique (100 ppp, pied exclu) à la p.{q} du PDF du commit 636bf6b"
        if q in direct_4:
            origine, obs, verdict = f"inspection directe p.{q} du PDF du commit 636bf6b (relecture à 100 ppp)", "", "conforme"
        else:
            r3 = [x for x in trouver(e3, e4[q]) if x in direct_3]
            if r3:
                origine, obs, verdict = f"inspection directe p.{r3[0]} du PDF du commit 5a9885e (journal V3)", j3[(code, r3[0])]["observation"], j3[(code, r3[0])]["verdict"]
            else:
                r2 = trouver(e2, e4[q])
                assert r2, f"{code} p.{q} (636bf6b) sans page inspectée identique"
                origine, r = origine_v2(code, r2[0])
                obs, verdict = r["observation"], r["verdict"]
        lignes.append([code, p, "identité graphique démontrée", preuve, origine, verdict, obs])

# verdicts : réserve de présentation connue (pages peu remplies, justifiées) ; aucun défaut ouvert
sortie = []
for code, p, m, preuve, origine, verdict, obs in lignes:
    assert verdict in ("OK", "conforme", "réserve de présentation"), f"{code} p.{p} : verdict d'origine « {verdict} » à traiter"
    reserve = p in faibles[code] or "réserve" in verdict
    if reserve:
        note = f"page remplie à {faibles[code][p]} % (avertissement C8, réserve connue)" if p in faibles[code] else ""
        obs = " ; ".join(x for x in (obs, note) if x)
        verdict = "réserve de présentation connue"
    else:
        verdict = "conforme"
    sortie.append([code, p, m, preuve, origine, verdict, obs])
with open(sys.argv[2], "w", encoding="utf-8-sig", newline="") as f:
    w = csv.writer(f, delimiter=";")
    w.writerow(["document", "page", "methode", "preuve", "inspection_d_origine", "verdict", "observation"])
    w.writerows(sortie)
from collections import Counter
print(len(sortie), "pages")
print(Counter((l[0], l[2]) for l in sortie))
print(Counter(l[5] for l in sortie))
