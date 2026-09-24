"""Point d'entrée des vues web du module Formations (training/urls et
training/views.py — voir aussi training/web_urls.py).

Fichier re-découpé par sous-domaine fonctionnel (tâche Notion « [ARCH]
Découper training/web_views.py et re-découper assets/web_views.py + règle de
taille pour le Tech Lead », ce fichier ayant atteint 1955 lignes), suivant le
même principe que le découpage déjà en place côté assets
(assets/installation_actions.py) : un module par sous-domaine fonctionnel,
regroupés ici :
- training/formation_perimetre.py — seuils de rôle, autorisations, périmètre
- training/contexte_formations.py — construction du contexte d'affichage
- training/catalogue_actions.py — création/édition du catalogue de formations
- training/referent_actions.py — référent formation du navire, personnel BRH
- training/session_actions.py — réservation de session, liste d'attente
- training/demande_place_actions.py — Circuit A (demande de places à quota)
- training/candidature_actions.py — Circuit B (candidature individuelle)
- training/formation_bord_actions.py — Circuit C (formation gérée par le bord)

Ce fichier ne contient plus que les trois vues elles-mêmes : la liste des
formations (dont le POST dispatche vers les actions ci-dessus via le
dictionnaire ACTION_HANDLERS, même pattern que
InstallationDetailView.post/assets.installation_actions.ACTION_HANDLERS), la
validation d'une formation pour un marin (ValiderFormationView) et l'arbre de
compétences (CompetencyTreeView).

Refactor pur : reproduit exactement le comportement d'origine."""
from datetime import date

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect, render
from django.views.generic import ListView, View

from accounts.models import AuditLog
from notifications.models import Notification

from .contexte_formations import construire_contexte_formations
from .formation_perimetre import _marins_validables
from .models import TrainingCourse, TrainingRecord, navire_de, peut_valider_formation
from .services import calculer_carte_competences, regrouper_par_categorie

from . import candidature_actions, catalogue_actions, demande_place_actions
from . import formation_bord_actions, referent_actions, session_actions

User = get_user_model()

# Table de dispatch des actions POST de TrainingCourseListView, fusionnant le
# dictionnaire ACTION_HANDLERS de chaque sous-domaine — même pattern que
# assets/installation_actions.py::ACTION_HANDLERS, utilisé par
# InstallationDetailView.post.
ACTION_HANDLERS = {}
ACTION_HANDLERS.update(catalogue_actions.ACTION_HANDLERS)
ACTION_HANDLERS.update(referent_actions.ACTION_HANDLERS)
ACTION_HANDLERS.update(session_actions.ACTION_HANDLERS)
ACTION_HANDLERS.update(demande_place_actions.ACTION_HANDLERS)
ACTION_HANDLERS.update(candidature_actions.ACTION_HANDLERS)
ACTION_HANDLERS.update(formation_bord_actions.ACTION_HANDLERS)


class TrainingCourseListView(LoginRequiredMixin, ListView):
    """Liste des formations, avec configuration des prérequis pour les chefs
    (T-FORM). Point d'entrée du module Formations, avant l'arbre de compétences
    proprement dit (CompetencyTreeView ci-dessous).

    Formation désormais GLOBALE, partagée par tous les navires (tâche Notion
    « Formation unique et portable entre navires ») : contrairement à la
    plupart des autres listes de Matrix, AUCUN filtre de périmètre n'est
    appliqué ici — le catalogue de formations est un référentiel commun,
    visible par tout utilisateur connecté quel que soit son navire. Seule la
    VALIDATION d'une formation pour un marin précis (ValiderFormationView) et
    la désignation de référents restent contrôlées par navire."""

    model = TrainingCourse
    template_name = "training/formations.html"
    context_object_name = "formations"

    def get_queryset(self):
        # Catalogue affiché = uniquement les formations ACTIVE (Circuit C —
        # Circuit d'approbation chef de secteur -> chef de service) : une
        # formation « gérée par le bord » proposée/modifiée par un chef de
        # secteur, tant qu'elle est en attente de validation ou refusée,
        # reste invisible ici pour tout le monde — elle n'apparaît que dans
        # les sections dédiées « Mes propositions » / « À valider » ci-dessous
        # (cf. contexte_formations.py::construire_contexte_formations), jamais
        # dans le catalogue général.
        qs = (
            TrainingCourse.objects.filter(statut_validation="ACTIVE")
            .prefetch_related("prerequisites", "records", "records__user")
            .order_by("title")
        )
        # Valeur issue du <select> HTML du filtre catégorie.
        categorie = self.request.GET.get("category", "").strip()
        if categorie:
            qs = qs.filter(category=categorie)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        return construire_contexte_formations(self, ctx)

    def post(self, request, *args, **kwargs):
        action = request.POST.get("action")
        handler = ACTION_HANDLERS.get(action)
        if handler is None:
            return redirect("formation-list")
        return handler(request)


