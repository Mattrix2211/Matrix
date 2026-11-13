"""Mesure la taille de police effective de chaque schéma à la largeur utile d'une page A4 portrait (176 mm).
Usage : python lisibilite_schemas.py <dossier_svg> <sortie.csv> [seuil_pt]"""
import csv
import re
import sys
from pathlib import Path

SVG, SORTIE = Path(sys.argv[1]), Path(sys.argv[2])
SEUIL = float(sys.argv[3]) if len(sys.argv) > 3 else 8.0
LARGEUR_PT = 176 / 25.4 * 72      # 499 pt
HAUTEUR_PT = 215 / 25.4 * 72      # 609 pt
lignes = [["schema", "largeur", "hauteur", "police_min_px", "echelle", "police_effective_pt", "verdict"]]
ko = 0
for f in sorted(SVG.glob("S*.svg")):
    t = f.read_text(encoding="utf-8")
    t = re.sub(r"[^{}]*mermaidTooltip\{[^}]*\}", "", t)     # règle d'infobulle, jamais affichée : exclue de la mesure
    m = re.search(r'viewBox="([\d.\-]+) ([\d.\-]+) ([\d.]+) ([\d.]+)"', t)
    w, h = float(m.group(3)), float(m.group(4))
    tailles = [float(x) for x in re.findall(r"font-size:\s*([\d.]+)px", t)] + [float(x) for x in re.findall(r'font-size="([\d.]+)', t)]
    # le texte courant est la taille la plus fréquente ; la plus petite hors bandeau compte pour la lisibilité
    mini = min(tailles) if tailles else 16.0
    ech = min(LARGEUR_PT / w, HAUTEUR_PT / h)
    eff = mini * ech
    v = "OK" if eff >= SEUIL else "TROP PETIT"
    ko += v != "OK"
    lignes.append([f.stem.split("_")[0], round(w), round(h), mini, round(ech, 3), round(eff, 1), v])
with SORTIE.open("w", newline="", encoding="utf-8") as g:
    csv.writer(g, delimiter=";").writerows(lignes)
for l in lignes[1:]:
    if l[-1] != "OK":
        print(l)
print(f"{len(lignes)-1} schémas, {ko} sous {SEUIL} pt")
