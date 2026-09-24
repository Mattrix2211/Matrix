"""Actions du Circuit A — demande et attribution de places à quota
(training/web_views.py).

Sous-domaine extrait lors du re-découpage du fichier (tâche Notion « [ARCH]
Découper training/web_views.py et re-découper assets/web_views.py ») : un
chef de secteur formule une demande de places pour son bord, l'organisme de
formation attribue ou refuse, puis le demandeur affecte les places obtenues
à des marins de son propre secteur.

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
    _parse_datetime_local,
    _peut_demander_places,
    filtres_perimetre_marin,
)
from .models import DemandePlace, PlaceAffectee, TrainingCourse, TrainingSession, navire_de, peut_valider_formation

User = get_user_model()


def _action_demander_places(request):
    """Circuit A (T-FORM demande de places) — un chef de secteur formule
    une demande de places sur une formation à quota, pour SON BORD. Le
    navire de la demande est TOUJOURS celui résolu de l'appelant
    (navire_de, jamais un identifiant posté) : impossible de demander des
    places au nom d'un autre bord en forgeant la requête."""
    if not _peut_demander_places(request.user):
        raise PermissionDenied
    navire = navire_de(request.user)
    if navire is None:
        messages.error(request, "Aucune unité rattachée à votre profil.")
        return redirect("formation-list")
    course_id = _entier_ou_none(request.POST.get("course_id"))
    # Formation ACTIVE uniquement (correctif QA — Circuit C) : une
    # formation « bord » en attente de validation ou refusée reste
    # invisible/inutilisable pour tout le monde sauf le proposeur/
    # validateur concerné, même en devinant son identifiant.
    course = (
        TrainingCourse.objects.filter(pk=course_id, statut_validation="ACTIVE").first()
        if course_id is not None else None
    )
    if course is None:
        messages.error(request, "Formation introuvable.")
        return redirect("formation-list")
    nb = _entier_ou_none(request.POST.get("nb_places_demandees"))
    if not nb or nb <= 0:
        messages.error(request, "Le nombre de places demandées doit être un nombre positif.")
        return redirect("formation-list")
    DemandePlace.objects.create(
        course=course, ship=navire, nb_places_demandees=nb, created_by=request.user,
    )
    messages.success(request, f"Demande de {nb} place(s) envoyée pour « {course.title} ».")
    return redirect("formation-list")


def _action_annuler_demande_place(request):
    """Annulation par le demandeur (created_by) de SA PROPRE demande,
    uniquement tant qu'elle n'a pas encore été traitée par l'organisme."""
    demande_id = _entier_ou_none(request.POST.get("demande_id"))
    demande = DemandePlace.objects.filter(pk=demande_id).first() if demande_id is not None else None
    if demande is None:
        messages.error(request, "Demande introuvable.")
        return redirect("formation-list")
    if demande.created_by_id != request.user.id:
        raise PermissionDenied
    if demande.statut != "REQUESTED":
        messages.info(request, "Cette demande n'est plus annulable.")
        return redirect("formation-list")
    demande.statut = "CANCELLED"
    demande.save(update_fields=["statut"])
    messages.success(request, "Demande annulée.")
    return redirect("formation-list")


def _action_attribuer_places(request):
    """Réponse de l'organisme de formation (référent de cette formation
    POUR SON PROPRE NAVIRE — l'école/centre de formation, cf.
    peut_valider_formation, réutilisé tel quel) à une DemandePlace :
    renseigne le nombre de places attribuées et relie une TrainingSession
    (existante, choisie parmi les sessions de la même formation, ou
    nouvellement créée), puis passe le statut à GRANTED."""
    demande_id = _entier_ou_none(request.POST.get("demande_id"))
    demande = (
        DemandePlace.objects.select_related("course", "ship").filter(pk=demande_id).first()
        if demande_id is not None else None
    )
    if demande is None:
        messages.error(request, "Demande introuvable.")
        return redirect("formation-list")
    # Revalidation du statut de la formation (correctif QA — Circuit C) :
    # une formation « bord » peut être revalidée/refusée entre la
    # DEMANDE (toujours ACTIVE à l'origine, cf. _action_demander_places) et
    # cette ATTRIBUTION — tant qu'aucune session ne lui est encore
    # rattachée, formation_bord_en_service ne bloque pas sa réédition.
    # Ne jamais attribuer de place sur une formation qui n'est plus (ou
    # pas encore) ACTIVE.
    if demande.course.statut_validation != "ACTIVE":
        messages.error(request, "Formation introuvable.")
        return redirect("formation-list")

    navire_organisme = navire_de(request.user)
    if not peut_valider_formation(request.user, demande.course, navire_organisme):
        raise PermissionDenied

    nb = _entier_ou_none(request.POST.get("nb_places_attribuees"))
    if not nb or nb <= 0:
        messages.error(request, "Le nombre de places attribuées doit être un nombre positif.")
        return redirect("formation-list")

    session_id = _entier_ou_none(request.POST.get("session_id"))
    session = None
    if session_id is not None:
        # Ne fait pas confiance au formulaire : la session choisie doit
        # bien concerner la formation de cette demande.
        session = TrainingSession.objects.filter(pk=session_id, course=demande.course).first()
        if session is None:
            messages.error(request, "Session introuvable pour cette formation.")
            return redirect("formation-list")
    else:
        nouvelle_date = request.POST.get("nouvelle_session_date", "").strip()
        if nouvelle_date:
            try:
                scheduled_at = _parse_datetime_local(nouvelle_date)
            except ValueError:
                messages.error(request, "Date de session invalide.")
                return redirect("formation-list")
            capacite_brut = request.POST.get("nouvelle_session_capacite", "").strip()
            session = TrainingSession.objects.create(
                course=demande.course,
                scheduled_at=scheduled_at,
                location=request.POST.get("nouvelle_session_lieu", "").strip(),
                capacite_max=_entier_ou_none(capacite_brut) if capacite_brut else None,
            )

    demande.nb_places_attribuees = nb
    demande.session = session
    demande.statut = "GRANTED"
    demande.attribue_par = request.user
    demande.date_attribution = timezone.now()
    demande.save(update_fields=[
        "nb_places_attribuees", "session", "statut", "attribue_par", "date_attribution",
    ])

    if demande.created_by_id:
        Notification.objects.create(
            user_id=demande.created_by_id,
            verb=(
                f"Demande de places accordée : {nb} place(s) pour « {demande.course.title} » "
                f"({demande.ship.name})."
            ),
        )
    messages.success(request, f"{nb} place(s) attribuée(s) pour « {demande.course.title} ».")
    return redirect("formation-list")


