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

from matrix.core.roles import RoleLevel, user_role_level
from matrix.core.scopes import scope_filters_for_user, ship_id_for_user
from notifications.models import Notification
from org.models import Ship

from .models import (
    NIVEAU_SUPERVISION_GLOBALE_FORMATION,
    ReferentFormation,
    ReferentFormationNavire,
    TrainingCourse,
    TrainingRecord,
    TrainingSession,
    navire_de,
    peut_valider_formation,
)
from .services import calculer_carte_competences, regrouper_par_categorie

User = get_user_model()

# Seuil de rôle requis pour configurer les prérequis/catégorie/référents d'une
# formation, cohérent avec RolePermission.min_level_write (matrix/core/permissions.py)
# déjà appliqué côté API sur TrainingCourseViewSet.
NIVEAU_REQUIS_GESTION_PREREQUIS = RoleLevel.CHEF_SECTION

# Seuil de rôle requis pour créer une toute nouvelle formation : volontairement
# plus strict que NIVEAU_REQUIS_GESTION_PREREQUIS (qui ne fait qu'éditer une
# formation existante). Demande explicite du Product Owner : la création reste
# réservée à un administrateur pour l'instant, les centres de formation
# externes prendront le relais dans une phase future non spécifiée. Seuil
# INCHANGÉ par la portabilité des formations (tâche Notion « Formation unique
# et portable entre navires ») : une formation devenant une fiche globale
# partagée par tous les navires, la garder réservée à un administrateur reste
# tout aussi pertinent, sinon davantage.
NIVEAU_REQUIS_CREATION_FORMATION = RoleLevel.ADMIN_NAVIRE

# Seuil de rôle générique à partir duquel un marin peut valider n'importe
# quelle formation de son périmètre organisationnel, MÊME sans être désigné
# référent — même seuil que NIVEAU_REQUIS_GESTION_PREREQUIS. Ce seuil
# générique s'ajoute (sans le remplacer) au vrai contrôle d'accès défini par
# training.models.peut_valider_formation (référent de la formation précise
# POUR LE NAVIRE DU MARIN CIBLÉ, référent formation du navire, ou COMMANDANT+,
# déjà utilisé côté API par TrainingRecordPermission) : un marin de rang
# inférieur à ce seuil peut donc tout de même valider une formation précise
# dès lors qu'il en est désigné référent — cf. _est_referent_formation et
# ValiderFormationView ci-dessous.
NIVEAU_REQUIS_VALIDATION = RoleLevel.CHEF_SECTION


def _peut_gerer_prerequis(user):
    return user_role_level(user) >= NIVEAU_REQUIS_GESTION_PREREQUIS


def _peut_creer_formation(user):
    return user_role_level(user) >= NIVEAU_REQUIS_CREATION_FORMATION


def _peut_valider_formation(user):
    return user_role_level(user) >= NIVEAU_REQUIS_VALIDATION


