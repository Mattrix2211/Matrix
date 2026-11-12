"""Construit les deux versions PDF du dossier : diffusable et restreinte, sans jamais les mélanger.

Usage : python construire_pdf.py <dossier_dossier_technique> <dossier_sortie>

Étapes : (1) contrôle de séparation (arrêt si une violation) ; (2) conversion Markdown → HTML par périmètre, à partir des seuls fichiers
de ce périmètre ; (3) impression PDF par Chromium (Playwright), avec signets, en-tête et pied de page portant le périmètre.
Nécessite : le paquet Python `markdown`, Node et Playwright (Chromium préinstallé). Aucune ressource distante n'est chargée.
"""
import html
import re
import subprocess
import sys
from pathlib import Path

import markdown

D = Path(sys.argv[1]).resolve()
OUT = Path(sys.argv[2]).resolve()
OUT.mkdir(parents=True, exist_ok=True)
OUTILS = Path(__file__).resolve().parent

sep = subprocess.run([sys.executable, str(OUTILS / "controle_separation.py"), str(D)], capture_output=True, text=True)
print(sep.stdout.strip().splitlines()[-1])
if sep.returncode != 0:
    print(sep.stdout)
    sys.exit("Export refusé : les parties diffusable et restreinte se mélangent.")

PERIMETRES = {
    "diffusable": {
        "titre": "Dossier technique intégral de Matrix — édition G0 — partie diffusable",
        "bandeau": "DIFFUSION GÉNÉRALE",
        "notice": "Usage, règles métier, circuits, parcours, droits en clair, glossaire, cible et historique. Aucune référence de code, aucun réglage d'exploitation. "
                  "Cette séparation n'est pas une autorisation de diffusion : la classification et les destinataires restent à valider par le PO.",
        "fichiers": sorted(D.glob("diffusable/[0-9]*.md")) + [D / "diffusable/annexes/A_glossaire.md", D / "diffusable/annexes/H_index_schemas.md"],
        "paysage": set(),
    },
    "restreint": {
        "titre": "Dossier technique intégral de Matrix — édition G0 — partie restreinte",
        "bandeau": "DIFFUSION RESTREINTE",
        "notice": "Architecture, données, sécurité, API, exploitation, déploiement, droits détaillés, registre des écarts et annexes générées. "
                  "Ne pas transmettre en dehors des destinataires validés par le PO et les SIC. La séparation n'est pas une autorisation de diffusion.",
        "fichiers": sorted(D.glob("restreint/[0-9]*.md"), key=lambda p: (int(p.name[:2]), p.name)) + [D / "restreint/ECARTS_DECISIONS_CODE.md"]
        + [D / f"restreint/annexes/{n}" for n in ("B_matrice_role_action.md", "C_index_routes.md", "D_index_modeles.md", "E_taches_commandes_variables.md",
                                                   "F_sources_branches_non_verifies.md", "G_matrice_couverture.md", "H_bis_schemas_restreints.md")],
        "paysage": {"B_matrice_role_action.md", "C_index_routes.md", "D_index_modeles.md", "E_taches_commandes_variables.md",
                    "F_sources_branches_non_verifies.md", "G_matrice_couverture.md", "ECARTS_DECISIONS_CODE.md"},
    },
}
CSS = """
@page { size: A4; margin: 18mm 15mm 18mm 15mm; }
@page paysage { size: A4 landscape; margin: 15mm 10mm 15mm 10mm; }
html { font-family: "DejaVu Sans", "Noto Sans", Arial, sans-serif; font-size: 9.6pt; line-height: 1.42; color: #14202e; }
body { margin: 0; }
.couverture { page-break-after: always; text-align: left; padding-top: 55mm; }
.couverture h1 { font-size: 24pt; border: none; margin: 0 0 8mm 0; page-break-before: avoid; }
.couverture .bandeau { display: inline-block; padding: 3mm 6mm; border: 2px solid #14202e; font-weight: bold; letter-spacing: 1px; margin-bottom: 10mm; }
.couverture p { max-width: 150mm; }
.toc { page-break-after: always; }
.toc h2 { font-size: 15pt; }
.toc li { margin: 1.2mm 0; list-style: none; }
.toc a { color: #14202e; text-decoration: none; }
.chapitre { page-break-before: always; }
.chapitre.paysage { page: paysage; font-size: 8pt; }
h1 { font-size: 18pt; border-bottom: 2px solid #14202e; padding-bottom: 2mm; margin-top: 0; }
h2 { font-size: 13pt; margin-top: 7mm; border-bottom: 1px solid #b9c3d0; padding-bottom: 1mm; page-break-after: avoid; }
h3 { font-size: 11pt; page-break-after: avoid; }
table { border-collapse: collapse; width: 100%; margin: 3mm 0; font-size: 8.4pt; page-break-inside: auto; }
.paysage table { font-size: 7.2pt; }
tr { page-break-inside: avoid; }
th, td { border: 1px solid #b9c3d0; padding: 1.2mm 1.8mm; vertical-align: top; overflow-wrap: break-word; word-break: normal; hyphens: manual; }
td code, th code { overflow-wrap: anywhere; }
th { background: #e8eef6; text-align: left; }
code { font-family: "DejaVu Sans Mono", monospace; font-size: 0.88em; background: #f1f4f8; padding: 0 1mm; overflow-wrap: anywhere; }
pre { background: #f1f4f8; padding: 2mm; overflow-wrap: anywhere; white-space: pre-wrap; }
blockquote { margin: 3mm 0; padding: 2mm 4mm; border-left: 3px solid #5a7aa0; background: #f4f7fb; }
img { max-width: 100%; max-height: 190mm; display: block; margin: 3mm auto; }
em { color: #3a4a5c; }
hr { border: none; border-top: 1px solid #b9c3d0; margin: 5mm 0; break-after: avoid; }
p { orphans: 3; widows: 3; }
li { break-inside: avoid; }
p.sources { break-before: avoid; }
.fin { break-inside: avoid; }
tbody tr:last-child { break-after: avoid; }
table { break-after: avoid; }
h1, h2, h3 { break-after: avoid; }
img { break-inside: avoid; }
"""


