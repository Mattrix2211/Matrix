"""Seuils de rôle, contrôles d'autorisation et périmètre organisationnel
partagés par les vues web du module Formations (training/web_views.py).

Module extrait lors du re-découpage du fichier (tâche Notion « [ARCH]
Découper training/web_views.py et re-découper assets/web_views.py + règle de
taille pour le Tech Lead », training/web_views.py ayant atteint 1955 lignes) :
regroupe toutes les fonctions de contrôle d'accès et de calcul de périmètre
réutilisées par les différents circuits de validation (Circuit A — demande de
places à quota, Circuit B — candidature individuelle, Circuit C — formation
gérée par le bord), ainsi que quelques utilitaires de parsing communs.

Refactor pur : reproduit exactement le comportement d'origine."""
from datetime import datetime

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.db.models import Q
from django.utils import timezone

from matrix.core.roles import RoleLevel, user_role_level
from matrix.core.scopes import scope_filters_for_user
from org.models import Ship

from .models import (
    NIVEAU_SUPERVISION_GLOBALE_FORMATION,
    PersonnelBRH,
    ReferentFormation,
    ReferentFormationNavire,
)

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
# _affecter_session (training/session_actions.py), SEUL usage restant de ce
# seuil. Il ne s'applique PLUS ni à la validation elle-même (création d'un
# TrainingRecord, ValiderFormationView), ni à la visibilité du bouton « Valider
# une formation » : pour ces deux usages, ce seuil générique contournait à tort
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
    _peut_valider_candidature_hierarchie ci-dessus, appliqué ici au
    CHEF_SECTEUR proposeur plutôt qu'à un marin candidat) — ou supervision
    globale (COMMANDANT+, même seuil que peut_valider_formation).

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
