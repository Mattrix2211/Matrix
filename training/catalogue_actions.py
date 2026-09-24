"""Actions de gestion du catalogue de formations (training/web_views.py).

Sous-domaine extrait lors du re-découpage du fichier (tâche Notion « [ARCH]
Découper training/web_views.py et re-découper assets/web_views.py ») :
création d'une formation « organisme » et mise à jour de ses prérequis/
catégorie/barème/référents — les deux seules actions de
TrainingCourseListView.post() qui ne relèvent pas d'un circuit de validation
dédié (Circuit A/B/C, cf. les autres modules *_actions.py de cette app).

Refactor pur : reproduit exactement le comportement d'origine."""
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied, ValidationError
from django.shortcuts import redirect

from matrix.core.validators import message_erreur_fichier, valider_document

from .formation_perimetre import (
    _afficher_erreur_prerequis,
    _entier_ou_none,
    _identifiants_valides,
    _peut_creer_formation,
    _peut_gerer_prerequis,
    _utilisateurs_du_navire_q,
)
from .models import ReferentFormation, TrainingCourse, navire_de

User = get_user_model()


def _action_create_course(request):
    if not _peut_creer_formation(request.user):
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
    bareme = request.FILES.get("bareme")
    erreur_bareme = message_erreur_fichier(bareme, valider_document)
    if erreur_bareme:
        messages.error(request, erreur_bareme)
        return redirect("formation-list")
    course = TrainingCourse.objects.create(
        title=titre,
        description=request.POST.get("description", "").strip(),
        category=request.POST.get("category", "").strip(),
        validity_days=validity_days,
        bareme=bareme,
    )
    # Prérequis facultatifs dès la création, parmi le catalogue global
    # existant (revalidation côté serveur, même principe que pour
    # l'édition ci-dessous).
    ids = _identifiants_valides(request.POST.getlist("prerequisites"))
    if ids:
        candidats = TrainingCourse.objects.exclude(pk=course.pk)
        course.prerequisites.set(candidats.filter(pk__in=ids))
    messages.success(request, "Formation créée.")
    return redirect("formation-list")


def _action_update_prerequisites(request):
    if not _peut_gerer_prerequis(request.user):
        raise PermissionDenied
    pk = _entier_ou_none(request.POST.get("pk"))
    # Formation ACTIVE uniquement (correctif QA — Circuit C, gap
    # supplémentaire trouvé dans le même esprit que les 4 signalés) :
    # une formation « bord » en attente de validation ou refusée ne
    # peut pas être éditée hors du circuit dédié
    # (_proposer_formation_bord), même par un autre chef de section
    # devinant son identifiant.
    course = (
        TrainingCourse.objects.filter(pk=pk, statut_validation="ACTIVE").first()
        if pk is not None else None
    )
    if course is None:
        messages.error(request, "Formation introuvable.")
        return redirect("formation-list")
    ids = _identifiants_valides(request.POST.getlist("prerequisites"))
    # Catalogue global : n'importe quelle autre formation peut être
    # choisie comme prérequis — ne fait pas confiance au formulaire,
    # revalidation côté serveur (même principe que
    # assets/web_views.py::_parent_candidats).
    candidats = TrainingCourse.objects.exclude(pk=course.pk)
    valides = candidats.filter(pk__in=ids)
    try:
        course.prerequisites.set(valides)
    except ValidationError as exc:
        _afficher_erreur_prerequis(request, exc)
        return redirect("formation-list")
    # Catégorie modifiable dans la même modale que les prérequis (un seul
    # clic pour tout mettre à jour) — champ absent du POST : on ne touche
    # pas à la catégorie existante (compatibilité avec un appel qui ne
    # gérerait que les prérequis).
    if "category" in request.POST:
        course.category = request.POST.get("category", "").strip()
        course.save(update_fields=["category"])
    # Barème modifiable dans la même modale (un seul clic pour tout mettre
    # à jour) : soit on téléverse un nouveau fichier (remplace l'ancien),
    # soit on coche « retirer_bareme » pour l'enlever sans le remplacer —
    # les deux ne sont jamais combinés dans un même envoi de formulaire.
    nouveau_bareme = request.FILES.get("bareme")
    erreur_bareme = message_erreur_fichier(nouveau_bareme, valider_document)
    if erreur_bareme:
        messages.error(request, erreur_bareme)
        return redirect("formation-list")
    if nouveau_bareme:
        course.bareme = nouveau_bareme
        course.save(update_fields=["bareme"])
    elif "retirer_bareme" in request.POST:
        course.bareme.delete(save=False)
        course.bareme = None
        course.save(update_fields=["bareme"])
    # Référents modifiables dans la même modale (un seul clic pour tout
    # mettre à jour) — champ absent du POST : on ne touche pas aux
    # référents existants (compatibilité avec un appel qui ne gérerait
    # que les prérequis/la catégorie). Portée TOUJOURS limitée au
    # navire de L'APPELANT (ReferentFormation, cf. training/models.py) :
    # un chef ne désigne des référents que pour son propre navire,
    # jamais pour un autre navire proposant la même formation globale.
    if "referents" in request.POST:
        navire = navire_de(request.user)
        if navire is not None:
            referent_ids = _identifiants_valides(request.POST.getlist("referents"))
            referents_valides = User.objects.filter(
                _utilisateurs_du_navire_q(navire), pk__in=referent_ids
            )
            ReferentFormation.objects.filter(course=course, ship=navire).delete()
            ReferentFormation.objects.bulk_create([
                ReferentFormation(course=course, ship=navire, user=u) for u in referents_valides
            ])
    messages.success(request, "Prérequis mis à jour.")
    return redirect("formation-list")


ACTION_HANDLERS = {
    "create_course": _action_create_course,
    "update_prerequisites": _action_update_prerequisites,
}
