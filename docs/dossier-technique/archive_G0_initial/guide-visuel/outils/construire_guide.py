"""Construit le guide visuel G0 (PDF paysage) à partir des captures et de captures/manifeste.json.

Usage : python3 construire_guide.py <sortie.html>   puis   node imprimer_guide.js <sortie.html> <pdf>
Chaque page est une page A4 paysage fixe ; les numéros de page sont donc connus à la construction.
"""
import html
import json
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
CAP = RACINE / "captures"
M = {m["id"]: m for m in json.load(open(CAP / "manifeste.json", encoding="utf-8"))}

PROFILS = {
    "equipier_a": "equipier_a — Matelot Karim Equipier A (équipier)",
    "chef_section_a": "chef_section_a — Quartier-maître Jade Chef Section A (chef de section)",
    "chef_secteur_a": "chef_secteur_a — Second-maître Hélène Chef Secteur A (chef de secteur)",
    "chef_service_a": "chef_service_a — Maître Gaël Chef Service A (chef de service)",
}
BANDEAU = "DIFFUSION RESTREINTE PROVISOIRE — classification et destinataires à valider par l'autorité compétente"
e = html.escape
pages = []


def fig(section, cid, titre, texte, ch, crop=None):
    pages.append(dict(t="fig", section=section, id=cid, titre=titre, texte=texte, ch=ch))


def paire(section, titre, texte, ch, items, cols=2):
    pages.append(dict(t="paire", section=section, titre=titre, texte=texte, ch=ch, items=items, cols=cols))


def texte_page(section, titre, corps, toc=True):
    pages.append(dict(t="texte", section=section, titre=titre, corps=corps, toc=toc))


# ---------- contenu ----------
pages.append(dict(t="couverture"))
texte_page("Lecture", "Ce que contient ce guide", """
<ul class="gros">
<li><b>Un complément documentaire</b> du dossier technique G0 : il montre l'application telle qu'elle est dans l'<b>état B</b> (<code>claude/l03-suppression-sure-v11</code>, <code>6d6d0be</code>, non fusionné dans <code>main</code>). Ce n'est pas une nouvelle version fonctionnelle de Matrix.</li>
<li><b>Des captures réelles</b>, prises le 12/11/2026 dans un navigateur sur une <b>instance de démonstration isolée</b> (base séparée, accessible seulement depuis la machine locale, 1366×768, aucun service externe). Aucune capture ne provient d'une autre branche ni d'une maquette.</li>
<li><b>Des données exclusivement fictives</b> : bâtiments et marins imaginaires. Quelques données fictives ont été ajoutées à la seule base de démonstration pour remplir des écrans vides (6 matériels, 2 ponts avec plans fictifs, 3 postes du bord). Aucune donnée réelle, opérationnelle ou personnelle n'apparaît.</li>
<li><b>Un profil par capture</b> : chaque légende donne le compte fictif utilisé, car l'écran dépend du rôle.</li>
<li><b>Des parcours</b> plutôt qu'un catalogue d'écrans : les captures sont ordonnées comme le marin ou le chef les rencontre. Les parcours écrivent dans la base de démonstration (compte rendu, anomalie, ticket) pour montrer le résultat.</li>
<li><b>Des repères numérotés</b> ajoutés sur le PDF pour guider l'œil ; ils ne figurent pas dans l'application ni dans les captures sources.</li>
</ul>
<table class="leg"><tr><th>Étiquette</th><th>Dans ce guide</th></tr>
<tr><td>🟢 réel vérifié</td><td>Toutes les captures : écrans réellement accessibles dans l'état B.</td></tr>
<tr><td>🔵 cible validée</td><td>Aucun écran : une fonction cible n'est jamais présentée comme développée.</td></tr>
<tr><td>🟣 proposition</td><td>Aucun écran.</td></tr>
<tr><td>⚪ non vérifié</td><td>Écrans ou comportements non capturés (voir « Limites de l'état B »).</td></tr></table>
""")
texte_page("Lecture", "Sommaire", "@@TOC@@", toc=False)
fig("Matrix en une page", "menu_deplie", "Matrix en une page : un menu par domaine, la recherche et les notifications",
    "Le menu de gauche regroupe l'application en sept domaines (Mon quotidien, Équipements, Maintenance, Activité, Compétences, Supervision, Administration). En haut : le bâtiment, la recherche globale, la cloche et le profil. Les entrées visibles dépendent du rôle.", "chapitres 2 et 17")

