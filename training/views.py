from django.contrib.auth import get_user_model
from rest_framework import viewsets, permissions
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
from matrix.core.permissions import RolePermission
from matrix.core.roles import user_role_level

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
    # périmètre à appliquer, le catalogue est visible par tout utilisateur
    # connecté (cf. peut_valider_formation pour l'autorisation d'écriture sur
    # les enregistrements de validation, seul point réellement sensible).
    queryset = TrainingCourse.objects.all()
    serializer_class = TrainingCourseSerializer
    permission_classes = [RolePermission]

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

class TrainingRequirementViewSet(viewsets.ModelViewSet):
    queryset = TrainingRequirement.objects.select_related("course").all()
    serializer_class = TrainingRequirementSerializer
    permission_classes = [RolePermission]


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


class TrainingSessionViewSet(viewsets.ModelViewSet):
    queryset = TrainingSession.objects.select_related("course", "instructor").all()
    serializer_class = TrainingSessionSerializer
    permission_classes = [TrainingSessionPermission]

class TrainingRecordViewSet(viewsets.ModelViewSet):
    queryset = TrainingRecord.objects.select_related("course", "user").all()
    serializer_class = TrainingRecordSerializer
    permission_classes = [TrainingRecordPermission]
