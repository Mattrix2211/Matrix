"""Table centrale des icônes de Matrix (docs/UX.md §16).

Un concept garde la même icône partout dans l'interface. Toute icône passe
par cette table : gabarits (balise ``{% icone "concept" %}``) comme code
Python (``classe_icone("concept")``). Bibliothèque unique : Bootstrap Icons,
auto-hébergée (``static/vendor/bootstrap-icons``). Aucun emoji.
"""

ICONES = {
    # Concepts transverses (§16)
    "anomalie": "bi-exclamation-triangle",
    "calendrier": "bi-calendar3",
    "maintenance": "bi-tools",
    "parametres": "bi-gear",
    "utilisateur": "bi-person",
    "suppression": "bi-trash",
    "modification": "bi-pencil",
    "piece": "bi-box",
    "historique": "bi-clock-history",
    "discussion": "bi-chat-left-text",
    "impression": "bi-printer",
    "document": "bi-file-earmark-text",
    # Actions courantes
    "ajout": "bi-plus-lg",
    "mot_de_passe": "bi-key",
    "generer": "bi-dice-5",
    "suite": "bi-chevron-right",
    "precedent": "bi-chevron-left",
    "recopie_bas": "bi-arrow-down-square",
    "monter": "bi-arrow-up",
    "descendre": "bi-arrow-down",
    "dupliquer": "bi-copy",
    "menu_actions": "bi-three-dots",
    "information": "bi-info-circle",
    # Types d'événements du calendrier
    "ticket": "bi-wrench",
    "formation": "bi-mortarboard",
    "quart": "bi-clock",
    "feuille_service": "bi-journal-text",
    "absence": "bi-calendar-x",
    "garde": "bi-shield-check",
    "ronde": "bi-compass",
    "tache": "bi-check2-square",
    "personnel": "bi-pin-angle",
    # Navigation latérale (§7)
    "aujourdhui": "bi-house-door",
    "materiel": "bi-box-seam",
    "catalogue": "bi-book",
    "installation": "bi-gear-wide-connected",
    "plan_navire": "bi-map",
    "configuration": "bi-sliders",
    "logistique": "bi-boxes",
    "pret_appareillage": "bi-life-preserver",
    "flotte": "bi-diagram-3",
    "specialite": "bi-award",
    "classe_navire": "bi-diagram-2",
    "annuaire": "bi-people",
    "replier_menu": "bi-chevron-bar-left",
    "deplier_menu": "bi-chevron-bar-right",
    # Barre supérieure (§8)
    "navire": "bi-water",
    "deconnexion": "bi-box-arrow-right",
    "deplier_liste": "bi-chevron-down",
    "recherche": "bi-search",
    # Centre de notifications
    "notifications": "bi-bell",
    "marquer_lu": "bi-check2",
    "tout_marquer_lu": "bi-check2-all",
    "lien_direct": "bi-box-arrow-up-right",
    # États
    "retard": "bi-alarm",
    "terminee": "bi-check-circle",
    "verrouille": "bi-lock",
    "arbre_competences": "bi-diagram-3",
}


def classe_icone(concept):
    """Classe Bootstrap Icons du concept ; lève KeyError si le concept est inconnu."""
    return ICONES[concept]
