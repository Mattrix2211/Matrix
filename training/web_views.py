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
from matrix.core.scopes import scope_filters_for_user, ship_id_for_user
from notifications.models import Notification
from org.models import Sector, Ship

from .models import (
    NIVEAU_SUPERVISION_GLOBALE_FORMATION,
    ReferentFormationNavire,
    TrainingCourse,
    TrainingRecord,
    TrainingSession,
    peut_valider_formation,
)
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

# Seuil de rôle générique à partir duquel un marin peut valider n'importe
# quelle formation de son périmètre organisationnel, MÊME sans être désigné
# référent — même seuil que NIVEAU_REQUIS_GESTION_PREREQUIS. Ce seuil
# générique s'ajoute (sans le remplacer) au vrai contrôle d'accès défini par
# training.models.peut_valider_formation (référent de la formation précise,
# référent formation du navire, ou COMMANDANT+, déjà utilisé côté API par
# TrainingRecordPermission) : un marin de rang inférieur à ce seuil peut donc
# tout de même valider une formation précise dès lors qu'il en est désigné
# référent — cf. _est_referent_formation et ValiderFormationView ci-dessous.
NIVEAU_REQUIS_VALIDATION = RoleLevel.CHEF_SECTION


def _peut_gerer_prerequis(user):
    return user_role_level(user) >= NIVEAU_REQUIS_GESTION_PREREQUIS


def _peut_creer_formation(user):
    return user_role_level(user) >= NIVEAU_REQUIS_CREATION_FORMATION


def _peut_valider_formation(user):
    return user_role_level(user) >= NIVEAU_REQUIS_VALIDATION


def _est_referent_formation(user):
    """Vrai si l'utilisateur est désigné référent d'au moins une formation
    précise (TrainingCourse.referents) ou référent formation d'un navire
    (ReferentFormationNavire) — cf. training.models.peut_valider_formation.
    Complète _peut_valider_formation ci-dessus (seuil générique CHEF_SECTION)
    pour un marin de rang inférieur (ex. EQUIPIER) désigné référent : sans ce
    contrôle, le bouton « Valider une formation » resterait invisible pour
    lui alors qu'il a bien l'autorité sur sa formation."""
    return (
        TrainingCourse.objects.filter(referents=user).exists()
        or ReferentFormationNavire.objects.filter(user=user).exists()
    )


# Seuil de rôle requis pour désigner/retirer le référent formation d'un
# navire (ReferentFormationNavire, training/models.py) : même niveau que la
# supervision globale d'une formation — il faut déjà disposer soi-même de
# l'autorité de validation sur tout le navire (COMMANDANT et au-dessus) pour
# pouvoir la déléguer à un référent unique, choisi pour sa compétence plutôt
# que pour son rang.
NIVEAU_REQUIS_GESTION_REFERENT_NAVIRE = NIVEAU_SUPERVISION_GLOBALE_FORMATION


def _peut_gerer_referent_navire(user):
    return user_role_level(user) >= NIVEAU_REQUIS_GESTION_REFERENT_NAVIRE


def _secteurs_visibles(user):
    """Secteurs visibles par l'utilisateur, en réutilisant scope_filters_for_user
    (via build_scope_q, même système que ScopedQuerySetMixin côté API) plutôt
    qu'un nouveau mécanisme de périmètre — même traduction de chemins que
    AssetTypeViewSet (assets/views.py) pour un modèle rattaché à un secteur.

    Le chemin "section_id" traduit le périmètre le plus fin (celui d'un
    équipier, rattaché à une section) vers le secteur qui la contient, via la
    relation inverse Section.sector (related_name="sections") — sans ce
    chemin, un utilisateur dont le profil est rattaché à une section (le cas
    le plus courant pour un équipier) n'avait accès à AUCUN secteur, alors que
    scope_filters_for_user() renvoyait bien {"section_id": ...} : build_scope_q
    ne trouvait aucune clé correspondante dans ce dict et retombait sur
    Q(pk__in=[]) (aucun secteur), d'où l'arbre de compétences totalement
    inaccessible aux équipiers."""
    return Sector.objects.filter(
        build_scope_q(user, {
            "ship_id": "service__ship_id",
            "service_id": "service_id",
            "sector_id": "id",
            "section_id": "sections__id",
        })
    ).select_related("service", "service__ship").order_by("service__ship__name", "service__name", "name").distinct()


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


