from collections import defaultdict
from datetime import date, datetime

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
    CandidatureFormation,
    DemandePlace,
    PersonnelBRH,
    PlaceAffectee,
    ReferentFormation,
    ReferentFormationNavire,
    TrainingCourse,
    TrainingRecord,
    TrainingSession,
    TrainingWaitlistEntry,
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

# Seuil de rôle générique à partir duquel un chef peut RÉSERVER (mais pas
# VALIDER) une place de session pour un marin de son propre périmètre
# organisationnel, sans être désigné référent de la formation précise — cf.
# _affecter_session ci-dessous, SEUL usage restant de ce seuil. Il ne
# s'applique PLUS ni à la validation elle-même (création d'un TrainingRecord,
# ValiderFormationView), ni à la visibilité du bouton « Valider une
# formation » : pour ces deux usages, ce seuil générique contournait à tort
# le vrai contrôle d'accès défini par training.models.peut_valider_formation
# (référent de la formation précise POUR LE NAVIRE DU MARIN CIBLÉ, référent
# formation du navire, ou COMMANDANT+, déjà utilisé côté API par
# TrainingRecordPermission) — faille corrigée (tâche Notion « Sécurité : la
# validation de formation contourne le contrôle par référent (seuil
# générique CHEF_SECTION+) »). Réserver une place ne certifie en rien qu'un
# marin a suivi/réussi la formation (seul ValiderFormationView crée un
# TrainingRecord) : le risque associé à ce seuil, pour ce seul usage restant,
# reste borné.
NIVEAU_REQUIS_VALIDATION = RoleLevel.CHEF_SECTION


def _peut_gerer_prerequis(user):
    return user_role_level(user) >= NIVEAU_REQUIS_GESTION_PREREQUIS


def _peut_creer_formation(user):
    return user_role_level(user) >= NIVEAU_REQUIS_CREATION_FORMATION


def _peut_valider_formation(user):
    """Seuil générique CHEF_SECTION+ — réservé à la RÉSERVATION proactive
    d'une place de session pour un marin (_affecter_session), PAS à la
    validation d'une formation elle-même (ValiderFormationView), qui ne doit
    reposer QUE sur le vrai contrôle d'accès par référent
    (training.models.peut_valider_formation, cf. NIVEAU_REQUIS_VALIDATION
    ci-dessus)."""
    return user_role_level(user) >= NIVEAU_REQUIS_VALIDATION


def _est_referent_formation(user):
    """Vrai si l'utilisateur est désigné référent d'au moins une formation
    précise pour au moins un navire (ReferentFormation) ou référent formation
    d'un navire entier (ReferentFormationNavire) — cf.
    training.models.peut_valider_formation. Complète le seuil de supervision
    globale (COMMANDANT+, NIVEAU_SUPERVISION_GLOBALE_FORMATION) pour un marin
    de rang inférieur (ex. EQUIPIER) désigné référent : sans ce contrôle, le
    bouton « Valider une formation » resterait invisible pour lui alors qu'il
    a bien l'autorité sur sa formation."""
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


# Seuil de rôle requis pour formuler/annuler une DemandePlace (Circuit A —
# demande et attribution de places à quota) pour son propre bord : même
# niveau que NIVEAU_REQUIS_VALIDATION, un chef de secteur étant déjà habilité
# à ce niveau à affecter des marins de son secteur sur une session
# (_affecter_session) — la demande de places n'est qu'une étape amont du même
# périmètre de responsabilité.
NIVEAU_REQUIS_DEMANDE_PLACES = RoleLevel.CHEF_SECTION


def _peut_demander_places(user):
    return user_role_level(user) >= NIVEAU_REQUIS_DEMANDE_PLACES


# Seuil de rôle requis pour valider une CandidatureFormation (Circuit B) en
# tant que hiérarchie du candidat : même niveau que NIVEAU_REQUIS_VALIDATION,
# TOUJOURS borné par filtres_perimetre_marin sur le marin candidat (cf.
# _peut_valider_candidature_hierarchie ci-dessous) — un chef de rang
# supérieur mais dont le marin candidat est hors périmètre reste refusé.
NIVEAU_REQUIS_VALIDATION_HIERARCHIE_CANDIDATURE = RoleLevel.CHEF_SECTION


def _peut_valider_candidature_hierarchie(user, marin):
    """Vrai si `user` peut valider/refuser, en tant que hiérarchie, la
    candidature individuelle (Circuit B) du `marin` donné : seuil générique
    CHEF_SECTION+ ET marin dans le périmètre organisationnel de l'appelant
    (filtres_perimetre_marin, même fonction que pour le Circuit A)."""
    if user_role_level(user) < NIVEAU_REQUIS_VALIDATION_HIERARCHIE_CANDIDATURE:
        return False
    q_perimetre = filtres_perimetre_marin(user)
    if q_perimetre is None:
        return True
    return User.objects.filter(q_perimetre, pk=marin.pk).exists()


def _peut_valider_candidature_brh(user, ship):
    """Vrai si `user` peut valider/refuser, en tant que BRH, une candidature
    individuelle (Circuit B) d'un marin rattaché au navire `ship` : désigné
    PersonnelBRH POUR CE NAVIRE, ou supervision globale (COMMANDANT+, même
    seuil que peut_valider_formation). `ship` est toujours celui du marin
    candidat (navire_de), jamais celui de l'appelant."""
    if user_role_level(user) >= NIVEAU_SUPERVISION_GLOBALE_FORMATION:
        return True
    if ship is None:
        return False
    return PersonnelBRH.objects.filter(ship=ship, user=user).exists()


