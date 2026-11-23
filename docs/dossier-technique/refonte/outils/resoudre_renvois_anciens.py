"""Remplace les anciens renvois « §N.M » (numérotation de l'édition initiale) par le titre de la section visée et, hors du fichier courant,
un renvoi résolu vers le fichier qui la contient. Les renvois au cahier des charges (« cahier des charges §24 ») restent intacts. Idempotent."""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import convertir_chapitres as C
from chemins import glob_ancien

R, DT = C.R, C.DT
# titres de l'ancienne édition : clé (famille, « N.M ») -> titre ; famille : "F" fonctionnel (diffusable), "T" technique (restreint)
TITRES = {}
for fam, glob in (("F", "diffusable/[0-9]*.md"), ("T", "restreint/[0-9]*.md")):
    for f in glob_ancien(glob):
        for l in f.read_text(encoding="utf-8").split("\n"):
            m = re.match(r"^#{2,3} (\d+)(T)?\.(\d+)(?: bis)? (.+)$", l)
            if m:
                TITRES[("T" if (fam == "T" or m.group(2)) else "F", f"{m.group(1)}.{m.group(3)}")] = m.group(4).strip()
FICHIER_RF = {n: s for n, s in C.CHAP_RF.items()}
FICHIER_DT = {n: s for n, s in C.CHAP_DT.items()}
NON = 0


def traiter(chemin, doc):
    global NON
    t = chemin.read_text(encoding="utf-8")
    stem = chemin.stem
    def rep(m):
        global NON
        avant = t[max(0, m.start() - 30):m.start()]
        if re.search(r"(?i)(cahier(?: des charges)?|REFERENCE\.md`?|Cahier) $", avant) or re.search(r"(?i)cahier[^.\n]{0,25}$", avant):
            return m.group(0)
        n, tech, mm = m.group(1), m.group(2), m.group(3)
        fam = "T" if (tech or (doc == "DT" and int(n) >= 18)) else "F"
        titre = TITRES.get((fam, f"{n}.{mm}"))
        if not titre:
            NON += 1
            return m.group(0)
        titre = re.sub(r"[`*]", "", titre)
        titre = re.sub(r" ?[🟢🔵🟣⚪]+", "", titre).strip()
        cible_stem = (FICHIER_DT if fam == "T" else FICHIER_RF).get(int(n))
        cible_doc = "DT" if fam == "T" else "RF"
        if cible_stem == stem or cible_stem is None:
            return f"la section « {titre} »"
        return f"la section « {titre} » ([[{cible_doc}:{cible_stem}]])"
    t2 = re.sub(r"§(\d+)(T)?\.(\d+)", rep, t)
    if t2 != t:
        chemin.write_text(t2, encoding="utf-8")
        print("renvois résolus :", chemin.name)


for d, doc in (("2_referentiel_fonctionnel", "RF"), ("3_dossier_technique", "DT"), ("1_guide_utilisateur", "GU")):
    for f in sorted((R / d).glob("[0-9][0-9]_*.md")):
        traiter(f, doc)
print("non résolus :", NON)
