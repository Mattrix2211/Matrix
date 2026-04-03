from rest_framework import viewsets, permissions
from django.contrib.auth.models import User
from .models import UserProfile, GradeChoice, SpecialityChoice, RoleAvailability
from .serializers import (
    UserSerializer,
    UserProfileSerializer,
    GradeChoiceSerializer,
    SpecialityChoiceSerializer,
    RoleAvailabilitySerializer,
)
from bordops.core.permissions import RolePermission, ManageUsersPermission
from bordops.core.roles import RoleLevel

class DefaultPermission(permissions.IsAuthenticated):
    pass

class UserViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = User.objects.all().order_by("username")
    serializer_class = UserSerializer
    permission_classes = [DefaultPermission]

class UserProfileViewSet(viewsets.ModelViewSet):
    queryset = UserProfile.objects.select_related("user", "ship", "service", "sector", "section").all()
    serializer_class = UserProfileSerializer
    permission_classes = [ManageUsersPermission]


class GradeChoiceViewSet(viewsets.ModelViewSet):
    queryset = GradeChoice.objects.all().order_by("name")
    serializer_class = GradeChoiceSerializer
    permission_classes = [RolePermission]
    min_role_level_write = RoleLevel.MASTER_ADMIN


class SpecialityChoiceViewSet(viewsets.ModelViewSet):
    queryset = SpecialityChoice.objects.all().order_by("name")
    serializer_class = SpecialityChoiceSerializer
    permission_classes = [RolePermission]
    min_role_level_write = RoleLevel.MASTER_ADMIN


class RoleAvailabilityViewSet(viewsets.ModelViewSet):
    queryset = RoleAvailability.objects.all().order_by("code")
    serializer_class = RoleAvailabilitySerializer
    permission_classes = [RolePermission]
    min_role_level_write = RoleLevel.MASTER_ADMIN
