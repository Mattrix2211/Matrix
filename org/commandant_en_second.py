"""Poste de commandant en second (ou officier en second) : helper de vision
globale en lecture et actions de configuration (onglet « Commandants adjoints »
des Réglages). Le titulaire garde son rôle (ETAT_MAJOR) : le poste lui ouvre en
LECTURE la vision du commandant sur son navire (sur son équipage en double
équipage), sans droit d'écriture supplémentaire (sauf suppléance explicite, org/suppleance.py,
ou droit métier configuré, droit_metier_en_second). Modifications tracées dans
l'AuditLog unifié."""
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db.models import Q

from matrix.core.roles import RoleLevel, user_role_level
from matrix.core.saisie import entier_ou_none
from matrix.core.scopes import equipage_marin_q, perimetre_navire_q

from .commandants_adjoints import _navire_cible, _tracer, titulaires_possibles
from .models import CommandantEnSecond, RoleThresholdConfig

ACTIONS = ("set_commandant_en_second", "delete_commandant_en_second")


def poste_en_second_de(user):
    """Poste de commandant en second dont `user` est titulaire sur SON navire,
    ou None. Un poste resté attaché à un ancien navire ne donne rien."""
    if not getattr(user, "is_authenticated", False):
        return None
    profile = getattr(user, "profile", None)
    navire_id = profile.navire_id_effectif if profile else None
    if not navire_id:
        return None
    return CommandantEnSecond.objects.filter(titulaire=user, ship_id=navire_id).first()


def a_vision_commandant(user):
    """Vrai si `user` est commandant/officier en second de son navire."""
    return poste_en_second_de(user) is not None


def niveau_lecture(user):
    """Niveau de rôle à comparer aux seuils de SUPERVISION (lecture transverse) :
    celui du commandant pour le titulaire du poste de commandant en second,
    sinon son niveau réel. Ne sert qu'à ouvrir des surfaces de lecture : les
    écritures continuent de comparer `user_role_level`."""
    niveau = user_role_level(user)
    if niveau < RoleLevel.COMMANDANT and a_vision_commandant(user):
        return RoleLevel.COMMANDANT
    return niveau


def droit_metier_en_second(user, cle_action):
    """Vrai si `user` est commandant/officier en second ET si son navire lui a
    confié l'action d'écriture métier `cle_action` (REGISTRE_DROITS_EN_SECOND).
    Faux par défaut : aucune écriture n'est ouverte tant qu'un navire ne l'a
    pas explicitement configurée."""
    from matrix.core.role_thresholds import REGISTRE_DROITS_EN_SECOND_PAR_CLE
    poste = poste_en_second_de(user)
    if poste is None or cle_action not in REGISTRE_DROITS_EN_SECOND_PAR_CLE:
        return False
    config = RoleThresholdConfig.objects.filter(ship_id=poste.ship_id).first()
    return bool(config and cle_action in config.droits_en_second)


def perimetre_lecture_q(user, prefix="profile__"):
    """Filtre Q du personnel que la vision de commandant en second couvre : tout
    le navire, limité à son équipage sur un bâtiment à double équipage (l'équipage
    à terre n'est pas concerné). Q jamais satisfait sans poste."""
    if not a_vision_commandant(user):
        return Q(pk__in=[])
    return perimetre_navire_q(user, prefix) & equipage_marin_q(user, prefix)


def contexte_onglet(ship):
    if ship is None:
        return {}
    equipages = list(ship.equipages.all()) if ship.double_equipage else [None]
    postes = {p.equipage_id: p for p in ship.commandants_en_second.select_related("titulaire", "equipage")}
    return {
        "second_emplacements": [
            {"equipage": e, "poste": postes.get(e.id if e else None)} for e in equipages
        ],
        "second_libelles": CommandantEnSecond.Libelle.choices,
        "second_titulaires_possibles": titulaires_possibles(ship),
    }


def traiter_action(request, action):
    """Exécute une action de configuration, limitée au navire de l'appelant
    (ou au navire choisi pour un superuser)."""
    ship = _navire_cible(request)
    if ship is None:
        messages.error(request, "Aucune unité sélectionnée.")
        return
    equipage = ship.equipages.filter(pk=request.POST.get("equipage_id") or 0).first()
    if ship.double_equipage and equipage is None:
        messages.error(request, "Choisissez l'équipage du poste.")
        return
    poste = CommandantEnSecond.objects.filter(ship=ship, equipage=equipage).first()

    if action == "delete_commandant_en_second":
        if poste is None:
            messages.error(request, "Poste introuvable.")
            return
        poste.delete()
        _tracer(request, action, ship, f"poste={poste.get_libelle_display()}")
        messages.success(request, f"{poste.get_libelle_display()} supprimé.")
        return

    libelle = request.POST.get("libelle")
    if libelle not in CommandantEnSecond.Libelle.values:
        messages.error(request, "Libellé inconnu.")
        return
    user_id = request.POST.get("user_id")
    titulaire = None
    if user_id:
        titulaire = titulaires_possibles(ship).filter(pk=entier_ou_none(user_id) or 0).first()
        if titulaire is None:
            messages.error(request, "Le titulaire doit être un membre de l'état-major de cette unité.")
            return
    if poste is None:
        poste = CommandantEnSecond(ship=ship, equipage=equipage)
    ancien = (poste.titulaire.username if poste.titulaire else "aucun") if poste.pk else "création"
    poste.libelle, poste.titulaire = libelle, titulaire
    try:
        poste.save()
    except ValidationError as erreur:
        messages.error(request, " ".join(erreur.messages))
        return
    _tracer(
        request, action, ship,
        f"poste={poste.get_libelle_display()}; {ancien} -> {titulaire.username if titulaire else 'aucun'}"
        + (f"; equipage={equipage.nom}" if equipage else ""),
    )
    messages.success(request, f"{poste.get_libelle_display()} mis à jour.")
