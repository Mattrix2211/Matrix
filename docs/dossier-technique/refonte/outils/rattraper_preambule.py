"""Rattrape le texte situé entre le cartouche d'un ancien chapitre et son premier titre de niveau 2, perdu par la première version du
convertisseur. Insère ce texte après la ligne « Public » du fichier converti, s'il n'y figure pas déjà. Usage : python rattraper_preambule.py"""
import re
from pathlib import Path

import convertir_chapitres as C
from nettoyer_sources import nettoyer

R, DT = C.R, C.DT


def preambule(ancien):
    ligne = (DT / ancien).read_text(encoding="utf-8").split("\n")
    i1 = next(i for i, l in enumerate(ligne) if l.startswith("# "))
    j = i1 + 1
    while j < len(ligne) and (not ligne[j].strip() or ligne[j].strip() == "---" or ligne[j].startswith(">")):
        j += 1
    k = j
    while k < len(ligne) and not ligne[k].startswith("## "):
        k += 1
    return ligne[j:k]


def transformer(lignes, doc):
    def img(m):
        alt, fichier = m.group(1), m.group(2)
        nom = Path(fichier).name
        sid = nom[:3]
        if doc == "RF" and sid in C.SCHEMAS_EN_TABLEAU:
            return f"**{alt}** (remplacé par un tableau)\n\n" + C.tableau_de_remplacement(sid)
        nom = C.SVG_NOUVEAU.get(nom, nom)
        if doc == "RF" and nom.startswith("S09"):
            nom = "S09_groupes_fonctionnels.svg"
        return f"![{alt}](../schemas/svg/{nom})"
    sortie = []
    for l in lignes:
        if l.strip() == "---" or re.match(r"^\*Schéma S\d+", l.strip()):
            continue
        sortie.append(re.sub(r"!\[([^\]]*)\]\(([^)]*\.svg)\)", img, l))
    t = "\n".join(sortie)
    t = C.renvois(t, doc)
    t = nettoyer(t, doc == "DT")
    return re.sub(r"\n{3,}", "\n\n", t).strip()


for liste, doc, dossier in ((C.RF, "RF", "2_referentiel_fonctionnel"), (C.DTX, "DT", "3_dossier_technique")):
    for ancien, nouveau, _ in liste:
        pre = preambule(ancien)
        if not any(l.strip() for l in pre):
            continue
        texte = transformer(pre, doc)
        f = R / dossier / nouveau
        t = f.read_text(encoding="utf-8")
        extrait = next((l for l in texte.split("\n") if len(l.strip()) > 25), "")
        if extrait and extrait in t:
            continue
        m = re.search(r'<div class="ligne-public">.*?</div>\n', t)
        if not m:
            print("pas de ligne Public :", nouveau)
            continue
        t = t[:m.end()] + "\n" + texte + "\n" + t[m.end():]
        f.write_text(t, encoding="utf-8")
        print("rattrapé", nouveau, len(texte.split()), "mots")