def _est_referent_formation(user):
    """Vrai si l'utilisateur est désigné référent d'au moins une formation
    précise pour au moins un navire (ReferentFormation) ou référent formation
    d'un navire entier (ReferentFormationNavire) — cf.
    training.models.peut_valider_formation. Complète _peut_valider_formation
    ci-dessus (seuil générique CHEF_SECTION) pour un marin de rang inférieur
    (ex. EQUIPIER) désigné référent : sans ce contrôle, le bouton « Valider
    une formation » resterait invisible pour lui alors qu'il a bien
    l'autorité sur sa formation."""
    return (
        ReferentFormation.objects.filter(user=user).exists()
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


def _utilisateurs_du_navire_q(ship):
    """Filtre les utilisateurs dont le profil couvre le navire donné, quel que
    soit le niveau de périmètre auquel leur profil est réellement rattaché
    (navire, service, secteur, ou section d'un secteur de ce navire) —
    utilisée pour proposer les candidats référents d'UNE formation POUR CE
    NAVIRE (ReferentFormation) ainsi que les candidats au rôle de référent
    formation du navire entier (ReferentFormationNavire)."""
    return (
        Q(profile__ship_id=ship.id)
        | Q(profile__service__ship_id=ship.id)
        | Q(profile__sector__service__ship_id=ship.id)
        | Q(profile__section__sector__service__ship_id=ship.id)
    )


def filtres_perimetre_marin(user):
    """Calcule le filtre de périmètre applicable à User (via son profil).

    Un marin peut être rattaché à n'importe quel niveau de la hiérarchie
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


def _marins_validables(user):
    """Marins proposables dans la modale de validation : le périmètre
    organisationnel habituel (filtres_perimetre_marin) COMPLÉTÉ, pour un
    référent, des marins des navires où il est référent d'au moins une
    formation (ReferentFormation) et de ceux du navire dont il est référent
    formation entier (ReferentFormationNavire) — un référent peut ainsi
    valider des marins hors de son propre périmètre hiérarchique, dès lors
    que ce sont des marins des navires dont il a la charge."""
    marins = User.objects.filter(is_active=True).select_related("profile")
    q = filtres_perimetre_marin(user)
    if q is None:
        # Périmètre déjà illimité (supervision globale, COMMANDANT et
        # au-dessus) : tous les marins sont déjà proposés, inutile d'élargir.
        return marins.order_by("last_name", "first_name", "username")
    for navire in Ship.objects.filter(referents_formation__user=user).distinct():
        q |= _utilisateurs_du_navire_q(navire)
    for navire in Ship.objects.filter(referent_formation__user=user):
        q |= _utilisateurs_du_navire_q(navire)
    return marins.filter(q).distinct().order_by("last_name", "first_name", "username")


def _entier_ou_none(valeur):
    """Convertit une valeur postée en entier, ou renvoie None si elle est vide
    ou non numérique — évite un ValueError non attrapé (donc une erreur 500)
    quand un POST forgé envoie une valeur non numérique dans un champ
    normalement issu d'un <select> HTML (ex. identifiant de formation)."""
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
        qs = (
            TrainingCourse.objects.all()
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
        ctx["peut_gerer_prerequis"] = _peut_gerer_prerequis(self.request.user)
        ctx["peut_creer_formation"] = _peut_creer_formation(self.request.user)

        # Navire de référence de l'appelant (résolu quel que soit le niveau de
        # son profil, cf. navire_de) : sert à la fois au bloc référent
        # formation du navire ci-dessous ET à la gestion des référents PAR
        # FORMATION (ReferentFormation), désormais toujours scopée au navire
        # de la personne qui gère la page — un chef ne désigne des référents
        # que pour SON propre navire, jamais pour un autre.
        navire_courant = navire_de(self.request.user)
        ctx["navire_courant"] = navire_courant

        # Référent formation du navire (ReferentFormationNavire) : géré ici
        # pour le NAVIRE DE L'APPELANT uniquement (pas la flotte entière),
        # cohérent avec le principe "espace personnel par marin" — un
        # COMMANDANT+ ne gère que son propre bord.
        ctx["peut_gerer_referent_navire"] = _peut_gerer_referent_navire(self.request.user)
        if ctx["peut_gerer_referent_navire"] and navire_courant is not None:
            ctx["referent_formation_navire"] = ReferentFormationNavire.objects.filter(
                ship=navire_courant
            ).select_related("user").first()
            ctx["candidats_referent_navire"] = (
                User.objects.filter(_utilisateurs_du_navire_q(navire_courant), is_active=True)
                .select_related("profile")
                .order_by("last_name", "first_name", "username")
                .distinct()
            )

        # Candidats prérequis : catalogue global (toutes les formations),
        # l'exclusion de la formation elle-même étant faite côté client (JS,
        # cf. formations.html) puisqu'une seule liste sert à toutes les cartes.
        toutes_formations = list(TrainingCourse.objects.order_by("title"))
        ctx["candidats_prerequis"] = toutes_formations

        # Catégories déjà utilisées (toutes formations confondues) : sert à
        # l'autocomplétion du champ catégorie (datalist HTML natif) pour
        # limiter les doublons/fautes de frappe sans imposer de liste fermée,
        # et au filtre déroulant en tête de page.
        ctx["categories_existantes"] = sorted(
            {c for c in TrainingCourse.objects.exclude(category="").values_list("category", flat=True)}
        )

        # Candidats référents (ReferentFormation) : les utilisateurs visibles
        # sur le NAVIRE de l'appelant — un chef ne peut désigner de référent
        # que pour son propre navire (cf. navire_courant ci-dessus).
        candidats_referents = []
        if navire_courant is not None:
            candidats_referents = list(
                User.objects.filter(_utilisateurs_du_navire_q(navire_courant))
                .select_related("profile")
                .order_by("username")
                .distinct()
            )
        ctx["candidats_referents"] = candidats_referents

        # Référents déjà désignés, POUR LE NAVIRE DE L'APPELANT uniquement
        # (un autre navire peut avoir désigné d'autres référents pour la même
        # formation globale, non affichés ici) — regroupés par formation pour
        # un accès direct côté template.
        formations = list(ctx["formations"])
        referents_par_formation = defaultdict(list)
        if navire_courant is not None:
            referents_qs = ReferentFormation.objects.filter(
                course_id__in=[f.id for f in formations], ship=navire_courant
            ).select_related("user")
            for r in referents_qs:
                referents_par_formation[r.course_id].append(r.user)
        ctx["referents_par_formation"] = dict(referents_par_formation)

        # Sessions à venir (planifiées, pas encore passées) de chaque formation
        # affichée, avec la place restante et l'état de réservation du marin
        # connecté — réservation self-service (T-FORM), page la plus naturelle
        # pour ça puisque c'est déjà ici que le marin consulte ses formations.
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
            f.mes_referents = referents_par_formation.get(f.id, [])
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
            # Catalogue global : toutes les formations sont proposables dans
            # la modale de validation (l'autorité réelle est revalidée côté
            # serveur par ValiderFormationView, au regard du navire du marin
            # ciblé — cf. peut_valider_formation). Les marins proposés
            # respectent le périmètre organisationnel de l'appelant, élargi
            # pour un référent (cf. _marins_validables).
            ctx["marins"] = _marins_validables(self.request.user)
            ctx["formations_validables"] = toutes_formations
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
            course = TrainingCourse.objects.create(
                title=titre,
                description=request.POST.get("description", "").strip(),
                category=request.POST.get("category", "").strip(),
                validity_days=validity_days,
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
        if action == "update_prerequisites":
            if not _peut_gerer_prerequis(request.user):
                raise PermissionDenied
            pk = _entier_ou_none(request.POST.get("pk"))
            course = TrainingCourse.objects.filter(pk=pk).first() if pk is not None else None
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
        if action == "reserver_session":
            return self._reserver_session(request)
        if action == "annuler_reservation":
            return self._annuler_reservation(request)
        if action == "affecter_session":
            return self._affecter_session(request)
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
            messages.error(request, "Aucune unité rattachée à votre profil.")
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
            messages.error(request, "Marin introuvable dans votre unité.")
            return redirect("formation-list")
        ReferentFormationNavire.objects.update_or_create(ship=navire, defaults={"user": candidat})
        if candidat != request.user:
            Notification.objects.create(
                user=candidat,
                verb=f"Vous avez été désigné référent formation de l'unité {navire.name}.",
            )
        messages.success(
            request,
            f"{candidat.get_full_name() or candidat.username} est désormais référent formation de l'unité {navire.name}.",
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
        messages.success(request, "Référent formation de l'unité retiré.")
        return redirect("formation-list")

    def _reserver_session(self, request):
        """Réservation self-service d'une place sur une session PLANNED, par le
        marin connecté pour lui-même uniquement — distincte de la validation de
        présence par un référent (attendees, non touché ici). Les règles
        métier (session toujours planifiée, capacité, prérequis) sont
        appliquées par le signal m2m TrainingSession.reservations
        (training/models.py::_controler_reservation), seule source de vérité.
        Catalogue global : toute session planifiée est réservable, quel que
        soit le navire qui l'organise (une session peut par exemple être
        organisée par un autre bord ou un centre de formation à terre)."""
        session_id = _entier_ou_none(request.POST.get("session_id"))
        session = (
            TrainingSession.objects.select_related("course").filter(pk=session_id).first()
            if session_id is not None else None
        )
        if session is None:
            messages.error(request, "Session introuvable.")
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

    def _affecter_session(self, request):
        """Un référent réserve PROACTIVEMENT une place sur une session pour un
        marin (contrairement à _reserver_session ci-dessus, où c'est le marin
        qui réserve pour lui-même) — équivaut à une réservation self-service
        (TrainingSession.reservations, PAS attendees : la présence/réussite
        réelle reste constatée séparément le jour J, cf. ValiderFormationView).
        Autorisation identique à ValiderFormationView (peut_valider_formation,
        POUR LE NAVIRE DU MARIN CIBLÉ) : pas de nouveau seuil de permission,
        même contrôle que pour la validation d'une formation. Les règles
        métier (capacité, session planifiée, prérequis) sont appliquées par le
        même signal m2m que la réservation self-service
        (training/models.py::_controler_reservation), seule source de vérité,
        qui se déclenche ici aussi car l'ajout se fait toujours par le même
        ManyToManyField, quel que soit l'appelant."""
        session_id = _entier_ou_none(request.POST.get("session_id"))
        marin_id = _entier_ou_none(request.POST.get("marin_id"))
        session = (
            TrainingSession.objects.select_related("course").filter(pk=session_id).first()
            if session_id is not None else None
        )
        marin = (
            User.objects.filter(pk=marin_id, is_active=True).first()
            if marin_id is not None else None
        )
        if session is None or marin is None:
            messages.error(request, "Session ou marin introuvable.")
            return redirect("formation-list")

        # Autorisation : référent de cette formation précise POUR LE NAVIRE DU
        # MARIN CIBLÉ, référent formation de ce navire, ou COMMANDANT+ — même
        # contrôle que ValiderFormationView, réutilisé tel quel, complété par
        # le seuil générique CHEF_SECTION+ borné au périmètre organisationnel
        # de l'appelant sur le marin.
        navire_marin = navire_de(marin)
        autorise_par_referent = peut_valider_formation(request.user, session.course, navire_marin)
        if not autorise_par_referent and not _peut_valider_formation(request.user):
            raise PermissionDenied

        # Revalidation côté serveur du marin ciblé, même principe que
        # ValiderFormationView : empêche d'affecter un marin hors périmètre en
        # forgeant la requête POST.
        if autorise_par_referent:
            if not _marins_validables(request.user).filter(pk=marin.pk).exists():
                raise PermissionDenied
        else:
            q_perimetre_marin = filtres_perimetre_marin(request.user)
            if q_perimetre_marin is not None and not User.objects.filter(q_perimetre_marin, pk=marin.pk).exists():
                raise PermissionDenied

        if marin in session.reservations.all():
            messages.info(request, "Ce marin a déjà une place réservée sur cette session.")
            return redirect("formation-list")
        try:
            # Savepoint explicite, même principe que _reserver_session ci-dessus.
            with transaction.atomic():
                session.reservations.add(marin)
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
            course = TrainingCourse.objects.get(pk=course_id)
        except TrainingCourse.DoesNotExist:
            messages.error(request, "Formation introuvable.")
            return redirect("formation-list")

        # Autorisation réelle de validation, branchée sur le vrai contrôle
        # d'accès du modèle (training.models.peut_valider_formation, déjà
        # utilisé côté API par TrainingRecordPermission) : référent de cette
        # formation précise POUR LE NAVIRE DU MARIN CIBLÉ, référent formation
        # de ce navire, ou COMMANDANT+. COMPLÉTÉE (sans être remplacée) par le
        # seuil générique CHEF_SECTION+ historique du web, dans ce cas
        # toujours borné au périmètre organisationnel effectif de l'appelant
        # sur le MARIN (le catalogue de formations, désormais global, n'a
        # plus de périmètre propre à revalider).
        navire_marin = navire_de(marin)
        autorise_par_referent = peut_valider_formation(request.user, course, navire_marin)
        if not autorise_par_referent:
            if not _peut_valider_formation(request.user):
                raise PermissionDenied

        # Revalidation côté serveur du marin ciblé : empêche de valider une
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
        formations = list(
            TrainingCourse.objects.all().prefetch_related("prerequisites").order_by("title")
        )
        carte = calculer_carte_competences(formations, request.user)
        categories = regrouper_par_categorie(carte)
        return render(request, self.template_name, {"categories": categories})
