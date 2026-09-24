"""Actions de désignation du référent formation du navire et du personnel BRH
(training/web_views.py).

Sous-domaine extrait lors du re-découpage du fichier (tâche Notion « [ARCH]
Découper training/web_views.py et re-découper assets/web_views.py ») :
gouvernance du module Formations pour un navire donné — un référent formation
unique par navire (ReferentFormationNavire), et plusieurs personnels BRH
possibles (PersonnelBRH, Circuit B — Candidature individuelle).

Refactor pur : reproduit exactement le comportement d'origine."""
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect

from matrix.core.scopes import ship_id_for_user
from notifications.models import Notification
from org.models import Ship

from .formation_perimetre import (
    _entier_ou_none,
    _peut_gerer_brh,
    _peut_gerer_referent_navire,
    _utilisateurs_du_navire_q,
)
from .models import PersonnelBRH, ReferentFormationNavire

User = get_user_model()


def _action_set_referent_navire(request):
    """Désigne (ou remplace) le référent formation du navire de l'appelant —
    un seul référent par navire (ReferentFormationNavire), qui obtient
    alors l'autorité de validation sur TOUTES les formations du navire
    (cf. training/models.py::peut_valider_formation), en plus des
    référents propres à chaque formation."""
    if not _peut_gerer_referent_navire(request.user):
        raise PermissionDenied
    ship_id = ship_id_for_user(request.user)
    navire = Ship.objects.filter(pk=ship_id).first() if ship_id else None
    if navire is None:
        messages.error(request, "Aucune unité rattachée à votre profil.")
        return redirect("formation-list")
    # Ne fait pas confiance au formulaire : seuls les utilisateurs
    # visibles sur ce navire peuvent être désignés (revalidation côté
    # serveur, même principe que pour les référents par formation).
    candidat_id = _entier_ou_none(request.POST.get("referent_navire_id"))
    candidat = (
        User.objects.filter(_utilisateurs_du_navire_q(navire), pk=candidat_id).first()
        if candidat_id is not None else None
    )
    if candidat is None:
        messages.error(request, "Marin introuvable dans votre unité.")
        return redirect("formation-list")
    ReferentFormationNavire.objects.update_or_create(ship=navire, defaults={"user": candidat})
    if candidat != request.user:
        Notification.objects.create(
            user=candidat,
            verb=f"Vous avez été désigné référent formation de l'unité {navire.name}.",
        )
    messages.success(
        request,
        f"{candidat.get_full_name() or candidat.username} est désormais référent formation de l'unité {navire.name}.",
    )
    return redirect("formation-list")


def _action_retirer_referent_navire(request):
    """Retire le référent formation actuellement désigné pour le navire de
    l'appelant (aucun effet si personne n'était désigné)."""
    if not _peut_gerer_referent_navire(request.user):
        raise PermissionDenied
    ship_id = ship_id_for_user(request.user)
    if ship_id:
        ReferentFormationNavire.objects.filter(ship_id=ship_id).delete()
    messages.success(request, "Référent formation de l'unité retiré.")
    return redirect("formation-list")


def _action_set_brh(request):
    """Désigne un personnel BRH supplémentaire pour le navire de
    l'appelant (Circuit B — Candidature individuelle) : PLUSIEURS
    personnes BRH sont possibles pour un même navire, contrairement au
    référent formation du navire ci-dessus (ReferentFormationNavire,
    unique)."""
    if not _peut_gerer_brh(request.user):
        raise PermissionDenied
    ship_id = ship_id_for_user(request.user)
    navire = Ship.objects.filter(pk=ship_id).first() if ship_id else None
    if navire is None:
        messages.error(request, "Aucune unité rattachée à votre profil.")
        return redirect("formation-list")
    # Ne fait pas confiance au formulaire : seuls les utilisateurs
    # visibles sur ce navire peuvent être désignés (même principe que
    # _action_set_referent_navire ci-dessus).
    candidat_id = _entier_ou_none(request.POST.get("brh_id"))
    candidat = (
        User.objects.filter(_utilisateurs_du_navire_q(navire), pk=candidat_id).first()
        if candidat_id is not None else None
    )
    if candidat is None:
        messages.error(request, "Marin introuvable dans votre unité.")
        return redirect("formation-list")
    _, cree = PersonnelBRH.objects.get_or_create(ship=navire, user=candidat)
    if not cree:
        messages.info(
            request,
            f"{candidat.get_full_name() or candidat.username} est déjà personnel BRH de l'unité {navire.name}.",
        )
        return redirect("formation-list")
    if candidat != request.user:
        Notification.objects.create(
            user=candidat,
            verb=f"Vous avez été désigné personnel BRH de l'unité {navire.name}.",
        )
    messages.success(
        request,
        f"{candidat.get_full_name() or candidat.username} est désormais personnel BRH de l'unité {navire.name}.",
    )
    return redirect("formation-list")


def _action_retirer_brh(request):
    """Retire un personnel BRH précis (parmi plusieurs possibles) du
    navire de l'appelant."""
    if not _peut_gerer_brh(request.user):
        raise PermissionDenied
    brh_id = _entier_ou_none(request.POST.get("brh_id"))
    ship_id = ship_id_for_user(request.user)
    if brh_id is not None and ship_id:
        PersonnelBRH.objects.filter(pk=brh_id, ship_id=ship_id).delete()
    messages.success(request, "Personnel BRH retiré.")
    return redirect("formation-list")


ACTION_HANDLERS = {
    "set_referent_navire": _action_set_referent_navire,
    "retirer_referent_navire": _action_retirer_referent_navire,
    "set_brh": _action_set_brh,
    "retirer_brh": _action_retirer_brh,
}
