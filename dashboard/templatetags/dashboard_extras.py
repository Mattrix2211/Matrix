from django import template

from accounts.models import SpecialityChoice
from dashboard.comanav import peut_voir_vue_comanav as _peut_voir_vue_comanav
from matrix.core.roles import RoleLevel, user_role_level
from matrix.core.scopes import is_master_admin
from org.models import Ship

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


@register.filter
def peut_voir_dashboard_specialite(user):
    """Vrai si l'utilisateur peut accéder à un dashboard transverse de
    spécialité : désigné responsable d'au moins une spécialité
    (accounts.ResponsableSpecialite), ou MASTER_ADMIN (supervision globale
    de la flotte)."""
    if not getattr(user, "is_authenticated", False):
        return False
    if is_master_admin(user):
        return SpecialityChoice.objects.filter(active=True).exists()  # sinon la page répond 403
    return user.specialites_dont_il_est_responsable.exists()


@register.filter
def peut_voir_dashboard_classe_navire(user):
    """Vrai si l'utilisateur peut accéder à un dashboard transverse de
    classe de navire : désigné responsable d'au moins une classe
    (org.ResponsableClasseNavire), ou MASTER_ADMIN."""
    if not getattr(user, "is_authenticated", False):
        return False
    if is_master_admin(user):
        return Ship.objects.exclude(classe_navire="").exists()  # sinon la page répond 403
    return user.classes_navire_dont_il_est_responsable.exists()


@register.filter
def peut_voir_vue_comanav(user):
    """Vrai si l'utilisateur peut ouvrir la Vue COMANAV (règle de dashboard.comanav)."""
    return bool(getattr(user, "is_authenticated", False)) and _peut_voir_vue_comanav(user)
