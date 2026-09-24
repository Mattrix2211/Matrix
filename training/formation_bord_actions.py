"""Actions du Circuit C — formation gérée par le bord (training/web_views.py).

Sous-domaine extrait lors du re-découpage du fichier (tâche Notion « [ARCH]
Découper training/web_views.py et re-découper assets/web_views.py ») : un
chef de secteur propose la création ou la modification d'une formation
« bord », invisible du catalogue général tant qu'un chef de service de son
périmètre (ou la supervision globale) ne l'a pas validée.

Refactor pur : reproduit exactement le comportement d'origine."""
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect

from accounts.models import AuditLog
from matrix.core.roles import user_role_level
from matrix.core.validators import message_erreur_fichier, valider_document
from notifications.models import Notification

from .formation_perimetre import (
    NIVEAU_REQUIS_VALIDATION_FORMATION_BORD,
    _entier_ou_none,
    _peut_proposer_formation_bord,
    formation_bord_en_service,
    peut_modifier_formation_bord,
    peut_valider_proposition_bord,
)
from .models import TrainingCourse


def _action_proposer_formation_bord(request):
    """Circuit C — un chef de secteur (CHEF_SECTEUR+) crée ou modifie une
    formation « gérée par le bord » : les champs sont appliqués
    immédiatement, mais la formation reste invisible du catalogue général
    (statut_validation WAITING_VALIDATION, cf. TrainingCourseListView.get_queryset)
    tant qu'un chef de service de son périmètre (ou supervision globale) ne
    l'a pas validée — même pattern d'état explicite que WAITING_VALIDATION
    sur les occurrences de maintenance (maintenance/models.py). Un
    CHEF_SERVICE+ proposant directement n'a besoin d'aucune validation
    supplémentaire : son propre rôle vaut déjà l'accord requis, la
    formation est immédiatement ACTIVE (cf.
    NIVEAU_REQUIS_VALIDATION_FORMATION_BORD).

    La MODIFICATION d'une formation bord existante (pk fourni) est
    toujours bornée au périmètre organisationnel de son proposeur
    d'origine (peut_modifier_formation_bord) et refusée si la formation
    est déjà ACTIVE et réellement en service (formation_bord_en_service)
    — deux contrôles ajoutés suite au refus du Tech Lead sur la première
    livraison de cette tâche (fuite inter-navire, absence de rollback),
    et réutilisés à l'identique côté API REST (training/views.py) suite
    au deuxième refus (même contrôle absent sur PATCH/PUT)."""
    if not _peut_proposer_formation_bord(request.user):
        raise PermissionDenied
    titre = request.POST.get("title", "").strip()
    if not titre:
        messages.error(request, "Le titre est obligatoire.")
        return redirect("formation-list")
    validity_days_brut = request.POST.get("validity_days", "").strip()
    validity_days = TrainingCourse._meta.get_field("validity_days").get_default()
    if validity_days_brut:
        try:
            validity_days = int(validity_days_brut)
            if validity_days <= 0:
                raise ValueError
        except ValueError:
            messages.error(request, "La durée de validité doit être un nombre de jours positif.")
            return redirect("formation-list")

    pk = _entier_ou_none(request.POST.get("pk"))
    course = None
    if pk is not None:
        # Modification d'une formation bord existante uniquement — jamais
        # une formation « organisme » (gere_par_le_bord=False), dont
        # l'édition des champs cœur reste hors du périmètre de ce circuit.
        course = TrainingCourse.objects.filter(pk=pk, gere_par_le_bord=True).first()
        if course is None:
            messages.error(request, "Formation introuvable, ou non gérée par un bord.")
            return redirect("formation-list")
        # Périmètre d'origine (issue Tech Lead n°2) : seul le proposeur
        # d'origine, un marin dont le périmètre le couvre, ou la
        # supervision globale peut modifier cette formation précise.
        if not peut_modifier_formation_bord(request.user, course):
            raise PermissionDenied
        # Formation déjà en service (issue Tech Lead n°3) : pas de
        # mutation en place d'une formation ACTIVE dont d'autres navires
        # dépendent déjà (validations, sessions, prérequis) — la revalider
        # la ferait disparaître partout sans possibilité de rollback.
        # Choix retenu : exclusion plutôt que snapshot/rollback (option
        # (b) du commentaire Tech Lead), une modification substantielle
        # d'une formation déjà utilisée doit passer par une NOUVELLE
        # formation proposée.
        if course.statut_validation == "ACTIVE" and formation_bord_en_service(course):
            messages.error(
                request,
                f"« {course.title} » est déjà active et utilisée (validations, sessions ou "
                "prérequis d'une autre formation) : proposez une nouvelle formation plutôt "
                "que de la modifier directement.",
            )
            return redirect("formation-list")
    if course is None:
        course = TrainingCourse()

    statut_cible = (
        "ACTIVE" if user_role_level(request.user) >= NIVEAU_REQUIS_VALIDATION_FORMATION_BORD
        else "WAITING_VALIDATION"
    )
    course.title = titre
    course.description = request.POST.get("description", "").strip()
    course.category = request.POST.get("category", "").strip()
    course.validity_days = validity_days
    course.gere_par_le_bord = True
    course.statut_validation = statut_cible
    # Barème facultatif, même principe que catalogue_actions.py
    # (_action_create_course/_action_update_prerequisites) : un nouveau
    # fichier remplace l'ancien, sinon « retirer_bareme » l'enlève sans le
    # remplacer.
    nouveau_bareme = request.FILES.get("bareme")
    erreur_bareme = message_erreur_fichier(nouveau_bareme, valider_document)
    if erreur_bareme:
        messages.error(request, erreur_bareme)
        return redirect("formation-list")
    if nouveau_bareme:
        course.bareme = nouveau_bareme
    elif "retirer_bareme" in request.POST and course.pk:
        course.bareme.delete(save=False)
        course.bareme = None
    if course.created_by_id is None:
        course.created_by = request.user
    course.updated_by = request.user
    course.save()

    if statut_cible == "WAITING_VALIDATION":
        messages.success(
            request,
            f"Formation « {course.title} » proposée, en attente de validation du chef de service.",
        )
    else:
        messages.success(request, f"Formation « {course.title} » enregistrée et active.")
    return redirect("formation-list")


