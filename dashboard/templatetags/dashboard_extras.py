from django import template

from matrix.core.roles import RoleLevel, user_role_level

register = template.Library()


@register.filter
def peut_voir_vue_flotte(user):
    """Vrai si l'utilisateur peut accéder à la Vue flotte : chef de section
    (ou au-dessus), même seuil que dashboard.web_views.VueFlotteView
    (RoleLevel.CHEF_SECTION, voir matrix/core/roles.py). La vue s'adapte
    ensuite au périmètre effectif de l'utilisateur (section/secteur/navire/
    flotte selon son rôle, cf. dashboard.web_views._perimetre_agregation)."""
    if not getattr(user, "is_authenticated", False):
        return False
    return user_role_level(user) >= RoleLevel.CHEF_SECTION


@register.filter
def peut_voir_pret_appareillage(user):
    """Vrai si l'utilisateur peut accéder à la page « Prêt à appareillage » :
    tout marin authentifié (EQUIPIER+, aucune restriction de rôle) — cocher un
    point de vérification sur la session en cours doit rester accessible à
    quiconque effectue le contrôle sur le terrain (spec PO, revue de la tâche
    Notion « [FEAT] Tableau de bord Prêt à appareillage »). Seules l'ouverture
    d'une session et sa signature restent réservées à CHEF_SECTEUR et aux
    rôles supérieurs (cf. dashboard.web_views)."""
    return bool(getattr(user, "is_authenticated", False))
