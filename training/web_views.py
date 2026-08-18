from collections import defaultdict

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied, ValidationError
from django.shortcuts import redirect, render
from django.views.generic import ListView, View

from matrix.core.mixins import ScopedQuerySetMixin, build_scope_q
from matrix.core.roles import RoleLevel, user_role_level
from org.models import Sector

from .models import TrainingCourse
from .services import calculer_carte_competences, regrouper_par_niveau

# Seuil de rôle requis pour configurer les prérequis d'une formation, cohérent
# avec RolePermission.min_level_write (matrix/core/permissions.py) déjà appliqué
# côté API sur TrainingCourseViewSet.
NIVEAU_REQUIS_GESTION_PREREQUIS = RoleLevel.CHEF_SECTION


def _peut_gerer_prerequis(user):
    return user_role_level(user) >= NIVEAU_REQUIS_GESTION_PREREQUIS


def _secteurs_visibles(user):
    """Secteurs visibles par l'utilisateur, en réutilisant scope_filters_for_user
    (via build_scope_q, même système que ScopedQuerySetMixin côté API) plutôt
    qu'un nouveau mécanisme de périmètre — même traduction de chemins que
    AssetTypeViewSet (assets/views.py) pour un modèle rattaché à un secteur."""
    return Sector.objects.filter(
        build_scope_q(user, {
            "ship_id": "service__ship_id",
            "service_id": "service_id",
            "sector_id": "id",
        })
    ).select_related("service", "service__ship").order_by("service__ship__name", "service__name", "name")


def _afficher_erreur_prerequis(request, erreur):
    """Affiche en français le message d'une ValidationError levée lors de la
    mise à jour des prérequis (protection anti-cycle ou formations manquantes),
    même principe que assets/web_views.py::_afficher_erreur_validation."""
    if hasattr(erreur, "messages"):
        messages.error(request, " ".join(erreur.messages))
    else:
        messages.error(request, str(erreur))


class TrainingCourseListView(LoginRequiredMixin, ScopedQuerySetMixin, ListView):
    """Liste des formations, avec configuration des prérequis pour les chefs
    (T-FORM). Point d'entrée du module Formations, avant l'arbre de compétences
    proprement dit (CompetencyTreeView ci-dessous)."""

    model = TrainingCourse
    template_name = "training/formations.html"
    context_object_name = "formations"

    def get_scoped_filters(self):
        # TrainingCourse n'a qu'un champ "sector" (pas de ship/service/section
        # direct) : même traduction de périmètre que AssetTypeViewSet
        # (assets/views.py) pour un modèle rattaché à un secteur uniquement.
        return build_scope_q(self.request.user, {
            "ship_id": "sector__service__ship_id",
            "service_id": "sector__service_id",
            "sector_id": "sector_id",
        })

    def get_queryset(self):
        qs = (
            super().get_queryset()
            .select_related("sector", "sector__service", "sector__service__ship")
            .prefetch_related("prerequisites")
            .order_by("sector__name", "title")
        )
        sector_id = self.request.GET.get("sector")
        if sector_id:
            qs = qs.filter(sector_id=sector_id)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["secteurs"] = _secteurs_visibles(self.request.user)
        ctx["peut_gerer_prerequis"] = _peut_gerer_prerequis(self.request.user)
        # Candidats prérequis pour chaque formation : uniquement les formations du
        # même secteur (l'arbre de compétences, comme les formations elles-mêmes,
        # est organisé par secteur — cf. CompetencyTreeView) — regroupés par
        # secteur pour un filtrage immédiat côté template sans requête supplémentaire.
        candidats_par_secteur = defaultdict(list)
        for c in TrainingCourse.objects.select_related("sector").order_by("title"):
            candidats_par_secteur[c.sector_id].append(c)
        ctx["candidats_par_secteur"] = dict(candidats_par_secteur)
        return ctx

    def post(self, request, *args, **kwargs):
        action = request.POST.get("action")
        if action == "update_prerequisites":
            if not _peut_gerer_prerequis(request.user):
                raise PermissionDenied
            pk = request.POST.get("pk")
            # Périmètre : seule une formation du périmètre de l'appelant peut être
            # modifiée (self.get_queryset(), scopé via ScopedQuerySetMixin).
            course = self.get_queryset().filter(pk=pk).first()
            if course is None:
                messages.error(request, "Formation introuvable.")
                return redirect("formation-list")
            ids = request.POST.getlist("prerequisites")
            # Seules les formations du même secteur peuvent être choisies comme
            # prérequis — ne fait pas confiance au formulaire, revalidation
            # côté serveur (même principe que _parent_candidats dans
            # assets/web_views.py).
            candidats = TrainingCourse.objects.filter(sector_id=course.sector_id).exclude(pk=course.pk)
            valides = candidats.filter(pk__in=ids)
            try:
                course.prerequisites.set(valides)
            except ValidationError as exc:
                _afficher_erreur_prerequis(request, exc)
                return redirect("formation-list")
            messages.success(request, "Prérequis mis à jour.")
        return redirect("formation-list")


class CompetencyTreeView(LoginRequiredMixin, View):
    """Arbre de compétences : formations d'un secteur disposées par niveau de
    profondeur (chaîne de prérequis), avec l'état de chacune pour le marin
    connecté (validé / disponible / verrouillé)."""

    template_name = "training/arbre_competences.html"

    def get(self, request, *args, **kwargs):
        secteurs = _secteurs_visibles(request.user)
        sector_id = request.GET.get("secteur")
        secteur = secteurs.filter(pk=sector_id).first() if sector_id else secteurs.first()
        niveaux = []
        if secteur is not None:
            formations = list(
                TrainingCourse.objects.filter(sector=secteur)
                .prefetch_related("prerequisites")
                .order_by("title")
            )
            carte = calculer_carte_competences(formations, request.user)
            niveaux = regrouper_par_niveau(carte)
        return render(request, self.template_name, {
            "secteurs": secteurs,
            "secteur": secteur,
            "niveaux": niveaux,
        })