S1 = "Parcours 1 — Le marin arrive et consulte sa journée"
fig(S1, "accueil_marin", "Étape 1 — L'accueil « Aujourd'hui »",
    "Après connexion, le marin arrive sur sa journée : ses actions à faire (urgentes en tête), ses quarts et services, ses prochains tours de service. La cloche indique 11 notifications non lues.", "chapitre 6")
fig(S1, "notifications", "Étape 2 — Les notifications",
    "La cloche ouvre le panneau : annonces à accuser, tâches attribuées par le chef. Les alertes urgentes sur l'appareil ne sont pas activées sur cette instance de démonstration.", "chapitre 9")
fig(S1, "calendrier_mois", "Étape 3 — Le calendrier",
    "Le calendrier du mois rassemble quarts, services, maintenance, tâches, absences et programme du bâtiment.", "chapitre 7")
paire(S1, "Étape 4 — La recherche globale",
      "Touche / ou Ctrl+K depuis n'importe quel écran : à gauche un équipement, une installation ou un ticket ; à droite une formation, une tâche ou une personne.", "chapitre 17",
      [("recherche_equipement", (380, 8, 600, 394)), ("recherche_information", (380, 8, 600, 394))])

S2 = "Parcours 2 — Le marin ouvre une tâche et ses consignes"
fig(S2, "taches_liste", "Étape 1 — Mes tâches", "Les tâches attribuées au marin, avec échéance et statut ; une tâche urgente ou bloquée est signalée.", "chapitre 10")
fig(S2, "tache_detail", "Étape 2 — Le détail d'une tâche", "La consigne, le bouton « Démarrer », la zone de compte rendu et la possibilité de signaler un blocage au chef.", "chapitre 10")
fig(S2, "p_tache_2_compte_rendu", "Étape 3 — Démarrer et rédiger le compte rendu", "Après « Démarrer », la tâche passe « En cours » (message de confirmation en bas à droite) ; le marin rédige son compte rendu.", "chapitre 10")
fig(S2, "p_tache_3_terminee", "Étape 4 — Terminer et rendre compte", "La tâche est « Terminée » ; le compte rendu apparaît dans le fil de la tâche et les chefs concernés sont prévenus.", "chapitre 10")

S3 = "Parcours 3 — Le marin réalise une maintenance et rédige le compte rendu"
fig(S3, "occurrences", "Étape 1 — Les maintenances à faire", "La liste des échéances par statut (en retard, en validation, terminée) avec les compteurs « à traiter ».", "chapitre 12")
fig(S3, "execution_fiche", "Étape 2 — La fiche de maintenance", "L'exécution guidée de « Graissage des paliers » (en retard) : contrôles à renseigner et consignes de sécurité de la fiche (EPI, précautions, points critiques).", "chapitre 12")
fig(S3, "p_maintenance_1_saisie", "Étape 3 — Renseigner les contrôles", "Les quatre contrôles sont marqués « Conforme » ; la progression indique 4 / 6 opérations réalisées.", "chapitre 12")
fig(S3, "p_maintenance_2_termine", "Étape 4 — Terminer la maintenance", "« Terminer la maintenance » enregistre le compte rendu ; le statut passe à « Terminée », le bouton devient « Maintenance terminée » et le retour à l'accueil est proposé.", "chapitre 12")

S4 = "Parcours 4 — Le marin signale une anomalie et suit le ticket"
fig(S4, "p_anomalie_1_objet", "Étape 1 — Signaler : l'objet concerné", "Un assistant en quatre étapes ; la première désigne l'installation ou le matériel concerné, le secteur et le lieu.", "chapitre 12")
fig(S4, "p_anomalie_2_nature", "Étape 2 — Signaler : nature et gravité", "Ce que le marin constate (titre court) et la gravité, de 1 (mineure) à 5 (critique).", "chapitre 12")
fig(S4, "p_anomalie_3_description", "Étape 3 — Signaler : description et photo", "Une description libre et une photo, toutes deux facultatives.", "chapitre 12")
fig(S4, "p_anomalie_4_verification", "Étape 4 — Vérifier puis envoyer", "Le récapitulatif avant l'envoi du signalement.", "chapitre 12")
fig(S4, "p_anomalie_5_suivi", "Étape 5 — Le marin suit son signalement", "L'anomalie est « Signalée » ; l'historique et le fil de commentaires sont visibles du marin.", "chapitre 12")
fig(S4, "p_anomalie_7_prise_en_compte", "Étape 6 — Le chef de secteur prend en compte", "Le chef fait avancer l'anomalie (« Prise en compte ») ; le bouton « Convertir en ticket correctif » ouvre le circuit de réparation.", "chapitre 12")
fig(S4, "p_anomalie_8_ticket", "Étape 7 — Le ticket correctif", "Le ticket créé garde le lien vers l'anomalie et suit sept étapes, de « Signalé » à « Clôture ».", "chapitre 12")

