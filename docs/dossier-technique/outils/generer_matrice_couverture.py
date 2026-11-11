"""Génère la matrice de couverture (annexe G) : élément du code -> chapitre -> état de rédaction.

Usage : python generer_matrice_couverture.py <dossier_dossier_technique>

Un modèle est « rédigé » dès que son nom figure dans un chapitre rédigé ; sinon il reste « dictionnaire seul »
(présent dans MODELES.md, expliqué dans l'ensemble indiqué).
"""
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

D = Path(sys.argv[1]).resolve()
inv = json.loads((D / "couverture/etat_B/inventaire.json").read_text(encoding="utf-8"))
redige = {p.name: p.read_text(encoding="utf-8") for p in list(D.glob("diffusable/*.md")) + list(D.glob("restreint/*.md"))
          if re.match(r"\d\d_", p.name)}
texte = "\n".join(redige.values())
texte_sans_19 = "\n".join(v for k, v in redige.items() if not k.startswith("19_"))
fichiers = sorted(redige)

PAQUETS = {  # paquet -> (chapitres, ensemble)
    "accounts": ("5, 19, 22", "E1"), "org": ("4, 19", "E1"), "core": ("5, 18, 22", "E1"),
    "dashboard": ("6, 16", "E2/E3"), "reports": ("6", "E2"), "calendar_app": ("7", "E2"),
    "quarts": ("8", "E2"), "absences": ("8", "E2"), "threads": ("9", "E2"), "annonces": ("9", "E2"),
    "notifications": ("9, 21", "E2/E4"), "taches": ("10", "E2"), "demandes": ("10", "E2"),
    "programme": ("10", "E2"), "postes": ("10", "E2"), "assets": ("11", "E3"), "maintenance": ("12", "E3"),
    "logistics": ("12, 13", "E3"), "rondes": ("12", "E3"), "training": ("14", "E3"),
    "documentation": ("15", "E3"), "retex": ("15", "E3"),
}
CIRCUITS = [  # circuit, chapitre, ensemble, mot-clé de preuve dans les chapitres rédigés
    ("Relève d'équipage", "4", "E1", "proposer_releve"), ("Archivage d'une unité", "4", "E1", "verifier_modele"),
    ("Suppression d'une unité", "4", "E1", "SuppressionRefusee|supprimer"),
    ("Création d'un compte", "5", "E1", "create_user"), ("Réinitialisation de mot de passe", "5", "E1", "reinitialiser_mot_de_passe"),
    ("Suppression d'un compte (réel) et désactivation (cible L04)", "5", "E1", "delete_user"),
    ("Proposer → valider → publier (transversal)", "22", "E1", "Proposer, valider, publier"),
    ("Confirmation explicite des validations critiques", "22", "E1", "confirmations"),
    ("Verrou des commandes de démonstration", "22", "E1", "COMPTES_DEMO|MATRIX_INSTANCE_DEMO"),
    ("Échange de service : fonctionnement actuel", "8", "E2", "analyser_echange"), ("Échange de service : fonctionnement cible (DEC-FDS-07/13)", "8", "E2", "DEC-FDS-13"),
   ("Activation d'une liste de services à quai", "8", "E2", "activer_liste"), ("Notifications et Web Push", "9", "E2", "creer_notifications_en_masse"), ("Difficulté signalée (demande)", "10", "E2", "changer_etat"), ("Programme du bâtiment", "10", "E2", "peut_deleguer"), ("Passation de relève", "6", "E2", "generer_passation"), ("Bilan et exports", "6", "E2", "GenererBilanView"), ("Recherche globale", "9", "E2", "rechercher"), ("Absences", "8", "E2", "peut_valider_absence"), ("Publication d'une liste de quarts ou de gardes", "8", "E2", "peut_publier_liste"),
    ("Feuille de service, visas et rectificatif", "8", "E2", "ouvrir_rectificatif"), ("Annonce et accusé de lecture", "9", "E2", "rappeler_accuses"),
    ("Tâche : attribution, blocage, clôture", "10", "E2", "signaler_blocage"),
    ("Ticket correctif et anomalie", "12", "E3", "TicketTransitionView"), ("Maintenance : exécution et clôture critique", "12", "E3", "OccurrenceExecuteView|installation \\*\\*critique\\*\\*"),
    ("Demande de pièces et mouvements de stock", "13", "E3", "enregistrer_mouvement|MouvementStock"), ("Fiche de maintenance : circuits de validation (bord et flotte)", "11", "E3", "fiche_validation"),
    ("Équiper le bord depuis le catalogue (proposition d'article)", "11", "E3", "proposition_article"),
    ("Formation : demande de places, candidature, formation du bord", "14", "E3", "_attribuer_places"), ("Validation de formation par un référent", "14", "E3", "peut_valider_formation"),
    ("Documentation : versions et validation", "15", "E3", "proposer_amelioration"),
    ("RETEX : fonctionnement actuel", "15", "E3", "valideurs"), ("RETEX : fonctionnement cible (DEC-RTX-01)", "15", "E3", "DEC-RTX-01"),
    ("Préparation à l'appareillage : fonctionnement actuel", "16", "E3", "SessionAppareillageSignerView"), ("Préparation à l'appareillage : fonctionnement cible (DEC-APP-14)", "16", "E3", "DEC-APP-14"),
]

