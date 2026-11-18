"""Génère le registre vivant (5_registre/registre.json) et ses vues (Markdown, HTML autonome).

Usage : python generer_registre.py <dossier-technique> <dossier_v12> <sortie_5_registre>
Sources : restreint/ECARTS_DECISIONS_CODE.md (A, B, D), AUDIT_GLOBAL_G0.md (AUD, NE), dossier V1.2 ({{fait:n_decisions_v12}} décisions et lots).
Règles : aucune entrée ne devient « décision » sans mention du PO ; l'état d'une décision est déduit du plan en lots
(M_PLAN_DEVELOPPEMENT.md) et des surcharges vérifiées dans le code ; sans rattachement, l'état reste « à instruire » ⚪.
"""
import html
import json
import unicodedata
import re
import sys
from pathlib import Path

D = Path(sys.argv[1]).resolve()
V12 = Path(sys.argv[2]).resolve()
OUT = Path(sys.argv[3]).resolve()
OUT.mkdir(parents=True, exist_ok=True)
DATE = "2026-11-13"
ETAT = "EB-2026-11-11"
LOTS_LIVRES = {"L01", "L02", "L03", "L05"}


def cellules(ligne):
    return [c.strip() for c in ligne.strip().strip("|").split("|")]


def court(t, n):
    """Coupe à la limite d'un mot, sans laisser de guillemets de code ni de gras ouverts."""
    if len(t) > n:
        t = t[:n].rsplit(" ", 1)[0].rstrip(" ,;(") + " …"
    if t.count("`") % 2:
        t = t.rsplit("`", 1)[0].rstrip() + " …"
    if t.count("**") % 2:
        t = t.rsplit("**", 1)[0].rstrip() + " …"
    return t


def sans_ancienne_mention(t):
    """Le registre cite des défauts de l'ancienne édition sans reproduire la mention qui prêtait à confusion
    (sauf les citations balisées d'AUD-001, conservées comme preuve)."""
    garde = re.findall(r"\[citation d[^\]]*\]", t)
    for k, g in enumerate(garde):
        t = t.replace(g, f"\u2063{k}\u2063", 1)
    t = re.sub(r"(?i)diffusion générale", "[ancienne mention de large diffusion]", t)
    t = t.replace("`**` et `` ` ``", "les astérisques et les accents graves")
    t = re.sub(r"(?i)\bdiffusables?\b", "[ancien qualificatif de large diffusion]", t)
    for k, g in enumerate(garde):
        t = t.replace(f"\u2063{k}\u2063", g)
    return t


def deplier_plages(t):
    """« DEC-PER-01 à 04 », « `DEC-MAT-01` à `DEC-MAT-04` », « DEC-UX-01 à 11 » deviennent des listes explicites."""
    def rep(m):
        fam, a, b = m.group(1), int(m.group(2)), int(m.group(3))
        return ", ".join(f"DEC-{fam}-{k:02d}" for k in range(a, b + 1))
    return re.sub(r"`?DEC-([A-Z]{2,4})-(\d{2})`?\s*(?:à|–)\s*`?(?:DEC-[A-Z]{2,4}-)?(\d{2})`?", rep, t)


TITRES = {
    "A5": "Identifiants stables pour de futures interfaces", "A6": "Documentation du dépôt en retard sur le nombre d'applications",
    "A7": "Modèle de droits sans moteur d'attributs général", "A8": "Cahier des charges partiellement obsolète",
    "A9": "Principe « Internet n'existe pas » et dépendances déclarées", "A10": "Vocabulaire cible sans équivalent dans le code",
    "A11": "Libellé « Mes tours de service »", "A12": "Impression de la feuille de service", "A13": "Priorités de tâche : deux niveaux au lieu de trois",
    "A14": "Confidentialité de la synthèse de passation", "A15": "Circuit de validation des RETEX", "A16": "Diffusion « flotte » d'un RETEX",
    "A17": "Préparation à l'appareillage : fiche de référence et circuit", "A18": "Transfert de matériel entre secteurs et services",
    "A19": "Demande de places de formation", "A20": "Échéance « En validation » : règle de sortie",
    "A21": "Périodicités nommées, remarques d'outillage, durée indicative", "A22": "Version de Python annoncée par l'installation",
    "A23": "Sécurité d'accès avec les SIC", "A24": "Sauvegarde, restauration, supervision, journaux",
    "A25": "Modules désactivés encore actifs par certains chemins", "A26": "Modules sans interface de programmation",
}


def nettoyer(t):
    return re.sub(r"\s+", " ", t.replace("**", "")).strip()


# ---------------- écarts A, points B, propositions D ----------------
ec = (D / "restreint/ECARTS_DECISIONS_CODE.md").read_text(encoding="utf-8")
ecarts = {}
# A1 à A4 : blocs « ### A1. Titre » avec tableau de rubriques
for m in re.finditer(r"### (A\d+)\. (.+?)\n(.*?)(?=\n### A|\n---|\Z)", ec, re.S):
    aid, titre, bloc = m.groups()
    champs = {}
    for l in bloc.split("\n"):
        if l.startswith("| **"):
            c = cellules(l)
            champs[nettoyer(c[0]).lower()] = c[1]
    ecarts[aid] = {"id": aid, "titre": titre.strip(), "regle": champs.get("règle validée", ""), "constat": champs.get("comportement observé", ""),
                   "sources": champs.get("sources", ""), "consequences": champs.get("conséquences", ""), "lot": nettoyer(champs.get("lot de correction", ""))}
