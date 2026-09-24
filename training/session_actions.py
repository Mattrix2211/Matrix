"""Actions de réservation de session (training/web_views.py).

Sous-domaine extrait lors du re-découpage du fichier (tâche Notion « [ARCH]
Découper training/web_views.py et re-découper assets/web_views.py ») :
réservation self-service d'une place par le marin lui-même, annulation,
retrait de la liste d'attente (T-ATTENTE), et réservation proactive par un
référent pour un marin de son périmètre.

Refactor pur : reproduit exactement le comportement d'origine."""
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.shortcuts import redirect
from django.utils import timezone

from notifications.models import Notification

from .formation_perimetre import (
    _afficher_erreur_prerequis,
    _entier_ou_none,
    _marins_validables,
    _peut_valider_formation,
    filtres_perimetre_marin,
)
from .models import TrainingSession, TrainingWaitlistEntry, navire_de, peut_valider_formation

User = get_user_model()


def _action_reserver_session(request):
    """Réservation self-service d'une place sur une session PLANNED, par le
    marin connecté pour lui-même uniquement — distincte de la validation de
    présence par un référent (attendees, non touché ici). Les règles
    métier (session toujours planifiée, capacité, prérequis) sont
    appliquées par le signal m2m TrainingSession.reservations
    (training/models.py::_controler_reservation), seule source de vérité.
    Catalogue global : toute session planifiée est réservable, quel que
    soit le navire qui l'organise (une session peut par exemple être
    organisée par un autre bord ou un centre de formation à terre).

    Liste d'attente (T-ATTENTE) : si la session est déjà complète au
    moment de la tentative, le marin est mis en fin de file FIFO
    (TrainingSession.inscrire_liste_attente) plutôt que simplement
    refusé — il sera notifié dès qu'une place se libère, à lui de la
    réserver lui-même (pas d'inscription automatique). Le contrôle de
    capacité est donc fait AVANT celui d'une éventuelle entrée en liste
    d'attente déjà existante : un marin notifié qu'une place s'est
    libérée doit pouvoir la réserver normalement, même s'il figure
    encore dans la file (son entrée est retirée automatiquement, cf.
    training/models.py::_controler_reservation, action post_add)."""
    session_id = _entier_ou_none(request.POST.get("session_id"))
    session = (
        TrainingSession.objects.select_related("course").filter(pk=session_id).first()
        if session_id is not None else None
    )
    if session is None:
        messages.error(request, "Session introuvable.")
        return redirect("formation-list")
    if request.user in session.reservations.all():
        messages.info(request, "Vous avez déjà réservé une place pour cette session.")
        return redirect("formation-list")
    if session.capacite_max is not None and session.places_restantes() == 0:
        if TrainingWaitlistEntry.objects.filter(session=session, user=request.user).exists():
            messages.info(request, "Vous êtes déjà en liste d'attente pour cette session.")
            return redirect("formation-list")
        try:
            entree = session.inscrire_liste_attente(request.user)
        except ValidationError as exc:
            _afficher_erreur_prerequis(request, exc)
            return redirect("formation-list")
        messages.success(
            request,
            f"Session complète : vous êtes en position {entree.position()} sur la liste "
            "d'attente. Vous serez prévenu dès qu'une place se libère.",
        )
        return redirect("formation-list")
    try:
        # Savepoint explicite : si le signal m2m (capacité, prérequis,
        # statut) refuse la réservation, seule cette opération est annulée,
        # pas le reste de la transaction de la requête.
        with transaction.atomic():
            session.reservations.add(request.user)
    except ValidationError as exc:
        _afficher_erreur_prerequis(request, exc)
        return redirect("formation-list")
    Notification.objects.create(
        user=request.user,
        verb=(
            f"Réservation confirmée: {session.course.title} — session du "
            f"{timezone.localtime(session.scheduled_at):%d/%m/%Y à %H:%M}"
        ),
    )
    messages.success(
        request,
        "Place réservée. La session apparaît maintenant dans votre calendrier personnel.",
    )
    return redirect("formation-list")


def _action_annuler_reservation(request):
    """Annulation de SA PROPRE réservation par le marin connecté, tant que
    la session n'a pas encore eu lieu (contrôle fait par le signal m2m
    TrainingSession.reservations, cf. training/models.py::_controler_reservation).
    La notification au premier de la liste d'attente (s'il y en a une) est
    déclenchée automatiquement par ce même signal (action post_remove),
    pas ici : seule source de vérité, quel que soit l'appelant."""
    session_id = _entier_ou_none(request.POST.get("session_id"))
    session = TrainingSession.objects.select_related("course").filter(pk=session_id).first() \
        if session_id is not None else None
    if session is None:
        messages.error(request, "Session introuvable.")
        return redirect("formation-list")
    if request.user not in session.reservations.all():
        messages.info(request, "Vous n'avez pas de réservation sur cette session.")
        return redirect("formation-list")
    try:
        # Savepoint explicite, même principe que _action_reserver_session ci-dessus.
        with transaction.atomic():
            session.reservations.remove(request.user)
    except ValidationError as exc:
        _afficher_erreur_prerequis(request, exc)
        return redirect("formation-list")
    messages.success(request, "Réservation annulée.")
    return redirect("formation-list")