S5 = "Parcours 5 — Le marin consulte son prochain tour de service"
fig(S5, "tours_par_jour", "Étape 1 — Les quarts et tours de service", "La semaine par jour, les créneaux du marin en surbrillance et, à droite, « Mon prochain tour ».", "chapitre 8")
fig(S5, "feuille_service", "Étape 2 — La feuille de service du jour", "En-tête, personnel de service et circuit de validation : rédaction, visa du chef de secteur, visa du chef de service, publication par le COMAEQ. Ici la version 1 est publiée.", "chapitre 8")

S6 = "Autres écrans utiles au marin et au chef"
fig(S6, "materiels", "Matériels", "Les matériels du secteur avec leur état. Les six fiches de cette démonstration ont été ajoutées pour la capture (données fictives).", "chapitre 11")
fig(S6, "materiel_detail", "Fiche d'un matériel", "Criticité, tickets ouverts, maintenances en retard, emplacement, et accès direct au signalement d'une anomalie.", "chapitre 11")
fig(S6, "plan_navire", "Plan du navire", "Un plan par pont, sur lequel les matériels sont épinglés ; la couleur de l'épingle indique l'état. Le dessin du pont est fictif.", "chapitre 11")
fig(S6, "stock", "Stock de pièces", "Les pièces par emplacement avec leur niveau (conforme, bas, critique).", "chapitre 13")
fig(S6, "formations", "Formations", "Le catalogue des formations, les qualifications du marin et leurs échéances (« à renouveler »).", "chapitre 14")
fig(S6, "postes", "Postes du bord", "Les postes, leur effectif pourvu et les qualifications manquantes, signalées sans bloquer l'affectation.", "chapitre 10")

S7 = "Fonctions des responsables"
fig(S7, "tache_synthese", "Le chef de section consulte l'activité de son personnel", "L'onglet « Synthèse » : avancement des tâches, retards, blocages, charge par marin et échéances pendant une absence.", "chapitres 6 et 10")
fig(S7, "equipe_calendrier", "Le calendrier de l'équipe", "L'onglet « Mon équipe » du calendrier : quarts, absences et échéances du personnel du chef.", "chapitre 7")
fig(S7, "tours_par_marin", "Quarts et services : la vue du chef de secteur", "Vue « par marin » avec la charge horaire de chacun ; le chef crée les listes et traite les échanges.", "chapitre 8")
fig(S7, "vue_secteur", "La vue d'ensemble du secteur", "Maintenances en retard, tickets ouverts, pièces sous le seuil et répartition des tickets par statut.", "chapitre 6")

