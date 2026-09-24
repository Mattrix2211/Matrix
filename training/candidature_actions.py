"""Actions du Circuit B — candidature individuelle (training/web_views.py).

Sous-domaine extrait lors du re-découpage du fichier (tâche Notion « [ARCH]
Découper training/web_views.py et re-découper assets/web_views.py ») : un
marin candidate lui-même sur une formation, la candidature doit être validée
par sa hiérarchie ET par le personnel BRH du navire (double validation
ascendante) avant d'être transmise à l'organisme de formation, qui la
sélectionne ou la refuse.

Refactor pur : reproduit exactement le comportement d'origine."""
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect
from django.utils import timezone

from notifications.models import Notification

from .formation_perimetre import (
    _entier_ou_none,
    _peut_valider_candidature_brh,
    _peut_valider_candidature_hierarchie,
)
from .models import CandidatureFormation, TrainingCourse, navire_de, peut_valider_formation


def _action_candidater_formation(request):
    """Circuit B — Candidature individuelle : le marin postule lui-même
    (TOUJOURS le marin connecté, jamais un tiers) sur une formation du
    catalogue. Un seul dépôt actif à la fois par formation (bloque un
    doublon tant qu'une candidature précédente n'est pas allée à son
    terme, refus compris)."""
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
    if CandidatureFormation.objects.filter(
        course=course, marin=request.user, statut__in=["PENDING_APPROVAL", "TRANSMITTED"],
    ).exists():
        messages.info(request, "Vous avez déjà une candidature en cours pour cette formation.")
        return redirect("formation-list")
    CandidatureFormation.objects.create(course=course, marin=request.user, created_by=request.user)
    messages.success(request, f"Candidature envoyée pour « {course.title} ».")
    return redirect("formation-list")


def _action_valider_candidature_hierarchie(request):
    """Première des deux validations ascendantes (Circuit B) : la
    hiérarchie du candidat (CHEF_SECTION+ dont le périmètre le couvre).
    Dès que la validation BRH est également réunie, le statut passe
    automatiquement à TRANSMITTED (cf.
    CandidatureFormation.transmettre_si_double_validation)."""
    candidature_id = _entier_ou_none(request.POST.get("candidature_id"))
    candidature = (
        CandidatureFormation.objects.select_related("course", "marin").filter(pk=candidature_id).first()
        if candidature_id is not None else None
    )
    if candidature is None:
        messages.error(request, "Candidature introuvable.")
        return redirect("formation-list")
    if not _peut_valider_candidature_hierarchie(request.user, candidature.marin):
        raise PermissionDenied
    if candidature.statut != "PENDING_APPROVAL":
        messages.info(request, "Cette candidature n'est plus en attente de validation.")
        return redirect("formation-list")
    candidature.hierarchie_validee_par = request.user
    candidature.date_validation_hierarchie = timezone.now()
    candidature.save(update_fields=["hierarchie_validee_par", "date_validation_hierarchie"])
    candidature.transmettre_si_double_validation()
    if candidature.statut == "TRANSMITTED":
        Notification.objects.create(
            user=candidature.marin,
            verb=f"Votre candidature à « {candidature.course.title} » a été transmise à l'organisme de formation.",
        )
        messages.success(
            request,
            "Validation hiérarchie enregistrée : les deux validations sont réunies, "
            "la candidature est transmise à l'organisme.",
        )
    else:
        messages.success(request, "Validation hiérarchie enregistrée. En attente de la validation BRH.")
    return redirect("formation-list")


