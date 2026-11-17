"""Contrôle C11 sur le PDF du registre : l'état de chacune des 125 décisions imprimé dans le tableau égale celui de registre.json.
Les lignes du tableau commencent par l'identifiant seul sur sa ligne de texte extrait.
Usage : python controle_statuts_pdf.py <registre.pdf> <registre.json>"""
import json
import re
import sys

import pypdfium2 as pdfium

pdf = pdfium.PdfDocument(sys.argv[1])
reg = json.load(open(sys.argv[2], encoding="utf-8"))
lignes = []
for i in range(len(pdf)):
    lignes += [l.strip() for l in pdf[i].get_textpage().get_text_range().replace("\r", "").split("\n")]
debuts = [(k, re.match(r"DEC-[A-Z]{2,4}-\d\d", l).group(0)) for k, l in enumerate(lignes) if re.match(r"DEC-[A-Z]{2,4}-\d\d (?![:—] )", l) and not re.match(r"DEC-[A-Z]{2,4}-\d\d [:—–]", l)]
vus, ecarts = {}, []
for n, (k, i) in enumerate(debuts):
    fin = debuts[n + 1][0] if n + 1 < len(debuts) else len(lignes)
    vus.setdefault(i, " ".join(lignes[k:fin]))
for d in reg["decisions"]:
    seg = re.sub(r"\s+", " ", vus.get(d["id"], "")).replace("⚪", "◯")
    base = d["etat_dans_etat_b"].replace("⚪", "◯").split(" (")[0]
    if not seg or base not in seg:
        ecarts.append((d["id"], d["etat_dans_etat_b"], "absente du tableau" if not seg else "état différent"))
print(f"{len(reg['decisions']) - len(ecarts)} décisions sur {len(reg['decisions'])} retrouvées avec leur état ; {len(ecarts)} écart(s) : {ecarts[:6]}")
sys.exit(1 if ecarts else 0)