# A5 à A26 : lignes de tableau
for l in ec.split("\n"):
    m = re.match(r"^\| (A\d+)\b", l)
    if m and m.group(1) not in ecarts:
        c = cellules(l)
        if len(c) >= 6:
            ecarts[m.group(1)] = {"id": m.group(1), "titre": "", "regle": c[1], "constat": c[2], "sources": c[3], "consequences": c[4], "lot": nettoyer(c[5])}
points = []
for l in ec.split("\n"):
    m = re.match(r"^\| (B\d+) — (.+?) \|", l)
    if m:
        c = cellules(l)
        points.append({"id": m.group(1), "titre": m.group(2).strip(), "decision_existante": c[1], "actuel": c[2], "cible": c[3]})
propositions = []
for l in ec.split("\n"):
    m = re.match(r"^\| (D\d+) \| ", l)
    if m:
        c = cellules(l)
        propositions.append({"id": m.group(1), "titre": nettoyer(c[1]), "origine": c[2], "garde_fous": c[3], "chapitres": c[4]})

# surcharges de l'audit (le registre porte les corrections, jamais l'ancien chapitre)
ecarts["A12"]["constat"] = ("Les versions de la feuille sont conservées (VersionFeuilleService). **Une impression par le navigateur existe** (bouton « Imprimer » de la fiche de la feuille, "
                            "constat AUD-002, vérifié dans le navigateur le 12/11/2026) ; il n'existe ni mise en page A4 dédiée à l'affichage, ni alerte de réimpression, ni réimpression versionnée.")
ecarts["A12"]["revision"] = "Texte révisé : l'ancien énoncé « aucune page imprimable » était inexact (AUD-002)."
ecarts["A14"]["verifications"] = ["test 12/11/2026 (8 tests, comptes fictifs)", "navigateur 12/11/2026 : chef de section de l'équipage sortant lit 28 tâches dont 12 hors de sa section ; équipier et chef d'un autre bâtiment : 404"]
ecarts["A20"]["verifications"] = ["test 12/11/2026 (18 tests)", "navigateur 12/11/2026 : bouton « Enregistrer la correction » visible du seul chef de secteur et au-delà"]
ecarts["A25"]["verifications"] = ["test 12/11/2026 (3 tests de constat)"]
PROFILS = {
    "A1": "administrateur d'unité ; commandement", "A2": "marins ; chefs de liste ; COMAEQ", "A3": "chefs de liste ; chefs de service ; COMAEQ ; commandement",
    "A4": "commandant en second", "A5": "développeurs ; intégrateurs", "A6": "développeurs", "A7": "responsables ; développeurs", "A8": "PO",
    "A9": "exploitants", "A10": "PO", "A11": "marins", "A12": "BSC ; COMAEQ", "A13": "chefs de secteur ; chefs de section", "A14": "chefs de section ; commandement ; équipage sortant",
    "A15": "auteurs de RETEX ; chefs de section, de secteur et de service", "A16": "auteurs de RETEX ; organismes destinataires", "A17": "chefs de secteur ; chefs de service ; COMANAV",
    "A18": "chefs de service ; gestionnaires de matériel", "A19": "référents de formation ; demandeurs ; organismes de formation", "A20": "exécutants ; chefs de secteur ; responsables des installations",
    "A21": "chefs de secteur", "A22": "développeurs ; exploitants", "A23": "exploitants ; SIC", "A24": "exploitants ; SIC", "A25": "administrateurs d'unité ; commandants ; intégrateurs", "A26": "intégrateurs",
}
NIVEAU = {"A14": "[T][N]", "A20": "[T][N]", "A25": "[T]", "A12": "[C][N]"}
liste_a = []
for i in range(1, 27):
    e = ecarts[f"A{i}"]
    e.update({"nature": "écart du logiciel", "statut": "documenté, non arbitré (pas une autorisation de modifier le logiciel)",
              "profils_concernes": PROFILS[e["id"]], "niveau_preuve": NIVEAU.get(e["id"], "[C]"),
              "derniere_verification": {"date": DATE if e["id"] in ("A12", "A14", "A20", "A25") else "2026-11-12", "etat_reference": ETAT}})
    e["titre"] = TITRES.get(e["id"]) or e["titre"]
    for k in ("regle", "constat", "consequences", "sources"):
        e[k] = deplier_plages(e.get(k, ""))
    e["sources"] = re.sub(r"`docs/dossier-technique-v12/([^`]+?)(?:\.md)?`", r"dossier V1.2 (\1)", e["sources"])      # document d'une autre branche : pas une référence de code
    liste_a.append(e)

PROFILS_B = {"B1": "COMAEQ ; commandants", "B2": "commandant en second", "B3": "chefs de liste ; COMAEQ", "B4": "COMAEQ ; commandants", "B5": "chefs de liste ; chefs de service",
             "B6": "marins ; chefs de section", "B7": "PO", "B8": "exploitants ; PO"}
for p in points:
    for k in ("decision_existante", "actuel", "cible"):
        p[k] = deplier_plages(p[k])
    p.update({"nature": "point à confirmer", "statut": "à confirmer par le PO", "profils_concernes": PROFILS_B.get(p["id"], ""), "niveau_preuve": "[C][R]",
              "derniere_verification": {"date": "2026-11-12", "etat_reference": ETAT}})
