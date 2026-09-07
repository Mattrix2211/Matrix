from django.contrib.auth import get_user_model
from django.db.models import Q
from rest_framework import viewsets, permissions
from rest_framework.exceptions import PermissionDenied as ApiPermissionDenied
from rest_framework.permissions import SAFE_METHODS
from .models import (
    NIVEAU_SUPERVISION_GLOBALE_FORMATION,
    ReferentFormation,
    TrainingCourse,
    TrainingRequirement,
    TrainingSession,
    TrainingRecord,
    navire_de,
    peut_valider_formation,
)
from .serializers import (
    ReferentFormationSerializer,
    TrainingCourseSerializer,
    TrainingRequirementSerializer,
    TrainingSessionSerializer,
    TrainingRecordSerializer,
)
# Réutilise le contrôle de périmètre du Circuit C (chef de secteur -> chef de
# service), déjà correct côté web — jamais recréé ici (cf. CLAUDE.md,
# principe « ne jamais recréer un système déjà existant »). Import direct de
# training.web_views : aucun cycle, web_views.py n'importe jamais views.py.
# peut_modifier_formation_bord/formation_bord_en_service/
# NIVEAU_REQUIS_VALIDATION_FORMATION_BORD : mêmes garde-fous que
# TrainingCourseListView._proposer_formation_bord, appliqués ici à
# TrainingCourseViewSet.perform_update/perform_destroy suite au deuxième
# refus du Tech Lead (tâche Notion Circuit C) — un PATCH/PUT/DELETE sur une
# formation « bord » via l'API contournait jusqu'ici totalement ces
# contrôles, pourtant déjà corrects côté web.
from .web_views import (
    formation_bord_en_service,
    NIVEAU_REQUIS_VALIDATION_FORMATION_BORD,
    peut_modifier_formation_bord,
    peut_valider_proposition_bord,
)
from matrix.core.permissions import RolePermission
from matrix.core.roles import user_role_level
from matrix.core.scopes import perimetre_navire_q, resoudre_affectation_dans_perimetre, ship_id_for_user

User = get_user_model()


def _entier_ou_none(valeur):
    """Convertit `valeur` en entier si possible, sinon None — évite une
    ValueError sur un payload malformé (même principe que la fonction
    homonyme de training/web_views.py)."""
    try:
        return int(valeur)
    except (TypeError, ValueError):
        return None

class DefaultPermission(permissions.IsAuthenticated):
    pass

