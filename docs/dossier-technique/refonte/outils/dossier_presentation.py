"""Dossier de présentation du pilote V1 : pages représentatives des trois documents, choix graphiques, points à arbitrer.
Usage : python dossier_presentation.py   (lit apercus_V1/*.pdf, écrit apercus_V1/DOSSIER_PRESENTATION_PILOTE_V1.pdf)"""
import html
import json
import re
import subprocess
from pathlib import Path

import pypdfium2 as pdfium
import yaml

R = Path(__file__).resolve().parent.parent
A = R / "apercus_V1"
IMG = A / "presentation_img"
IMG.mkdir(exist_ok=True)
ident = yaml.safe_load((R / "config/identite.yaml").read_text(encoding="utf-8"))
PDF = {"RF": "Matrix_G0R2_2_Referentiel_fonctionnel_PROVISOIRE_RESTREINT.pdf", "GU": "Matrix_G0R2_1_Guide_utilisateur_PROVISOIRE_RESTREINT.pdf",
       "DT": "Matrix_G0R2_3_Dossier_technique_reprise_PROVISOIRE_RESTREINT.pdf"}


def page_contenant(code, marqueur, apres=0):
    d = pdfium.PdfDocument(str(A / PDF[code]))
    for i in range(len(d)):
        if i >= apres and marqueur in d[i].get_textpage().get_text_range():
            return i + 1
    raise SystemExit(f"{code} : marqueur introuvable : {marqueur}")


def image(code, page, dpi=110):
    d = pdfium.PdfDocument(str(A / PDF[code]))
    f = IMG / f"{code}_p{page:02d}.png"
    d[page - 1].render(scale=dpi / 72).to_pil().convert("RGB").save(f, optimize=True)
    return f.as_uri(), len(d)


CHOIX = [
    ("RF", "⟦rf-1-1⟧", "Fiche de module", "Ouverture directe sur le contenu (surtitre de partie discret, plus de page de titre). Cartouche réduit à une ligne ; une fiche = à quoi ça sert, qui fait quoi, règles, état actuel et prévu, limites."),
    ("RF", "⟦rf-1-6⟧", "Actuel / prévu / décisions", "Pastilles 🟢 🔵 🟣 ◯ dessinées ; seules les décisions utiles au lecteur sont affichées, avec renvoi au registre central (RE)."),
    ("GU", "La liste des maintenances", "Page de capture", "Capture pleine largeur en paysage ; légende : profil de démonstration, étiquette, repères ; mention « capture provisoire » tant que la phase 4 n'a pas repris les captures."),
    ("GU", "Étape 2 — La fiche", "Repères numérotés", "Repères discrets (4,4 mm, placés dans la marge gauche de l'élément) : jamais sur un bouton ni un libellé d'action."),
    ("GU", "LIMITE ACTUELLE", "Limite visible", "Une limite du logiciel (écart A20) est illustrée par un écran réel et renvoie à l'écart documenté, sans règle inventée."),
    ("DT", "⟦dt-1-3⟧", "Schéma et transitions", "Schéma lisible (≥ 8 pt) suivi d'un tableau « transition → où elle est écrite » avec fichier et ligne."),
    ("DT", "⟦dt-1-7⟧", "Routes générées", "Tableau généré depuis l'inventaire du code ; césures contrôlées (plus de mots coupés au hasard)."),
]
vignettes = []
for code, marqueur, titre, texte in CHOIX:
    p = page_contenant(code, marqueur if marqueur.startswith("⟦") else marqueur, 2)
    src, n = image(code, p)
    vignettes.append((code, p, n, titre, texte, src))

S09_new = (R / "schemas/svg/S09_groupes_fonctionnels.svg").as_uri()
S09_old = (R / "schemas/svg/S09d_dependances_detail.svg").as_uri()
S17 = (R / "schemas/svg/S17_echange_cible.svg").as_uri()
S10a = (R / "schemas/svg/S10_organisation_rattachement.svg").as_uri()