S8 = "Limites de l'état B"
fig(S8, "en_validation_execution", "A20 — Une occurrence « En validation »", "Dans l'état B, une maintenance déclarée non conforme passe « En validation ». Ici, le nettoyage du séparateur est dans cet état : la fiche ne propose pas de bouton de validation, seul « Enregistrer la correction » est offert. Aucune règle de sortie n'est décidée (écart A20).", "chapitre 12")
fig(S8, "pret_appareillage", "Prêt à appareiller : aucune session ouverte", "L'écran existe mais reste vide tant qu'un chef n'ouvre pas de session d'appareillage. Il n'a pas été rempli pour cette capture : aucun circuit d'appareillage n'est présenté ici.", "chapitre 16")
texte_page(S8, "Ce que ce guide ne montre pas", """
<table class="lim"><tr><th>Sujet</th><th>Constat dans l'état B</th><th>Dans ce guide</th></tr>
<tr><td><b>A14</b> · synthèse de passation</td><td>Un chef de section lit les tâches, blocages et anomalies de l'autre section ; la règle attendue (sa seule section) n'est pas appliquée. Confirmé par test, comptes fictifs.</td><td>⚪ Non capturé : la synthèse n'existe qu'après la validation d'une relève A/B, parcours non rejoué.</td></tr>
<tr><td><b>A20</b> · « En validation »</td><td>Pas d'action de validation dédiée ; trois chemins de sortie constatés par test ; pas de notification ni d'échéance associées.</td><td>🟢 Figure précédente.</td></tr>
<tr><td><b>A25</b> · modules désactivés</td><td>Les routes web sont refusées mais l'API, l'administration et les tâches planifiées restent actives.</td><td>⚪ Non capturé : aucun écran ne montre ces effets.</td></tr>
<tr><td>Notifications d'appareil et alertes planifiées</td><td>Dépendent de services (clé d'envoi, tâches planifiées) non lancés sur l'instance de démonstration.</td><td>⚪ Seules les notifications déjà créées sont visibles.</td></tr>
<tr><td>Plans de maintenance du secteur</td><td>Écran vide dans cette démonstration (« Aucun plan de maintenance dans votre secteur »).</td><td>⚪ Non illustré.</td></tr>
<tr><td>Transfert de matériel, circuit RETEX cible, fonctions 🔵 et 🟣</td><td>Non développés dans l'état B.</td><td>Aucun écran ; ne pas les déduire de ce guide.</td></tr>
<tr><td>Module « rondes »</td><td>Retiré de l'interface.</td><td>Aucun écran.</td></tr>
<tr><td>Autres navigateurs, autres résolutions, poste Windows</td><td>Non essayés.</td><td>Captures prises avec un seul navigateur à 1366×768.</td></tr></table>
<p class="note">Ce guide complète le dossier technique G0 sans le remplacer. Les écarts A1 à A26 et les points à confirmer sont dans le registre du dossier.</p>
""")
texte_page("Renvois", "Renvois vers le dossier technique", """
<table class="lim"><tr><th>Écran ou parcours</th><th>Chapitre du dossier</th><th>Écran ou parcours</th><th>Chapitre du dossier</th></tr>
<tr><td>Accueil, supervision, vue du secteur</td><td>6 — Accueil et pilotage</td><td>Matériels, plan du navire, installations</td><td>11 — Matériel et installations</td></tr>
<tr><td>Calendrier</td><td>7 — Calendrier</td><td>Maintenance, anomalies, tickets</td><td>12 — Maintenance, anomalies, tickets</td></tr>
<tr><td>Quarts, services, feuille de service</td><td>8 — Quarts, services, feuille</td><td>Stock</td><td>13 — Logistique</td></tr>
<tr><td>Notifications, annonces</td><td>9 — Communication</td><td>Formations</td><td>14 — Formations</td></tr>
<tr><td>Tâches, postes du bord, programme</td><td>10 — Tâches, demandes, programme, postes</td><td>Prêt à appareiller</td><td>16 — Préparation à l'appareillage</td></tr>
<tr><td>Recherche, menu, navigation</td><td>17 — Ergonomie et navigation</td><td>Écarts A14, A20, A25</td><td>Registre des écarts ; chapitres 6, 12 et 25</td></tr></table>
<p class="note">Captures sources organisées par fonctionnalité : dossier <code>guide-visuel/captures/</code> (une image par écran, <code>manifeste.json</code> pour le profil et l'adresse de chaque capture). Écrans capturés mais non retenus dans ce PDF : catalogue, installations, RETEX, documentation, programme du bâtiment, absences, difficultés signalées, vue du service, profil, paramètres.</p>
""")