class TrainingCourseViewSet(viewsets.ModelViewSet):
    # Formation désormais globale (aucun rattachement navire) : aucun filtre de
    # périmètre à appliquer au catalogue ACTIVE, visible par tout utilisateur
    # connecté (cf. peut_valider_formation pour l'autorisation d'écriture sur
    # les enregistrements de validation, seul point réellement sensible). En
    # revanche, une formation « bord » encore WAITING_VALIDATION/REFUSED
    # (Circuit C) reste hors de get_queryset ci-dessous pour tout marin
    # normal — voir aussi TrainingCourseSerializer.Meta.read_only_fields pour
    # l'écriture de gere_par_le_bord/statut_validation. `queryset` reste
    # déclaré ici (non filtré) uniquement pour que le routeur DRF puisse en
    # déduire le `basename` : la requête réelle passe toujours par
    # get_queryset ci-dessous, jamais par cet attribut directement.
    queryset = TrainingCourse.objects.all()
    serializer_class = TrainingCourseSerializer
    permission_classes = [RolePermission]

    def get_queryset(self):
        user = self.request.user
        if not user.is_authenticated:
            return TrainingCourse.objects.none()
        base = TrainingCourse.objects.all()
        if user_role_level(user) >= NIVEAU_SUPERVISION_GLOBALE_FORMATION:
            return base
        # Mêmes deux ensembles complémentaires que
        # TrainingCourseListView.get_context_data (mes_propositions_bord /
        # formations_bord_a_valider) côté web, transposés à l'API : le
        # catalogue ACTIVE, PLUS les propositions du marin connecté
        # (peu importe leur statut), PLUS les propositions que ce marin a
        # autorité de valider (WAITING_VALIDATION uniquement — une formation
        # déjà REFUSED ne reste visible qu'à son propre proposeur).
        en_attente_ou_refusees = base.exclude(statut_validation="ACTIVE")
        mes_propositions_ids = list(
            en_attente_ou_refusees.filter(updated_by=user).values_list("pk", flat=True)
        )
        propositions_en_attente = (
            en_attente_ou_refusees.filter(gere_par_le_bord=True, statut_validation="WAITING_VALIDATION")
            .select_related("updated_by")
        )
        a_valider_ids = [
            c.pk for c in propositions_en_attente
            if peut_valider_proposition_bord(user, c.updated_by)
        ]
        return base.filter(
            Q(statut_validation="ACTIVE") | Q(pk__in=mes_propositions_ids) | Q(pk__in=a_valider_ids)
        )

    def perform_update(self, serializer):
        instance = serializer.instance
        if not instance.gere_par_le_bord:
            # Formation « organisme » classique : aucun garde-fou du Circuit C
            # ne s'applique, seul le seuil générique RolePermission compte.
            serializer.save()
            return
        # Périmètre organisationnel du proposeur d'origine (deuxième refus du
        # Tech Lead, tâche Notion Circuit C) : un CHEF_SECTION satisfait le
        # seuil d'écriture générique du ViewSet (RolePermission.min_level_write)
        # sans que cela lui donne autorité sur une formation bord hors de son
        # périmètre — même contrôle, mot pour mot, que côté web.
        if not peut_modifier_formation_bord(self.request.user, instance):
            raise ApiPermissionDenied(
                "Vous n'avez pas l'autorité pour modifier cette formation gérée par un "
                "bord : elle est hors de votre périmètre."
            )
        # Formation déjà en service (validations, sessions, ou prérequis
        # d'une autre formation) : pas de mutation en place, même règle que
        # TrainingCourseListView._proposer_formation_bord.
        if instance.statut_validation == "ACTIVE" and formation_bord_en_service(instance):
            raise ApiPermissionDenied(
                f"« {instance.title} » est déjà active et utilisée (validations, sessions ou "
                "prérequis d'une autre formation) : proposez une nouvelle formation plutôt "
                "que de la modifier directement."
            )
        # Une modification en place d'une formation bord pas encore en
        # service repasse par le même circuit de (re)validation que côté web :
        # ACTIVE immédiatement si l'auteur de LA MODIFICATION est déjà
        # CHEF_SERVICE+ de son périmètre (son propre rôle vaut l'accord
        # requis, cf. peut_modifier_formation_bord ci-dessus qui l'a déjà
        # vérifié), WAITING_VALIDATION sinon — jamais silencieusement ACTIVE
        # (issue signalée par le Tech Lead en complément du contrôle
        # d'accès). `gere_par_le_bord`/`statut_validation` restent en lecture
        # seule côté serializer (Meta.read_only_fields) : ce sont ces kwargs
        # explicites de .save() qui les pilotent, jamais le payload posté.
        statut_cible = (
            "ACTIVE" if user_role_level(self.request.user) >= NIVEAU_REQUIS_VALIDATION_FORMATION_BORD
            else "WAITING_VALIDATION"
        )
        serializer.save(statut_validation=statut_cible, updated_by=self.request.user)

    def perform_destroy(self, instance):
        if instance.gere_par_le_bord and not peut_modifier_formation_bord(self.request.user, instance):
            raise ApiPermissionDenied(
                "Vous n'avez pas l'autorité pour supprimer cette formation gérée par un "
                "bord : elle est hors de votre périmètre."
            )
        instance.delete()