for p in propositions:
    for k in ("garde_fous", "titre", "origine"):
        p[k] = deplier_plages(p[k])
    p.update({"nature": "proposition (non arbitrée)", "statut": "🟣 à valider par le PO — pas une décision", "profils_concernes": "", "niveau_preuve": "[R]"})

NE = [
    ("NE-01", "Bouton « Exécuter » affiché sans droit d'exécution", "La liste de maintenance affiche « Exécuter » pour des occurrences que le serveur refuse (403) à l'utilisateur ; le bouton « M'assigner » existe aussi.", "marins ; chefs de section", "[N]", "audit_preuves/navigateur_droits.md"),
    ("NE-02", "Lignes de tickets cliquables sans lien ni focus clavier", "Les lignes de la liste des tickets s'ouvrent par un gestionnaire de clic sur la ligne seulement ; non accessible au clavier.", "tous profils", "[C]", "matrix/templates/logistics/ticket_list.html (accès restreint)"),
    ("NE-03", "Redirection HTTPS sans réglage de proxy inverse", "SECURE_SSL_REDIRECT est actif en production sans réglage de proxy TLS ; comportement derrière un proxy non testé.", "exploitants ; SIC", "[C][?]", "chapitre « Exploitation » du dossier technique"),
    ("NE-04", "QR codes liés au nom d'hôte de la requête", "Le QR d'un équipement encode l'adresse absolue de la requête ; un QR imprimé depuis un autre nom d'hôte pointe vers une adresse erronée ; non documenté avant l'audit.", "exploitants ; gestionnaires de matériel", "[C]", "assets/views.py (accès restreint)"),
    ("NE-05", "Codes de refus 404 et 403 hétérogènes", "L'équipier reçoit 404 sur certaines pages d'écriture (nouvelle documentation, passation) et 403 sur la plupart des autres ; masquage volontaire ou incohérence non documentée.", "marins", "[N]", "audit_preuves/navigateur_droits.md"),
    ("NE-07", "Message de fin de compte rendu inexact pour une installation", "À la fin d'un compte rendu non conforme, l'écran annonce « Un ticket correctif sera (ou a été) ouvert automatiquement » pour toute échéance, y compris celle d'une installation, pour laquelle le code ne crée aucun ticket (navigateur, 14/11/2026 : échéance « En validation », 0 ticket créé). Le lien « signaler une anomalie » de cet écran n'apparaît que pour un relevé chiffré hors plage, pas pour un contrôle non conforme.", "marins ; chefs de section ; responsables des installations", "[N][C]", "audit_preuves/maintenance_non_conforme_installation_fin_de_compte_rendu.png ; matrix/templates/maintenance/_execute_done.html:3-4 (accès restreint)"),
    ("NE-06", "Synthèse de passation lisible par l'équipage sortant", "Les chefs de l'équipage sortant, passé à terre, lisent la synthèse figée ; conforme au code, mais l'écart A14 les concerne aussi.", "chefs de l'équipage sortant", "[N]", "audit_preuves/a14_navigateur_chef_section.png"),
]
NE.sort(key=lambda t: t[0])
nouveaux = [{"id": i, "titre": t, "constat": c, "nature": "écart du logiciel (nouveau, issu de l'audit)", "statut": "documenté, non arbitré (pas une autorisation de modifier le logiciel)",
             "profils_concernes": p, "niveau_preuve": n, "preuve": s, "derniere_verification": {"date": "2026-11-12", "etat_reference": ETAT}} for i, t, c, p, n, s in NE]

# ---------------- anomalies documentaires (audit) ----------------
audit = (D / "AUDIT_GLOBAL_G0.md").read_text(encoding="utf-8")
TRAITE = {"AUD-001": "P0-1", "AUD-002": "P0-2", "AUD-004": "P0-2", "AUD-005": "P0-2", "AUD-007": "P0-2", "AUD-010": "P0-2", "AUD-030": "P0-2", "AUD-033": "P0-3", "AUD-003": "P0-4", "AUD-012": "P0-4 / P1-2",
          "AUD-008": "P0-5", "AUD-006": "P0-6", "AUD-031": "P0-6", "AUD-032": "P0-6", "AUD-035": "P0-7", "AUD-011": "P1-1", "AUD-023": "P1-2", "AUD-013": "P1-3", "AUD-016": "P1-3", "AUD-025": "P1-3",
          "AUD-024": "P1-4", "AUD-036": "P1-5", "AUD-022": "P1-6", "AUD-026": "P1-6", "AUD-034": "P1-8 (architecture)"}