# Seuil de rôle requis pour désigner/retirer un personnel BRH d'un navire
# (PersonnelBRH, training/models.py) : même niveau que la désignation du
# référent formation du navire (ReferentFormationNavire) — décision produit
# explicite, cf. tâche Notion « Circuit B — Candidature individuelle ».
NIVEAU_REQUIS_GESTION_BRH = NIVEAU_REQUIS_GESTION_REFERENT_NAVIRE


def _peut_gerer_brh(user):
    return user_role_level(user) >= NIVEAU_REQUIS_GESTION_BRH


# Seuil de rôle requis pour proposer la création ou la modification d'une
# formation « gérée par le bord » (Circuit C — Circuit d'approbation chef de
# secteur -> chef de service) : CHEF_SECTEUR+, à ne pas confondre avec
# NIVEAU_REQUIS_CREATION_FORMATION (ADMIN_NAVIRE+, INCHANGÉ) qui reste le seul
# seuil de création d'une formation « organisme » classique.
NIVEAU_REQUIS_PROPOSITION_FORMATION_BORD = RoleLevel.CHEF_SECTEUR


def _peut_proposer_formation_bord(user):
    return user_role_level(user) >= NIVEAU_REQUIS_PROPOSITION_FORMATION_BORD


# Seuil de rôle à partir duquel une proposition de formation « bord » est
# ACTIVE immédiatement, sans passer par l'état WAITING_VALIDATION (cf.
# training/models.py::TrainingCourse.statut_validation) : le proposeur est
# déjà au moins chef de service, son propre rôle vaut l'accord requis.
NIVEAU_REQUIS_VALIDATION_FORMATION_BORD = RoleLevel.CHEF_SERVICE


def peut_valider_proposition_bord(user, proposeur):
    """Vrai si `user` peut valider/refuser une formation « gérée par le bord »
    (Circuit C) proposée par `proposeur` : seuil générique CHEF_SERVICE+ ET
    proposeur dans le périmètre organisationnel de l'appelant
    (filtres_perimetre_marin, même principe que
    _peut_valider_candidature_hierarchie pour le Circuit B ci-dessous,
    appliqué ici au CHEF_SECTEUR proposeur plutôt qu'à un marin candidat) —
    ou supervision globale (COMMANDANT+, même seuil que peut_valider_formation).

    Nom public (sans préfixe `_`) car réutilisée telle quelle par
    training/views.py (API REST) pour filtrer le queryset de
    TrainingCourseViewSet — une formation WAITING_VALIDATION/REFUSED ne doit
    être visible, via l'API comme via le web, qu'à son proposeur et à ses
    validateurs compétents (cf. commentaire Tech Lead, tâche Notion Circuit C)."""
    if user_role_level(user) >= NIVEAU_SUPERVISION_GLOBALE_FORMATION:
        return True
    if user_role_level(user) < NIVEAU_REQUIS_VALIDATION_FORMATION_BORD:
        return False
    if proposeur is None:
        return False
    q_perimetre = filtres_perimetre_marin(user)
    if q_perimetre is None:
        return True
    return User.objects.filter(q_perimetre, pk=proposeur.pk).exists()


def peut_modifier_formation_bord(user, course):
    """Vrai si `user` peut modifier CETTE formation « bord » précise, déjà
    existante (édition via _proposer_formation_bord, `pk` fourni dans le
    POST) : le proposeur d'origine lui-même (course.updated_by — jamais
    réécrit par la validation/le refus, cf. _valider_formation_bord et
    _refuser_formation_bord qui ne touchent que statut_validation), un autre
    marin dont le périmètre organisationnel couvre ce proposeur d'origine
    (filtres_perimetre_marin, même principe que peut_valider_proposition_bord
    ci-dessus), ou la supervision globale (COMMANDANT+).

    Sans ce contrôle, un chef de secteur d'un AUTRE navire pourrait modifier
    — donc faire disparaître le temps de la revalidation, du catalogue
    général comme des prérequis et de l'arbre de compétences — une formation
    bord hors de son périmètre (faille signalée par le Tech Lead, tâche
    Notion Circuit C).

    Nom public (sans préfixe `_`, comme peut_valider_proposition_bord
    ci-dessus) car réutilisée telle quelle par training/views.py (API REST) :
    le premier refus du Tech Lead portait sur la visibilité en lecture,
    le second sur l'écriture (PATCH) — cette fonction couvre désormais les
    deux entrées (web ET API) au même périmètre, sans dupliquer la règle."""
    if user_role_level(user) >= NIVEAU_SUPERVISION_GLOBALE_FORMATION:
        return True
    proposeur_origine = course.updated_by
    if proposeur_origine is None:
        return False
    if user.pk == proposeur_origine.pk:
        return True
    q_perimetre = filtres_perimetre_marin(user)
    if q_perimetre is None:
        return True
    return User.objects.filter(q_perimetre, pk=proposeur_origine.pk).exists()


def formation_bord_en_service(course):
    """Vrai si une formation « bord » déjà ACTIVE est réellement utilisée en
    production : au moins une validation enregistrée (TrainingRecord), une
    session liée (TrainingSession), ou un rôle de prérequis pour une autre
    formation (`unlocks`, related_name de TrainingCourse.prerequisites).

    Dans ce cas, une modification en place (via _proposer_formation_bord côté
    web OU via un PATCH/PUT côté API REST, cf. training/views.py) est
    refusée : la formation redeviendrait invisible du catalogue général, des
    prérequis et de l'arbre de compétences pour TOUS les navires l'ayant déjà
    validée, le temps de la revalidation — sans rollback possible (faille
    signalée par le Tech Lead, tâche Notion Circuit C). Une modification
    substantielle d'une formation déjà utilisée doit alors passer par une
    NOUVELLE formation proposée, pas par une mutation en place d'une fiche
    dont d'autres dépendent déjà.

    Nom public (sans préfixe `_`) pour la même raison que
    peut_modifier_formation_bord ci-dessus."""
    return course.records.exists() or course.sessions.exists() or course.unlocks.exists()


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