def _action_quitter_liste_attente(request):
    """Retrait volontaire de SA PROPRE entrée en liste d'attente, sans
    attendre qu'une place ne se libère — aucune règle métier
    supplémentaire à appliquer (contrairement à l'annulation d'une
    réservation ferme), l'entrée est simplement supprimée."""
    session_id = _entier_ou_none(request.POST.get("session_id"))
    supprimees, _ = TrainingWaitlistEntry.objects.filter(
        session_id=session_id, user=request.user
    ).delete()
    if supprimees:
        messages.success(request, "Vous avez quitté la liste d'attente.")
    else:
        messages.info(request, "Vous n'êtes pas en liste d'attente pour cette session.")
    return redirect("formation-list")


def _action_affecter_session(request):
    """Un référent réserve PROACTIVEMENT une place sur une session pour un
    marin (contrairement à _action_reserver_session ci-dessus, où c'est le
    marin qui réserve pour lui-même) — équivaut à une réservation self-service
    (TrainingSession.reservations, PAS attendees : la présence/réussite
    réelle reste constatée séparément le jour J, cf. ValiderFormationView).
    Autorisation branchée sur le même contrôle par référent que
    ValiderFormationView (peut_valider_formation, POUR LE NAVIRE DU MARIN
    CIBLÉ), MAIS complétée ici par le seuil générique CHEF_SECTION+
    (borné au périmètre organisationnel de l'appelant sur le marin, cf.
    ci-dessous) — DEPUIS LA CORRECTION DE LA FAILLE sur ValiderFormationView
    (tâche Notion « Sécurité : la validation de formation contourne le
    contrôle par référent »), ce n'est PLUS le même contrôle : réserver
    une place ne certifie en rien que le marin a suivi/réussi la
    formation (seul ValiderFormationView crée un TrainingRecord), donc un
    chef peut toujours planifier une session pour un marin de son propre
    périmètre sans en être désigné référent — risque bien moindre que
    celui corrigé sur la validation elle-même. Les règles métier
    (capacité, session planifiée, prérequis) sont appliquées par le même
    signal m2m que la réservation self-service
    (training/models.py::_controler_reservation), seule source de vérité,
    qui se déclenche ici aussi car l'ajout se fait toujours par le même
    ManyToManyField, quel que soit l'appelant."""
    session_id = _entier_ou_none(request.POST.get("session_id"))
    marin_id = _entier_ou_none(request.POST.get("marin_id"))
    session = (
        TrainingSession.objects.select_related("course").filter(pk=session_id).first()
        if session_id is not None else None
    )
    marin = (
        User.objects.filter(pk=marin_id, is_active=True).first()
        if marin_id is not None else None
    )
    if session is None or marin is None:
        messages.error(request, "Session ou marin introuvable.")
        return redirect("formation-list")

    # Autorisation : référent de cette formation précise POUR LE NAVIRE DU
    # MARIN CIBLÉ, référent formation de ce navire, ou COMMANDANT+ (même
    # fonction que ValiderFormationView, réutilisée telle quelle) —
    # COMPLÉTÉE ICI (contrairement à ValiderFormationView depuis le
    # correctif de sécurité ci-dessus) par le seuil générique
    # CHEF_SECTION+ borné au périmètre organisationnel de l'appelant sur
    # le marin : réserver une place ne valide rien, cf. docstring de
    # cette fonction.
    navire_marin = navire_de(marin)
    autorise_par_referent = peut_valider_formation(request.user, session.course, navire_marin)
    if not autorise_par_referent and not _peut_valider_formation(request.user):
        raise PermissionDenied

    # Revalidation côté serveur du marin ciblé, même principe que
    # ValiderFormationView : empêche d'affecter un marin hors périmètre en
    # forgeant la requête POST.
    if autorise_par_referent:
        if not _marins_validables(request.user).filter(pk=marin.pk).exists():
            raise PermissionDenied
    else:
        q_perimetre_marin = filtres_perimetre_marin(request.user)
        if q_perimetre_marin is not None and not User.objects.filter(q_perimetre_marin, pk=marin.pk).exists():
            raise PermissionDenied

    if marin in session.reservations.all():
        messages.info(request, "Ce marin a déjà une place réservée sur cette session.")
        return redirect("formation-list")
    try:
        # Savepoint explicite, même principe que _action_reserver_session ci-dessus.
        with transaction.atomic():
            session.reservations.add(marin)
    except ValidationError as exc:
        _afficher_erreur_prerequis(request, exc)
        return redirect("formation-list")
    Notification.objects.create(
        user=marin,
        verb=(
            f"Une place vous a été réservée: {session.course.title} — session du "
            f"{timezone.localtime(session.scheduled_at):%d/%m/%Y à %H:%M}"
        ),
    )
    messages.success(
        request,
        f"Place réservée pour {marin.get_full_name() or marin.username}. "
        "La session apparaît désormais dans son calendrier personnel.",
    )
    return redirect("formation-list")


ACTION_HANDLERS = {
    "reserver_session": _action_reserver_session,
    "annuler_reservation": _action_annuler_reservation,
    "quitter_liste_attente": _action_quitter_liste_attente,
    "affecter_session": _action_affecter_session,
}
