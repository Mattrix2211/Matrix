"""Vocabulaire des textes visibles : le niveau d'organisation réel du marin (bâtiment, service, secteur, section)
au lieu du mot générique « périmètre ». N'agit que sur l'affichage : les contrôles d'accès restent dans scopes.py."""
NIVEAUX = {
    "ship": ("bâtiment", "le", "Bâtiment"),
    "service": ("service", "le", "Service"),
    "sector": ("secteur", "le", "Secteur"),
    "section": ("section", "la", "Section"),
}
SANS_RATTACHEMENT = "votre rattachement"


def niveau_de(user, avec_nom=False):
    """Niveau de rattachement du marin, avec ses formes courantes ; repli neutre si aucun rattachement.
    Le nom du service, secteur ou section (une requête de plus) n'est résolu qu'à la demande."""
    profil = getattr(user, "profile", None) if getattr(user, "is_authenticated", False) else None
    niveau, _ = profil.scope if profil else (None, None)
    if niveau not in NIVEAUX:
        return {"libelle": "Rattachement", "nom": "", "votre": SANS_RATTACHEMENT, "de_votre": f"de {SANS_RATTACHEMENT}",
                "du": "du rattachement", "tout": "Tout le rattachement", "mon": "Mon rattachement", "le": "le rattachement"}
    mot, article, libelle = NIVEAUX[niveau]
    feminin = article == "la"
    return {
        "libelle": libelle, "nom": _nom_du_noeud(profil, niveau) if avec_nom else "", "votre": f"votre {mot}", "de_votre": f"de votre {mot}",
        "du": f"{'de la' if feminin else 'du'} {mot}", "le": f"{article} {mot}",
        "tout": f"Toute la {mot}" if feminin else f"Tout le {mot}", "mon": f"{'Ma' if feminin else 'Mon'} {mot}",
    }


def _nom_du_noeud(profil, niveau):
    noeud = getattr(profil, niveau)
    return getattr(noeud, "name", str(noeud)) if noeud else ""


def votre_niveau(user):
    """« votre secteur », « votre section »… pour les messages ; « votre rattachement » sans niveau connu."""
    return niveau_de(user)["votre"]