# ---------- rendu ----------
CSS = """
@page { size: 297mm 210mm; margin: 0 }
* { box-sizing: border-box }
html, body { margin: 0; padding: 0; background: #fff; font-family: 'Noto Sans','DejaVu Sans',Arial,sans-serif; color: #14202e }
.page { width: 297mm; height: 210mm; position: relative; overflow: hidden; page-break-after: always; break-after: page }
.page:last-child { page-break-after: auto }
.hd { position: absolute; top: 0; left: 0; right: 0; height: 11mm; padding: 3.2mm 12mm 0; font-size: 7.5pt; color: #3c4b5e; border-bottom: .4mm solid #c3ccd8; display: flex; justify-content: space-between }
.hd b { color: #14202e }
.ft { position: absolute; bottom: 0; left: 0; right: 0; height: 8mm; padding: 2mm 12mm 0; font-size: 7.5pt; color: #3c4b5e; display: flex; justify-content: space-between }
.sec { position: absolute; top: 13.5mm; left: 12mm; right: 12mm; font-size: 8pt; letter-spacing: .06em; text-transform: uppercase; color: #1d5b7a; font-weight: 600 }
.titre { position: absolute; top: 18.5mm; left: 12mm; right: 12mm; font-size: 14.5pt; font-weight: 700; color: #14202e; line-height: 1.2 }
.texte { position: absolute; top: 28mm; left: 12mm; right: 12mm; font-size: 9.5pt; line-height: 1.35; color: #2a3a4d }
.cadre { position: absolute; left: 12mm; border: .3mm solid #9aa8ba; background: #fff; overflow: hidden }
.cadre img { display: block; width: 100% }
.rep { position: absolute; width: 5.2mm; height: 5.2mm; margin: -2.6mm 0 0 -6.4mm; border-radius: 50%; background: #b3261e; color: #fff; font-size: 7.5pt; font-weight: 700; text-align: center; line-height: 5.2mm; border: .3mm solid #fff }
.cap { position: absolute; left: 12mm; right: 12mm; bottom: 10mm; font-size: 8pt; line-height: 1.35; color: #2a3a4d }
.cap .l1 { font-weight: 600; color: #14202e }
.cap .rp b { color: #b3261e }
.pair .cadre { }
.pair .cap2 { position: absolute; font-size: 7.5pt; color: #2a3a4d; line-height: 1.3 }
.gros { font-size: 10pt; line-height: 1.4; padding-left: 5mm; margin: 0 0 4mm }
.gros li { margin: 0 0 2.2mm }
table { border-collapse: collapse; width: 100%; font-size: 8.8pt; line-height: 1.3 }
th, td { border: .25mm solid #b9c3d0; padding: 1.6mm 2.2mm; text-align: left; vertical-align: top }
th { background: #e9eef4 }
.bl { display: inline-block; width: 2.6mm; height: 2.6mm; border: .35mm solid #6b7a8f; border-radius: 50%; background: #fff; vertical-align: -.3mm; margin-right: .6mm }
.note { font-size: 8.5pt; color: #3c4b5e; margin-top: 3mm }
code { font-family: 'DejaVu Sans Mono', monospace; font-size: 8.4pt; background: #eef2f6; padding: 0 1mm }
.corps { position: absolute; top: 28mm; left: 12mm; right: 12mm }
.toc { font-size: 10.5pt; line-height: 1.9; width: 70% }
.toc div { display: flex; border-bottom: .2mm dotted #b9c3d0 }
.toc span:first-child { flex: 1 }
.cv { background: #14202e; color: #fff }
.cv .bar { position: absolute; left: 0; top: 0; bottom: 0; width: 14mm; background: #1d5b7a }
.cv h1 { position: absolute; left: 34mm; top: 52mm; margin: 0; font-size: 34pt; font-weight: 700 }
.cv .s1 { position: absolute; left: 34mm; top: 76mm; font-size: 15pt; color: #c9d6e6 }
.cv .s2 { position: absolute; left: 34mm; top: 100mm; font-size: 10.5pt; line-height: 1.6; color: #c9d6e6; width: 220mm }
.cv .s3 { position: absolute; left: 34mm; bottom: 24mm; width: 225mm; border: .4mm solid #e6b94c; color: #f4dc97; padding: 3mm 4mm; font-size: 10pt; line-height: 1.45 }
"""


def img_src(cid):
    m = M[cid]
    return (CAP / m["fichier"]).as_uri()


def entete(p, n):
    return f'<div class="hd"><span><b>Matrix — Guide visuel</b> · édition G0 · état B (6d6d0be)</span><span>{BANDEAU}</span></div>'


def pied(n):
    return f'<div class="ft"><span>Captures réelles — instance de démonstration isolée — données fictives</span><span>Page {n}</span></div>'


def tete_page(p):
    return f'<div class="sec">{e(p["section"])}</div><div class="titre">{e(p["titre"])}</div>'


