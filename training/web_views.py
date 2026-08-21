from collections import defaultdict
from datetime import date

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import Q
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.generic import ListView, View

from matrix.core.mixins import ScopedQuerySetMixin, build_scope_q
from matrix.core.roles import RoleLevel, user_role_level
from matrix.core.scopes import scope_filters_for_user
from notifications.models import Notification
from org.models import Sector

from .models import TrainingCourse, TrainingRecord, TrainingSession
from .services import calculer_carte_competences, regrouper_par_categorie

User = get_user_model()

# Seuil de rôle requis pour configurer les prérequis d'une formation, cohérent
# avec RolePermission.min_level_write (matrix/core/permissions.py) déjà appliqué
# côté API sur TrainingCourseViewSet.
NIVEAU_REQUIS_GESTION_PREREQUIS = RoleLevel.CHEF_SECTION

# Seuil de rôle requis pour créer une toute nouvelle formation : volontairement
# plus strict que NIVEAU_REQUIS_GESTION_PREREQUIS (qui ne fait qu'éditer une
# formation existante). Demande explicite du Product Owner : la création reste
# réservée à un administrateur pour l'instant, les centres de formation
# externes prendront le relais dans une phase future non spécifiée.
NIVEAU_REQUIS_CREATION_FORMATION = RoleLevel.ADMIN_NAVIRE

# Seuil de rôle requis pour valider qu'un marin a suivi/réussi une formation
# (création d'un TrainingRecord) : même seuil que NIVEAU_REQUIS_GESTION_PREREQUIS.
# Le modèle ne définit pas (encore) de référents dédiés par validation, donc
# pas de nouveau système de contrôle d'accès ici.
NIVEAU_REQUIS_VALIDATION = RoleLevel.CHEF_SECTION


def _peut_gerer_prerequis(user):
    return user_role_level(user) >= NIVEAU_REQUIS_GESTION_PREREQUIS


def _peut_creer_formation(user):
    return user_role_level(user) >= NIVEAU_REQUIS_CREATION_FORMATION


def _peut_valider_formation(user):
    return user_role_level(user) >= NIVEAU_REQUIS_VALIDATION


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


def _utilisateurs_du_secteur_q(sector):
    """Filtre les utilisateurs dont le profil couvre le secteur donné, quel que
    soit le niveau de périmètre auquel leur profil est réellement scopé
    (navire, service, secteur, ou section rattachée à ce secteur) — même
    principe que _ship_du_profil_q (logistics/web_views.py), décliné au
    niveau secteur pour proposer les candidats référents d'une formation."""
    return (
        Q(profile__ship_id=sector.service.ship_id)
        | Q(profile__service_id=sector.service_id)
        | Q(profile__sector_id=sector.id)
        | Q(profile__section__sector_id=sector.id)
    )


def _formations_visibles(user):
    """Formations visibles par l'utilisateur, même traduction de périmètre que
    TrainingCourseListView.get_scoped_filters — réutilisée aussi par
    ValiderFormationView pour revalider côté serveur que la formation ciblée
    est bien dans le périmètre de l'appelant."""
    return TrainingCourse.objects.filter(build_scope_q(user, {
        "ship_id": "sector__service__ship_id",
        "service_id": "sector__service_id",
        "sector_id": "sector_id",
        "section_id": "sector__sections__id",
    }))


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


def _entier_ou_none(valeur):
    """Convertit une valeur postée en entier, ou renvoie None si elle est vide
    ou non numérique — évite un ValueError non attrapé (donc une erreur 500)
    quand un POST forgé envoie une valeur non numérique dans un champ
    normalement issu d'un <select> HTML (ex. secteur, identifiant de
    formation)."""
    try:
        return int(valeur)
    except (TypeError, ValueError):
        return None


