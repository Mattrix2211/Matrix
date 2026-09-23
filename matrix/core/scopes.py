from typing import Dict, Any, Optional
from django.contrib.auth import get_user_model
from django.db.models import Q


def scope_filters_for_user(user) -> Dict[str, Any]:
    if not user.is_authenticated:
        return {}
    profile = getattr(user, "profile", None)
    if not profile:
        return {}
    level, obj_id = profile.scope
    if level == "ship":
        return {"ship_id": obj_id}
    if level == "service":
        return {"service_id": obj_id}
    if level == "sector":
        return {"sector_id": obj_id}
    if level == "section":
        return {"section_id": obj_id}
    return {}


def is_master_admin(user) -> bool:
    """Vrai si l'utilisateur a un accès multi-navires (flotte entière) :
    superutilisateur ou rôle MASTER_ADMIN, seul niveau au-dessus de ADMIN_NAVIRE
    dans la hiérarchie (matrix/core/roles.py). Tous les autres rôles (ADMIN_NAVIRE
    compris) sont rattachés à un navire précis. Même règle que celle déjà
    appliquée dans org/views.py::_is_master_admin, centralisée ici pour être
    réutilisée par toute vue nécessitant un périmètre "navire entier" (ex. Vue
    flotte du tableau de bord)."""
    if getattr(user, "is_superuser", False):
        return True
    profile = getattr(user, "profile", None)
    return bool(profile and profile.role == "MASTER_ADMIN")


def ship_id_for_user(user) -> Optional[int]:
    """Renvoie l'id du navire rattaché au profil de l'utilisateur, ou None si
    aucun navire n'est renseigné. Contrairement à scope_filters_for_user() (qui
    renvoie le niveau le plus précis du profil), ceci renvoie toujours le
    navire, quel que soit le service/secteur/section également renseigné —
    utile pour les vues agrégées à l'échelle du bâtiment entier."""
    profile = getattr(user, "profile", None)
    ship = getattr(profile, "ship", None)
    return ship.id if ship else None


def sector_id_for_user(user) -> Optional[int]:
    """Renvoie l'id du secteur rattaché au profil de l'utilisateur, ou None si
    aucun secteur n'est renseigné. Même logique que ship_id_for_user() ci-dessus,
    déclinée au niveau secteur — utile pour les vues agrégées bornées au
    secteur d'un CHEF_SECTEUR (ex. Vue flotte)."""
    profile = getattr(user, "profile", None)
    sector = getattr(profile, "sector", None)
    return sector.id if sector else None


def perimetre_navire_q(user, prefix: str = "") -> Q:
    """Filtre Q couvrant tout le personnel rattaché au navire de
    l'utilisateur, à n'importe quel niveau de la hiérarchie organisationnelle
    (navire/service/secteur/section). Utilisé pour restreindre un COMMANDANT
    ou un ADMIN_NAVIRE à son propre navire dans l'annuaire du personnel.

    Contrairement à build_scope_q() (matrix/core/mixins.py), qui compare le
    périmètre de l'appelant au seul champ direct de même niveau sur la
    cible, ce filtre doit couvrir tout marin du navire quel que soit le
    niveau de rattachement renseigné sur sa fiche : certains profils ne
    renseignent qu'un secteur ou une section, sans remplir eux-mêmes le
    champ "Unité" (ship). Sans ce parcours de la hiérarchie, un COMMANDANT
    ne verrait que les marins dont le profil porte directement le champ
    ship, et perdrait de vue tout le reste de son équipage.

    `prefix` permet de préfixer les lookups Django selon le modèle interrogé
    (ex. "profile__" pour filtrer le modèle User, "" pour filtrer
    UserProfile lui-même). Si l'utilisateur n'a pas de navire rattaché,
    renvoie un Q qui n'égale jamais rien : mieux vaut ne rien montrer que de
    renvoyer une donnée hors périmètre.
    """
    ship_id = ship_id_for_user(user)
    if not ship_id:
        return Q(pk__in=[])
    return (
        Q(**{f"{prefix}ship_id": ship_id})
        | Q(**{f"{prefix}service__ship_id": ship_id})
        | Q(**{f"{prefix}sector__service__ship_id": ship_id})
        | Q(**{f"{prefix}section__sector__service__ship_id": ship_id})
    )


def resoudre_affectation_dans_perimetre(acting_user, ship_id=None, service_id=None, sector_id=None, section_id=None):
    """Résout les valeurs d'affectation (navire/service/secteur/section) demandées
    pour un utilisateur, en s'assurant qu'elles appartiennent au périmètre navire
    de l'appelant : un COMMANDANT ou un ADMIN_NAVIRE ne peut affecter un
    utilisateur qu'à son propre navire (ou à un service/secteur/section qui en
    dépend) ; MASTER_ADMIN (et un superutilisateur) garde une liberté totale sur
    la flotte entière. Centralisée ici pour être réutilisée aussi bien par
    l'annuaire web (accounts/web_views.py) que par l'API DRF
    (accounts/serializers.py::UserProfileSerializer), plutôt que dupliquée.

    Avant correction, l'annuaire web (create_user, edit_user, bulk_update_*)
    faisait confiance à l'id transmis par le formulaire sans jamais vérifier
    qu'il appartenait au périmètre de l'appelant, et l'API DRF
    (UserProfileViewSet) n'effectuait aucune vérification équivalente en
    écriture : un COMMANDANT pouvait ainsi rattacher un utilisateur de son
    navire à un navire/service/secteur/section d'un AUTRE navire.

    Renvoie (True, ship, service, sector, section) si toutes les valeurs
    demandées (celles non vides) existent et sont dans le périmètre. Renvoie
    (False, None, None, None, None) si l'une d'elles est invalide ou hors
    périmètre : l'appelant ne doit alors procéder à AUCUNE modification, pour
    éviter un état partiellement appliqué."""
    from org.models import Ship, Service, Sector, Section
    if is_master_admin(acting_user):
        ship_qs, service_qs = Ship.objects.all(), Service.objects.all()
        sector_qs, section_qs = Sector.objects.all(), Section.objects.all()
    else:
        mon_navire_id = ship_id_for_user(acting_user)
        ship_qs = Ship.objects.filter(pk=mon_navire_id)
        service_qs = Service.objects.filter(ship_id=mon_navire_id)
        sector_qs = Sector.objects.filter(service__ship_id=mon_navire_id)
        section_qs = Section.objects.filter(sector__service__ship_id=mon_navire_id)
    try:
        ship = ship_qs.get(pk=ship_id) if ship_id else None
        service = service_qs.get(pk=service_id) if service_id else None
        sector = sector_qs.get(pk=sector_id) if sector_id else None
        section = section_qs.get(pk=section_id) if section_id else None
    except (Ship.DoesNotExist, Service.DoesNotExist, Sector.DoesNotExist, Section.DoesNotExist):
        return False, None, None, None, None
    return True, ship, service, sector, section


def section_id_for_user(user) -> Optional[int]:
    """Renvoie l'id de la section rattachée au profil de l'utilisateur, ou None
    si aucune section n'est renseignée. Même logique que ship_id_for_user()
    ci-dessus, déclinée au niveau section — utile pour les vues agrégées
    bornées à la section d'un CHEF_SECTION (ex. Vue flotte)."""
    profile = getattr(user, "profile", None)
    section = getattr(profile, "section", None)
    return section.id if section else None