def _utilisateurs_du_navire_q(ship):
    """Filtre les utilisateurs dont le profil couvre le navire donné, quel que
    soit le niveau de périmètre auquel leur profil est réellement rattaché
    (navire, service, secteur, ou section d'un secteur de ce navire) — même
    principe que _utilisateurs_du_secteur_q ci-dessus, décliné au niveau
    navire pour proposer les candidats au rôle de référent formation du
    navire (ReferentFormationNavire, autorité sur toutes les formations du
    navire quel que soit le secteur)."""
    return (
        Q(profile__ship_id=ship.id)
        | Q(profile__service__ship_id=ship.id)
        | Q(profile__sector__service__ship_id=ship.id)
        | Q(profile__section__sector__service__ship_id=ship.id)
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


def _formations_validables(user, formations_visibles):
    """Formations proposables dans la modale de validation (et revalidées
    côté serveur par ValiderFormationView) : le périmètre organisationnel
    habituel de la page (`formations_visibles`, même liste que les cartes
    affichées) COMPLÉTÉ des formations dont l'utilisateur est spécifiquement
    référent, ainsi que de toutes celles du navire dont il est référent
    formation — un référent (TrainingCourse.referents / ReferentFormationNavire)
    peut être rattaché à un secteur différent de celui de la formation dont il
    a la charge (cf. training/models.py), donc potentiellement absentes du
    périmètre organisationnel de la page."""
    return (
        TrainingCourse.objects.filter(
            Q(pk__in=formations_visibles.values_list("pk", flat=True))
            | Q(referents=user)
            | Q(sector__service__ship__referent_formation__user=user)
        )
        .select_related("sector", "sector__service")
        .distinct()
        .order_by("sector__name", "title")
    )


def _marins_validables(user):
    """Marins proposables dans la modale de validation : le périmètre
    organisationnel habituel (filtres_perimetre_marin) COMPLÉTÉ, pour un
    référent, des marins des secteurs des formations dont il est référent et
    de ceux du navire dont il est référent formation — même principe que
    _formations_validables ci-dessus, appliqué aux marins plutôt qu'aux
    formations, pour qu'un référent rattaché à un autre secteur/navire que
    celui de sa formation puisse malgré tout désigner un marin de ce
    secteur/navire dans le select."""
    marins = User.objects.filter(is_active=True).select_related("profile")
    q = filtres_perimetre_marin(user)
    if q is None:
        # Périmètre déjà illimité (supervision globale, COMMANDANT et
        # au-dessus) : tous les marins sont déjà proposés, inutile d'élargir.
        return marins.order_by("last_name", "first_name", "username")
    for secteur in Sector.objects.filter(training_courses__referents=user).distinct():
        q |= _utilisateurs_du_secteur_q(secteur)
    for navire in Ship.objects.filter(referent_formation__user=user):
        q |= _utilisateurs_du_navire_q(navire)
    return marins.filter(q).distinct().order_by("last_name", "first_name", "username")


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
        # Référent formation du navire (ReferentFormationNavire) : géré ici
        # pour le NAVIRE DE L'APPELANT uniquement (pas la flotte entière),
        # cohérent avec le principe "espace personnel par marin" — un
        # COMMANDANT+ ne gère que son propre bord. Un MASTER_ADMIN sans
        # navire rattaché à son profil ne voit pas ce bloc (aucun navire de
        # référence pour lui), hypothèse à confirmer avec le Product Owner.
        ctx["peut_gerer_referent_navire"] = _peut_gerer_referent_navire(self.request.user)
        if ctx["peut_gerer_referent_navire"]:
            ship_id = ship_id_for_user(self.request.user)
            navire_courant = Ship.objects.filter(pk=ship_id).first() if ship_id else None
            ctx["navire_courant"] = navire_courant
            if navire_courant is not None:
                ctx["referent_formation_navire"] = ReferentFormationNavire.objects.filter(
                    ship=navire_courant
                ).select_related("user").first()
                ctx["candidats_referent_navire"] = (
                    User.objects.filter(_utilisateurs_du_navire_q(navire_courant), is_active=True)
                    .select_related("profile")
                    .order_by("last_name", "first_name", "username")
                    .distinct()
                )
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

        # Peut valider une formation : seuil générique CHEF_SECTION+ (comme
        # avant) COMPLÉTÉ par le statut de référent (formation précise ou
        # navire entier) — sans quoi un référent de rang inférieur (ex.
        # EQUIPIER) ne verrait jamais le bouton alors qu'il a bien
        # l'autorité de valider SA formation (training.models.
        # peut_valider_formation, déjà utilisée côté API).
        peut_valider = _peut_valider_formation(self.request.user) or _est_referent_formation(self.request.user)
        ctx["peut_valider"] = peut_valider
        if peut_valider:
            # Marins et formations proposables dans la modale de validation :
            # le périmètre organisationnel habituel, complété pour un
            # référent des marins/formations hors de ce périmètre mais bien
            # dans son autorité de validation — sans quoi le select resterait
            # vide ou incomplet pour un référent rattaché à un autre secteur
            # que celui de la formation dont il a la charge.
            ctx["marins"] = _marins_validables(self.request.user)
            ctx["formations_validables"] = _formations_validables(self.request.user, formations_visibles)
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
        if action == "set_referent_navire":
            return self._set_referent_navire(request)
        if action == "retirer_referent_navire":
            return self._retirer_referent_navire(request)
        return redirect("formation-list")

    def _set_referent_navire(self, request):
        """Désigne (ou remplace) le référent formation du navire de l'appelant —
        un seul référent par navire (ReferentFormationNavire), qui obtient
        alors l'autorité de validation sur TOUTES les formations du navire
        (cf. training/models.py::peut_valider_formation), en plus des
        référents propres à chaque formation."""
        if not _peut_gerer_referent_navire(request.user):
            raise PermissionDenied
        ship_id = ship_id_for_user(request.user)
        navire = Ship.objects.filter(pk=ship_id).first() if ship_id else None
        if navire is None:
            messages.error(request, "Aucun navire rattaché à votre profil.")
            return redirect("formation-list")
        # Ne fait pas confiance au formulaire : seuls les utilisateurs
        # visibles sur ce navire peuvent être désignés (revalidation côté
        # serveur, même principe que pour les référents par formation).
        candidat_id = _entier_ou_none(request.POST.get("referent_navire_id"))
        candidat = (
            User.objects.filter(_utilisateurs_du_navire_q(navire), pk=candidat_id).first()
            if candidat_id is not None else None
        )
        if candidat is None:
            messages.error(request, "Marin introuvable dans votre navire.")
            return redirect("formation-list")
        ReferentFormationNavire.objects.update_or_create(ship=navire, defaults={"user": candidat})
        if candidat != request.user:
            Notification.objects.create(
                user=candidat,
                verb=f"Vous avez été désigné référent formation du navire {navire.name}.",
            )
        messages.success(
            request,
            f"{candidat.get_full_name() or candidat.username} est désormais référent formation du navire {navire.name}.",
        )
        return redirect("formation-list")

    def _retirer_referent_navire(self, request):
        """Retire le référent formation actuellement désigné pour le navire de
        l'appelant (aucun effet si personne n'était désigné)."""
        if not _peut_gerer_referent_navire(request.user):
            raise PermissionDenied
        ship_id = ship_id_for_user(request.user)
        if ship_id:
            ReferentFormationNavire.objects.filter(ship_id=ship_id).delete()
        messages.success(request, "Référent formation du navire retiré.")
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
            course = TrainingCourse.objects.select_related("sector", "sector__service").get(pk=course_id)
        except TrainingCourse.DoesNotExist:
            messages.error(request, "Formation introuvable.")
            return redirect("formation-list")

        # Autorisation réelle de validation, branchée sur le vrai contrôle
        # d'accès du modèle (training.models.peut_valider_formation, déjà
        # utilisé côté API par TrainingRecordPermission) : référent de cette
        # formation précise, référent formation du navire, ou COMMANDANT+.
        # COMPLÉTÉE (sans être remplacée) par le seuil générique CHEF_SECTION+
        # historique du web — dans ce cas uniquement, la formation doit rester
        # dans le périmètre organisationnel effectif de l'appelant, comme
        # avant, pour ne pas laisser un chef valider une formation d'un
        # secteur hors de son périmètre en forgeant la requête POST.
        autorise_par_referent = peut_valider_formation(request.user, course)
        if not autorise_par_referent:
            if not _peut_valider_formation(request.user):
                raise PermissionDenied
            if not _formations_visibles(request.user).filter(pk=course.pk).exists():
                raise PermissionDenied

        # Même revalidation côté serveur, appliquée cette fois au marin ciblé
        # (et non plus seulement à la formation) : empêche de valider une
        # formation pour un marin hors périmètre, en forgeant la requête POST
        # avec un autre marin_id que ceux proposés par le select du GET. Pour
        # un référent (formation précise ou navire), le périmètre est élargi
        # en conséquence (_marins_validables) ; pour le seuil générique
        # CHEF_SECTION+, le périmètre organisationnel habituel reste seul
        # applicable, comme avant.
        if autorise_par_referent:
            if not _marins_validables(request.user).filter(pk=marin.pk).exists():
                raise PermissionDenied
        else:
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


def _secteurs_arbre_competences(user):
    """Secteurs dont l'arbre de compétences est accessible à l'utilisateur :
    son propre périmètre (_secteurs_visibles, qui couvre déjà son propre
    secteur/service/navire — y compris via une section) UNION les secteurs où
    il est désigné référent d'au moins une formation (TrainingCourse.referents,
    système déjà livré — cf. training/models.py::peut_valider_formation), même
    si ce secteur est hors de son périmètre hiérarchique : un référent doit
    pouvoir suivre la progression des marins qu'il forme, quel que soit son
    propre rattachement — UNION, enfin, tous les secteurs du ou des navires
    dont il est référent formation désigné (ReferentFormationNavire), même
    logique appliquée à l'échelle du navire entier plutôt qu'à une formation
    précise."""
    ids_perimetre = _secteurs_visibles(user).values_list("id", flat=True)
    ids_navires_referes = ReferentFormationNavire.objects.filter(user=user).values_list("ship_id", flat=True)
    return (
        Sector.objects.filter(
            Q(pk__in=ids_perimetre)
            | Q(training_courses__referents=user)
            | Q(service__ship_id__in=ids_navires_referes)
        )
        .select_related("service", "service__ship")
        .order_by("service__ship__name", "service__name", "name")
        .distinct()
    )


class CompetencyTreeView(LoginRequiredMixin, View):
    """Arbre de compétences : formations d'un secteur disposées par niveau de
    profondeur (chaîne de prérequis), avec l'état de chacune pour le marin
    connecté (validé / disponible / verrouillé). Le calcul du graphe (niveaux,
    anti-cycle) porte sur l'ensemble des formations du secteur — les
    prérequis peuvent traverser les catégories — mais l'affichage regroupe
    les formations par catégorie (domaine métier) via regrouper_par_categorie.

    Secteurs proposés : le périmètre propre de l'utilisateur, plus les
    secteurs où il est référent d'une formation (cf. _secteurs_arbre_competences)
    — chaque marin voit ainsi toujours SON arbre, et un référent voit en plus
    les arbres des secteurs qu'il forme."""

    template_name = "training/arbre_competences.html"

    def get(self, request, *args, **kwargs):
        secteurs = _secteurs_arbre_competences(request.user)
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