def _marins_perimetre_demandeur(user):
    """Marins proposables pour l'affectation des places attribuées d'une
    DemandePlace : périmètre organisationnel habituel du demandeur
    (filtres_perimetre_marin), identique à celui revalidé côté serveur dans
    _affecter_place_demandee — contrairement à _marins_validables ci-dessus,
    pas d'élargissement aux navires où le demandeur serait référent : une
    DemandePlace ne s'affecte qu'à des marins de son PROPRE secteur."""
    marins = User.objects.filter(is_active=True).select_related("profile")
    q = filtres_perimetre_marin(user)
    if q is None:
        return marins.order_by("last_name", "first_name", "username")
    return marins.filter(q).order_by("last_name", "first_name", "username")


def _marins_perimetre_hierarchie(user):
    """Marins dont une candidature individuelle (Circuit B) est validable par
    `user` en tant que hiérarchie : périmètre organisationnel habituel
    (filtres_perimetre_marin), même principe que _marins_perimetre_demandeur
    ci-dessus — utilisé pour restreindre, côté requête, les candidatures
    proposées à un chef sans devoir tester marin par marin en Python."""
    marins = User.objects.filter(is_active=True)
    q = filtres_perimetre_marin(user)
    if q is None:
        return marins
    return marins.filter(q)


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


