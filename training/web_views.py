from datetime import date

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect
from django.utils import timezone
from django.views import View
from django.views.generic import ListView

from matrix.core.mixins import ScopedQuerySetMixin
from matrix.core.roles import RoleLevel, user_role_level
from matrix.core.scopes import scope_filters_for_user

from .models import TrainingCourse, TrainingRecord

User = get_user_model()

# Niveau de rôle minimum pour valider une formation au nom d'un marin.
# Le modèle ne définit pas (encore) de référents dédiés par formation : on
# réutilise donc le même seuil que celui déjà appliqué à la création d'un
# TrainingRecord via l'API (RolePermission, cf. training/views.py) plutôt
# que d'inventer un nouveau système de contrôle d'accès.
NIVEAU_MIN_VALIDATION = RoleLevel.CHEF_SECTION


class FormationsListView(LoginRequiredMixin, ScopedQuerySetMixin, ListView):
    """Page centrale des formations : suivi des validations par formation et
    formulaire permettant à un chef de valider qu'un marin a suivi/réussi
    une formation."""

    model = TrainingCourse
    template_name = "training/formations.html"
    context_object_name = "courses"

    def get_queryset(self):
        return (
            super().get_queryset()
            .select_related("sector")
            .prefetch_related("records", "records__user")
            .order_by("sector__name", "title")
        )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        aujourdhui = timezone.localdate()
        for course in ctx["courses"]:
            records = list(course.records.all())
            course.nb_a_jour = sum(1 for r in records if r.expires_at >= aujourdhui)
            course.nb_expires = sum(1 for r in records if r.expires_at < aujourdhui)
            course.dernieres_validations = sorted(records, key=lambda r: r.completed_at, reverse=True)[:5]

        peut_valider = user_role_level(self.request.user) >= NIVEAU_MIN_VALIDATION
        ctx["peut_valider"] = peut_valider
        if peut_valider:
            # Marins visibles limités au périmètre du validateur (même logique
            # de scope que le reste de l'application), sauf pour les rôles à
            # supervision globale (COMMANDANT et au-dessus) pour qui le scope
            # est vide et qui voient donc tous les marins.
            marins = User.objects.filter(is_active=True).select_related("profile").order_by("last_name", "first_name", "username")
            filters = scope_filters_for_user(self.request.user)
            profile_filters = {f"profile__{champ}": valeur for champ, valeur in filters.items()}
            if profile_filters:
                marins = marins.filter(**profile_filters)
            ctx["marins"] = marins
        ctx["aujourdhui"] = aujourdhui.isoformat()
        return ctx


class ValiderFormationView(LoginRequiredMixin, View):
    """Crée un TrainingRecord : un chef valide qu'un marin a suivi/réussi une
    formation. L'expiration est calculée automatiquement via
    TrainingRecord.compute_expiry, comme pour toute création côté API."""

    def post(self, request):
        if user_role_level(request.user) < NIVEAU_MIN_VALIDATION:
            raise PermissionDenied

        marin_id = request.POST.get("marin_id")
        course_id = request.POST.get("course_id")
        completed_at_str = request.POST.get("completed_at")

        if not (marin_id and course_id and completed_at_str):
            messages.error(request, "Le marin, la formation et la date de complétion sont obligatoires.")
            return redirect("formations")

        try:
            marin = User.objects.get(pk=marin_id, is_active=True)
        except User.DoesNotExist:
            messages.error(request, "Marin introuvable.")
            return redirect("formations")

        try:
            course = TrainingCourse.objects.get(pk=course_id)
        except TrainingCourse.DoesNotExist:
            messages.error(request, "Formation introuvable.")
            return redirect("formations")

        try:
            completed_at = date.fromisoformat(completed_at_str)
        except ValueError as _:
            messages.error(request, "Date de complétion invalide.")
            return redirect("formations")

        expires_at = TrainingRecord.compute_expiry(completed_at, course.validity_days)
        TrainingRecord.objects.create(
            user=marin,
            course=course,
            completed_at=completed_at,
            expires_at=expires_at,
            validated_by=request.user,
            created_by=request.user,
        )
        # Niveau 25 = validation réussie (constante de niveau la plus élevée du
        # module de messages Django, juste au-dessus du niveau d'information).
        messages.add_message(
            request,
            25,
            f"Formation « {course.title} » validée pour {marin.get_full_name() or marin.username} "
            f"(expire le {expires_at.strftime('%d/%m/%Y')}).",
        )
        return redirect("formations")
