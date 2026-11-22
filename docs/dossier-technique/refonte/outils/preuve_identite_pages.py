"""Preuve d'identité graphique d'une page avec une page déjà inspectée : même rendu (résolution et dimensions identiques, 100 ppp),
pixel pour pixel, bandeau de pied de page exclu (il porte le numéro de page, qui change avec la pagination). Le bandeau d'en-tête est inclus.
Usage : python preuve_identite_pages.py <pdf_nouveau> <sortie.json> <pdf_reference:pages_inspectees|tout> [...]
  ex. : preuve_identite_pages.py new.pdf out.json v2.pdf:tout v4.pdf:9,16,17"""
import hashlib
import json
import sys

import pypdfium2 as pdfium

PPP = 100


def empreintes(chemin, pages=None):
    pdf = pdfium.PdfDocument(chemin)
    sortie = {}
    for i in range(len(pdf)):
        if pages is not None and (i + 1) not in pages:
            continue
        im = pdf[i].render(scale=PPP / 72).to_pil().convert("L")
        w, h = im.size
        sortie.setdefault(hashlib.sha256(im.crop((0, 0, w, int(h * 0.93))).tobytes()).hexdigest(), []).append((i + 1, w, h))
    return sortie


nouveau = empreintes(sys.argv[1])
n_pages = len(pdfium.PdfDocument(sys.argv[1]))
refs = {}
for arg in sys.argv[3:]:
    chemin, _, pages = arg.partition(":")
    pg = None if pages in ("tout", "") else {int(x) for x in pages.split(",")}
    for h, lst in empreintes(chemin, pg).items():
        refs.setdefault(h, []).extend((chemin.split("/")[-1], p, w, hh) for p, w, hh in lst)
res = {}
for h, lst in nouveau.items():
    for (p, w, hh) in lst:
        res[p] = [r for r in refs.get(h, []) if (r[2], r[3]) == (w, hh)]
ident = sorted(p for p, r in res.items() if r)
json.dump({str(p): res.get(p) or [] for p in range(1, n_pages + 1)}, open(sys.argv[2], "w"), ensure_ascii=False)
print(f"{len(ident)} pages sur {n_pages} identiques (pixel pour pixel, pied de page exclu) à une page inspectée ; {n_pages - len(ident)} à examiner")
print("à examiner :", [p for p in range(1, n_pages + 1) if p not in set(ident)])