TITRES_AUD = {
    "AUD-001": "L'en-tête de chaque page de l'ancien PDF portait une mention de large diffusion contradictoire avec la classification non validée",
    "AUD-002": "Impression de la feuille de service : le dossier la disait introuvable alors qu'un bouton « Imprimer » existe",
    "AUD-003": "Écrans décrits comme « non rejoués » alors que le guide visuel et l'audit les ont rejoués dans un navigateur",
    "AUD-004": "Le premier chapitre promettait les rondes de contrôle, module retiré de l'interface",
    "AUD-005": "La barre de parcours du quotidien (Mon quotidien, Mon équipe, Suivi, Synthèse) n'est décrite nulle part",
    "AUD-006": "Schémas : légende séparée de sa figure et schéma S10 illisible (5,0 pt)",
    "AUD-007": "Le bouton « Exécuter » est affiché sans droit d'exécution, mais c'est le serveur qui décide (refus 403)",
    "AUD-008": "« Vérifié par test » : les fichiers de test n'étaient conservés dans aucun dépôt",
    "AUD-009": "Pages portant 1 à 5 lignes, que le rapport de clôture disait absentes (fusionnée dans AUD-034)",
    "AUD-010": "Rapport du guide visuel : « 25 captures non retenues » et lien de ligne des tickets, deux affirmations inexactes",
    "AUD-011": "Aucun document court pour un décideur",
    "AUD-012": "Sommaires sans numéros de page et deux parcours « marin » contradictoires dans les guides de lecture",
    "AUD-013": "35 captures sur 64 utilisées : des écrans importants manquaient",
    "AUD-014": "Textes anglais du navigateur dans une interface française (dates, boutons de fichier, heures)",
    "AUD-015": "Messages de confirmation superposés et mention « Brouillon abandonné » sur des captures",
    "AUD-016": "Captures en doublon exact ou quasi exact dans le guide visuel",
    "AUD-017": "Formule répétée : « dans la partie restreinte du dossier et la partie restreinte du dossier »",
    "AUD-018": "Identifiants coupés en milieu de mot dans les cellules des tableaux",
    "AUD-019": "Le symbole ⚪ se rendait en petit cercle alors que 🟢, 🔵 et 🟣 sont des pastilles",
    "AUD-020": "Texte de schémas trop petit (5,8 à 6,2 pt) (fusionnée dans AUD-036)",
    "AUD-021": "Trois chiffres différents pour le nombre de tests (≈ 3 950 fonctions, 3 963 tests)",
    "AUD-022": "Recherche de personnes classée cible alors que la catégorie « Marins » existe",
    "AUD-023": "Les chapitres techniques renvoyaient à des chapitres absents du PDF restreint",
    "AUD-024": "Pas de recette du premier jour pour un développeur ni de mise en garde sur la redirection HTTPS derrière un proxy",
    "AUD-025": "Écart A20 : le texte ne précisait pas que l'exécutant et le chef de section ne voient pas le bouton de correction",
    "AUD-026": "Les décisions DEC-… renvoient à une branche et à Notion, non joignables depuis le dossier",
    "AUD-027": "Lignes de la liste des tickets cliquables à la souris seulement, non accessibles au clavier",
    "AUD-028": "Rapports précédents aux chiffres d'origine contradictoires ; 11 fichiers de pilotage à la racine",
    "AUD-029": "Deux personnages différents portent le nom « Durand » dans le chapitre 6 ; noms des captures non repris",
    "AUD-030": "Chemin erroné du scan web : « assets/scan/UUID/ » au lieu de « /scan/UUID/ »",
    "AUD-031": "Annexe générée : lignes tronquées, fragments de tableau et symboles Markdown bruts",
    "AUD-032": "Tableaux Markdown non rendus (barres verticales brutes) dans le PDF restreint",
    "AUD-033": "Des plages de décisions présentées comme « cible, non développée » alors que certaines sont réalisées",
    "AUD-034": "Densité des pages : trop de pages remplies à moins de 70 % et compléments techniques répétitifs",
    "AUD-035": "Les schémas de circuit cible ne se distinguent pas des schémas de fonctionnement réel",
    "AUD-036": "Qualité des 42 schémas : listes de cases sans information relationnelle, un schéma difficile, un illisible",
    "AUD-037": "Rubriques « bis » : traces d'édition d'insertions tardives",
    "AUD-038": "Deux chiffres pour le même inventaire ; annexe F.4 datée de l'ensemble 4",
}
FUSION = {"AUD-009": "AUD-034", "AUD-020": "AUD-036"}
aud = []
def cellules_audit(ligne):
    """Cellules d'une ligne du rapport d'audit ; les barres verticales échappées (\\|) restent dans la cellule."""
    return [c.replace("\\|", "/").strip() for c in re.split(r"(?<!\\)\|", ligne.strip().strip("|"))]


def citer_historique(t):
    """AUD-001 : les formulations anciennes sont conservées comme preuve, balisées comme citations de documents antérieurs."""
    t = re.sub(r"« ?DIFFUSION GÉNÉRALE ?»", "[citation d'un document antérieur : « DIFFUSION GÉNÉRALE »]", t)
    t = re.sub(r"« ?DIFFUSABLE ?»", "[citation du nom d'un fichier antérieur : « DIFFUSABLE »]", t)
    t = re.sub(r"PDF diffusable", "PDF [citation du nom d'un fichier antérieur : « diffusable »]", t)
    return t


CHEMINS = [("`ticket_list.html", "`matrix/templates/logistics/ticket_list.html"), ("`recherche.py:", "`matrix/core/recherche.py:"),
           ("`settings.py:", "`matrix/settings.py:"), ("`23_configuration_deploiement_exploitation.md:", "`restreint/23_configuration_deploiement_exploitation.md:")]


def sain(t):
    for a, b in CHEMINS:
        t = t.replace(a, b)
    t = t.replace("`**` et `` ` ``", "les astérisques et les accents graves")
    return sans_ancienne_mention(nettoyer(t))