def _action_valider_formation_bord(request):
    """Validation, par un chef de service (CHEF_SERVICE+) du même
    périmètre que le proposeur, ou par supervision globale (COMMANDANT+),
    d'une formation « bord » en attente — fait passer la formation en
    ACTIVE, désormais visible dans le catalogue (cf.
    peut_valider_proposition_bord)."""
    pk = _entier_ou_none(request.POST.get("pk"))
    course = (
        TrainingCourse.objects.filter(pk=pk, statut_validation="WAITING_VALIDATION")
        .select_related("updated_by").first()
        if pk is not None else None
    )
    if course is None:
        messages.error(request, "Proposition de formation introuvable ou déjà traitée.")
        return redirect("formation-list")
    if not peut_valider_proposition_bord(request.user, course.updated_by):
        raise PermissionDenied
    course.statut_validation = "ACTIVE"
    course.save(update_fields=["statut_validation"])
    # Journal d'audit transverse (§30 cahier des charges) : validation d'une
    # formation « bord » proposée par un chef de secteur — action sensible
    # équivalente à la validation d'un ticket/occurrence critique, cf. tâche
    # Notion « Unifier les modèles d'historique/audit ».
    AuditLog.objects.create(
        actor=request.user, action="validate_training_course_bord",
        target_user=course.updated_by, details=f"course={course.pk}; title={course.title}",
    )
    if course.updated_by_id:
        Notification.objects.create(
            user_id=course.updated_by_id,
            verb=f"Votre proposition de formation « {course.title} » a été validée par le chef de service.",
        )
    messages.success(request, f"Formation « {course.title} » validée et désormais active.")
    return redirect("formation-list")


def _action_refuser_formation_bord(request):
    """Refus par le chef de service (même autorisation que la
    validation, cf. _action_valider_formation_bord) : la formation reste hors
    du catalogue (statut REFUSED), le chef de secteur pouvant la reprendre
    et la soumettre à nouveau (cf. _action_proposer_formation_bord)."""
    pk = _entier_ou_none(request.POST.get("pk"))
    course = (
        TrainingCourse.objects.filter(pk=pk, statut_validation="WAITING_VALIDATION")
        .select_related("updated_by").first()
        if pk is not None else None
    )
    if course is None:
        messages.error(request, "Proposition de formation introuvable ou déjà traitée.")
        return redirect("formation-list")
    if not peut_valider_proposition_bord(request.user, course.updated_by):
        raise PermissionDenied
    course.statut_validation = "REFUSED"
    course.save(update_fields=["statut_validation"])
    AuditLog.objects.create(
        actor=request.user, action="refuse_training_course_bord",
        target_user=course.updated_by, details=f"course={course.pk}; title={course.title}",
    )
    if course.updated_by_id:
        Notification.objects.create(
            user_id=course.updated_by_id,
            level="warning",
            verb=f"Votre proposition de formation « {course.title} » a été refusée par le chef de service.",
        )
    messages.success(request, "Proposition de formation refusée.")
    return redirect("formation-list")


ACTION_HANDLERS = {
    "proposer_formation_bord": _action_proposer_formation_bord,
    "valider_formation_bord": _action_valider_formation_bord,
    "refuser_formation_bord": _action_refuser_formation_bord,
}
