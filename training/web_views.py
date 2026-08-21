from datetime import date

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.shortcuts import redirect
from django.utils import timezone
from django.views import View
from django.views.generic import ListView

from matrix.core.roles import RoleLevel, user_role_level
from matrix.core.scopes import scope_filters_for_user
from org.models import Section, Sector

from .models import TrainingCourse, TrainingRecord

User = get_user_model()

# Niveau de rôle minimum pour valider une formation au nom d'un marin.
# Le modèle ne définit pas (encore) de référents dédiés par formation : on
# réutilise donc le même seuil que celui déjà appliqué à la création d'un
# TrainingRecord via l'API (RolePermission, cf. training/views.py) plutôt
# que d'inventer un nouveau système de contrôle d'accès.
NIVEAU_MIN_VALIDATION = RoleLevel.CHEF_SECTION


def filtres_perimetre_formation(user):
    """Calcule les filtres de périmètre applicables à TrainingCourse.

    TrainingCourse n'a qu'un champ ``sector`` (pas de champ ``section``,
    ``service`` ni ``ship`` comme les modèles qui portent nativement les 4
    niveaux de périmètre, ex. StockPiece). ``scope_filters_for_user``
    renvoie un seul niveau parmi section_id/sector_id/service_id/ship_id
    selon le périmètre du profil de l'utilisateur : on le résout ici
    explicitement vers le(s) secteur(s) correspondant, dans un sens ou dans
    l'autre selon la hiérarchie Navire > Service > Secteur > Section :
    - section  : on remonte au secteur parent (filtre exact)
    - secteur  : déjà le bon niveau, inchangé
    - service  : on descend à tous les secteurs de ce service (filtre __in)
    - navire   : on descend à tous les secteurs de ce navire (filtre __in)

    Le dict retourné n'utilise que des clés directement compatibles avec
    TrainingCourse.objects.filter(**filtres) (``sector_id`` ou
    ``sector_id__in``), utilisable tel quel aussi bien pour la liste que
    pour la revalidation côté serveur du formulaire de validation."""
    filters = scope_filters_for_user(user)

    section_id = filters.pop("section_id", None)
    if section_id is not None:
        section = Section.objects.filter(pk=section_id).select_related("sector").first()
        # Section introuvable (cas dégénéré) : on ne montre aucune formation
        # plutôt que de tout exposer par erreur (sector_id=None ne
        # correspond à aucune formation, le champ étant obligatoire).
        return {"sector_id": section.sector_id if section else None}

    service_id = filters.pop("service_id", None)
    if service_id is not None:
        secteurs = Sector.objects.filter(service_id=service_id).values_list("pk", flat=True)
        return {"sector_id__in": list(secteurs)}

    ship_id = filters.pop("ship_id", None)
    if ship_id is not None:
        secteurs = Sector.objects.filter(service__ship_id=ship_id).values_list("pk", flat=True)
        return {"sector_id__in": list(secteurs)}

    # Cas restant : sector_id (déjà le bon champ, inchangé) ou dict vide
    # (supervision globale, COMMANDANT et au-dessus).
    return filters


def filtres_perimetre_marin(user):
    """Calcule le filtre de périmètre applicable à User (via son profil).

    Contrairement à TrainingCourse (toujours rattaché à un secteur), un
    marin peut être rattaché à n'importe quel niveau de la hiérarchie
    Navire > Service > Secteur > Section (UserProfile.scope renvoie le
    niveau le plus fin renseigné). Un simple préfixage "profile__" du
    résultat de scope_filters_for_user ne suffit donc pas : un chef de
    service scopé au niveau service_id ne verrait alors que les marins dont
    le profil a directement service_id renseigné, pas ceux rattachés à un
    secteur ou une section de ce service (cas le plus courant). Il faut
    donc, selon le niveau du validateur, couvrir tous les marins rattachés
    n'importe où EN DESSOUS de ce niveau dans la hiérarchie, via un Q
    combinant chaque chemin possible.

    Renvoie un objet Q, ou None si le périmètre est vide (supervision
    globale, COMMANDANT et au-dessus, qui voient tous les marins)."""
    filters = scope_filters_for_user(user)

    section_id = filters.get("section_id")
    if section_id is not None:
        return Q(profile__section_id=section_id)

    sector_id = filters.get("sector_id")
    if sector_id is not None:
        return Q(profile__sector_id=sector_id) | Q(profile__section__sector_id=sector_id)

    service_id = filters.get("service_id")
    if service_id is not None:
        return (
            Q(profile__service_id=service_id)
            | Q(profile__sector__service_id=service_id)
            | Q(profile__section__sector__service_id=service_id)
        )

    ship_id = filters.get("ship_id")
    if ship_id is not None:
        return (
            Q(profile__ship_id=ship_id)
            | Q(profile__service__ship_id=ship_id)
            | Q(profile__sector__service__ship_id=ship_id)
            | Q(profile__section__sector__service__ship_id=ship_id)
        )

    return None


class FormationsListView(LoginRequiredMixin, ListView):
    """Page centrale des formations : suivi des validations par formation et
    formulaire permettant à un chef de valider qu'un marin a suivi/réussi
    une formation."""

    model = TrainingCourse
    template_name = "training/formations.html"
    context_object_name = "courses"

    def get_queryset(self):
        # Filtrage appliqué directement (pas via ScopedQuerySetMixin) : les
        # filtres de filtres_perimetre_formation peuvent utiliser un lookup
        # __in (périmètre service/navire résolu vers plusieurs secteurs), que
        # le garde-fou générique du mixin (hasattr sur le nom de champ nu)
        # ignorerait silencieusement, exposant tout le navire par erreur.
        filtres = filtres_perimetre_formation(self.request.user)
        return (
            TrainingCourse.objects.filter(**filtres)
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
            q_perimetre_marin = filtres_perimetre_marin(self.request.user)
            if q_perimetre_marin is not None:
                marins = marins.filter(q_perimetre_marin)
            ctx["marins"] = marins
        # Objet date (pas de chaîne) : comparé tel quel à r.expires_at dans le
        # template pour le badge À jour/Expirée. Le rendu template d'un objet
        # date appelle str(), qui produit déjà le format ISO AAAA-MM-JJ
        # attendu par l'attribut value de l'input type="date" du formulaire.
        ctx["aujourdhui"] = aujourdhui
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

        # Revalidation côté serveur : la formation ciblée doit être dans le
        # périmètre effectif de l'utilisateur, pas seulement proposée par le
        # GET qui alimente le select (empêche un chef de section de valider
        # une formation d'un secteur hors de son périmètre en forgeant la
        # requête POST).
        filtres = filtres_perimetre_formation(request.user)
        if filtres and not TrainingCourse.objects.filter(pk=course.pk, **filtres).exists():
            raise PermissionDenied

        # Même revalidation côté serveur, appliquée cette fois au marin ciblé
        # (et non plus seulement à la formation) : empêche un chef de valider
        # une formation de son périmètre pour un marin qui n'en fait pas
        # partie, en forgeant la requête POST avec un autre marin_id que ceux
        # proposés par le select du GET.
        q_perimetre_marin = filtres_perimetre_marin(request.user)
        if q_perimetre_marin is not None and not User.objects.filter(q_perimetre_marin, pk=marin.pk).exists():
            raise PermissionDenied

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