for l in audit.split("\n"):
    m = re.match(r"^\| (AUD-\d{3}) \|", l)
    if not m:
        continue
    c = cellules_audit(l)
    if m.group(1) == "AUD-001":
        c = [citer_historique(x) for x in c]
    i = m.group(1)
    n = int(i[4:])
    if len(c) == 9:                        # phase 1 : id, gravité, document, où, constat, preuve, conséquence, correction, priorité
        g, doc, ou, constat, preuve, cons, corr, prio = c[1], c[2], c[3], c[4], c[5], c[6], c[7], c[8]
        if n not in (1, 6):                # dans ces lignes la 4e cellule rappelle l'énoncé mis en cause : elle fait partie du constat
            constat, ou = f"{ou} — {constat}", ""
    elif n <= 29:                          # phase 1 sans colonne « Où » : le document et la page sont dans une seule cellule
        g, doc, ou, constat, preuve, cons, corr, prio = c[1], c[2], "", c[3], c[4], c[5], c[6], c[7]
    elif len(c) == 8:                      # phase 2 : id, gravité, nature, lieu, constat, preuve, correction, priorité
        g, doc, ou, constat, preuve, cons, corr, prio = c[1], c[3], "", c[4], c[5], "", c[6], c[7]
    else:                                  # AUD-031 : barres dans le constat
        g, doc, ou, constat, preuve, cons, corr, prio = c[1], c[3], "", " ".join(c[4:-3]), c[-3], "", c[-2], c[-1]
    if " — " in doc and not ou:            # « Guide visuel p.11, 12 — Messages … » : séparer le document de l'objet du constat
        doc, _, reste = doc.partition(" — ")
        constat = f"{reste} : {constat}" if constat and not constat.startswith("[") else (reste or constat)
    if n >= 30 and not cons:
        cons = "Voir le constat."
    aud.append({"id": i, "nature": "anomalie documentaire", "gravite": sain(g), "document": sain(doc), "page_ou_lieu": sain(ou), "constat": sain(constat),
                "preuve": sain(preuve), "consequence": sain(cons), "correction": sain(corr), "priorite": sain(prio),
                "statut": f"fusionnée dans {FUSION[i]}" if i in FUSION else "ouverte — à traiter par la refonte", "traite_par": TRAITE.get(i, "P2" if i not in FUSION else FUSION[i]),
                "niveau_preuve": "[V][A][C]", "derniere_verification": {"date": "2026-11-12", "etat_reference": ETAT}})

# ---------------- décisions et lots ----------------
src = {}
for l in (V12 / "A1_DECISIONS_S1_S2.md").read_text(encoding="utf-8").split("\n"):
    m = re.match(r"^\| (DEC-[A-Z]{2,4}-\d{2}) \|", l)
    if m:
        c = cellules(l)
        src[m.group(1)] = {"source": c[1], "statut_po": c[2], "acteurs": c[3], "regle": c[4], "precisions": c[5] if len(c) > 5 else ""}
def expand(texte):
    """Identifiants DEC cités dans un texte, plages (« à ») et listes (« 06, 08, 09 ») développées."""
    ids = set()
    for mm in re.finditer(r"DEC-([A-Z]{2,4})-(\d{2})((?:\s*(?:,|et)\s*\d{2}(?!\d))*)(?:\s*(?:à|–)\s*(?:DEC-[A-Z]{2,4}-)?(\d{2}))?", texte):
        fam, a, suite, fin = mm.group(1), int(mm.group(2)), mm.group(3), mm.group(4)
        ids.add(f"DEC-{fam}-{a:02d}")
        for n in re.findall(r"\d{2}", suite or ""):
            ids.add(f"DEC-{fam}-{int(n):02d}")
        if fin:
            for k in range(a, int(fin) + 1):
                ids.add(f"DEC-{fam}-{k:02d}")
    return ids


plan = (V12 / "M_PLAN_DEVELOPPEMENT.md").read_text(encoding="utf-8")
lots = {}
for m in re.finditer(r"^## (L\d{2}) — ([^\n]+?)(?:\s+—\s+\*\*[^\n]*)?\n(.*?)(?=^## L\d{2}|\Z)", plan, re.M | re.S):
    lid, titre, bloc = m.groups()
    ligne = ""
    for l in bloc.split("\n"):
        if re.match(r"^\| \*\*D[ée]cisions", l):
            ligne = l
            break
    if not ligne:
        mm = re.search(r"[Dd][ée]cisions(?: appliquées)?\s+(DEC-[^;\n]*)", bloc)
        ligne = mm.group(1) if mm else ""
    ids = expand(ligne)
    lots[lid] = {"titre": titre.strip(), "decisions": sorted(ids)}
par_decision = {}
for lid, l in lots.items():
    for i in l["decisions"]:
        par_decision.setdefault(i, []).append(lid)
