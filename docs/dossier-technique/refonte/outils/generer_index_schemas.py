"""Génère `2_referentiel_fonctionnel/31_index_des_schemas.md` : index exhaustif des schémas de la refonte (un par fichier .svg du dossier
schemas/svg), avec leur présence RÉELLE dans le guide, le référentiel et le dossier technique (lue dans les sources), un nom homogène et
des renvois résolus. Un schéma présent seulement dans le dossier technique n'est pas présenté comme figurant dans le référentiel.
Usage : python generer_index_schemas.py"""
import re
from pathlib import Path

R = Path(__file__).resolve().parent.parent
DOCS = {"GU": "1_guide_utilisateur", "RF": "2_referentiel_fonctionnel", "DT": "3_dossier_technique"}
CIBLES = {"S17", "S21", "S31", "S33"}
IMG = re.compile(r"!\[([^\]]*)\]\(\.\./schemas/svg/(S\d+[a-z]?)_[^)]*\.svg\)")
TITRES = {"S02": "Carte des modules et de leurs liens", "S09": "Groupes fonctionnels de paquets", "S09d": "Dépendances entre paquets (détail)", "S10": "Modèle de l'organisation (rattachement)",
          "S10b": "Équipages, modules et seuils", "S24": "Du plan de maintenance à la réalisation", "S25d": "États d'une occurrence de maintenance (vue détaillée)", "S28": "Les trois circuits de formation",
          "S28b": "Formation gérée par le bord", "S39": "Dépendances entre lots", "S40": "Généalogie des branches", "S38": "Feuille de route : cinq phases et lots livrés"}          # N° -> titre homogène (le premier libellé trouvé dans les sources sinon)
PRESENCE = {}        # N° -> {doc: [(fichier, titre h1)]}
for code, d in DOCS.items():
    for f in sorted((R / d).glob("[0-9][0-9]_*.md")):
        t = f.read_text(encoding="utf-8")
        if f.name == "31_index_des_schemas.md":
            continue
        h1 = re.search(r"^# (.+)$", t, re.M)
        for m in IMG.finditer(t):
            alt, n = m.groups()
            titre = re.sub(r"^Schéma S\d+[a-z]? [—-] ", "", alt).strip()
            titre = titre[:1].upper() + titre[1:]
            TITRES.setdefault(n, titre)
            PRESENCE.setdefault(n, {}).setdefault(code, [])
            if (f.stem, h1.group(1)) not in PRESENCE[n][code]:
                PRESENCE[n][code].append((f.stem, h1.group(1)))
tous = sorted({p.name.split("_")[0] for p in (R / "schemas/svg").glob("S*.svg")}, key=lambda s: (int(re.match(r"S(\d+)", s).group(1)), s))
noms = {}
for p in (R / "schemas/svg").glob("S*.svg"):
    noms[p.name.split("_")[0]] = p.stem.split("_", 1)[1].replace("_", " ")
L = ["<!-- couvre: diffusable/annexes/H_index_schemas.md | Annexe H — Index des schémas (généré) -->", "<!-- partie: Références -->", "# Index des schémas", "",
     '<div class="ligne-public"><b>Public :</b> tous · <b>Ce que vous y trouverez :</b> les {n} schémas de la révision 2, la forme de chacun et les documents où ils figurent réellement</div>'.format(n=len(tous)), "",
     "Cet index est **généré** à partir des fichiers de schémas et des sources des trois documents : une ligne par schéma, sans exception. Une colonne par document indique où le schéma figure **réellement** ; « — » signifie qu'il n'y figure pas. Les schémas **CIBLE** portent un bandeau « CIBLE — non développé » dans l'image. Les schémas détaillés propres au dossier technique ne figurent pas dans ce référentiel ; les schémas qui ne sont repris dans aucun des trois documents restent disponibles comme fichiers de la refonte (annexes consultables, table H1).", "",
     "| N° | Schéma | Forme | Guide | Référentiel | Dossier technique |", "|---|---|---|---|---|---|"]
sans = []
for n in tous:
    titre = TITRES.get(n) or noms.get(n, "").capitalize()
    forme = "figure CIBLE" if n in CIBLES else "figure"
    cols = []
    for code in ("GU", "RF", "DT"):
        pr = PRESENCE.get(n, {}).get(code, [])
        cols.append("<br>".join(f"[[{code}:{s}]]" for s, _ in pr) if pr else "—")
    if not PRESENCE.get(n):
        sans.append(n)
    L.append(f"| {n} | {titre} | {forme} | {cols[0]} | {cols[1]} | {cols[2]} |")
L += ["", f"**Schémas non repris dans les trois documents ({len(sans)}) :** " + (", ".join(sans) or "aucun") + ". Leurs fichiers sont conservés dans le dépôt ; leur absence des documents est un choix éditorial de la maquette, pas une perte de fichier.", ""]
(R / "2_referentiel_fonctionnel/31_index_des_schemas.md").write_text("\n".join(L), encoding="utf-8")
print(len(tous), "schémas ;", len(sans), "non repris :", sans)