class ReferentFormationPermission(RolePermission):
    """Désignation d'un référent (ReferentFormation) soumise au seuil générique
    CHEF_SECTION (RolePermission), mais TOUJOURS scopée au navire de
    L'APPELANT (navire_de) — jamais au navire fourni dans le payload. Sans ce
    contrôle, un CHEF_SECTION d'un navire A pourrait poster un `ship` d'un
    navire B et se faire désigner (ou désigner un tiers) référent de ce
    navire B, obtenant l'autorité de valider des formations de marins qui ne
    sont pas de son bord — faille corrigée ici. Seuls les rôles de
    supervision globale (COMMANDANT et au-dessus, cf.
    training.models.NIVEAU_SUPERVISION_GLOBALE_FORMATION) peuvent agir sur
    n'importe quel navire. Reproduit exactement la même logique que
    training/web_views.py::update_prerequisites (déjà correcte côté web) —
    voir aussi ReferentFormationNavire (training/models.py), volontairement
    sans route API et gérée uniquement côté web scopé, pour la même
    raison."""

    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return super().has_permission(request, view)
        if not super().has_permission(request, view):
            return False
        if request.method != "POST":
            # PUT/PATCH/DELETE : le contrôle du navire ciblé porte sur
            # l'objet existant, tranché par has_object_permission ci-dessous.
            return True
        if user_role_level(request.user) >= NIVEAU_SUPERVISION_GLOBALE_FORMATION:
            return True
        navire = navire_de(request.user)
        return navire is not None and _entier_ou_none(request.data.get("ship")) == navire.id

    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True
        if not super().has_object_permission(request, view, obj):
            return False
        if user_role_level(request.user) >= NIVEAU_SUPERVISION_GLOBALE_FORMATION:
            return True
        navire = navire_de(request.user)
        if navire is None or obj.ship_id != navire.id:
            return False
        # Si la requête tente de déplacer le référent vers un autre navire
        # (champ `ship` présent dans le payload), ce nouveau navire doit lui
        # aussi être celui de l'appelant.
        if "ship" in request.data:
            return _entier_ou_none(request.data.get("ship")) == navire.id
        return True


class ReferentFormationViewSet(viewsets.ModelViewSet):
    queryset = ReferentFormation.objects.select_related("course", "ship", "user").all()
    serializer_class = ReferentFormationSerializer
    permission_classes = [ReferentFormationPermission]

    def get_queryset(self):
        # ReferentFormationPermission (ci-dessus) scope déjà l'ÉCRITURE au
        # navire de l'appelant, mais la LECTURE (GET liste/détail) n'était
        # soumise à aucun filtre de périmètre avant cette correction : un
        # utilisateur pouvait lister/consulter via l'API les référents de
        # TOUS les navires, alors que la même information est déjà scopée
        # au navire de l'appelant côté web (training/web_views.py, cf.
        # test_referent_dun_autre_navire_non_affiche) — faille corrigée ici
        # (audit sécurité scoping API, tâche Notion « Audit complet du
        # scoping par périmètre »).
        qs = super().get_queryset()
        user = self.request.user
        if not user.is_authenticated:
            return ReferentFormation.objects.none()
        if user_role_level(user) >= NIVEAU_SUPERVISION_GLOBALE_FORMATION:
            return qs
        ship_id = ship_id_for_user(user)
        if ship_id is None:
            return qs.none()
        return qs.filter(ship_id=ship_id)


class TrainingRequirementPermission(RolePermission):
    """Une exigence de formation (TrainingRequirement) peut cibler un navire/
    service/secteur/section précis (applies_to_ship/service/sector/section),
    soumise au seuil générique CHEF_SECTION (RolePermission) — mais ce
    rattachement doit TOUJOURS appartenir au périmètre navire de L'APPELANT,
    jamais à un navire fourni librement dans le payload (faille corrigée :
    avant ce contrôle, un CHEF_SECTION pouvait imposer une exigence de
    formation à n'importe quel navire/service/secteur/section de la flotte).
    Réutilise resoudre_affectation_dans_perimetre (matrix/core/scopes.py),
    déjà utilisé pour le même contrôle côté annuaire
    (accounts/serializers.py::UserProfileSerializer), plutôt que de recréer
    une vérification équivalente. Seuls les rôles de supervision globale
    (COMMANDANT et au-dessus, cf. NIVEAU_SUPERVISION_GLOBALE_FORMATION)
    peuvent cibler n'importe quel navire, ou ne cibler aucun navire du tout
    (exigence valable pour toute la flotte)."""

    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return super().has_permission(request, view)
        if not super().has_permission(request, view):
            return False
        if request.method != "POST":
            # PUT/PATCH/DELETE : le contrôle du rattachement porte sur
            # l'objet existant, tranché par has_object_permission ci-dessous.
            return True
        return self._perimetre_valide(request)

    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True
        if not super().has_object_permission(request, view, obj):
            return False
        return self._perimetre_valide(request, existant=obj)

    @staticmethod
    def _perimetre_valide(request, existant=None):
        if user_role_level(request.user) >= NIVEAU_SUPERVISION_GLOBALE_FORMATION:
            return True
        data = request.data

        def _id_demande(champ_payload, champ_modele):
            if champ_payload in data:
                return _entier_ou_none(data.get(champ_payload))
            return getattr(existant, champ_modele, None) if existant else None

        ship_id = _id_demande("applies_to_ship", "applies_to_ship_id")
        service_id = _id_demande("applies_to_service", "applies_to_service_id")
        sector_id = _id_demande("applies_to_sector", "applies_to_sector_id")
        section_id = _id_demande("applies_to_section", "applies_to_section_id")
        if not any([ship_id, service_id, sector_id, section_id]):
            # Aucun rattachement organisationnel précisé : une exigence
            # valable pour TOUTE la flotte est réservée à la supervision
            # globale, pour qu'un chef de section ne puisse pas l'imposer
            # sans validation d'un rôle supérieur.
            return False
        ok, *_ = resoudre_affectation_dans_perimetre(
            request.user, ship_id=ship_id, service_id=service_id, sector_id=sector_id, section_id=section_id,
        )
        return ok