SURCHARGE = {
    "DEC-PER-01": ("partielle", "Les échéances sont générées depuis les plans et fiches (constat sur le code) ; les périodicités nommées ne le sont pas (L19)."),
    "DEC-PER-04": ("réalisée", "Journal d'états des occurrences, retards compris (constat sur le code)."),
    "DEC-UX-01": ("partielle", "Accueil « Aujourd'hui » existant ; cartes et aide progressive non développées (L24)."),
    "DEC-UX-08": ("écart (A11)", "Le libellé affiché est « Mes tours de service »."),
    "DEC-PRE-02": ("réalisée", "Pas de module autonome de passation ; synthèse intégrée."), "DEC-PRE-03": ("réalisée", "Exports PDF, Excel et CSV conservés ; amélioration non traitée."),
    "DEC-PRE-04": ("réalisée", "QR et inspections mobiles : existant conservé, non prioritaire."), "DEC-APP-13": ("réalisée", "Matrix ne délivre pas l'autorisation d'appareiller."),
    "DEC-FDS-07": ("écart (A2)", "La décision revient au chef de liste ou au commandement dans le code (L10)."), "DEC-FDS-14": ("écart (A3)", "Publication par chef de service ou commandement (L09)."),
    "DEC-DRT-02": ("écart (A1)", "L'administrateur d'unité atteint les seuils métier par son niveau (L06)."), "DEC-TAC-04": ("écart (A13)", "Deux priorités seulement (L14)."),
    "DEC-TAC-05": ("écart (A13)", "Pas de règle d'abaissement (L14)."), "DEC-RTX-01": ("écart (A15)", "Une seule étape de validation (L11)."), "DEC-APP-14": ("non développée (A17)", "Pas de fiche de référence d'appareillage (L23)."),
}
decisions = []
for i in sorted(src):
    s = src[i]
    lots_i = par_decision.get(i, [])
    if i in SURCHARGE:
        etat, note, methode = SURCHARGE[i][0], SURCHARGE[i][1], "vérifié dans le code de l'état B"
    elif lots_i and all(l in LOTS_LIVRES for l in lots_i):
        etat, note, methode = "réalisée (lot livré dans l'état B)", "", "plan en lots (V1.2) et comptes rendus de lots"
    elif any(l in LOTS_LIVRES for l in lots_i):
        etat, note, methode = f"partielle ({sum(l in LOTS_LIVRES for l in lots_i)} lot(s) livré(s) sur {len(lots_i)})", "", "plan en lots (V1.2) et comptes rendus de lots"
    elif lots_i:
        etat, note, methode = "non développée", "", "plan en lots (V1.2) : lot non livré dans l'état B"
    else:
        etat, note, methode = "à instruire ⚪", "Non rattachée à un lot par le plan V1.2 ; état dans l'état B non établi.", "aucun rattachement"
    decisions.append({"id": i, "nature": "décision du PO", "statut_po": s["statut_po"], "regle": deplier_plages(s["regle"]), "precisions": deplier_plages(s["precisions"]), "source_po": s["source"], "acteurs": s["acteurs"],
                      "lots": lots_i, "etat_dans_etat_b": etat, "etat_methode": methode, "note": note, "niveau_preuve": "[C]" if methode.startswith("vérifié") else "[R]",
                      "derniere_verification": {"date": DATE, "etat_reference": ETAT}})

# ---- état lot par lot (plan V1.2, comptes rendus de lots et dépôt de l'état B) ----
LOT_ETAT = {"L01": "livré", "L02": "livré", "L03": "livré (validation du PO en attente selon le plan)", "L05": "livré"}
def etat_lot(l):
    return LOT_ETAT.get(l, "non livré dans l'état B")
for d in decisions:
    d["lots_detail"] = [{"lot": l, "titre": lots.get(l, {}).get("titre", ""), "etat": etat_lot(l)} for l in d["lots"]]
    if d["lots_detail"]:
        d["lots_texte"] = " ; ".join(f"{x['lot']} {x['etat'].split(' (')[0]}" for x in d["lots_detail"])
    if d["id"] == "DEC-DRT-05":
        d["note"] = ("Partielle : l'archivage effectif (L02) et la suppression sûre des unités (L03) sont livrés dans l'état B ; le volet « comptes : désactiver au lieu de supprimer » (L04) "
                     "n'est pas lancé. Statut global conservé : partielle. Les lots L02 et L03 attendent encore la validation du PO selon le plan.")
    if d["id"] == "DEC-PRE-06":
        d["note"] = "Partielle : le verrou des commandes de démonstration (L01) est livré ; la sécurité d'accès avec les SIC (L21) n'est pas lancée."
par_id = {d["id"]: d for d in decisions}
def resume_decisions(ids):
    sortie = []
    for i in ids:
        d = par_id[i]
        sortie.append(f"{i} : {d['etat_dans_etat_b']}" + (f" ({', '.join(d['lots'])})" if d["lots"] else ""))
    return sortie
A21 = [f"DEC-PER-{k:02d}" for k in range(1, 5)] + [f"DEC-OUT-{k:02d}" for k in range(1, 6)] + [f"DEC-DUR-{k:02d}" for k in range(1, 8)]
for e in liste_a:
    if e["id"] == "A21":
        e["regle"] = "Périodicités nommées, remarques d'outillage et durée indicative : décisions " + ", ".join(A21) + "."
        e["constat"] = ("État décision par décision (les statuts viennent du plan en lots et du code, sans promotion) : " + " ; ".join(resume_decisions(A21)) + ". "
                        "**Réellement disponible** : génération des échéances depuis les plans et fiches par un intervalle en jours (90 par défaut) ; historique des états conservé, retards compris. "
                        "**Reste à développer** : périodicités nommées (hebdomadaire à quinquennale), échéance calculée depuis la réalisation effective, remarques d'outillage, durée indicative actualisée. "
                        "Seules DEC-PER-01 (partielle) et DEC-PER-04 (réalisée) ont une part existante.")
        e["consequences"] = "Cible validée par le PO, pour l'essentiel non développée ; ne contredit pas le fonctionnement actuel. Aucune règle nouvelle."
        e["lot"] = "L19 (périodicités), L26 (outillage), L20 (durée) : non livrés dans l'état B"

registre = {"meta": {"serie": "Matrix — G0, révision 2", "date": DATE, "etat_reference": ETAT, "mention": "DOCUMENT PROVISOIRE — DIFFUSION RESTREINTE",
                     "regle": "Aucune entrée ne devient une décision sans mention du PO. Une modification = un commit daté.",
                     "preuves": "audit_preuves/ (tests A14, A20, A25 conservés dans les preuves versionnées ; non intégrés au dépôt applicatif sans autorisation du PO)"},
            "ecarts": liste_a, "points_a_confirmer": points, "propositions": propositions, "nouveaux_ecarts": nouveaux, "anomalies_documentaires": aud, "decisions": decisions, "lots": lots}