def rendre(p, n, toc_html):
    if p["t"] == "couverture":
        return f"""<section class="page cv"><div class="bar"></div><h1>Matrix — Guide visuel</h1>
<div class="s1">Complément documentaire du dossier technique, édition G0</div>
<div class="s2">Écrans réels de l'état B (<code style="background:#243447;color:#c9d6e6">claude/l03-suppression-sure-v11</code>, <code style="background:#243447;color:#c9d6e6">6d6d0be</code>, non fusionné dans <code style="background:#243447;color:#c9d6e6">main</code>)<br>Parcours du marin et fonctions des responsables · 12/11/2026<br>Instance de démonstration isolée — données entièrement fictives</div>
<div class="s3"><b>DIFFUSION RESTREINTE PROVISOIRE.</b> Aucune diffusion externe. La classification et les destinataires définitifs restent à faire valider par l'autorité compétente. Ce guide n'est pas une nouvelle version fonctionnelle de Matrix.</div></section>"""
    if p["t"] == "texte":
        corps = toc_html if p["corps"] == "@@TOC@@" else p["corps"]
        return f'<section class="page">{entete(p, n)}{tete_page(p)}<div class="corps">{corps}</div>{pied(n)}</section>'
    if p["t"] == "fig":
        m = M[p["id"]]
        rep = "".join(f'<div class="rep" style="left:{r["x"]*100:.2f}%;top:{r["y"]*100:.2f}%">{r["n"]}</div>' for r in m.get("reperes", []))
        leg = " ".join(f'<b>{r["n"]}</b> {e(r["texte"])}' for r in m.get("reperes", []))
        w = 247.0
        h = w * 768 / 1366
        top = 36.5
        return f"""<section class="page">{entete(p, n)}{tete_page(p)}<div class="texte" style="height:8mm">{e(p['texte'])}</div>
<div class="cadre" style="top:{top+6:.1f}mm;left:{(297-w)/2:.1f}mm;width:{w}mm;height:{h:.1f}mm"><img src="{img_src(p['id'])}">{rep}</div>
<div class="cap"><div class="l1">Capture réelle 🟢 · profil : {e(PROFILS[m['profil']])}</div><div>Adresse : {e(m['urlFinale'])} · Dossier technique : {e(p['ch'])}{(' · <span class="rp">Repères : ' + leg + '</span>') if leg else ''}</div></div>{pied(n)}</section>"""
    if p["t"] == "paire":
        items = p["items"]
        k = len(items)
        gap = 4
        cols = p.get("cols", 2)
        w = (297 - 24 - gap * (cols - 1)) / cols
        blocs = []
        for i, (cid, (x0, y0, cw, ch_)) in enumerate(items):
            m = M[cid]
            row, col = divmod(i, cols)
            h = w * ch_ / cw
            top = 38 + row * (h + 14)
            left = 12 + col * (w + gap)
            ig = f'<img style="width:{1366/cw*100:.2f}%;margin-left:-{x0/cw*100:.2f}%;margin-top:-{y0/cw*100:.2f}%" src="{img_src(cid)}">'
            blocs.append(f'<div class="cadre" style="top:{top:.1f}mm;left:{left:.1f}mm;width:{w:.1f}mm;height:{h:.1f}mm">{ig}</div>'
                         f'<div class="cap2" style="top:{top+h+1:.1f}mm;left:{left:.1f}mm;width:{w:.1f}mm"><b>{e(m["titre"])}</b><br>Profil : {e(m["profil"])} · {e(m["urlFinale"])}</div>')
        return f'<section class="page pair">{entete(p, n)}{tete_page(p)}<div class="texte" style="height:8mm">{e(p["texte"])}</div>{"".join(blocs)}<div class="cap"><div class="l1">Captures réelles 🟢 (extraits rognés de la page, sans retouche) · Dossier technique : {e(p["ch"])}</div></div>{pied(n)}</section>'


def table_matieres(pages):
    lignes, vus = [], set()
    for i, p in enumerate(pages, 1):
        s = p.get("section")
        if p["t"] == "couverture" or not s or s in vus or p["t"] == "texte" and p.get("titre") == "Sommaire":
            continue
        vus.add(s)
        lignes.append(f'<div><span>{e(s)}</span><span>p. {i}</span></div>')
    return '<div class="toc">' + "".join(lignes) + "</div>"


def main(sortie):
    toc = table_matieres(pages)
    corps = "".join(rendre(p, i, toc) for i, p in enumerate(pages, 1))
    Path(sortie).write_text(f'<!doctype html><html lang="fr"><head><meta charset="utf-8"><title>Matrix — Guide visuel G0</title><style>{CSS}</style></head><body>{corps}</body></html>'.replace("⚪", '<span class="bl"></span>'), encoding="utf-8")
    print(len(pages), "pages")


main(sys.argv[1])
