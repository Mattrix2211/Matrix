from rest_framework.permissions import BasePermission, SAFE_METHODS
from .roles import user_role_level, RoleLevel
from django.contrib.auth import get_user_model
from accounts.models import Roles


class RolePermission(BasePermission):
    # Valeurs par défaut minimales et pragmatiques par action ; à affiner par ViewSet si besoin
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
        # Autorise les assignés à modifier leurs propres occurrences/exécutions de maintenance
        model_name = obj.__class__.__name__
        if model_name == 'MaintenanceOccurrence':
            return lvl >= RoleLevel.CHEF_SECTION or request.user in obj.assignees.all()
        return lvl >= getattr(view, 'min_role_level_write', self.min_level_write)


class IsAuthorOrReadOnly(BasePermission):
    """Lecture autorisée pour les utilisateurs authentifiés ; écriture réservée à l'auteur de l'objet."""

    def has_permission(self, request, view):
        # Authentification obligatoire pour tout accès
        return request.user and request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True
        # Seul l'auteur peut effectuer une opération d'écriture
        author = getattr(obj, 'author', None)
        return author == request.user


class ManageUsersPermission(BasePermission):
    """Lecture autorisée pour les utilisateurs authentifiés ; écriture réservée si le rôle de
    l'utilisateur courant peut gérer le rôle cible.

    Règles :
    - MASTER_ADMIN : gère tout
    - ADMIN_NAVIRE : gère tout (scoping par navire à implémenter au besoin)
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
        # Lecture autorisée pour les utilisateurs authentifiés
        if request.method in SAFE_METHODS:
            return request.user and request.user.is_authenticated
        # Passage forcé pour le super-utilisateur
        if getattr(request.user, 'is_superuser', False):
            return True
        # ADMIN_NAVIRE peut gérer (scoping navire à appliquer côté viewset/form)
        profile = getattr(request.user, 'profile', None)
        if not profile:
            return False
        if profile.role in (Roles.MASTER_ADMIN, Roles.ADMIN_NAVIRE):
            return True
        # Pour une création/modification, vérifie le rôle demandé dans le payload, sinon refuse
        target_role = request.data.get('role')
        if not target_role:
            return False
        allowed = self.MANAGE_MAP.get(profile.role, set())
        return target_role in allowed

    def has_object_permission(self, request, view, obj):
        # Méthodes sûres déjà autorisées dans has_permission
        if request.method in SAFE_METHODS:
            return True
        if getattr(request.user, 'is_superuser', False):
            return True
        profile = getattr(request.user, 'profile', None)
        if not profile:
            return False
        if profile.role in (Roles.MASTER_ADMIN, Roles.ADMIN_NAVIRE):
            return True
        # Vérifie le rôle actuel de l'utilisateur cible
        obj_role = getattr(obj, 'role', None)
        allowed = self.MANAGE_MAP.get(profile.role, set())
        return obj_role in allowed
