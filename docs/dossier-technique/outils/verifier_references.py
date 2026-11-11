"""Vérifie que les références de code citées dans les chapitres existent sur l'état B.

Usage : python verifier_references.py <racine_etat_B> <dossier_dossier_technique> [<ref_git_v12>]

Contrôles : chaque `fichier:ligne` (ou `fichier:l1,l2` ou `:ligne` rattaché au dernier fichier cité) désigne un
fichier existant, une ligne existante et non vide ; chaque chemin cité existe ; chaque identifiant DEC-xxx-nn cité
existe dans le registre des décisions du dossier V1.2 (si une référence git est fournie).
Sortie : code 0 si tout est valide, 1 sinon.
"""
import re
import subprocess
import sys
from pathlib import Path

B = Path(sys.argv[1]).resolve()
D = Path(sys.argv[2]).resolve()
V12 = sys.argv[3] if len(sys.argv) > 3 else None
DEPOT = D.parents[1]

EXT = r"(?:py|html|js|md|json|yml|bat|txt|csv)"
RE_JETON = re.compile(r"`([^`\n]+)`")
RE_FICHIER_LIGNES = re.compile(rf"^([\w./-]+\.{EXT}):(\d+(?:[,-]\d+)*)$")
RE_LIGNES_SEULES = re.compile(r"^:(\d+(?:[,-]\d+)*)$")
RE_CHEMIN = re.compile(rf"^[\w./-]+\.{EXT}$")
RE_DEC = re.compile(r"\bDEC-[A-Z]+-\d+\b")
RE_SYMBOLE = re.compile(r"^[A-Za-z_][\w.]*(?:\(.*\))?$")

erreurs, verifies = [], 0
lignes_cache = {}


def lignes(chemin):
    if chemin not in lignes_cache:
        lignes_cache[chemin] = chemin.read_text(encoding="utf-8", errors="replace").splitlines()
    return lignes_cache[chemin]


def trouver(fichier):
    for base in (B, DEPOT, D):
        if (base / fichier).is_file():
            return base / fichier
    return None


def verifier_lignes(doc, no, fichier, spec):
    global verifies
    chemin = trouver(fichier)
    if chemin is None or chemin.is_relative_to(D) or chemin.is_relative_to(DEPOT / "docs"):
        base_b = B / fichier
        if not base_b.is_file():
            erreurs.append(f"{doc}:{no}: fichier absent de l'état B : {fichier}")
            return
        chemin = base_b
    contenu = lignes(chemin)
    for morceau in spec.split(","):
        bornes = [int(x) for x in morceau.split("-")]
        for n in bornes:
            verifies += 1
            if n < 1 or n > len(contenu):
                erreurs.append(f"{doc}:{no}: {fichier}:{n} hors du fichier ({len(contenu)} lignes)")
            elif not contenu[n - 1].strip():
                erreurs.append(f"{doc}:{no}: {fichier}:{n} ligne vide")


def verifier_symbole(doc, no, fichier, spec, symbole):
    """La ligne citée (la première de `spec`) contient le symbole annoncé juste avant la référence."""
    global verifies
    chemin = B / fichier
    if not chemin.is_file():
        return
    nom = symbole.split("(")[0].split(".")[-1]
    n = int(re.split(r"[,-]", spec)[0])
    contenu = lignes(chemin)
    if 1 <= n <= len(contenu) and nom not in contenu[n - 1]:
        erreurs.append(f"{doc}:{no}: {fichier}:{n} ne contient pas « {nom} » : {contenu[n - 1].strip()[:70]}")


registre = ""
if V12:
    for piece in ("A_REGISTRE_DECISIONS.md", "A1_DECISIONS_S1_S2.md"):
        res = subprocess.run(["git", "-C", str(DEPOT), "show", f"{V12}:docs/dossier-technique-v12/{piece}"],
                             capture_output=True, text=True)
        registre += res.stdout

for md in sorted(D.rglob("*.md")):
    if "couverture" in md.parts or md.name.startswith("G0_") or md.name.startswith("RAPPORT"):
        continue
    doc = str(md.relative_to(D))
    dernier = None
    for no, ligne in enumerate(md.read_text(encoding="utf-8").splitlines(), 1):
        if ligne.startswith("```"):
            continue
        precedent = None
        for correspondance in RE_JETON.finditer(ligne):
            jeton = correspondance.group(1)
            ecart = ligne[precedent.end():correspondance.start()] if precedent else ""
            symbole = precedent.group(1) if precedent is not None and len(ecart) <= 8 and RE_SYMBOLE.match(precedent.group(1)) \
                and not RE_CHEMIN.match(precedent.group(1)) else None
            precedent = correspondance
            m = RE_FICHIER_LIGNES.match(jeton)
            if m:
                dernier = m.group(1)
                verifier_lignes(doc, no, m.group(1), m.group(2))
                if symbole:
                    verifier_symbole(doc, no, m.group(1), m.group(2), symbole)
                continue
            m = RE_LIGNES_SEULES.match(jeton)
            if m and dernier:
                verifier_lignes(doc, no, dernier, m.group(1))
                if symbole:
                    verifier_symbole(doc, no, dernier, m.group(1), symbole)
                continue
            if RE_CHEMIN.match(jeton) and "/" in jeton:
                dernier = jeton  # un chemin seul fixe le fichier des `:ligne` qui suivent
            if RE_CHEMIN.match(jeton) and "/" in jeton and not jeton.startswith(("docs/dossier-technique-v12", "outils/", "couverture/", "schemas/", "restreint/", "diffusable/")):
                verifies += 1
                if not (B / jeton).is_file() and not (DEPOT / jeton).is_file():
                    erreurs.append(f"{doc}:{no}: chemin introuvable sur l'état B : {jeton}")
        if V12:
            for dec in RE_DEC.findall(ligne):
                verifies += 1
                if dec not in registre:
                    erreurs.append(f"{doc}:{no}: décision inconnue du registre V1.2 : {dec}")

print(f"{verifies} références contrôlées, {len(erreurs)} erreur(s)")
for e in erreurs:
    print("ERREUR", e)
sys.exit(1 if erreurs else 0)
