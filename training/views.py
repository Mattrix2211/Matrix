from rest_framework import viewsets, permissions
from .models import TrainingCourse, TrainingRequirement, TrainingSession, TrainingRecord
from .serializers import TrainingCourseSerializer, TrainingRequirementSerializer, TrainingSessionSerializer, TrainingRecordSerializer
from bordops.core.permissions import RolePermission

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

class TrainingSessionViewSet(viewsets.ModelViewSet):
    queryset = TrainingSession.objects.select_related("course", "instructor").all()
    serializer_class = TrainingSessionSerializer
    permission_classes = [RolePermission]

class TrainingRecordViewSet(viewsets.ModelViewSet):
    queryset = TrainingRecord.objects.select_related("course", "user").all()
    serializer_class = TrainingRecordSerializer
    permission_classes = [RolePermission]
