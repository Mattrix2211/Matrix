"""Contrôle C4 de la refonte : références au code applicatif ET références aux preuves documentaires, comptées séparément.

Usage : python verifier_references_refonte.py <racine_etat_B> <fichier.md ...> --rapport <r.md>

Trois classes de références, jamais mélangées :
  CODE     `fichier.py:ligne`, `fichier.py` : vérifiées sur l'état B (fichier, ligne non vide, symbole cité juste avant).
  PREUVE   `audit_preuves/…`, `refonte/…`, `schemas/…`, `couverture/…` : vérifiées dans le dépôt documentaire.
  CLE      identifiants DEC-xxx-nn, A/B/D/NE : vérifiés dans le registre.
Une référence qui n'est pas retrouvée est une ERREUR, jamais une « erreur attendue » : elle n'est comptée dans aucun total de réussite.
Sortie : code 1 s'il existe au moins une erreur ; le rapport donne les trois totaux de réussite et la liste des erreurs.
"""
import argparse
import json
import re
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent          # refonte/
DT = RACINE.parent                                          # docs/dossier-technique/
EXT = r"(?:py|html|js|md|json|yml|bat|txt|csv|png|sh)"
RE_JETON = re.compile(r"`([^`\n]+)`")
RE_FICHIER_LIGNES = re.compile(rf"^([\w./<>-]+\.{EXT}):(\d+(?:[,-]\d+)*)$")
RE_LIGNES_SEULES = re.compile(r"^:(\d+(?:[,-]\d+)*)$")
RE_CHEMIN = re.compile(rf"^[\w./-]+\.{EXT}$")
RE_SYMBOLE = re.compile(r"^[A-Za-z_][\w.]*(?:\(.*\))?$")
PREFIXES_PREUVE = ("audit_preuves/", "refonte/", "schemas/", "couverture/", "guide-visuel/", "outils/", "restreint/", "diffusable/", "pdf/")
RE_CLE = re.compile(r"\b(DEC-[A-Z]{2,4}-\d{2}|NE-\d{2})\b")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("etat_b")
    ap.add_argument("fichiers", nargs="+")
    ap.add_argument("--rapport", required=True)
    a = ap.parse_args()
    B = Path(a.etat_b).resolve()
    reg = json.loads((RACINE / "5_registre/registre.json").read_text(encoding="utf-8"))
    cles = {d["id"] for d in reg["decisions"]} | {e["id"] for e in reg["nouveaux_ecarts"]}
    cache = {}

    def lignes(p):
        if p not in cache:
            cache[p] = p.read_text(encoding="utf-8", errors="replace").splitlines()
        return cache[p]

    ok = {"CODE": 0, "PREUVE": 0, "CLE": 0}
    err = []
    for f in map(Path, a.fichiers):
        dernier = None
        for no, ligne in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
            if ligne.startswith("```") or ligne.lstrip().startswith("<!--"):
                continue
            precedent = None
            for m in RE_JETON.finditer(ligne):
                jeton = m.group(1)
                ecart = ligne[precedent.end():m.start()] if precedent else ""
                symbole = precedent.group(1) if precedent is not None and len(ecart) <= 8 and RE_SYMBOLE.match(precedent.group(1)) and not RE_CHEMIN.match(precedent.group(1)) else None
                precedent = m
                mf = RE_FICHIER_LIGNES.match(jeton)
                ml = RE_LIGNES_SEULES.match(jeton)
                if ml and dernier:
                    fichier, spec = dernier, ml.group(1)
                elif mf:
                    fichier, spec = mf.group(1), mf.group(2)
                    dernier = fichier
                elif RE_CHEMIN.match(jeton) and "/" in jeton:
                    fichier, spec = jeton, None
                    dernier = fichier
                else:
                    continue
                if fichier.startswith(PREFIXES_PREUVE):
                    cible = DT / fichier
                    if cible.is_file():
                        ok["PREUVE"] += 1
                    else:
                        err.append(f"{f.name}:{no}: PREUVE absente du dépôt documentaire : {fichier}")
                    continue
                chemin = B / fichier
                if not chemin.is_file():
                    err.append(f"{f.name}:{no}: CODE absent de l'état B : {fichier}")
                    continue
                if spec is None:
                    ok["CODE"] += 1
                    continue
                contenu = lignes(chemin)
                bon = True
                for morceau in spec.split(","):
                    for n in [int(x) for x in morceau.split("-")]:
                        if n < 1 or n > len(contenu) or not contenu[n - 1].strip():
                            err.append(f"{f.name}:{no}: CODE {fichier}:{n} hors fichier ou ligne vide")
                            bon = False
                if bon and symbole:
                    nom = symbole.split("(")[0].split(".")[-1]
                    n = int(re.split(r"[,-]", spec)[0])
                    if nom not in contenu[n - 1]:
                        err.append(f"{f.name}:{no}: CODE {fichier}:{n} ne contient pas « {nom} »")
                        bon = False
                if bon:
                    ok["CODE"] += 1
            for c in RE_CLE.findall(ligne):
                if c in cles:
                    ok["CLE"] += 1
                else:
                    err.append(f"{f.name}:{no}: CLE inconnue du registre : {c}")
    L = ["# Contrôle C4 — références au code, aux preuves et aux clés du registre", "",
         "| Classe | Vérifiées avec succès |", "|---|---|", f"| Code applicatif (état B) | {ok['CODE']} |", f"| Preuves documentaires | {ok['PREUVE']} |", f"| Clés du registre | {ok['CLE']} |",
         f"| **Erreurs** | **{len(err)}** |", ""]
    L += [f"- {e}" for e in err] or ["Aucune erreur. Aucune erreur « attendue » n'est tolérée ni comptée comme une réussite."]
    Path(a.rapport).write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L[:9]))
    sys.exit(1 if err else 0)


main()