(OUT / "registre.json").write_text(json.dumps(registre, ensure_ascii=False, indent=1), encoding="utf-8")

# ---------------- vues Markdown (alimentent le PDF du registre) ----------------
def fiche(e, champs):
    L = [f"## {e['id']} — {court(e.get('titre',''), 220)}", "", "| Rubrique | Contenu |", "|---|---|"]
    for k, lab in champs:
        v = e.get(k)
        if isinstance(v, list):
            v = " ; ".join(v)
        if v:
            L.append(f"| **{lab}** | {str(v).replace('|', '/')} |")
    return L + [""]


M = ["# Lire ce registre", "", "> **Public :** PO, responsables, mainteneurs · **Accès restreint** · Source unique : `registre.json` (généré).", "",
     "Ce registre rassemble les **écarts** entre ce que le PO a décidé et ce que fait le logiciel, les **points à confirmer**, les **propositions** non arbitrées, les **anomalies du dossier** et l'**état des {{fait:n_decisions_v12}} décisions**. "
     "Un écart est **documenté, pas autorisé à corriger** : il ne modifie ni le logiciel ni une décision du PO.", "",
     "| Niveau de preuve | Signification |", "|---|---|", "| [C] | lu dans le code de l'état B |", "| [N] | vérifié dans le navigateur (instance de démonstration, données fictives) |",
     "| [T] | vérifié par un test exécuté |", "| [V] | vérifié visuellement |", "| [A] | mesure automatique |", "| [R] | rapporté par une source antérieure, non revérifié |", "| [?] | non vérifié |", "",
     f"**Répartition :** {len(liste_a)} écarts, {len(points)} points à confirmer, {len(propositions)} propositions, {len(nouveaux)} nouveaux écarts du logiciel, {len(aud)} anomalies documentaires ({sum(1 for a in aud if a['statut'].startswith('ouverte'))} ouvertes), {len(decisions)} décisions.", ""]
M += ["# Écarts du logiciel (A1 à A26)", ""]
for e in liste_a:
    M += fiche(e, [("regle", "Règle validée"), ("constat", "Constat dans l'état B"), ("consequences", "Conséquences"), ("sources", "Sources et preuves"), ("profils_concernes", "Profils concernés"), ("lot", "Lot de correction prévu"),
                   ("verifications", "Vérifications"), ("niveau_preuve", "Niveau de preuve"), ("revision", "Révision"), ("statut", "Statut")])
M += [f"# Nouveaux écarts du logiciel (NE-01 à NE-{len(nouveaux):02d})", ""]
for e in nouveaux:
    M += fiche(e, [("constat", "Constat"), ("profils_concernes", "Profils concernés"), ("niveau_preuve", "Niveau de preuve"), ("preuve", "Preuve"), ("statut", "Statut")])
M += ["# Points à confirmer (B1 à B8)", ""]
for e in points:
    M += fiche(e, [("decision_existante", "Décision existante applicable"), ("actuel", "Fonctionnement actuel vérifié"), ("cible", "Règle cible"), ("profils_concernes", "Profils concernés"), ("statut", "Statut")])
M += ["# Propositions non arbitrées (D1 à D7) 🟣", ""]
for e in propositions:
    M += fiche(e, [("origine", "Origine"), ("garde_fous", "Garde-fous demandés"), ("chapitres", "Chapitres concernés"), ("statut", "Statut")])
M += ["# Anomalies du dossier (audit)", "", "> Une fiche par anomalie : constat, document et page, preuve, gravité, traitement prévu et statut sont séparés. Les niveaux de preuve [C] [N] [T] [V] [A] [R] [?] sont définis en début de registre."]
for a in aud:
    M += ["", f"## {a['id']} — {TITRES_AUD[a['id']]}", "", "| Rubrique | Contenu |", "|---|---|"]
    for lab, k in (("Constat", "constat"), ("Document et page concernés", "document"), ("Page, chapitre ou capture", "page_ou_lieu"), ("Preuve", "preuve"), ("Conséquence pour le lecteur", "consequence"),
                   ("Correction recommandée", "correction"), ("Gravité", "gravite"), ("Priorité", "priorite"), ("Traitement prévu", "traite_par"), ("Statut", "statut")):
        if a.get(k):
            M.append(f"| **{lab}** | {a[k].replace('|', '/')} |")
M += ["", "# Décisions du PO et état dans l'état B", "", "> Colonne « Méthode » : **code** = vérifié dans le code de l'état B ; **plan en lots** = déduit du plan en lots du dossier V1.2 (lot livré ou non dans l'état B) ; **aucune** = non rattachée à un lot. « À instruire » signifie que le dossier ne l'a pas établi : ce n'est pas un constat de non-réalisation.", "",
      "| Décision | Règle | Lot(s) | État dans l'état B | Méthode |", "|---|---|---|---|---|"]
for d in decisions:
    METH = {"vérifié dans le code de l'état B": "code", "plan en lots (V1.2) et comptes rendus de lots": "plan en lots", "plan en lots (V1.2) : lot non livré dans l'état B": "plan en lots", "aucun rattachement": "aucune"}
    M.append(f"| <span class='nb'>{d['id']}</span> | {court(d['regle'], 170).replace('|','/')} | {d.get('lots_texte') or '—'} | {d['etat_dans_etat_b']} | {METH.get(d['etat_methode'], d['etat_methode'])} |")