def _identifiants_valides(valeurs):
    """Filtre une liste d'identifiants postés (ex. request.POST.getlist) pour ne
    garder que ceux convertibles en entier — même principe que
    _entier_ou_none, appliqué à une liste utilisée ensuite dans un filtre
    pk__in, qui lève le même ValueError non attrapé si une valeur n'est pas
    numérique."""
    return [v for v in valeurs if _entier_ou_none(v) is not None]


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
            "section_id": "sector__sections__id",
        })

    def get_queryset(self):
        qs = (
            super().get_queryset()
            .select_related("sector", "sector__service", "sector__service__ship")
            .prefetch_related("prerequisites", "referents", "records", "records__user")
            .order_by("sector__name", "title")
        )
        # Valeur issue du <select> HTML du filtre : peut arriver non numérique
        # sur un GET/POST forgé (ex. "action=update_prerequisites" appelle
        # cette méthode via self.get_queryset() plus bas) — même principe que
        # _entier_ou_none appliqué au reste du fichier, on ignore le filtre
        # plutôt que de planter sur un ValueError non attrapé.
        sector_id = _entier_ou_none(self.request.GET.get("sector"))
        if sector_id is not None:
            qs = qs.filter(sector_id=sector_id)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["secteurs"] = _secteurs_visibles(self.request.user)
        ctx["peut_gerer_prerequis"] = _peut_gerer_prerequis(self.request.user)
        ctx["peut_creer_formation"] = _peut_creer_formation(self.request.user)
        # Périmètre de l'utilisateur, appliqué manuellement ici : ces deux blocs
        # portent volontairement sur TOUS les secteurs visibles (pas seulement
        # celui sélectionné dans le filtre GET "sector" de la liste), mais ne
        # doivent jamais porter sur l'ensemble des formations de la flotte —
        # sous peine de fuite de catégories et de titres de formation hors
        # périmètre dans le HTML (datalist + cases à cocher des prérequis).
        formations_visibles = _formations_visibles(self.request.user)
        # Candidats prérequis pour chaque formation : uniquement les formations du
        # même secteur (l'arbre de compétences, comme les formations elles-mêmes,
        # est organisé par secteur — cf. CompetencyTreeView) — regroupés par
        # secteur pour un filtrage immédiat côté template sans requête supplémentaire.
        candidats_par_secteur = defaultdict(list)
        for c in formations_visibles.select_related("sector").order_by("title"):
            candidats_par_secteur[c.sector_id].append(c)
        ctx["candidats_par_secteur"] = dict(candidats_par_secteur)
        # Catégories déjà utilisées, par secteur : sert à l'autocomplétion du
        # champ catégorie (datalist HTML natif) pour limiter les doublons/fautes
        # de frappe (ex. "Incendie" vs "incendie") sans imposer de liste fermée.
        categories_par_secteur = defaultdict(set)
        for sector_id, categorie in (
            formations_visibles.exclude(category="").values_list("sector_id", "category")
        ):
            categories_par_secteur[sector_id].add(categorie)
        ctx["categories_par_secteur"] = {
            sector_id: sorted(categories) for sector_id, categories in categories_par_secteur.items()
        }
        # Candidats référents pour chaque formation : les utilisateurs visibles
        # dans le secteur de la formation (même logique que
        # logistics/web_views.py::_ship_du_profil_q, déclinée au secteur) —
        # un référent est désigné pour sa compétence, pas pour son rang, mais
        # reste choisi parmi les personnes rattachées au secteur concerné pour
        # garder une liste de candidats gérable dans la modale.
        secteurs_des_formations = {c.sector for c in formations_visibles.select_related(
            "sector", "sector__service"
        )}
        utilisateurs_par_secteur = {}
        for secteur in secteurs_des_formations:
            utilisateurs_par_secteur[secteur.id] = list(
                User.objects.filter(_utilisateurs_du_secteur_q(secteur))
                .select_related("profile")
                .order_by("username")
                .distinct()
            )
        ctx["utilisateurs_par_secteur"] = utilisateurs_par_secteur
        # Sessions à venir (planifiées, pas encore passées) de chaque formation
        # affichée, avec la place restante et l'état de réservation du marin
        # connecté — réservation self-service (T-FORM), page la plus naturelle
        # pour ça puisque c'est déjà ici que le marin consulte ses formations.
        formations = list(ctx["formations"])
        sessions_qs = (
            TrainingSession.objects.filter(
                course_id__in=[f.id for f in formations],
                status="PLANNED",
                scheduled_at__gte=timezone.now(),
            )
            .select_related("instructor")
            .prefetch_related("reservations")
            .order_by("scheduled_at")
        )
        sessions_par_formation = defaultdict(list)
        for s in sessions_qs:
            s.deja_reserve = self.request.user in s.reservations.all()
            sessions_par_formation[s.course_id].append(s)
        # Suivi des validations (T-FORM) : compteurs à jour/expirées et
        # dernières validations par formation, affichés directement sur
        # chaque carte sans navigation supplémentaire.
        aujourdhui = timezone.localdate()
        for f in formations:
            f.sessions_a_venir = sessions_par_formation.get(f.id, [])
            records = list(f.records.all())
            f.nb_a_jour = sum(1 for r in records if r.expires_at >= aujourdhui)
            f.nb_expires = sum(1 for r in records if r.expires_at < aujourdhui)
            f.dernieres_validations = sorted(records, key=lambda r: r.completed_at, reverse=True)[:5]
        ctx["formations"] = formations

        peut_valider = _peut_valider_formation(self.request.user)
        ctx["peut_valider"] = peut_valider
        if peut_valider:
            # Marins visibles limités au périmètre du validateur (même logique
            # de scope que le reste de l'application), sauf pour les rôles à
            # supervision globale (COMMANDANT et au-dessus) pour qui le
            # périmètre est vide et qui voient donc tous les marins.
            marins = User.objects.filter(is_active=True).select_related("profile").order_by(
                "last_name", "first_name", "username"
            )
            q_perimetre_marin = filtres_perimetre_marin(self.request.user)
            if q_perimetre_marin is not None:
                marins = marins.filter(q_perimetre_marin)
            ctx["marins"] = marins
        # Objet date (pas de chaîne) : comparé tel quel à r.expires_at dans le
        # template pour le badge À jour/Expirée. Le rendu template d'un objet
        # date appelle str(), qui produit déjà le format ISO AAAA-MM-JJ attendu
        # par l'attribut value de l'input type="date" du formulaire.
        ctx["aujourdhui"] = aujourdhui
        return ctx

    def post(self, request, *args, **kwargs):
        action = request.POST.get("action")
        if action == "create_course":
            if not _peut_creer_formation(request.user):
                raise PermissionDenied
            titre = request.POST.get("title", "").strip()
            # Le secteur doit faire partie du périmètre visible de l'appelant —
            # ne fait pas confiance à la valeur postée (même principe que le
            # filtrage des prérequis/référents ci-dessous), sous peine de
            # permettre à un administrateur navire de créer une formation sur
            # un secteur d'un autre navire auquel il n'a pas accès.
            sector_id = _entier_ou_none(request.POST.get("sector"))
            secteur = (
                _secteurs_visibles(request.user).filter(pk=sector_id).first()
                if sector_id is not None else None
            )
            if not titre or secteur is None:
                messages.error(request, "Le titre et le secteur (dans votre périmètre) sont obligatoires.")
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
            course = TrainingCourse.objects.create(
                sector=secteur,
                title=titre,
                description=request.POST.get("description", "").strip(),
                category=request.POST.get("category", "").strip(),
                validity_days=validity_days,
            )
            # Prérequis facultatifs dès la création, limités aux formations déjà
            # existantes du même secteur (revalidation côté serveur, même
            # principe que pour l'édition ci-dessous).
            ids = _identifiants_valides(request.POST.getlist("prerequisites"))
            if ids:
                candidats = TrainingCourse.objects.filter(sector=secteur).exclude(pk=course.pk)
                course.prerequisites.set(candidats.filter(pk__in=ids))
            messages.success(request, "Formation créée.")
            return redirect("formation-list")
        if action == "update_prerequisites":
            if not _peut_gerer_prerequis(request.user):
                raise PermissionDenied
            pk = _entier_ou_none(request.POST.get("pk"))
            # Périmètre : seule une formation du périmètre de l'appelant peut être
            # modifiée (self.get_queryset(), scopé via ScopedQuerySetMixin).
            course = self.get_queryset().filter(pk=pk).first() if pk is not None else None
            if course is None:
                messages.error(request, "Formation introuvable.")
                return redirect("formation-list")
            ids = _identifiants_valides(request.POST.getlist("prerequisites"))
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
            # Catégorie modifiable dans la même modale que les prérequis (un seul
            # clic pour tout mettre à jour) — champ absent du POST : on ne touche
            # pas à la catégorie existante (compatibilité avec un appel qui ne
            # gérerait que les prérequis).
            if "category" in request.POST:
                course.category = request.POST.get("category", "").strip()
                course.save(update_fields=["category"])
            # Référents modifiables dans la même modale (un seul clic pour tout
            # mettre à jour) — champ absent du POST : on ne touche pas aux
            # référents existants (compatibilité avec un appel qui ne gérerait
            # que les prérequis/la catégorie). Ne fait pas confiance au
            # formulaire : seuls les utilisateurs visibles dans le secteur de
            # la formation peuvent être désignés (revalidation côté serveur).
            if "referents" in request.POST:
                referent_ids = _identifiants_valides(request.POST.getlist("referents"))
                referents_valides = User.objects.filter(
                    _utilisateurs_du_secteur_q(course.sector), pk__in=referent_ids
                )
                course.referents.set(referents_valides)
            messages.success(request, "Prérequis mis à jour.")
            return redirect("formation-list")
        if action == "reserver_session":
            return self._reserver_session(request)
        if action == "annuler_reservation":
            return self._annuler_reservation(request)
        return redirect("formation-list")

    def _reserver_session(self, request):
        """Réservation self-service d'une place sur une session PLANNED, par le
        marin connecté pour lui-même uniquement — distincte de la validation de
        présence par un référent (attendees, non touché ici). Les règles
        métier (session toujours planifiée, capacité, prérequis) sont
        appliquées par le signal m2m TrainingSession.reservations
        (training/models.py::_controler_reservation), seule source de vérité."""
        session_id = _entier_ou_none(request.POST.get("session_id"))
        # Périmètre : seule une session d'une formation visible par l'appelant
        # peut être réservée — ne fait pas confiance à l'identifiant posté.
        session = (
            TrainingSession.objects.select_related("course")
            .filter(pk=session_id, course_id__in=self.get_queryset().values_list("id", flat=True))
            .first()
            if session_id is not None else None
        )
        if session is None:
            messages.error(request, "Session introuvable ou hors de votre périmètre.")
            return redirect("formation-list")
        if request.user in session.reservations.all():
            messages.info(request, "Vous avez déjà réservé une place pour cette session.")
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

    def _annuler_reservation(self, request):
        """Annulation de SA PROPRE réservation par le marin connecté, tant que
        la session n'a pas encore eu lieu (contrôle fait par le signal m2m
        TrainingSession.reservations, cf. training/models.py::_controler_reservation)."""
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
            # Savepoint explicite, même principe que _reserver_session ci-dessus.
            with transaction.atomic():
                session.reservations.remove(request.user)
        except ValidationError as exc:
            _afficher_erreur_prerequis(request, exc)
            return redirect("formation-list")
        messages.success(request, "Réservation annulée.")
        return redirect("formation-list")


