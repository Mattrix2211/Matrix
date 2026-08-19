from rest_framework import viewsets, permissions
from rest_framework.permissions import SAFE_METHODS
from .models import TrainingCourse, TrainingRequirement, TrainingSession, TrainingRecord, peut_valider_formation
from .serializers import TrainingCourseSerializer, TrainingRequirementSerializer, TrainingSessionSerializer, TrainingRecordSerializer
from matrix.core.permissions import RolePermission

class DefaultPermission(permissions.IsAuthenticated):
    pass

class TrainingCourseViewSet(viewsets.ModelViewSet):
    queryset = TrainingCourse.objects.select_related("sector").all()
    serializer_class = TrainingCourseSerializer
    permission_classes = [RolePermission]

class TrainingRequirementViewSet(viewsets.ModelViewSet):
    queryset = TrainingRequirement.objects.select_related("course").all()
    serializer_class = TrainingRequirementSerializer
    permission_classes = [RolePermission]


class TrainingRecordPermission(RolePermission):
    """Seuls les référents désignés pour la formation concernée (ou un rôle de
    supervision globale — cf. TrainingCourse.referents / peut_valider_formation)
    peuvent créer, modifier ou supprimer un enregistrement de validation
    (TrainingRecord). La lecture reste ouverte à tout utilisateur connecté :
    le statut de qualification d'un marin doit rester consultable partout,
    conformément à la portabilité du module Formations (CLAUDE.md)."""

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
        if course is None:
            # Formation absente ou invalide : on laisse le serializer renvoyer
            # une erreur de validation explicite plutôt qu'un refus d'accès
            # qui masquerait le vrai problème.
            return True
        return peut_valider_formation(request.user, course)

    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True
        return peut_valider_formation(request.user, obj.course)


class TrainingSessionPermission(RolePermission):
    """La planification d'une session (date, intervenant, lieu, statut) reste
    soumise au seuil générique CHEF_SECTION (RolePermission). La gestion des
    présences (attendees) — qui revient à certifier la participation à une
    formation — est en revanche tranchée UNIQUEMENT par peut_valider_formation
    (référents de cette formation, ou rôle de supervision globale), SANS
    jamais passer par le seuil générique CHEF_SECTION : un référent est
    désigné pour sa compétence sur la formation, pas pour son rang, et peut
    donc être EQUIPIER. Si la requête modifie aussi d'autres champs de
    planification en même temps que les présences, ces autres champs restent
    soumis au seuil générique."""

    @staticmethod
    def _modifie_d_autres_champs_que_attendees(request):
        return any(champ != "attendees" for champ in request.data)

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
        if course is not None and not peut_valider_formation(request.user, course):
            return False
        if self._modifie_d_autres_champs_que_attendees(request):
            return super().has_permission(request, view)
        return True

    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True
        if "attendees" not in request.data:
            return super().has_object_permission(request, view, obj)
        if not peut_valider_formation(request.user, obj.course):
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