par_app = defaultdict(list)
for m in inv["modeles"]:
    par_app[m["app"]].append(m["modele"])
L = ["# Annexe G — Matrice de couverture (générée)", "",
     "> Diffusion restreinte. Générée par `outils/generer_matrice_couverture.py` à partir de l'inventaire de l'état B "
     "(`couverture/etat_B/inventaire.json`) et des chapitres rédigés. Ne pas éditer à la main.", "",
     f"Chapitres rédigés pris en compte : {', '.join(fichiers)}.", "",
     "## G.1 Modèles de données", "",
     "Statut : **Expliqué** = le nom du modèle figure dans un chapitre de domaine rédigé (hors chapitre 19) ; "
     "**Nommé** = cité seulement dans la présentation par familles du chapitre 19 ; **Dictionnaire seul** = présent "
     "uniquement dans `couverture/etat_B/MODELES.md`. Seuls les modèles « expliqués » sont couverts ; les autres le seront "
     "dans l'ensemble indiqué.", "",
     "| Paquet | Modèles | Expliqués | Nommés (ch. 19) | Dictionnaire seul | Chapitres | Ensemble |", "|---|---|---|---|---|---|---|"]
tot = red = nom_tot = 0
detail_non = []
for app in sorted(par_app):
    ch, ens = PAQUETS.get(app, ("?", "?"))
    noms = par_app[app]
    ok = [n for n in noms if re.search(rf"\b{n}\b", texte_sans_19)]
    nommes = [n for n in noms if n not in ok and re.search(rf"\b{n}\b", texte)]
    tot += len(noms)
    red += len(ok)
    nom_tot += len(nommes)
    L.append(f"| `{app}` | {len(noms)} | {len(ok)} | {len(nommes)} | {len(noms) - len(ok) - len(nommes)} | {ch} | {ens} |")
    if ens == "E1" and len(ok) < len(noms):
        detail_non += [f"`{app}.{n}`" for n in noms if n not in ok]
L.append(f"| **Total** | **{tot}** | **{red}** | **{nom_tot}** | **{tot - red - nom_tot}** | | |")
L += ["", "Modèles de l'ensemble 1 non nommés dans un chapitre rédigé : " + (", ".join(detail_non) or "aucun") + ".", ""]

routes = defaultdict(int)
for r in inv["routes"]:
    routes[r["vue"].split(".")[0]] += 1
L += ["## G.2 Routes (pages et API)", "", "| Paquet de la vue | Routes | Chapitres | Ensemble |", "|---|---|---|---|"]
for app in sorted(routes):
    ch, ens = PAQUETS.get(app, ("18, 20", "E1/E4") if app in ("matrix", "rest_framework", "django") else ("?", "?"))
    L.append(f"| `{app}` | {routes[app]} | {ch} | {ens} |")
L.append(f"| **Total** | **{sum(routes.values())}** | | |")
L += ["", "Le détail des routes est généré dans `couverture/etat_B/ROUTES.md` (annexe C, ensemble 4).", "",
      "## G.3 Tâches planifiées", "", "| Tâche | Nom | Citée dans un chapitre rédigé |", "|---|---|---|"]
for b in inv["beat"]:
    cite = "oui" if b["nom"] in texte or b["tache"].split(".")[-1] in texte else "domaine seulement (ch. 18), détail ch. 21"
    L.append(f"| `{b['tache']}` | `{b['nom']}` | {cite} |")
L += ["", "## G.4 Commandes de gestion", "", "| Commande | Citée dans un chapitre rédigé |", "|---|---|"]
for c in inv["commandes"]:
    nom = Path(c).stem
    L.append(f"| `{nom}` | {'oui' if nom in texte else 'non (ensemble indiqué en annexe E, ensemble 4)'} |")
L += ["", "## G.5 Actions à seuil de rôle", "",
      f"{len(inv['actions_seuils'])} actions : toutes figurent dans l'annexe B (générée depuis le registre). "
      "Exemples expliqués au chapitre 5.", "",
      "## G.6 Circuits métier (liste fermée, révisée)", "",
      "| Circuit | Chapitre | Ensemble | Statut |", "|---|---|---|---|"]
for nom, ch, ens, preuve in CIRCUITS:
    if preuve is None:
        st = "à rédiger"
    else:
        st = "rédigé" if re.search(preuve, texte) else "À VÉRIFIER : preuve absente"
    L.append(f"| {nom} | {ch} | {ens} | {st} |")
L += ["", "## G.7 Dépendances entre paquets", "",
      "Matrice générée dans `couverture/etat_B/INVENTAIRE.md` ; synthèse expliquée au chapitre 18 (§18.6).", ""]
(D / "couverture/MATRICE_COUVERTURE.md").write_text("\n".join(L), encoding="utf-8")
print(f"modèles : {red}/{tot} expliqués, {nom_tot} nommés (ch. 19) ; circuits E1 : " + str(sum(1 for c in CIRCUITS if c[2] == 'E1')))