def _action_refuser_candidature_hierarchie(request):
    """Refus par la hiérarchie : arrête définitivement la candidature,
    sans attendre la validation BRH (même autorisation que la
    validation, cf. _action_valider_candidature_hierarchie)."""
    candidature_id = _entier_ou_none(request.POST.get("candidature_id"))
    candidature = (
        CandidatureFormation.objects.select_related("course", "marin").filter(pk=candidature_id).first()
        if candidature_id is not None else None
    )
    if candidature is None:
        messages.error(request, "Candidature introuvable.")
        return redirect("formation-list")
    if not _peut_valider_candidature_hierarchie(request.user, candidature.marin):
        raise PermissionDenied
    if candidature.statut != "PENDING_APPROVAL":
        messages.info(request, "Cette candidature n'est plus en attente de validation.")
        return redirect("formation-list")
    candidature.statut = "REJECTED_HIERARCHIE"
    candidature.save(update_fields=["statut"])
    Notification.objects.create(
        user=candidature.marin,
        level="warning",
        verb=f"Votre candidature à « {candidature.course.title} » a été refusée par votre hiérarchie.",
    )
    messages.success(request, "Candidature refusée.")
    return redirect("formation-list")


def _action_valider_candidature_brh(request):
    """Seconde des deux validations ascendantes (Circuit B) : le
    personnel BRH désigné pour le navire du candidat (ou supervision
    globale). Dès que la validation hiérarchie est également réunie, le
    statut passe automatiquement à TRANSMITTED."""
    candidature_id = _entier_ou_none(request.POST.get("candidature_id"))
    candidature = (
        CandidatureFormation.objects.select_related("course", "marin").filter(pk=candidature_id).first()
        if candidature_id is not None else None
    )
    if candidature is None:
        messages.error(request, "Candidature introuvable.")
        return redirect("formation-list")
    navire_marin = navire_de(candidature.marin)
    if not _peut_valider_candidature_brh(request.user, navire_marin):
        raise PermissionDenied
    if candidature.statut != "PENDING_APPROVAL":
        messages.info(request, "Cette candidature n'est plus en attente de validation.")
        return redirect("formation-list")
    candidature.brh_validee_par = request.user
    candidature.date_validation_brh = timezone.now()
    candidature.save(update_fields=["brh_validee_par", "date_validation_brh"])
    candidature.transmettre_si_double_validation()
    if candidature.statut == "TRANSMITTED":
        Notification.objects.create(
            user=candidature.marin,
            verb=f"Votre candidature à « {candidature.course.title} » a été transmise à l'organisme de formation.",
        )
        messages.success(
            request,
            "Validation BRH enregistrée : les deux validations sont réunies, "
            "la candidature est transmise à l'organisme.",
        )
    else:
        messages.success(request, "Validation BRH enregistrée. En attente de la validation de la hiérarchie.")
    return redirect("formation-list")


def _action_refuser_candidature_brh(request):
    """Refus par le BRH : arrête définitivement la candidature, sans
    attendre la validation hiérarchie (même autorisation que la
    validation, cf. _action_valider_candidature_brh)."""
    candidature_id = _entier_ou_none(request.POST.get("candidature_id"))
    candidature = (
        CandidatureFormation.objects.select_related("course", "marin").filter(pk=candidature_id).first()
        if candidature_id is not None else None
    )
    if candidature is None:
        messages.error(request, "Candidature introuvable.")
        return redirect("formation-list")
    navire_marin = navire_de(candidature.marin)
    if not _peut_valider_candidature_brh(request.user, navire_marin):
        raise PermissionDenied
    if candidature.statut != "PENDING_APPROVAL":
        messages.info(request, "Cette candidature n'est plus en attente de validation.")
        return redirect("formation-list")
    candidature.statut = "REJECTED_BRH"
    candidature.save(update_fields=["statut"])
    Notification.objects.create(
        user=candidature.marin,
        level="warning",
        verb=f"Votre candidature à « {candidature.course.title} » a été refusée par le BRH.",
    )
    messages.success(request, "Candidature refusée.")
    return redirect("formation-list")