CSS = """
@page { size: A4 landscape; margin: 20mm 14mm 16mm 14mm; }
html { font-family: "DejaVu Sans","Noto Sans",Arial,sans-serif; font-size: 10pt; line-height: 1.42; color:#14202e }
h1 { font-size: 21pt; border-bottom: 2px solid #14202e; padding-bottom: 2mm; margin: 0 0 4mm 0 }
h2 { font-size: 14pt; margin: 0 0 3mm 0; color:#1f3b63 }
.page { page-break-after: always } .page:last-child { page-break-after: auto }
.deux { display: flex; gap: 8mm; align-items: flex-start }
.deux figure { margin: 0; width: 50% ; text-align:center }
.deux img { width: 100%; max-height: 137mm; object-fit: contain; border: .3mm solid #8d9bb0; background:#fff }
figcaption { font-size: 8.8pt; text-align: left; margin-top: 1.6mm }
table { border-collapse: collapse; width: 100%; font-size: 9.4pt } th, td { border: 1px solid #b9c3d0; padding: 1.5mm 2.2mm; vertical-align: top } th { background:#e8eef6; text-align:left }
.mention { display:inline-block; border:2px solid #14202e; padding:2mm 5mm; font-weight:700; letter-spacing:.7px; margin-bottom:3mm }
.petit { font-size: 8.6pt; color:#5a6b7d } ul { margin: 0 0 3mm 0; padding-left: 5mm }
.s09 img { max-width: 100%; max-height: 120mm } .s09 .deux figure { width: 50% }
"""
def fig(src, cap):
    return f'<figure><img src="{src}"><figcaption>{cap}</figcaption></figure>'
P = []
P.append(f"""<section class="page"><div class="mention">{html.escape(ident['mention'])}</div>
<p class="petit">{html.escape(ident['precaution'])}</p>
<h1>Dossier de présentation du pilote — jalon V1</h1>
<p><b>{ident['serie']}</b> · {ident['reference_documentaire']} · édition {ident['date_edition']} · état décrit {ident['etat_reference']}</p>
<p>Ce dossier aide à relire <b>les trois PDF pilotes dans leur forme réelle</b>. Il ne remplace pas leur lecture : il montre des pages représentatives, explique les choix graphiques et liste les points qui restent à arbitrer. Seul le chapitre « Maintenance » est rédigé ; aucune rédaction complète n'est engagée.</p>
<table><tr><th>À examiner (dossier <code>refonte/apercus_V1/</code>)</th><th>Pages</th><th>Public</th></tr>
<tr><td>Guide utilisateur illustré (GU)</td><td>{vignettes[2][2]}</td><td>marins, chefs</td></tr>
<tr><td>Référentiel fonctionnel et de gouvernance (RF)</td><td>{vignettes[0][2]}</td><td>responsables, commandement, décideurs</td></tr>
<tr><td>Dossier technique de reprise (DT)</td><td>{vignettes[5][2]}</td><td>développeurs, mainteneurs (accès restreint)</td></tr>
<tr><td>Registre des écarts et décisions (RE) — vue du registre central, hors pilote de rédaction</td><td>36</td><td>PO, mainteneurs (accès restreint)</td></tr></table>
</section><section class="page"><h2>Ce qui a changé depuis le rapport V1 (vos arbitrages)</h2>
<table><tr><th>Arbitrage</th><th>Réalisé</th></tr>
<tr><td>1. Supprimer les pages de partie presque vides</td><td>Fait : la partie devient un surtitre au-dessus du premier titre ; aucune page de titre seule.</td></tr>
<tr><td>2. Conserver des repères discrets</td><td>Fait : repères réduits (4,4 mm) et posés dans la marge de l'élément ; vérifiés à l'œil sur les 2 pages du pilote qui en portent (GU p. 4 et 5).</td></tr>
<tr><td>3. Fiches : écarts et décisions pertinents seulement</td><td>Fait : 6 décisions (sur 21) et 5 écarts (sur 7) affichés ; un encadré « Registre central » renvoie au reste.</td></tr>
<tr><td>4. S09 : vue par groupes fonctionnels</td><td>Fait : S09 synthétique (5 groupes) ; l'ancien S09 devient S09d, réservé au dossier technique (page suivante).</td></tr>
<tr><td>5. Contrôleur C4</td><td>Fait : trois totaux séparés (code, preuves, clés du registre) ; aucune erreur « attendue » tolérée ; essai négatif réussi (3 fausses références détectées).</td></tr>
<tr><td>6. Revue manuelle de C2</td><td>Faite : 14 affirmations étiquetées relues contre l'ancien texte et le code ; 3 corrections ou précisions ; voir <code>REVUE_MANUELLE_C2.md</code>.</td></tr></table></section>""")
for i in range(0, len(vignettes), 2):
    g = vignettes[i:i + 2]
    P.append('<section class="page"><h2>Pages représentatives</h2><div class="deux">' + "".join(
        fig(v[5], f"<b>{v[0]} p. {v[1]} / {v[2]} — {html.escape(v[3])}.</b> {html.escape(v[4])}") for v in g) + "</div></section>")