class TrainingRequirementViewSet(viewsets.ModelViewSet):
    queryset = TrainingRequirement.objects.select_related(
        "course", "applies_to_ship", "applies_to_service", "applies_to_sector", "applies_to_section"
    ).all()
    serializer_class = TrainingRequirementSerializer
    permission_classes = [TrainingRequirementPermission]

    def get_queryset(self):
        # Aucun filtre de périmètre n'était appliqué avant cette correction :
        # n'importe quel utilisateur authentifié pouvait lister/consulter via
        # l'API les exigences de formation de TOUS les navires (audit
        # sécurité scoping API, tâche Notion « Audit complet du scoping par
        # périmètre »). Une exigence sans aucun rattachement (applies_to_*
        # tous vides) vaut pour toute la flotte et reste visible de tous ;
        # les autres ne le sont que pour le navire qu'elles ciblent
        # (perimetre_navire_q parcourt les 4 niveaux de rattachement
        # possibles, même logique que pour le personnel de l'annuaire,
        # matrix/core/scopes.py).
        qs = super().get_queryset()
        user = self.request.user
        if not user.is_authenticated:
            return TrainingRequirement.objects.none()
        if user_role_level(user) >= NIVEAU_SUPERVISION_GLOBALE_FORMATION:
            return qs
        return qs.filter(
            perimetre_navire_q(user, "applies_to_")
            | Q(
                applies_to_ship__isnull=True,
                applies_to_service__isnull=True,
                applies_to_sector__isnull=True,
                applies_to_section__isnull=True,
            )
        )


class TrainingRecordPermission(RolePermission):
    """Seuls les référents désignés pour la formation concernée, POUR LE NAVIRE
    DU MARIN CIBLÉ (ou un rôle de supervision globale — cf.
    training.models.peut_valider_formation), peuvent créer, modifier ou
    supprimer un enregistrement de validation (TrainingRecord). La lecture
    reste ouverte à tout utilisateur connecté : le statut de qualification
    d'un marin doit rester consultable partout, conformément à la
    portabilité du module Formations (CLAUDE.md)."""

    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return super().has_permission(request, view)
        if not request.user.is_authenticated:
            return False
        if request.method != "POST":
            # PUT/PATCH/DELETE : le contrôle porte sur l'objet existant,
            # tranché par has_object_permission ci-dessous.
            return True
        course = TrainingCourse.objects.filter(pk=request.data.get("course")).first()
        marin = User.objects.filter(pk=request.data.get("user")).first()
        if course is None or marin is None:
            # Formation ou marin absent/invalide : on laisse le serializer
            # renvoyer une erreur de validation explicite plutôt qu'un refus
            # d'accès qui masquerait le vrai problème.
            return True
        return peut_valider_formation(request.user, course, navire_de(marin))

    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True
        return peut_valider_formation(request.user, obj.course, navire_de(obj.user))