def _action_selectionner_candidature(request):
    """Sélection par l'organisme de formation (référent de la formation
    POUR SON PROPRE NAVIRE, ou supervision globale, cf.
    peut_valider_formation) d'une candidature déjà TRANSMITTED (double
    validation hiérarchie + BRH réunie). La réussite effective du stage
    sera ensuite actée séparément par un TrainingRecord classique
    (ValiderFormationView), pas ici."""
    candidature_id = _entier_ou_none(request.POST.get("candidature_id"))
    candidature = (
        CandidatureFormation.objects.select_related("course", "marin").filter(pk=candidature_id).first()
        if candidature_id is not None else None
    )
    if candidature is None:
        messages.error(request, "Candidature introuvable.")
        return redirect("formation-list")
    # Revalidation du statut de la formation (correctif QA — Circuit C,
    # durcissement défensif par cohérence avec les 5 autres points déjà
    # corrigés — cf. _attribuer_places (training/demande_place_actions.py)
    # pour le même pattern) : une formation « bord » peut être repassée en
    # attente ou refusée entre la TRANSMISSION de la candidature et cette
    # SÉLECTION.
    if candidature.course.statut_validation != "ACTIVE":
        messages.error(request, "Formation introuvable.")
        return redirect("formation-list")
    # Autorisation calquée sur le Circuit A (_attribuer_places) : le
    # navire de référence est celui de L'ORGANISME (l'appelant, souvent
    # une école — navire_de(request.user)), PAS celui du marin candidat —
    # un référent d'école valide pour son propre établissement, quel que
    # soit le bord d'origine du candidat.
    navire_organisme = navire_de(request.user)
    if not peut_valider_formation(request.user, candidature.course, navire_organisme):
        raise PermissionDenied
    if candidature.statut != "TRANSMITTED":
        messages.info(request, "Cette candidature n'est pas (ou plus) transmise à l'organisme.")
        return redirect("formation-list")
    candidature.statut = "SELECTED"
    candidature.save(update_fields=["statut"])
    Notification.objects.create(
        user=candidature.marin,
        verb=f"Vous avez été sélectionné(e) pour le stage « {candidature.course.title} ».",
    )
    messages.success(request, "Candidature sélectionnée.")
    return redirect("formation-list")


def _action_refuser_candidature_organisme(request):
    """Refus par l'organisme de formation d'une candidature TRANSMITTED
    (même autorisation que la sélection, cf. _action_selectionner_candidature)."""
    candidature_id = _entier_ou_none(request.POST.get("candidature_id"))
    candidature = (
        CandidatureFormation.objects.select_related("course", "marin").filter(pk=candidature_id).first()
        if candidature_id is not None else None
    )
    if candidature is None:
        messages.error(request, "Candidature introuvable.")
        return redirect("formation-list")
    # Même revalidation que _action_selectionner_candidature ci-dessus
    # (correctif QA — Circuit C, durcissement défensif par cohérence).
    if candidature.course.statut_validation != "ACTIVE":
        messages.error(request, "Formation introuvable.")
        return redirect("formation-list")
    # Même autorisation que _action_selectionner_candidature ci-dessus (navire
    # de l'ORGANISME, l'appelant — pas celui du marin candidat).
    navire_organisme = navire_de(request.user)
    if not peut_valider_formation(request.user, candidature.course, navire_organisme):
        raise PermissionDenied
    if candidature.statut != "TRANSMITTED":
        messages.info(request, "Cette candidature n'est pas (ou plus) transmise à l'organisme.")
        return redirect("formation-list")
    candidature.statut = "REJECTED_ORGANISME"
    candidature.save(update_fields=["statut"])
    Notification.objects.create(
        user=candidature.marin,
        level="warning",
        verb=f"Votre candidature à « {candidature.course.title} » a été refusée par l'organisme de formation.",
    )
    messages.success(request, "Candidature refusée.")
    return redirect("formation-list")


ACTION_HANDLERS = {
    "candidater_formation": _action_candidater_formation,
    "valider_candidature_hierarchie": _action_valider_candidature_hierarchie,
    "refuser_candidature_hierarchie": _action_refuser_candidature_hierarchie,
    "valider_candidature_brh": _action_valider_candidature_brh,
    "refuser_candidature_brh": _action_refuser_candidature_brh,
    "selectionner_candidature": _action_selectionner_candidature,
    "refuser_candidature_organisme": _action_refuser_candidature_organisme,
}