P.append(f"""<section class="page s09"><h2>S09 : vue synthétique et vue détaillée</h2><div class="deux">
{fig(S09_new, "<b>Vue synthétique (référentiel et dossier technique).</b> 5 groupes fonctionnels ; seuls les couples de groupes reliés par au moins 5 liens entre paquets sont tracés ; les chiffres viennent de l'inventaire complet du code (imports entre paquets). Note à porter dans le texte : <i>notifications</i> (socle) lit presque tous les autres paquets.")}
{fig(S09_old, "<b>Vue détaillée (dossier technique seulement).</b> L'ancien S09 (extrait de 31 liens entre paquets), conservé tel quel pour le mainteneur.")}
</div></section>""")
P.append(f"""<section class="page"><h2>Autres choix graphiques</h2>
<table><tr><th>Sujet</th><th>Choix</th><th>Pourquoi</th></tr>
<tr><td>Mention</td><td>« {html.escape(ident['mention'])} » en en-tête de chaque page et sur la couverture, avec la précaution « pas une classification officielle »</td><td>Précaution documentaire, sans laisser croire à une diffusion autorisée</td></tr>
<tr><td>Identité</td><td>Référence {ident['reference_documentaire']}, série « {ident['serie']} », état décrit {ident['etat_reference']} ; correspondance avec l'état applicatif seulement dans la couverture du DT</td><td>Traçabilité sans exposer de référence interne dans GU et RF</td></tr>
<tr><td>Étiquettes</td><td>Pastilles 🟢 🔵 🟣 ◯ (le ⚪ était rendu « ◦ » illisible)</td><td>Distinction actuel / cible / proposition / non vérifié reconnaissable</td></tr>
<tr><td>Schémas</td><td>Corps ≥ 8 pt à la largeur de page (44 sur 44) ; S10 scindé ; circuits cibles (S17, S21, S31, S33) marqués « CIBLE… NON DÉVELOPPÉ » dans l'image avec cadre pointillé</td><td>Ne jamais prendre une cible pour un existant</td></tr>
<tr><td>Sommaire</td><td>Paginé, calculé en deux passes, vérifié (0 écart)</td><td>Consultation comme manuel de référence</td></tr>
<tr><td>Captures</td><td>Paysage, pleine largeur, légende avec profil et repères ; « capture provisoire » tant que la phase 4 n'est pas faite</td><td>Lisibilité ; honnêteté sur l'état des captures</td></tr>
<tr><td>Tableaux</td><td>En-tête répétée, lignes jamais coupées, identifiants avec césures contrôlées</td><td>Lisibilité des annexes</td></tr></table>
<p class="petit">Exemple de schéma cible marqué dans l'image (S17) : voir <code>refonte/schemas/svg/S17_echange_cible.svg</code>.</p></section>""")
P.append(f"""<section class="page"><h2>Points restant à arbitrer</h2>
<table><tr><th>#</th><th>Sujet</th><th>Constat</th><th>Options</th></tr>
<tr><td>1</td><td>Fins de page blanches</td><td>Une page de texte portrait suivie d'une page de capture paysage laisse le bas de la page de texte vide (GU p. 3 : environ 40 % de blanc ; p. 18)</td><td>(a) accepter ; (b) regrouper tout le texte d'un parcours avant les captures ; (c) captures en portrait, plus petites (texte d'écran ≈ 5 pt : non recommandé)</td></tr>
<tr><td>2</td><td>Taille des captures</td><td>232 mm de large, texte d'écran ≈ 6 pt. Les captures contiennent le menu latéral et l'en-tête de l'application</td><td>(a) conserver ; (b) recadrer sur la zone utile (sans menu) pour agrandir de 25 % ; (c) deux niveaux : écran entier puis zoom</td></tr>
<tr><td>3</td><td>Renvois entre documents</td><td><code>GU §1</code>, <code>RF §1</code>, <code>RE §7</code> sont des mentions de texte : seuls les renvois du même document sont des liens</td><td>(a) accepter (PDF séparés) ; (b) créer une édition « bundle » avec liens ; (c) ajouter la page de destination aux renvois</td></tr>
<tr><td>4</td><td>Sommaire du pilote</td><td>Une page de sommaire n'a qu'un chapitre ; normal en pilote</td><td>Sans objet après rédaction complète</td></tr>
<tr><td>5</td><td>Décisions « à instruire »</td><td>20 décisions sur 125 n'ont pas de lot dans le plan V1.2 ; leur état n'est pas établi</td><td>(a) les instruire pendant la rédaction ; (b) les laisser « à instruire » avec la mention actuelle</td></tr>
<tr><td>6</td><td>Captures provisoires</td><td>12 captures du 12/11/2026, textes anglais du navigateur, messages parasites</td><td>Reprise en phase 4 (non engagée)</td></tr>
<tr><td>7</td><td>Relecture indépendante</td><td>Mon inspection des aperçus est partielle et n'est pas indépendante (voir rapport)</td><td>Relecture par une personne autre que l'auteur ; je peux préparer une grille de relecture</td></tr>
<tr><td>8</td><td>Place du registre central (RE)</td><td>Un PDF de 36 pages existe en aperçu ; les fiches n'en reprennent que l'essentiel</td><td>(a) conserver comme 4e document ; (b) l'intégrer au dossier technique</td></tr></table>
<p><b>Aucune des phases 4 à 13 n'est lancée. J'attends votre validation explicite de V1.</b></p></section>""")
html_doc = f'<!doctype html><html lang="fr"><head><meta charset="utf-8"><title>Dossier de présentation du pilote V1</title><style>{CSS}</style></head><body>{"".join(P)}</body></html>'
(A / "presentation.html").write_text(html_doc, encoding="utf-8")
cfg = A / "presentation.config.json"
cfg.write_text(json.dumps({"entete_gauche": f"{ident['reference_documentaire']} · présentation du pilote V1 · {ident['date_edition']}", "entete_centre": ident["mention"], "entete_droite": ident["serie"],
                           "pied_gauche": "Dossier de présentation du pilote V1 — non validé"}, ensure_ascii=False), encoding="utf-8")
r = subprocess.run(["node", str(R / "outils/imprimer.js"), str(A / "presentation.html"), str(A / "DOSSIER_PRESENTATION_PILOTE_V1.pdf"), str(cfg)], capture_output=True, text=True)
print(r.returncode, r.stderr[-300:])
print(len(pdfium.PdfDocument(str(A / "DOSSIER_PRESENTATION_PILOTE_V1.pdf"))), "pages")
