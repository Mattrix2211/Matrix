"""Contrôle de non-perte : chaque ligne substantielle d'un ancien chapitre doit se retrouver dans le(s) document(s) qui le reprennent
(texte comparé sans mise en forme Markdown). Les lignes absentes sont listées pour relecture ; aucune n'est ignorée en silence.
Usage : python controle_perte_contenu.py [--rapport fichier.md]"""
import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import convertir_chapitres as C
from chemins import ancien as chemin_ancien

R, DT = C.R, C.DT


def norm(t):
    t = re.sub(r"<!--.*?-->", "", t, flags=re.S)
    t = re.sub(r"\[\[[^\]]*\]\]|`|\*|_|\||>|#", " ", t)
    t = t.replace("’", "'")
    return re.sub(r"[^\wàâäçéèêëîïôöûùüÿœ']+", " ", t.lower()).strip()


def corps_nouveaux():
    tout = {}
    for d in ("1_guide_utilisateur", "2_referentiel_fonctionnel", "3_dossier_technique", "5_registre"):
        for f in sorted((R / d).glob("*.md")):
            tout[f"{d}/{f.name}"] = norm(f.read_text(encoding="utf-8"))
    return tout


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rapport", default=str(R / "apercus_G1/controle_perte_contenu.md"))
    a = ap.parse_args()
    nouveaux = corps_nouveaux()
    blob = " ".join(nouveaux.values())
    L, total, perdues = [], 0, 0
    for ancien in [x[0] for x in C.RF + C.DTX] + ["diffusable/01_vision.md", "diffusable/03_lire_ce_dossier.md", "restreint/12_maintenance_anomalies_tickets_technique.md", "diffusable/12_maintenance_anomalies_tickets.md"]:
        manque = []
        for l in chemin_ancien(ancien).read_text(encoding="utf-8").split("\n"):
            if re.match(r"^\s*(#|>|\*Schéma|!\[|---|\*\*Sources)", l):
                continue                      # titres (couverts par les directives), cartouche, légendes de schémas, pieds de sources
            n = norm(l)
            if len(n.split()) < 6:
                continue
            total += 1
            # une ligne est retrouvée si 85 % de ses mots consécutifs (par fenêtres de 5 mots) figurent dans les nouveaux textes
            mots = n.split()
            fen = [" ".join(mots[i:i + 5]) for i in range(0, max(1, len(mots) - 4), 3)]
            if sum(1 for w in fen if w in blob) / len(fen) < 0.6:
                manque.append(l.strip()[:160])
        if manque:
            perdues += len(manque)
            L += [f"### {ancien} — {len(manque)} ligne(s) non retrouvée(s)"] + [f"- {m}" for m in manque] + [""]
    out = [f"# Contrôle de non-perte de contenu", "", f"{total} lignes substantielles examinées ; {perdues} non retrouvées telles quelles (à relire : reformulation, déplacement vers le registre ou perte).", ""] + L
    Path(a.rapport).write_text("\n".join(out), encoding="utf-8")
    print(out[2])
    return perdues


if __name__ == "__main__":
    main()
