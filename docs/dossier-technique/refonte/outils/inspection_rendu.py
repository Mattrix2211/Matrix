"""Phase 11 : rend chaque page d'un PDF en images de lecture (portrait : 3 pages par image ; paysage : 2 pages par image) pour l'inspection
visuelle, et enregistre l'empreinte de chaque page (pixels à 48 ppp) pour comparer deux constructions.
Usage : python inspection_rendu.py <pdf> <dossier_sortie> [--ppp 96] [--empreintes empreintes.json]"""
import argparse
import hashlib
import json
from pathlib import Path

import pypdfium2 as pdfium
from PIL import Image, ImageDraw

ap = argparse.ArgumentParser()
ap.add_argument("pdf")
ap.add_argument("sortie")
ap.add_argument("--ppp", type=int, default=96)
ap.add_argument("--empreintes")
a = ap.parse_args()
pdf = pdfium.PdfDocument(a.pdf)
out = Path(a.sortie)
out.mkdir(parents=True, exist_ok=True)
pages = []
emp = {}
for i in range(len(pdf)):
    pg = pdf[i]
    w, h = pg.get_size()
    im = pg.render(scale=a.ppp / 72).to_pil().convert("RGB")
    pages.append((i + 1, w > h, im))
    emp[i + 1] = hashlib.sha256(pg.render(scale=48 / 72).to_pil().convert("L").tobytes()).hexdigest()[:16]
groupes, cur = [], []
for p in pages:
    taille = 3 if not p[1] else 2
    if cur and (cur[0][1] != p[1] or len(cur) >= taille):
        groupes.append(cur); cur = []
    cur.append(p)
if cur:
    groupes.append(cur)
for g in groupes:
    W = sum(im.width for _, _, im in g) + 8 * (len(g) - 1)
    H = max(im.height for _, _, im in g)
    s = Image.new("RGB", (W, H), "#999999")
    x = 0
    for n, _, im in g:
        s.paste(im, (x, 0)); x += im.width + 8
    nom = f"p{g[0][0]:03d}-{g[-1][0]:03d}.png"
    s.save(out / nom)
print(len(groupes), "images de lecture ;", len(pages), "pages")
if a.empreintes:
    Path(a.empreintes).write_text(json.dumps(emp), encoding="utf-8")