class ValiderFormationView(LoginRequiredMixin, View):
    """Crée un TrainingRecord : un chef valide qu'un marin a suivi/réussi une
    formation. L'expiration est calculée automatiquement via
    TrainingRecord.compute_expiry, comme pour toute création côté API."""

    def post(self, request):
        if not _peut_valider_formation(request.user):
            raise PermissionDenied

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
            course = TrainingCourse.objects.get(pk=course_id)
        except TrainingCourse.DoesNotExist:
            messages.error(request, "Formation introuvable.")
            return redirect("formation-list")

        # Revalidation côté serveur : la formation ciblée doit être dans le
        # périmètre effectif de l'utilisateur, pas seulement proposée par le
        # GET qui alimente le select (empêche un chef de valider une formation
        # d'un secteur hors de son périmètre en forgeant la requête POST).
        if not _formations_visibles(request.user).filter(pk=course.pk).exists():
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
    """Arbre de compétences : formations d'un secteur disposées par niveau de
    profondeur (chaîne de prérequis), avec l'état de chacune pour le marin
    connecté (validé / disponible / verrouillé). Le calcul du graphe (niveaux,
    anti-cycle) porte sur l'ensemble des formations du secteur — les
    prérequis peuvent traverser les catégories — mais l'affichage regroupe
    les formations par catégorie (domaine métier) via regrouper_par_categorie."""

    template_name = "training/arbre_competences.html"

    def get(self, request, *args, **kwargs):
        secteurs = _secteurs_visibles(request.user)
        secteur_brut = request.GET.get("secteur")
        if secteur_brut:
            # Même principe que le filtre "sector" de TrainingCourseListView :
            # une valeur non numérique (POST/GET forgé) est traitée comme un
            # secteur introuvable (secteur = None ci-dessous), exactement
            # comme un identifiant numérique valide mais absent en base,
            # plutôt que de planter sur un ValueError non attrapé.
            sector_id = _entier_ou_none(secteur_brut)
            secteur = secteurs.filter(pk=sector_id).first() if sector_id is not None else None
        else:
            secteur = secteurs.first()
        categories = []
        if secteur is not None:
            formations = list(
                TrainingCourse.objects.filter(sector=secteur)
                .prefetch_related("prerequisites")
                .order_by("title")
            )
            carte = calculer_carte_competences(formations, request.user)
            categories = regrouper_par_categorie(carte)
        return render(request, self.template_name, {
            "secteurs": secteurs,
            "secteur": secteur,
            "categories": categories,
        })