def titre_de(md):
    m = re.search(r"^# (.+)$", md, re.M)
    return m.group(1).strip() if m else "Sans titre"


def separer_listes(texte):
    """Python-Markdown exige une ligne vide avant une liste ; GitHub l'admet sans : on l'ajoute pour un rendu identique."""
    sortie, precedent, dans_code = [], "", False
    for ligne in texte.split("\n"):
        if ligne.lstrip().startswith("```"):
            dans_code = not dans_code
        est_item = bool(re.match(r"^(\s*)([-*+]|\d+\.) ", ligne))
        prec_item = bool(re.match(r"^(\s*)([-*+]|\d+\.) ", precedent)) or precedent.startswith("  ")
        if not dans_code and est_item and precedent.strip() and not prec_item and not precedent.lstrip().startswith(("|", ">")):
            sortie.append("")
        sortie.append(ligne)
        precedent = ligne
    return "\n".join(sortie)


def convertir(chemin, paysage):
    brut = separer_listes(chemin.read_text(encoding="utf-8"))
    corps = markdown.markdown(brut, extensions=["tables", "fenced_code", "sane_lists"])
    base = chemin.parent
    def img(m):
        cible = (base / m.group(1)).resolve()
        return f'src="{cible.as_uri()}"'
    corps = re.sub(r'src="(\.\./schemas/svg/[^"]+)"', img, corps)
    corps = re.sub(r'<a href="[^"#][^"]*\.md[^"]*">(.*?)</a>', r"\1", corps)  # liens entre fichiers : texte seul
    corps = re.sub(r"<p>(<strong>Sources)", r'<p class="sources">\1', corps)
    # Le dernier bloc, le filet et les sources restent ensemble : jamais une page qui ne porte que les sources.
    corps = re.sub(r'(<ul>(?:(?!<ul>).)*?</ul>|<p>(?:(?!</p>).)*</p>)(\s*<hr ?/?>\s*<p class="sources">.*?</p>)',
                   r'<div class="fin">\1\2</div>', corps, flags=re.S)
    return titre_de(brut), corps


for nom, cfg in PERIMETRES.items():
    blocs, entrees = [], []
    for i, f in enumerate(cfg["fichiers"]):
        if not f.is_file():
            sys.exit(f"fichier attendu absent : {f}")
        titre, corps = convertir(f, f.name in cfg["paysage"])
        ident = f"c{i}"
        classe = "chapitre paysage" if f.name in cfg["paysage"] else "chapitre"
        corps = re.sub(r"<h1>", f'<h1 id="{ident}">', corps, count=1)
        blocs.append(f'<section class="{classe}">{corps}</section>')
        entrees.append(f'<li><a href="#{ident}">{html.escape(titre)}</a></li>')
    couverture = (f'<section class="couverture"><div class="bandeau">{cfg["bandeau"]}</div><h1>{cfg["titre"]}</h1>'
                  "<p><strong>État du logiciel décrit :</strong> état B, branche <code>claude/l03-suppression-sure-v11</code>, commit <code>6d6d0be</code>, "
                  "<strong>non fusionné dans <code>main</code></strong>.</p>"
                  "<p>Édition G0 — version PDF produite pour validation finale par le PO. Aucun code applicatif n'a été modifié pour la produire.</p>"
                  f"<p>{cfg['notice']}</p>"
                  "<p>Étiquettes : 🟢 réel vérifié · 🔵 cible validée par le PO · 🟣 proposition à valider par le PO · ⚪ non vérifié.</p></section>")
    toc = '<section class="toc"><h2>Sommaire</h2><ul>' + "".join(entrees) + "</ul></section>"
    page = (f'<!doctype html><html lang="fr"><head><meta charset="utf-8"><title>{html.escape(cfg["titre"])}</title><style>{CSS}</style></head><body>'
            + couverture + toc + "".join(blocs) + "</body></html>")
    fichier_html = OUT / f"dossier_{nom}.html"
    fichier_html.write_text(page, encoding="utf-8")
    pdf = OUT / f"Matrix_Dossier_technique_G0_{nom.upper()}.pdf"
    r = subprocess.run(["node", str(OUTILS / "imprimer_pdf.js"), str(fichier_html), str(pdf), cfg["bandeau"] + " — Matrix, dossier technique G0 (état B, non fusionné)"],
                       capture_output=True, text=True)
    print(r.stdout.strip() or r.stderr.strip(), "->", pdf.name)
