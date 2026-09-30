"""Poste de commandant en second (ou officier en second) : helper de vision
globale en lecture et actions de configuration (onglet « Commandants adjoints »
des Réglages). Le titulaire garde son rôle (ETAT_MAJOR) : le poste lui ouvre en
LECTURE la vision du commandant sur son navire (sur son équipage en double
équipage), sans droit d'écriture supplémentaire. Modifications tracées dans
l'AuditLog unifié."""
from django.contrib import messages
from django.db.models import Q

from matrix.core.scopes import equipage_marin_q, perimetre_navire_q

from .commandants_adjoints import _navire_cible, _tracer, titulaire_sans_equipage, titulaires_possibles
from .models import CommandantEnSecond

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
        titulaire = titulaires_possibles(ship).filter(pk=user_id if user_id.isdigit() else 0).first()
        if titulaire is None:
            messages.error(request, "Le titulaire doit être un membre de l'état-major de cette unité.")
            return
        if titulaire_sans_equipage(ship, CommandantEnSecond(ship=ship, equipage=equipage), titulaire):
            messages.error(request, "Ce marin n'est rattaché à aucun équipage : rattachez-le d'abord à l'équipage (page « Équipages »).")
            return
        if equipage and titulaire.profile.equipage_id not in (None, equipage.id):
            messages.error(request, f"Ce marin appartient à l'autre équipage : le poste doit être de l'équipage {equipage.nom}.")
            return
    if poste is None:
        poste = CommandantEnSecond(ship=ship, equipage=equipage)
    ancien = (poste.titulaire.username if poste.titulaire else "aucun") if poste.pk else "création"
    poste.libelle, poste.titulaire = libelle, titulaire
    poste.save()
    _tracer(
        request, action, ship,
        f"poste={poste.get_libelle_display()}; {ancien} -> {titulaire.username if titulaire else 'aucun'}"
        + (f"; equipage={equipage.nom}" if equipage else ""),
    )
    messages.success(request, f"{poste.get_libelle_display()} mis à jour.")