def _parse_datetime_local(date_str):
    """Convertit la valeur d'un champ <input type="datetime-local"> en
    date/heure « aware », en tenant compte du fuseau horaire local du bord —
    même principe que calendar_app/views.py::_parse_personal_event_datetime,
    réutilisé ici pour la création d'une nouvelle TrainingSession à
    l'attribution d'une DemandePlace (peut lever ValueError si la chaîne
    postée n'est pas une date/heure valide, laissé à l'appelant à attraper)."""
    naive_dt = datetime.fromisoformat(date_str)
    if timezone.is_aware(naive_dt):
        return naive_dt
    return timezone.make_aware(naive_dt)


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
        # Catalogue affiché = uniquement les formations ACTIVE (Circuit C —
        # Circuit d'approbation chef de secteur -> chef de service) : une
        # formation « gérée par le bord » proposée/modifiée par un chef de
        # secteur, tant qu'elle est en attente de validation ou refusée,
        # reste invisible ici pour tout le monde — elle n'apparaît que dans
        # les sections dédiées « Mes propositions » / « À valider » ci-dessous
        # (cf. get_context_data), jamais dans le catalogue général.
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

        # Personnels BRH du navire (Circuit B — Candidature individuelle) :
        # géré ici pour le NAVIRE DE L'APPELANT uniquement, même principe que
        # le référent formation du navire ci-dessus, mais PLUSIEURS personnes
        # possibles par navire (PersonnelBRH, FK simple répétable).
        ctx["peut_gerer_brh"] = _peut_gerer_brh(self.request.user)
        if ctx["peut_gerer_brh"] and navire_courant is not None:
            ctx["personnels_brh"] = list(
                PersonnelBRH.objects.filter(ship=navire_courant).select_related("user")
            )
            ctx["candidats_brh"] = (
                User.objects.filter(_utilisateurs_du_navire_q(navire_courant), is_active=True)
                .select_related("profile")
                .order_by("last_name", "first_name", "username")
                .distinct()
            )

        # Candidats prérequis : catalogue global des formations ACTIVE
        # uniquement (une formation « bord » en attente de validation ou
        # refusée ne peut pas encore servir de prérequis à une autre, cf.
        # Circuit C), l'exclusion de la formation elle-même étant faite côté
        # client (JS, cf. formations.html) puisqu'une seule liste sert à
        # toutes les cartes.
        toutes_formations = list(TrainingCourse.objects.filter(statut_validation="ACTIVE").order_by("title"))
        ctx["candidats_prerequis"] = toutes_formations

        # Catégories déjà utilisées (formations ACTIVE uniquement) : sert à
        # l'autocomplétion du champ catégorie (datalist HTML natif) pour
        # limiter les doublons/fautes de frappe sans imposer de liste fermée,
        # et au filtre déroulant en tête de page.
        ctx["categories_existantes"] = sorted({
            c for c in TrainingCourse.objects.filter(statut_validation="ACTIVE")
            .exclude(category="").values_list("category", flat=True)
        })

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
            .prefetch_related("reservations", "liste_attente")
            .order_by("scheduled_at")
        )
        sessions_par_formation = defaultdict(list)
        for s in sessions_qs:
            s.deja_reserve = self.request.user in s.reservations.all()
            # Liste d'attente (T-ATTENTE) : entrées déjà triées FIFO par le
            # prefetch (Meta.ordering de TrainingWaitlistEntry = created_at),
            # aucune requête supplémentaire par session.
            entrees_attente = list(s.liste_attente.all())
            s.nb_en_attente = len(entrees_attente)
            s.mon_entree_attente = next(
                (e for e in entrees_attente if e.user_id == self.request.user.id), None
            )
            s.ma_position_attente = (
                entrees_attente.index(s.mon_entree_attente) + 1 if s.mon_entree_attente else None
            )
            sessions_par_formation[s.course_id].append(s)
        # Suivi des validations (T-FORM) : compteurs à jour/expirées et
        # dernières validations par formation, affichés directement sur
        # chaque carte sans navigation supplémentaire.
        aujourdhui = timezone.localdate()
        # Circuit B — Candidature individuelle : la candidature la PLUS
        # RÉCENTE du marin connecté pour chaque formation, affichée sur la
        # carte à la place du bouton « Candidater » tant qu'elle est active
        # (cf. _candidater_formation, qui bloque un nouveau dépôt tant que la
        # précédente n'est pas allée à son terme). Le queryset est trié du
        # plus récent au plus ancien (Meta.ordering de CandidatureFormation) :
        # setdefault garde la PREMIÈRE occurrence rencontrée par formation,
        # donc la plus récente, plutôt que la dernière (ce que ferait un
        # simple dict comprehension, qui écraserait avec la plus ancienne).
        mes_candidatures_par_course = {}
        for c in CandidatureFormation.objects.filter(marin=self.request.user).select_related("course"):
            mes_candidatures_par_course.setdefault(c.course_id, c)
        for f in formations:
            f.sessions_a_venir = sessions_par_formation.get(f.id, [])
            f.mes_referents = referents_par_formation.get(f.id, [])
            f.ma_candidature = mes_candidatures_par_course.get(f.id)
            records = list(f.records.all())
            f.nb_a_jour = sum(1 for r in records if r.expires_at >= aujourdhui)
            f.nb_expires = sum(1 for r in records if r.expires_at < aujourdhui)
            f.dernieres_validations = sorted(records, key=lambda r: r.completed_at, reverse=True)[:5]
        ctx["formations"] = formations

        # Peut valider une formation : rôle de supervision globale
        # (COMMANDANT+, comme training.models.peut_valider_formation) OU
        # statut de référent (formation précise ou navire entier) — SANS le
        # seuil générique CHEF_SECTION+ historique, qui autorisait à tort
        # tout chef de section (et au-dessus) à valider n'importe quelle
        # formation de son périmètre sans en être désigné référent (faille
        # corrigée, tâche Notion « Sécurité : la validation de formation
        # contourne le contrôle par référent »). Un référent de rang
        # inférieur (ex. EQUIPIER) voit quand même le bouton, cf.
        # _est_referent_formation.
        peut_valider = (
            user_role_level(self.request.user) >= NIVEAU_SUPERVISION_GLOBALE_FORMATION
            or _est_referent_formation(self.request.user)
        )
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

        # Circuit A — Demande et attribution de places (T-FORM demande de
        # places) : un chef de secteur (CHEF_SECTION+) peut formuler une
        # demande pour son propre bord (navire_courant, résolu ci-dessus).
        ctx["peut_demander_places"] = _peut_demander_places(self.request.user) and navire_courant is not None
        if ctx["peut_demander_places"]:
            ctx["mes_demandes_places"] = list(
                DemandePlace.objects.filter(created_by=self.request.user)
                .select_related("course", "session")
                .order_by("-created_at")
            )
            # Marins proposables pour l'affectation des places attribuées :
            # même périmètre organisationnel que celui revalidé côté serveur
            # dans _affecter_place_demandee.
            ctx["marins_demande"] = _marins_perimetre_demandeur(self.request.user)

        # Demandes à traiter par l'organisme de formation (référent de la
        # formation POUR SON PROPRE NAVIRE, ou supervision globale) : même
        # autorisation que l'attribution/le refus (peut_valider_formation).
        demandes_en_attente = list(
            DemandePlace.objects.filter(statut="REQUESTED").select_related("course", "ship")
        )
        demandes_a_traiter = [
            d for d in demandes_en_attente
            if peut_valider_formation(self.request.user, d.course, navire_courant)
        ]
        for d in demandes_a_traiter:
            d.sessions_disponibles = list(
                TrainingSession.objects.filter(course=d.course, status="PLANNED").order_by("scheduled_at")
            )
        ctx["demandes_a_traiter"] = demandes_a_traiter

        # Circuit B — Candidature individuelle : trois files de traitement
        # distinctes, une par niveau de validation (hiérarchie, BRH,
        # organisme), chacune filtrée selon l'autorité réelle de l'appelant
        # (même principe que demandes_a_traiter ci-dessus pour le Circuit A).
        if user_role_level(self.request.user) >= NIVEAU_REQUIS_VALIDATION_HIERARCHIE_CANDIDATURE:
            marins_perimetre_ids = _marins_perimetre_hierarchie(self.request.user).values_list("pk", flat=True)
            ctx["candidatures_hierarchie_a_traiter"] = list(
                CandidatureFormation.objects.filter(
                    statut="PENDING_APPROVAL",
                    hierarchie_validee_par__isnull=True,
                    marin_id__in=marins_perimetre_ids,
                ).select_related("course", "marin", "marin__profile")
            )
        else:
            ctx["candidatures_hierarchie_a_traiter"] = []

        candidatures_brh_en_attente = list(
            CandidatureFormation.objects.filter(
                statut="PENDING_APPROVAL", brh_validee_par__isnull=True,
            ).select_related("course", "marin", "marin__profile")
        )
        ctx["candidatures_brh_a_traiter"] = [
            c for c in candidatures_brh_en_attente
            if _peut_valider_candidature_brh(self.request.user, navire_de(c.marin))
        ]

        # Autorisation calquée sur le Circuit A (demandes_a_traiter
        # ci-dessus) : navire de référence = celui de L'ORGANISME (l'appelant
        # lui-même, navire_courant, résolu plus haut), PAS celui de chaque
        # marin candidat — un référent d'école traite les candidatures reçues
        # par son propre établissement, quel que soit le bord d'origine du
        # candidat.
        candidatures_transmises = list(
            CandidatureFormation.objects.filter(statut="TRANSMITTED")
            .select_related("course", "marin", "marin__profile")
        )
        ctx["candidatures_organisme_a_traiter"] = [
            c for c in candidatures_transmises
            if peut_valider_formation(self.request.user, c.course, navire_courant)
        ]

        # Circuit C — Circuit d'approbation chef de secteur -> chef de service
        # (formations « gérées par le bord ») : un chef de secteur propose,
        # invisible du catalogue général (get_queryset) tant qu'un chef de
        # service de son périmètre (ou supervision globale) ne l'a pas
        # validée — même pattern d'état explicite que WAITING_VALIDATION sur
        # les occurrences de maintenance (maintenance/models.py).
        ctx["peut_proposer_formation_bord"] = _peut_proposer_formation_bord(self.request.user)
        if ctx["peut_proposer_formation_bord"]:
            # Mes propres propositions (création ou modification), qu'elles
            # soient encore en attente ou déjà refusées : permet au chef de
            # secteur de suivre l'état de ce qu'il a soumis, et de reprendre
            # une proposition refusée pour la corriger et la soumettre à
            # nouveau (cf. _proposer_formation_bord).
            ctx["mes_propositions_bord"] = list(
                TrainingCourse.objects.filter(
                    gere_par_le_bord=True,
                    updated_by=self.request.user,
                    statut_validation__in=["WAITING_VALIDATION", "REFUSED"],
                ).order_by("-updated_at")
            )
        # Propositions à valider par l'appelant (CHEF_SERVICE+ du périmètre du
        # proposeur, ou supervision globale) : même principe que
        # candidatures_brh_a_traiter ci-dessus, filtrage Python sur l'autorité
        # réelle après un premier filtre côté requête sur le statut.
        propositions_en_attente = list(
            TrainingCourse.objects.filter(
                gere_par_le_bord=True, statut_validation="WAITING_VALIDATION",
            ).select_related("updated_by")
        )
        ctx["formations_bord_a_valider"] = [
            c for c in propositions_en_attente
            if peut_valider_proposition_bord(self.request.user, c.updated_by)
        ]

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
                bareme=request.FILES.get("bareme"),
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
        if action == "reserver_session":
            return self._reserver_session(request)
        if action == "annuler_reservation":
            return self._annuler_reservation(request)
        if action == "quitter_liste_attente":
            return self._quitter_liste_attente(request)
        if action == "affecter_session":
            return self._affecter_session(request)
        if action == "demander_places":
            return self._demander_places(request)
        if action == "annuler_demande_place":
            return self._annuler_demande_place(request)
        if action == "attribuer_places":
            return self._attribuer_places(request)
        if action == "refuser_demande_place":
            return self._refuser_demande_place(request)
        if action == "affecter_place_demandee":
            return self._affecter_place_demandee(request)
        if action == "set_referent_navire":
            return self._set_referent_navire(request)
        if action == "retirer_referent_navire":
            return self._retirer_referent_navire(request)
        if action == "set_brh":
            return self._set_brh(request)
        if action == "retirer_brh":
            return self._retirer_brh(request)
        if action == "candidater_formation":
            return self._candidater_formation(request)
        if action == "valider_candidature_hierarchie":
            return self._valider_candidature_hierarchie(request)
        if action == "refuser_candidature_hierarchie":
            return self._refuser_candidature_hierarchie(request)
        if action == "valider_candidature_brh":
            return self._valider_candidature_brh(request)
        if action == "refuser_candidature_brh":
            return self._refuser_candidature_brh(request)
        if action == "selectionner_candidature":
            return self._selectionner_candidature(request)
        if action == "refuser_candidature_organisme":
            return self._refuser_candidature_organisme(request)
        if action == "proposer_formation_bord":
            return self._proposer_formation_bord(request)
        if action == "valider_formation_bord":
            return self._valider_formation_bord(request)
        if action == "refuser_formation_bord":
            return self._refuser_formation_bord(request)
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

    def _set_brh(self, request):
        """Désigne un personnel BRH supplémentaire pour le navire de
        l'appelant (Circuit B — Candidature individuelle) : PLUSIEURS
        personnes BRH sont possibles pour un même navire, contrairement au
        référent formation du navire ci-dessus (ReferentFormationNavire,
        unique)."""
        if not _peut_gerer_brh(request.user):
            raise PermissionDenied
        ship_id = ship_id_for_user(request.user)
        navire = Ship.objects.filter(pk=ship_id).first() if ship_id else None
        if navire is None:
            messages.error(request, "Aucune unité rattachée à votre profil.")
            return redirect("formation-list")
        # Ne fait pas confiance au formulaire : seuls les utilisateurs
        # visibles sur ce navire peuvent être désignés (même principe que
        # _set_referent_navire ci-dessus).
        candidat_id = _entier_ou_none(request.POST.get("brh_id"))
        candidat = (
            User.objects.filter(_utilisateurs_du_navire_q(navire), pk=candidat_id).first()
            if candidat_id is not None else None
        )
        if candidat is None:
            messages.error(request, "Marin introuvable dans votre unité.")
            return redirect("formation-list")
        _, cree = PersonnelBRH.objects.get_or_create(ship=navire, user=candidat)
        if not cree:
            messages.info(
                request,
                f"{candidat.get_full_name() or candidat.username} est déjà personnel BRH de l'unité {navire.name}.",
            )
            return redirect("formation-list")
        if candidat != request.user:
            Notification.objects.create(
                user=candidat,
                verb=f"Vous avez été désigné personnel BRH de l'unité {navire.name}.",
            )
        messages.success(
            request,
            f"{candidat.get_full_name() or candidat.username} est désormais personnel BRH de l'unité {navire.name}.",
        )
        return redirect("formation-list")

    def _retirer_brh(self, request):
        """Retire un personnel BRH précis (parmi plusieurs possibles) du
        navire de l'appelant."""
        if not _peut_gerer_brh(request.user):
            raise PermissionDenied
        brh_id = _entier_ou_none(request.POST.get("brh_id"))
        ship_id = ship_id_for_user(request.user)
        if brh_id is not None and ship_id:
            PersonnelBRH.objects.filter(pk=brh_id, ship_id=ship_id).delete()
        messages.success(request, "Personnel BRH retiré.")
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
        organisée par un autre bord ou un centre de formation à terre).

        Liste d'attente (T-ATTENTE) : si la session est déjà complète au
        moment de la tentative, le marin est mis en fin de file FIFO
        (TrainingSession.inscrire_liste_attente) plutôt que simplement
        refusé — il sera notifié dès qu'une place se libère, à lui de la
        réserver lui-même (pas d'inscription automatique). Le contrôle de
        capacité est donc fait AVANT celui d'une éventuelle entrée en liste
        d'attente déjà existante : un marin notifié qu'une place s'est
        libérée doit pouvoir la réserver normalement, même s'il figure
        encore dans la file (son entrée est retirée automatiquement, cf.
        training/models.py::_controler_reservation, action post_add)."""
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
        if session.capacite_max is not None and session.places_restantes() == 0:
            if TrainingWaitlistEntry.objects.filter(session=session, user=request.user).exists():
                messages.info(request, "Vous êtes déjà en liste d'attente pour cette session.")
                return redirect("formation-list")
            try:
                entree = session.inscrire_liste_attente(request.user)
            except ValidationError as exc:
                _afficher_erreur_prerequis(request, exc)
                return redirect("formation-list")
            messages.success(
                request,
                f"Session complète : vous êtes en position {entree.position()} sur la liste "
                "d'attente. Vous serez prévenu dès qu'une place se libère.",
            )
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
        TrainingSession.reservations, cf. training/models.py::_controler_reservation).
        La notification au premier de la liste d'attente (s'il y en a une) est
        déclenchée automatiquement par ce même signal (action post_remove),
        pas ici : seule source de vérité, quel que soit l'appelant."""
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

    def _quitter_liste_attente(self, request):
        """Retrait volontaire de SA PROPRE entrée en liste d'attente, sans
        attendre qu'une place ne se libère — aucune règle métier
        supplémentaire à appliquer (contrairement à l'annulation d'une
        réservation ferme), l'entrée est simplement supprimée."""
        session_id = _entier_ou_none(request.POST.get("session_id"))
        supprimees, _ = TrainingWaitlistEntry.objects.filter(
            session_id=session_id, user=request.user
        ).delete()
        if supprimees:
            messages.success(request, "Vous avez quitté la liste d'attente.")
        else:
            messages.info(request, "Vous n'êtes pas en liste d'attente pour cette session.")
        return redirect("formation-list")

    def _affecter_session(self, request):
        """Un référent réserve PROACTIVEMENT une place sur une session pour un
        marin (contrairement à _reserver_session ci-dessus, où c'est le marin
        qui réserve pour lui-même) — équivaut à une réservation self-service
        (TrainingSession.reservations, PAS attendees : la présence/réussite
        réelle reste constatée séparément le jour J, cf. ValiderFormationView).
        Autorisation branchée sur le même contrôle par référent que
        ValiderFormationView (peut_valider_formation, POUR LE NAVIRE DU MARIN
        CIBLÉ), MAIS complétée ici par le seuil générique CHEF_SECTION+
        (borné au périmètre organisationnel de l'appelant sur le marin, cf.
        ci-dessous) — DEPUIS LA CORRECTION DE LA FAILLE sur ValiderFormationView
        (tâche Notion « Sécurité : la validation de formation contourne le
        contrôle par référent »), ce n'est PLUS le même contrôle : réserver
        une place ne certifie en rien que le marin a suivi/réussi la
        formation (seul ValiderFormationView crée un TrainingRecord), donc un
        chef peut toujours planifier une session pour un marin de son propre
        périmètre sans en être désigné référent — risque bien moindre que
        celui corrigé sur la validation elle-même. Les règles métier
        (capacité, session planifiée, prérequis) sont appliquées par le même
        signal m2m que la réservation self-service
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
        # MARIN CIBLÉ, référent formation de ce navire, ou COMMANDANT+ (même
        # fonction que ValiderFormationView, réutilisée telle quelle) —
        # COMPLÉTÉE ICI (contrairement à ValiderFormationView depuis le
        # correctif de sécurité ci-dessus) par le seuil générique
        # CHEF_SECTION+ borné au périmètre organisationnel de l'appelant sur
        # le marin : réserver une place ne valide rien, cf. docstring de
        # cette méthode.
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

    def _demander_places(self, request):
        """Circuit A (T-FORM demande de places) — un chef de secteur formule
        une demande de places sur une formation à quota, pour SON BORD. Le
        navire de la demande est TOUJOURS celui résolu de l'appelant
        (navire_de, jamais un identifiant posté) : impossible de demander des
        places au nom d'un autre bord en forgeant la requête."""
        if not _peut_demander_places(request.user):
            raise PermissionDenied
        navire = navire_de(request.user)
        if navire is None:
            messages.error(request, "Aucune unité rattachée à votre profil.")
            return redirect("formation-list")
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
        nb = _entier_ou_none(request.POST.get("nb_places_demandees"))
        if not nb or nb <= 0:
            messages.error(request, "Le nombre de places demandées doit être un nombre positif.")
            return redirect("formation-list")
        DemandePlace.objects.create(
            course=course, ship=navire, nb_places_demandees=nb, created_by=request.user,
        )
        messages.success(request, f"Demande de {nb} place(s) envoyée pour « {course.title} ».")
        return redirect("formation-list")

    def _annuler_demande_place(self, request):
        """Annulation par le demandeur (created_by) de SA PROPRE demande,
        uniquement tant qu'elle n'a pas encore été traitée par l'organisme."""
        demande_id = _entier_ou_none(request.POST.get("demande_id"))
        demande = DemandePlace.objects.filter(pk=demande_id).first() if demande_id is not None else None
        if demande is None:
            messages.error(request, "Demande introuvable.")
            return redirect("formation-list")
        if demande.created_by_id != request.user.id:
            raise PermissionDenied
        if demande.statut != "REQUESTED":
            messages.info(request, "Cette demande n'est plus annulable.")
            return redirect("formation-list")
        demande.statut = "CANCELLED"
        demande.save(update_fields=["statut"])
        messages.success(request, "Demande annulée.")
        return redirect("formation-list")

    def _attribuer_places(self, request):
        """Réponse de l'organisme de formation (référent de cette formation
        POUR SON PROPRE NAVIRE — l'école/centre de formation, cf.
        peut_valider_formation, réutilisé tel quel) à une DemandePlace :
        renseigne le nombre de places attribuées et relie une TrainingSession
        (existante, choisie parmi les sessions de la même formation, ou
        nouvellement créée), puis passe le statut à GRANTED."""
        demande_id = _entier_ou_none(request.POST.get("demande_id"))
        demande = (
            DemandePlace.objects.select_related("course", "ship").filter(pk=demande_id).first()
            if demande_id is not None else None
        )
        if demande is None:
            messages.error(request, "Demande introuvable.")
            return redirect("formation-list")
        # Revalidation du statut de la formation (correctif QA — Circuit C) :
        # une formation « bord » peut être revalidée/refusée entre la
        # DEMANDE (toujours ACTIVE à l'origine, cf. _demander_places) et
        # cette ATTRIBUTION — tant qu'aucune session ne lui est encore
        # rattachée, formation_bord_en_service ne bloque pas sa réédition.
        # Ne jamais attribuer de place sur une formation qui n'est plus (ou
        # pas encore) ACTIVE.
        if demande.course.statut_validation != "ACTIVE":
            messages.error(request, "Formation introuvable.")
            return redirect("formation-list")

        navire_organisme = navire_de(request.user)
        if not peut_valider_formation(request.user, demande.course, navire_organisme):
            raise PermissionDenied

        nb = _entier_ou_none(request.POST.get("nb_places_attribuees"))
        if not nb or nb <= 0:
            messages.error(request, "Le nombre de places attribuées doit être un nombre positif.")
            return redirect("formation-list")

        session_id = _entier_ou_none(request.POST.get("session_id"))
        session = None
        if session_id is not None:
            # Ne fait pas confiance au formulaire : la session choisie doit
            # bien concerner la formation de cette demande.
            session = TrainingSession.objects.filter(pk=session_id, course=demande.course).first()
            if session is None:
                messages.error(request, "Session introuvable pour cette formation.")
                return redirect("formation-list")
        else:
            nouvelle_date = request.POST.get("nouvelle_session_date", "").strip()
            if nouvelle_date:
                try:
                    scheduled_at = _parse_datetime_local(nouvelle_date)
                except ValueError:
                    messages.error(request, "Date de session invalide.")
                    return redirect("formation-list")
                capacite_brut = request.POST.get("nouvelle_session_capacite", "").strip()
                session = TrainingSession.objects.create(
                    course=demande.course,
                    scheduled_at=scheduled_at,
                    location=request.POST.get("nouvelle_session_lieu", "").strip(),
                    capacite_max=_entier_ou_none(capacite_brut) if capacite_brut else None,
                )

        demande.nb_places_attribuees = nb
        demande.session = session
        demande.statut = "GRANTED"
        demande.attribue_par = request.user
        demande.date_attribution = timezone.now()
        demande.save(update_fields=[
            "nb_places_attribuees", "session", "statut", "attribue_par", "date_attribution",
        ])

        if demande.created_by_id:
            Notification.objects.create(
                user_id=demande.created_by_id,
                verb=(
                    f"Demande de places accordée : {nb} place(s) pour « {demande.course.title} » "
                    f"({demande.ship.name})."
                ),
            )
        messages.success(request, f"{nb} place(s) attribuée(s) pour « {demande.course.title} ».")
        return redirect("formation-list")

    def _refuser_demande_place(self, request):
        """Refus d'une demande par l'organisme de formation (même autorisation
        que l'attribution, cf. _attribuer_places)."""
        demande_id = _entier_ou_none(request.POST.get("demande_id"))
        demande = (
            DemandePlace.objects.select_related("course", "ship").filter(pk=demande_id).first()
            if demande_id is not None else None
        )
        if demande is None:
            messages.error(request, "Demande introuvable.")
            return redirect("formation-list")
        navire_organisme = navire_de(request.user)
        if not peut_valider_formation(request.user, demande.course, navire_organisme):
            raise PermissionDenied
        demande.statut = "REFUSED"
        demande.attribue_par = request.user
        demande.date_attribution = timezone.now()
        demande.save(update_fields=["statut", "attribue_par", "date_attribution"])
        if demande.created_by_id:
            Notification.objects.create(
                user_id=demande.created_by_id,
                verb=f"Demande de places refusée pour « {demande.course.title} » ({demande.ship.name}).",
            )
        messages.success(request, "Demande refusée.")
        return redirect("formation-list")

    def _affecter_place_demandee(self, request):
        """Affecte un marin sur une place ATTRIBUÉE d'une DemandePlace précise
        : seul le chef de secteur demandeur (created_by de la demande) peut
        affecter, uniquement des marins de son propre périmètre
        organisationnel (filtres_perimetre_marin, même périmètre que le
        chef non-référent dans _affecter_session), et seulement dans la
        limite du quota attribué à SA demande.

        Double contrôle de quota (point métier clé — plusieurs bords peuvent
        partager la même session, chacun avec son propre quota) : le plafond
        attribué à CETTE demande précise (PlaceAffectee.objects.filter(...).count(),
        compté par bord) est contrôlé ICI, EN PLUS du plafond physique global
        de la session déjà appliqué par le signal m2m existant
        (training/models.py::_controler_reservation, non dupliqué)."""
        demande_id = _entier_ou_none(request.POST.get("demande_id"))
        marin_id = _entier_ou_none(request.POST.get("marin_id"))
        demande = (
            DemandePlace.objects.select_related("course", "session").filter(pk=demande_id).first()
            if demande_id is not None else None
        )
        marin = User.objects.filter(pk=marin_id, is_active=True).first() if marin_id is not None else None
        if demande is None or marin is None:
            messages.error(request, "Demande ou marin introuvable.")
            return redirect("formation-list")

        if demande.created_by_id != request.user.id:
            raise PermissionDenied
        if demande.statut != "GRANTED" or demande.session_id is None:
            messages.error(
                request,
                "Cette demande n'a pas encore de places attribuées et reliées à une session.",
            )
            return redirect("formation-list")

        # Revalidation côté serveur du marin ciblé : ne fait pas confiance au
        # formulaire, même principe que _affecter_session.
        q_perimetre_marin = filtres_perimetre_marin(request.user)
        if q_perimetre_marin is not None and not User.objects.filter(q_perimetre_marin, pk=marin.pk).exists():
            raise PermissionDenied

        if demande.nb_places_attribuees is not None and demande.places_consommees() >= demande.nb_places_attribuees:
            messages.error(request, "Le quota de places attribuées à votre unité pour cette demande est atteint.")
            return redirect("formation-list")

        session = demande.session
        if marin in session.reservations.all():
            messages.info(request, "Ce marin a déjà une place réservée sur cette session.")
            return redirect("formation-list")
        try:
            # Savepoint explicite, même principe que _reserver_session : la
            # réservation globale (m2m) et la trace du quota par bord
            # (PlaceAffectee) sont créées ensemble, ou pas du tout.
            with transaction.atomic():
                session.reservations.add(marin)
                PlaceAffectee.objects.create(demande_place=demande, marin=marin)
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

    def _candidater_formation(self, request):
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

    def _valider_candidature_hierarchie(self, request):
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

    def _refuser_candidature_hierarchie(self, request):
        """Refus par la hiérarchie : arrête définitivement la candidature,
        sans attendre la validation BRH (même autorisation que la
        validation, cf. _valider_candidature_hierarchie)."""
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

    def _valider_candidature_brh(self, request):
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

    def _refuser_candidature_brh(self, request):
        """Refus par le BRH : arrête définitivement la candidature, sans
        attendre la validation hiérarchie (même autorisation que la
        validation, cf. _valider_candidature_brh)."""
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

    def _selectionner_candidature(self, request):
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
        # corrigés — cf. _attribuer_places ci-dessus pour le même pattern) :
        # une formation « bord » peut être repassée en attente ou refusée
        # entre la TRANSMISSION de la candidature et cette SÉLECTION.
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

    def _refuser_candidature_organisme(self, request):
        """Refus par l'organisme de formation d'une candidature TRANSMITTED
        (même autorisation que la sélection, cf. _selectionner_candidature)."""
        candidature_id = _entier_ou_none(request.POST.get("candidature_id"))
        candidature = (
            CandidatureFormation.objects.select_related("course", "marin").filter(pk=candidature_id).first()
            if candidature_id is not None else None
        )
        if candidature is None:
            messages.error(request, "Candidature introuvable.")
            return redirect("formation-list")
        # Même revalidation que _selectionner_candidature ci-dessus (correctif
        # QA — Circuit C, durcissement défensif par cohérence).
        if candidature.course.statut_validation != "ACTIVE":
            messages.error(request, "Formation introuvable.")
            return redirect("formation-list")
        # Même autorisation que _selectionner_candidature ci-dessus (navire
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

    def _proposer_formation_bord(self, request):
        """Circuit C — un chef de secteur (CHEF_SECTEUR+) crée ou modifie une
        formation « gérée par le bord » : les champs sont appliqués
        immédiatement, mais la formation reste invisible du catalogue général
        (statut_validation WAITING_VALIDATION, cf. get_queryset) tant qu'un
        chef de service de son périmètre (ou supervision globale) ne l'a pas
        validée — même pattern d'état explicite que WAITING_VALIDATION sur
        les occurrences de maintenance (maintenance/models.py). Un
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
        # Barème facultatif, même principe que create_course et
        # update_prerequisites ci-dessus : un nouveau fichier remplace
        # l'ancien, sinon « retirer_bareme » l'enlève sans le remplacer.
        nouveau_bareme = request.FILES.get("bareme")
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

    def _valider_formation_bord(self, request):
        """Validation, par un chef de service (CHEF_SERVICE+) du même
        périmètre que le proposeur, ou par supervision globale (COMMANDANT+),
        d'une formation « bord » en attente — fait passer la formation en
        ACTIVE, désormais visible dans le catalogue (cf.
        _peut_valider_proposition_bord)."""
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
        if course.updated_by_id:
            Notification.objects.create(
                user_id=course.updated_by_id,
                verb=f"Votre proposition de formation « {course.title} » a été validée par le chef de service.",
            )
        messages.success(request, f"Formation « {course.title} » validée et désormais active.")
        return redirect("formation-list")

    def _refuser_formation_bord(self, request):
        """Refus par le chef de service (même autorisation que la
        validation, cf. _valider_formation_bord) : la formation reste hors du
        catalogue (statut REFUSED), le chef de secteur pouvant la reprendre
        et la soumettre à nouveau (cf. _proposer_formation_bord)."""
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
        if course.updated_by_id:
            Notification.objects.create(
                user_id=course.updated_by_id,
                level="warning",
                verb=f"Votre proposition de formation « {course.title} » a été refusée par le chef de service.",
            )
        messages.success(request, "Proposition de formation refusée.")
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
        # _marins_validables), en forgeant la requête POST avec un autre
        # marin_id que ceux proposés par le select du GET.
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
