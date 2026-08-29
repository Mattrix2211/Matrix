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
from matrix.core.mixins import build_scope_q
from matrix.core.permissions import RolePermission, ManageUsersPermission
from matrix.core.roles import user_role_level, RoleLevel

class DefaultPermission(permissions.IsAuthenticated):
    pass


def _utilisateurs_visibles_par(user):
    """Périmètre de lecture des comptes utilisateurs, aligné sur celui déjà
    appliqué à l'annuaire web (UserDirectoryView, accounts/web_views.py) :
    COMMANDANT et au-dessus voient la flotte entière, en-dessous la lecture
    est restreinte au périmètre hiérarchique du profil de l'appelant (navire/
    service/secteur/section). Sans ce filtre, l'API exposait l'ensemble des
    comptes (identifiants, rôles, rattachements) à tout utilisateur connecté,
    y compris un simple équipier (T-SEC).

    User ne porte pas directement les 4 champs de périmètre — c'est son
    profil qui les porte — d'où le préfixe "profile__" passé à build_scope_q.
    """
    if user_role_level(user) >= RoleLevel.COMMANDANT:
        return User.objects.all()
    return User.objects.filter(build_scope_q(user, "profile__"))


class UserViewSet(viewsets.ReadOnlyModelViewSet):
    # queryset non filtré conservé uniquement pour que le routeur DRF puisse en
    # déduire le nom de base (basename) — le filtrage réel du périmètre se fait
    # dans get_queryset() ci-dessous, comme pour tout ViewSet scopé de l'appli.
    queryset = User.objects.all().order_by("username")
    serializer_class = UserSerializer
    permission_classes = [DefaultPermission]

    def get_queryset(self):
        return _utilisateurs_visibles_par(self.request.user).order_by("username")

class UserProfileViewSet(viewsets.ModelViewSet):
    # queryset non filtré conservé uniquement pour l'inférence du basename par
    # le routeur DRF (même remarque que UserViewSet ci-dessus).
    queryset = UserProfile.objects.select_related("user", "ship", "service", "sector", "section").all()
    serializer_class = UserProfileSerializer
    permission_classes = [ManageUsersPermission]

    def get_queryset(self):
        # Même périmètre de lecture que UserViewSet ci-dessus, traduit sur
        # UserProfile lui-même (qui porte directement les 4 champs de
        # périmètre, contrairement à User).
        qs = UserProfile.objects.select_related("user", "ship", "service", "sector", "section").all()
        if user_role_level(self.request.user) >= RoleLevel.COMMANDANT:
            return qs
        return qs.filter(build_scope_q(self.request.user, ""))


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
