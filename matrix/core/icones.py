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
    # Actions courantes
    "ajout": "bi-plus-lg",
    "mot_de_passe": "bi-key",
    "generer": "bi-dice-5",
    # Types d'événements du calendrier
    "ticket": "bi-wrench",
    "formation": "bi-mortarboard",
    "quart": "bi-clock",
    "garde": "bi-shield-check",
    "ronde": "bi-compass",
    "personnel": "bi-pin-angle",
    # États
    "retard": "bi-alarm",
    "terminee": "bi-check-circle",
}


def classe_icone(concept):
    """Classe Bootstrap Icons du concept ; lève KeyError si le concept est inconnu."""
    return ICONES[concept]