def _action_refuser_demande_place(request):
    """Refus d'une demande par l'organisme de formation (même autorisation
    que l'attribution, cf. _action_attribuer_places)."""
    demande_id = _entier_ou_none(request.POST.get("demande_id"))
    demande = (
        DemandePlace.objects.select_related("course", "ship").filter(pk=demande_id).first()
        if demande_id is not None else None
    )
    if demande is None:
        messages.error(request, "Demande introuvable.")
        return redirect("formation-list")
    navire_organisme = navire_de(request.user)
    if not peut_valider_formation(request.user, demande.course, navire_organisme):
        raise PermissionDenied
    demande.statut = "REFUSED"
    demande.attribue_par = request.user
    demande.date_attribution = timezone.now()
    demande.save(update_fields=["statut", "attribue_par", "date_attribution"])
    if demande.created_by_id:
        Notification.objects.create(
            user_id=demande.created_by_id,
            verb=f"Demande de places refusée pour « {demande.course.title} » ({demande.ship.name}).",
        )
    messages.success(request, "Demande refusée.")
    return redirect("formation-list")


def _action_affecter_place_demandee(request):
    """Affecte un marin sur une place ATTRIBUÉE d'une DemandePlace précise
    : seul le chef de secteur demandeur (created_by de la demande) peut
    affecter, uniquement des marins de son propre périmètre
    organisationnel (filtres_perimetre_marin, même périmètre que le
    chef non-référent dans _action_affecter_session), et seulement dans la
    limite du quota attribué à SA demande.

    Double contrôle de quota (point métier clé — plusieurs bords peuvent
    partager la même session, chacun avec son propre quota) : le plafond
    attribué à CETTE demande précise (PlaceAffectee.objects.filter(...).count(),
    compté par bord) est contrôlé ICI, EN PLUS du plafond physique global
    de la session déjà appliqué par le signal m2m existant
    (training/models.py::_controler_reservation, non dupliqué)."""
    demande_id = _entier_ou_none(request.POST.get("demande_id"))
    marin_id = _entier_ou_none(request.POST.get("marin_id"))
    demande = (
        DemandePlace.objects.select_related("course", "session").filter(pk=demande_id).first()
        if demande_id is not None else None
    )
    marin = User.objects.filter(pk=marin_id, is_active=True).first() if marin_id is not None else None
    if demande is None or marin is None:
        messages.error(request, "Demande ou marin introuvable.")
        return redirect("formation-list")

    if demande.created_by_id != request.user.id:
        raise PermissionDenied
    if demande.statut != "GRANTED" or demande.session_id is None:
        messages.error(
            request,
            "Cette demande n'a pas encore de places attribuées et reliées à une session.",
        )
        return redirect("formation-list")

    # Revalidation côté serveur du marin ciblé : ne fait pas confiance au
    # formulaire, même principe que _action_affecter_session.
    q_perimetre_marin = filtres_perimetre_marin(request.user)
    if q_perimetre_marin is not None and not User.objects.filter(q_perimetre_marin, pk=marin.pk).exists():
        raise PermissionDenied

    if demande.nb_places_attribuees is not None and demande.places_consommees() >= demande.nb_places_attribuees:
        messages.error(request, "Le quota de places attribuées à votre unité pour cette demande est atteint.")
        return redirect("formation-list")

    session = demande.session
    if marin in session.reservations.all():
        messages.info(request, "Ce marin a déjà une place réservée sur cette session.")
        return redirect("formation-list")
    try:
        # Savepoint explicite, même principe que _action_reserver_session : la
        # réservation globale (m2m) et la trace du quota par bord
        # (PlaceAffectee) sont créées ensemble, ou pas du tout.
        with transaction.atomic():
            session.reservations.add(marin)
            PlaceAffectee.objects.create(demande_place=demande, marin=marin)
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
    "demander_places": _action_demander_places,
    "annuler_demande_place": _action_annuler_demande_place,
    "attribuer_places": _action_attribuer_places,
    "refuser_demande_place": _action_refuser_demande_place,
    "affecter_place_demandee": _action_affecter_place_demandee,
}
