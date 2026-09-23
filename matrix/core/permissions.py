from rest_framework.permissions import BasePermission, SAFE_METHODS
from .roles import user_role_level, RoleLevel
from .role_thresholds import seuil_role, ship_id_de
from django.contrib.auth import get_user_model
from accounts.models import Roles


class RolePermission(BasePermission):
    # Valeurs par défaut minimales et pragmatiques par action ; à affiner par ViewSet si besoin
    min_level_write = RoleLevel.CHEF_SECTION

    def _seuil_requis(self, request, view):
        """Seuil de rôle minimal pour la méthode d'écriture courante.

        Un ViewSet peut définir `role_threshold_action_write` (et, pour un
        seuil DELETE spécifique, `role_threshold_action_delete`) : une clé du
        registre `matrix/core/role_thresholds.py`, résolue dynamiquement
        selon la configuration du navire de l'appelant (configurable par
        ADMIN_NAVIRE/MASTER_ADMIN, onglet « Sécurité » des Réglages).

        Les anciens attributs `min_role_level_write`/`min_role_level_delete`
        (constante RoleLevel figée) restent pris en charge pour les ViewSets
        non couverts par cette tâche, en repli si aucune clé d'action n'est
        définie — comportement inchangé pour eux.

        Par défaut, le seuil s'applique uniformément à toute écriture
        (POST/PUT/PATCH/DELETE), comme avant. Un ViewSet peut exiger un
        seuil plus élevé spécifiquement sur DELETE (ex. AssetViewSet :
        création/modification réservées à CHEF_SECTION mais suppression
        réservée à CHEF_SERVICE, même seuil que
        AssetListView.ACTION_VERS_SEUIL côté web)."""
        if request.method == 'DELETE':
            cle_delete = getattr(view, 'role_threshold_action_delete', None)
            if cle_delete is not None:
                return seuil_role(cle_delete, ship_id_de(request.user))
            seuil_delete = getattr(view, 'min_role_level_delete', None)
            if seuil_delete is not None:
                return seuil_delete
        cle_write = getattr(view, 'role_threshold_action_write', None)
        if cle_write is not None:
            return seuil_role(cle_write, ship_id_de(request.user))
        return getattr(view, 'min_role_level_write', self.min_level_write)

    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return request.user.is_authenticated
        if request.user.is_superuser:
            return True
        lvl = user_role_level(request.user)
        return lvl >= self._seuil_requis(request, view)

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
        return lvl >= self._seuil_requis(request, view)


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
    - ADMIN_NAVIRE : gère tout le personnel de son navire (le scoping par
      navire de la DESTINATION d'affectation — ship/service/sector/section —
      est appliqué dans UserProfileSerializer.validate(), pas ici : cette
      permission ne porte que sur le RÔLE gérable, pas sur le périmètre)
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