M += ["", "## Précisions sur les décisions partielles", ""]
for d in decisions:
    if d.get("note") and d["etat_dans_etat_b"].startswith("partielle"):
        M.append(f"- **{d['id']}** — {d['note']}")
(OUT / "ECARTS_ET_DECISIONS.md").write_text("\n".join(M) + "\n", encoding="utf-8")
# fichiers sources du document RE (un par partie)
for ancien in OUT.glob("0[0-9]_*.md"):
    ancien.unlink()
parts = "\n".join(M).split("\n# ")
ancien_titres = [re.sub(r"^#+\s+", "", l).strip() for l in (D / "restreint/ECARTS_DECISIONS_CODE.md").read_text(encoding="utf-8").split("\n") if re.match(r"^#{1,4} ", l)]
couvre_ancien = "".join(f"<!-- couvre: restreint/ECARTS_DECISIONS_CODE.md | {t} -->\n" for t in ancien_titres)
for n, p in enumerate(parts, 1):
    texte = (p if p.startswith("# ") else "# " + p)
    if n == 1:
        texte = couvre_ancien + texte
    if texte.startswith(("# Points à confirmer", "# Propositions non arbitrées")):
        texte = "<!-- suite -->\n" + texte
    nom = unicodedata.normalize("NFD", re.sub(r"<!--.*?-->\s*", "", texte).split("\n")[0][2:].lower()).encode("ascii", "ignore").decode()
    (OUT / f"{n:02d}_{re.sub(r'[^a-z0-9]+', '_', nom).strip('_')[:30]}.md").write_text(texte + "\n", encoding="utf-8")

# ---------------- vue HTML autonome (hors ligne) ----------------
def tr(cles, e):
    return "<tr>" + "".join(f"<td>{html.escape(str(e.get(k) if not isinstance(e.get(k), list) else ' ; '.join(e.get(k)) or ''))}</td>" for k in cles) + "</tr>"
corps = []
for titre, cle, cles in [("Écarts du logiciel", "ecarts", ["id", "titre", "constat", "profils_concernes", "lot", "niveau_preuve", "statut"]),
                          ("Nouveaux écarts", "nouveaux_ecarts", ["id", "titre", "constat", "profils_concernes", "niveau_preuve", "statut"]),
                          ("Points à confirmer", "points_a_confirmer", ["id", "titre", "actuel", "cible", "statut"]),
                          ("Propositions", "propositions", ["id", "titre", "origine", "garde_fous", "statut"]),
                          ("Anomalies du dossier", "anomalies_documentaires", ["id", "gravite", "constat", "traite_par", "statut"]),
                          ("Décisions", "decisions", ["id", "regle", "lots", "etat_dans_etat_b", "etat_methode"])]:
    corps.append(f"<h2>{titre}</h2><table class='t'><thead><tr>" + "".join(f"<th>{c}</th>" for c in cles) + "</tr></thead><tbody>" + "".join(tr(cles, e) for e in registre[cle]) + "</tbody></table>")
(OUT / "registre.html").write_text(
    "<!doctype html><html lang='fr'><head><meta charset='utf-8'><title>Registre des écarts et décisions — MTX-G0-R2</title><style>"
    "body{font:14px/1.4 sans-serif;margin:16px;color:#14202e}.bandeau{border:2px solid #14202e;padding:6px 10px;font-weight:700;margin-bottom:6px}"
    "table{border-collapse:collapse;width:100%;margin-bottom:24px}td,th{border:1px solid #b9c3d0;padding:4px 6px;vertical-align:top;font-size:12.5px}th{background:#e8eef6;text-align:left;cursor:pointer}"
    "input{padding:6px;width:320px;margin:6px 0}</style></head><body><div class='bandeau'>DOCUMENT PROVISOIRE — DIFFUSION RESTREINTE</div>"
    "<p>Précaution documentaire : cette mention n'est pas une classification officielle. Classification et destinataires à valider par l'autorité compétente. Ne pas diffuser. "
    f"Édition {DATE} · état décrit {ETAT}.</p><h1>Registre des écarts et décisions</h1><input id='f' placeholder='Filtrer (texte, identifiant, profil…)'>" + "".join(corps) +
    "<script>const f=document.getElementById('f');f.oninput=()=>{const q=f.value.toLowerCase();document.querySelectorAll('tbody tr').forEach(r=>r.style.display=r.textContent.toLowerCase().includes(q)?'':'none')};"
    "document.querySelectorAll('th').forEach(h=>h.onclick=()=>{const t=h.closest('table'),i=[...h.parentNode.children].indexOf(h),b=t.tBodies[0],rs=[...b.rows];"
    "const d=h.dataset.d=h.dataset.d==='1'?-1:1;rs.sort((a,c)=>a.cells[i].textContent.localeCompare(c.cells[i].textContent,'fr',{numeric:true})*d).forEach(r=>b.appendChild(r))})</script></body></html>", encoding="utf-8")

import collections
print("écarts", len(liste_a), "| points", len(points), "| propositions", len(propositions), "| NE", len(nouveaux), "| AUD", len(aud), "| décisions", len(decisions), "| lots", len(lots))
print(collections.Counter(d["etat_dans_etat_b"] for d in decisions))
