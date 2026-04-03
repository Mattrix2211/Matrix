from rest_framework.permissions import BasePermission, SAFE_METHODS
from .roles import user_role_level, RoleLevel
from django.contrib.auth import get_user_model
from accounts.models import Roles


class RolePermission(BasePermission):
    # Minimal, pragmatic defaults per action; fine-tune per ViewSet if needed
    min_level_write = RoleLevel.CHEF_SECTION

    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return request.user.is_authenticated
        if request.user.is_superuser:
            return True
        lvl = user_role_level(request.user)
        return lvl >= getattr(view, 'min_role_level_write', self.min_level_write)

    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True
        if request.user.is_superuser:
            return True
        lvl = user_role_level(request.user)
        # Allow assignees to update their own maintenance occurrences/executions
        model_name = obj.__class__.__name__
        if model_name == 'MaintenanceOccurrence':
            return lvl >= RoleLevel.CHEF_SECTION or request.user in obj.assignees.all()
        return lvl >= getattr(view, 'min_role_level_write', self.min_level_write)


class IsAuthorOrReadOnly(BasePermission):
    """Allow read to authenticated users; write only to the object's author."""

    def has_permission(self, request, view):
        # Must be authenticated for any access
        return request.user and request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True
        # Author required for unsafe methods
        author = getattr(obj, 'author', None)
        return author == request.user


class ManageUsersPermission(BasePermission):
    """Allow read to authenticated; write only if current user's role can manage target role.

    Rules:
    - MASTER_ADMIN: manage all
    - ADMIN_NAVIRE: manage all (scoping par navire à implémenter au besoin)
    - COMMANDANT: peut gérer ETAT_MAJOR, CHEF_SERVICE, CHEF_SECTEUR, CHEF_SECTION, EQUIPIER
    - ETAT_MAJOR: peut gérer CHEF_SERVICE, CHEF_SECTEUR, CHEF_SECTION, EQUIPIER
    - CHEF_SERVICE: peut gérer CHEF_SECTEUR, CHEF_SECTION, EQUIPIER
    - CHEF_SECTEUR: peut gérer CHEF_SECTION, EQUIPIER
    - CHEF_SECTION: peut gérer EQUIPIER
    """

    MANAGE_MAP = {
        Roles.COMMANDANT: {Roles.ETAT_MAJOR, Roles.CHEF_SERVICE, Roles.CHEF_SECTEUR, Roles.CHEF_SECTION, Roles.EQUIPIER},
        Roles.ETAT_MAJOR: {Roles.CHEF_SERVICE, Roles.CHEF_SECTEUR, Roles.CHEF_SECTION, Roles.EQUIPIER},
        Roles.CHEF_SERVICE: {Roles.CHEF_SECTEUR, Roles.CHEF_SECTION, Roles.EQUIPIER},
        Roles.CHEF_SECTEUR: {Roles.CHEF_SECTION, Roles.EQUIPIER},
        Roles.CHEF_SECTION: {Roles.EQUIPIER},
    }

    def has_permission(self, request, view):
        # Read allowed for authenticated users
        if request.method in SAFE_METHODS:
            return request.user and request.user.is_authenticated
        # Superuser override
        if getattr(request.user, 'is_superuser', False):
            return True
        # ADMIN_NAVIRE peut gérer (scoping navire à appliquer côté viewset/form)
        profile = getattr(request.user, 'profile', None)
        if not profile:
            return False
        if profile.role in (Roles.MASTER_ADMIN, Roles.ADMIN_NAVIRE):
            return True
        # For create/update, check requested role in payload, else deny
        target_role = request.data.get('role')
        if not target_role:
            return False
        allowed = self.MANAGE_MAP.get(profile.role, set())
        return target_role in allowed

    def has_object_permission(self, request, view, obj):
        # Safe methods already allowed in has_permission
        if request.method in SAFE_METHODS:
            return True
        if getattr(request.user, 'is_superuser', False):
            return True
        profile = getattr(request.user, 'profile', None)
        if not profile:
            return False
        if profile.role in (Roles.MASTER_ADMIN, Roles.ADMIN_NAVIRE):
            return True
        # Check target user's current role
        obj_role = getattr(obj, 'role', None)
        allowed = self.MANAGE_MAP.get(profile.role, set())
        return obj_role in allowed