def _ids_postes(valeur):
    """Normalise la valeur postée pour le champ `attendees` (liste d'ids,
    éventuellement sous forme de chaînes) en un ensemble d'entiers valides —
    une valeur non convertible est simplement ignorée ici, le serializer se
    chargeant de la rejeter proprement le cas échéant."""
    if not valeur:
        return set()
    ids = set()
    for v in valeur:
        try:
            ids.add(int(v))
        except (TypeError, ValueError):
            continue
    return ids


class TrainingSessionPermission(RolePermission):
    """La planification d'une session (date, intervenant, lieu, statut) reste
    soumise au seuil générique CHEF_SECTION (RolePermission). La gestion des
    présences (attendees) — qui revient à certifier la participation à une
    formation — est en revanche tranchée UNIQUEMENT par peut_valider_formation,
    POUR CHAQUE MARIN CONCERNÉ (ajouté ou retiré), au regard du NAVIRE DE CE
    MARIN — jamais du navire de l'appelant. Un référent est désigné pour sa
    compétence sur la formation, pas pour son rang, et peut donc être
    EQUIPIER. Si la requête modifie aussi d'autres champs de planification en
    même temps que les présences, ces autres champs restent soumis au seuil
    générique."""

    @staticmethod
    def _modifie_d_autres_champs_que_attendees(request):
        return any(champ != "attendees" for champ in request.data)

    @staticmethod
    def _autorise_pour_marins(user, course, ids_marins):
        if not ids_marins:
            return True
        marins = User.objects.filter(pk__in=ids_marins).select_related("profile")
        return all(peut_valider_formation(user, course, navire_de(m)) for m in marins)

    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return super().has_permission(request, view)
        if request.method != "POST":
            # PUT/PATCH/DELETE : le contrôle porte sur l'objet existant,
            # tranché par has_object_permission ci-dessous.
            return True
        if "attendees" not in request.data:
            return super().has_permission(request, view)
        course = TrainingCourse.objects.filter(pk=request.data.get("course")).first()
        if course is not None:
            ids = _ids_postes(request.data.get("attendees"))
            if not self._autorise_pour_marins(request.user, course, ids):
                return False
        if self._modifie_d_autres_champs_que_attendees(request):
            return super().has_permission(request, view)
        return True

    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True
        if "attendees" not in request.data:
            return super().has_object_permission(request, view, obj)
        # Seuls les marins réellement TOUCHÉS par la modification (ajoutés ou
        # retirés) sont revalidés : les autres, déjà présents et non touchés
        # par ce PATCH, n'ont pas à être re-couverts par l'autorité du
        # référent (un référent d'un navire peut retirer un marin de SON
        # navire sans avoir autorité sur les marins d'autres navires déjà
        # inscrits par ailleurs).
        ids_nouveaux = _ids_postes(request.data.get("attendees"))
        ids_actuels = set(obj.attendees.values_list("id", flat=True))
        ids_concernes = ids_nouveaux ^ ids_actuels
        if not self._autorise_pour_marins(request.user, obj.course, ids_concernes):
            return False
        if self._modifie_d_autres_champs_que_attendees(request):
            return super().has_object_permission(request, view, obj)
        return True


# Lecture volontairement non scopée (queryset non filtré, comme
# TrainingRecordViewSet ci-dessous) : une session de formation n'est plus
# rattachée à un périmètre organisationnel précis depuis que TrainingCourse
# est une fiche globale partagée par tous les navires (portabilité des
# qualifications), et CalendarView (calendar_app/views.py) affiche
# volontairement TOUTES les sessions à tout utilisateur pour que la
# planification (disponibilité salles/formateurs) reste visible flotte
# entière. Seule l'ÉCRITURE reste contrôlée finement (TrainingSessionPermission
# ci-dessus, par affectation personnelle des marins concernés).
class TrainingSessionViewSet(viewsets.ModelViewSet):
    queryset = TrainingSession.objects.select_related("course", "instructor").all()
    serializer_class = TrainingSessionSerializer
    permission_classes = [TrainingSessionPermission]

class TrainingRecordViewSet(viewsets.ModelViewSet):
    queryset = TrainingRecord.objects.select_related("course", "user").all()
    serializer_class = TrainingRecordSerializer
    permission_classes = [TrainingRecordPermission]