class ValiderFormationView(LoginRequiredMixin, View):
    """Crée un TrainingRecord : un chef valide qu'un marin a suivi/réussi une
    formation. L'expiration est calculée automatiquement via
    TrainingRecord.compute_expiry, comme pour toute création côté API."""

    def post(self, request):
        marin_id = request.POST.get("marin_id")
        course_id = request.POST.get("course_id")
        completed_at_str = request.POST.get("completed_at")

        if not (marin_id and course_id and completed_at_str):
            messages.error(request, "Le marin, la formation et la date de complétion sont obligatoires.")
            return redirect("formation-list")

        try:
            marin = User.objects.get(pk=marin_id, is_active=True)
        except User.DoesNotExist:
            messages.error(request, "Marin introuvable.")
            return redirect("formation-list")

        try:
            # Formation ACTIVE uniquement (correctif QA — Circuit C) : une
            # formation « bord » en attente de validation ou refusée reste
            # invisible/inutilisable pour tout le monde sauf le proposeur/
            # validateur concerné, même en devinant son identifiant.
            course = TrainingCourse.objects.get(pk=course_id, statut_validation="ACTIVE")
        except TrainingCourse.DoesNotExist:
            messages.error(request, "Formation introuvable.")
            return redirect("formation-list")

        # Autorisation réelle de validation, UNIQUEMENT branchée sur le vrai
        # contrôle d'accès du modèle (training.models.peut_valider_formation,
        # déjà utilisé côté API par TrainingRecordPermission) : référent de
        # cette formation précise POUR LE NAVIRE DU MARIN CIBLÉ, référent
        # formation de ce navire, ou COMMANDANT+. Le seuil générique
        # CHEF_SECTION+ historique du web a été RETIRÉ (faille corrigée,
        # tâche Notion « Sécurité : la validation de formation contourne le
        # contrôle par référent (seuil générique CHEF_SECTION+) ») : il
        # autorisait à tort n'importe quel chef de section (et au-dessus) à
        # valider n'importe quelle formation de son périmètre organisationnel
        # sans en être désigné référent.
        navire_marin = navire_de(marin)
        if not peut_valider_formation(request.user, course, navire_marin):
            raise PermissionDenied

        # Revalidation côté serveur du marin ciblé : empêche de valider une
        # formation pour un marin hors périmètre (parmi ceux proposés à un
        # référent, potentiellement élargi à plusieurs navires — cf.
        # formation_perimetre.py::_marins_validables), en forgeant la requête
        # POST avec un autre marin_id que ceux proposés par le select du GET.
        if not _marins_validables(request.user).filter(pk=marin.pk).exists():
            raise PermissionDenied

        try:
            completed_at = date.fromisoformat(completed_at_str)
        except ValueError:
            messages.error(request, "Date de complétion invalide.")
            return redirect("formation-list")

        expires_at = TrainingRecord.compute_expiry(completed_at, course.validity_days)
        TrainingRecord.objects.create(
            user=marin,
            course=course,
            completed_at=completed_at,
            expires_at=expires_at,
            validated_by=request.user,
            created_by=request.user,
        )
        # Journal d'audit transverse (§30 cahier des charges) : validation
        # qu'un marin a suivi/réussi une formation — action sensible au même
        # titre qu'une validation de maintenance/ticket, cf. tâche Notion
        # « Unifier les modèles d'historique/audit ».
        AuditLog.objects.create(
            actor=request.user, action="validate_training_record", target_user=marin,
            details=f"course={course.pk}; title={course.title}; expire_le={expires_at.isoformat()}",
        )
        # Informe le marin lui-même de sa qualification validée (§38 cahier des
        # charges, notifications intelligentes) — jusqu'ici seul le chef qui
        # valide voyait la confirmation (message Django ci-dessous), le marin
        # concerné n'était jamais notifié.
        Notification.objects.create(
            user=marin,
            verb=(
                f"Formation « {course.title} » validée : expire le "
                f"{expires_at.strftime('%d/%m/%Y')}."
            ),
        )
        # Niveau 25 = validation réussie (constante de niveau la plus élevée du
        # module de messages Django, juste au-dessus du niveau d'information).
        messages.add_message(
            request,
            25,
            f"Formation « {course.title} » validée pour {marin.get_full_name() or marin.username} "
            f"(expire le {expires_at.strftime('%d/%m/%Y')}).",
        )
        return redirect("formation-list")


class CompetencyTreeView(LoginRequiredMixin, View):
    """Arbre de compétences : formations disposées par niveau de profondeur
    (chaîne de prérequis), avec l'état de chacune pour le marin connecté
    (validé / disponible / verrouillé). Formation désormais globale (tâche
    Notion « Formation unique et portable entre navires ») : l'arbre porte
    sur l'ENSEMBLE du catalogue, partagé par tous les navires — il n'y a plus
    de sélecteur de secteur, chaque marin voit le même arbre quel que soit
    son bord. Le calcul du graphe (niveaux, anti-cycle) porte sur l'ensemble
    des formations — les prérequis peuvent traverser les catégories — mais
    l'affichage regroupe les formations par catégorie (domaine métier) via
    regrouper_par_categorie."""

    template_name = "training/arbre_competences.html"

    def get(self, request, *args, **kwargs):
        # Formations ACTIVE uniquement (Circuit C) : une formation « bord »
        # en attente de validation ou refusée n'apparaît pas encore dans
        # l'arbre de compétences, même principe que le catalogue général
        # (cf. TrainingCourseListView.get_queryset).
        formations = list(
            TrainingCourse.objects.filter(statut_validation="ACTIVE")
            .prefetch_related("prerequisites").order_by("title")
        )
        carte = calculer_carte_competences(formations, request.user)
        categories = regrouper_par_categorie(carte)
        return render(request, self.template_name, {"categories": categories})
