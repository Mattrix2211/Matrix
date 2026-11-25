from rest_framework.permissions import BasePermission, SAFE_METHODS
from .ecriture_service import niveau_ecriture_sur
from .roles import est_administrateur_general, est_administrateur_technique, niveau_ecriture, RoleLevel, user_role_level
from .role_thresholds import REGISTRE_PAR_CLE, niveau_pour_action, seuil_role, ship_id_de
from .scopes import ship_id_for_user
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
        selon la configuration du navire de l'appelant (configurable par le
        commandement ou l'administration technique selon l'action, onglet « Sécurité » des Réglages).

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

    def _niveau(self, request, view):
        """Niveau de l'acteur pour l'action de seuil du ViewSet : un acte de gouvernance est exercé explicitement par
        l'administrateur général (AC-15) ; sinon son niveau d'écriture métier."""
        cle = getattr(view, 'role_threshold_action_delete', None) if request.method == 'DELETE' else None
        cle = cle or getattr(view, 'role_threshold_action_write', None)
        return niveau_pour_action(request.user, cle) if cle else niveau_ecriture(request.user)

    def has_permission(self, request, view):
        # Aucune écriture sans compte, même quand le seuil d'action est celui d'un équipier (anonyme = niveau équipier).
        if not request.user.is_authenticated:
            return False
        if request.method in SAFE_METHODS:
            return True
        return self._niveau(request, view) >= self._seuil_requis(request, view)

    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True
        cle = getattr(view, 'role_threshold_action_write', None)
        if cle and REGISTRE_PAR_CLE[cle].gouvernance and est_administrateur_general(request.user):
            return True
        # Un état-major n'écrit que sur les services rattachés à sa fonction de commandant adjoint.
        lvl = niveau_ecriture_sur(request.user, obj, strict=False)
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
    """Lecture autorisée pour les utilisateurs authentifiés ; écriture selon l'autorité sur le rôle visé.

    Règles (AC-01, AC-02) :
    - administrateur général (indicateur ; le superutilisateur Django n'en est pas un) : désigne et révoque commandant et second,
      rattache les marins aux bâtiments, attribue et révoque les droits techniques (AC-15, AC-19) ; aucune autre autorité de bord ;
    - COMMANDANT : désigne commandants adjoints, chefs de service, de secteur, de section et équipiers ;
    - ÉTAT-MAJOR : désigne chefs de secteur, de section et équipiers (les chefs de service relèvent du commandant) ;
    - CHEF_SERVICE : chefs de secteur, de section et équipiers ; CHEF_SECTEUR : chefs de section et équipiers ;
      CHEF_SECTION : équipiers ; le commandant en second ne désigne personne ;
    - l'administrateur technique (indicateur indépendant du rôle) modifie un compte ordinaire sans changer son rôle ; il ne
      désigne aucune autorité métier ni n'attribue ou ne révoque aucun droit technique (AC-19) ;
    - personne ne modifie son propre rôle ni ses propres droits techniques.
    """

    MANAGE_MAP = {
        Roles.COMMANDANT: {Roles.COMMANDANT_EN_SECOND, Roles.ETAT_MAJOR, Roles.CHEF_SERVICE, Roles.CHEF_SECTEUR, Roles.CHEF_SECTION, Roles.EQUIPIER},
        Roles.ETAT_MAJOR: {Roles.CHEF_SECTEUR, Roles.CHEF_SECTION, Roles.EQUIPIER},
        Roles.CHEF_SERVICE: {Roles.CHEF_SECTEUR, Roles.CHEF_SECTION, Roles.EQUIPIER},
        Roles.CHEF_SECTEUR: {Roles.CHEF_SECTION, Roles.EQUIPIER},
        Roles.CHEF_SECTION: {Roles.EQUIPIER},
    }

    # Champs qui portent une autorité ou un périmètre : jamais modifiés par un administrateur technique, ni par quiconque sur
    # son propre profil ; la fonction de commandant adjoint exige le commandant (AC-02).
    CHAMPS_AUTORITE = ("role", "fonction_coma", "ship", "service", "sector", "section", "allowed_sectors", "equipage")

    @staticmethod
    def _modifie_droits_techniques(request):
        return "administrateur_technique" in request.data

    @classmethod
    def _champs_d_autorite_presents(cls, request):
        return [champ for champ in cls.CHAMPS_AUTORITE if champ in request.data]

    @staticmethod
    def _change(obj, champ, valeur):
        """Vrai si `valeur` modifie le champ d'autorité de `obj` (clés étrangères comparées par identifiant)."""
        if champ == "allowed_sectors":
            envoyes = {str(v) for v in (valeur if isinstance(valeur, (list, tuple)) else [valeur])}
            return envoyes != {str(pk) for pk in obj.allowed_sectors.values_list("pk", flat=True)}
        actuel = getattr(obj, f"{champ}_id", None) if champ in ("ship", "service", "sector", "section") else getattr(obj, champ, "")
        return str(actuel if actuel is not None else "") != str(valeur if valeur is not None else "")

    # Gouvernance (AC-15) : l'administrateur général désigne et révoque le commandement du bâtiment (commandant, second) ;
    # il ne désigne aucune autre autorité de bord. Révoquer = ramener le compte au rôle d'équipier.
    ROLES_DE_GOUVERNANCE = {Roles.COMMANDANT, Roles.COMMANDANT_EN_SECOND, Roles.EQUIPIER}

    def has_permission(self, request, view):
        # Lecture autorisée pour les utilisateurs authentifiés
        if request.method in SAFE_METHODS:
            return request.user and request.user.is_authenticated
        profile = getattr(request.user, 'profile', None)
        if not profile or not request.user.is_authenticated:
            return False
        general = est_administrateur_general(request.user)
        technique = est_administrateur_technique(request.user)
        # Les droits techniques s'attribuent et se révoquent par l'administrateur général seul (AC-19).
        if self._modifie_droits_techniques(request) and not general:
            return False
        target_role = request.data.get('role')
        if not target_role:
            # Sans rôle dans la requête : modification technique, jamais d'un champ d'autorité ou de périmètre
            # (sauf rattachement par l'administrateur général).
            autorite = self._champs_d_autorite_presents(request)
            return (technique and not autorite) or (general and (not autorite or set(autorite) <= self.CHAMPS_RATTACHEMENT))
        if general and target_role in self.ROLES_DE_GOUVERNANCE:
            return True
        return target_role in self.MANAGE_MAP.get(profile.role, set())

    # Rattachement des marins aux bâtiments : gouvernance de l'administrateur général.
    CHAMPS_RATTACHEMENT = {"ship", "service", "sector", "section", "allowed_sectors", "equipage"}

    def has_object_permission(self, request, view, obj):
        # Méthodes sûres déjà autorisées dans has_permission
        if request.method in SAFE_METHODS:
            return True
        profile = getattr(request.user, 'profile', None)
        if not profile:
            return False
        general = est_administrateur_general(request.user)
        modifies = [champ for champ in self._champs_d_autorite_presents(request) if self._change(obj, champ, request.data.get(champ))]
        if getattr(obj, 'user_id', None) == request.user.pk and (self._modifie_droits_techniques(request) or modifies):
            return False
        if "fonction_coma" in modifies and user_role_level(request.user) < RoleLevel.COMMANDANT:
            return False
        technique = est_administrateur_technique(request.user)
        if general:
            if request.data.get('role'):
                return obj.role in self.ROLES_DE_GOUVERNANCE and set(modifies) <= self.CHAMPS_RATTACHEMENT | {"role"}
            return True
        dans_la_matrice = obj.role in self.MANAGE_MAP.get(profile.role, set())
        if request.data.get('role'):
            return dans_la_matrice
        technique_sur_son_batiment = (
            technique and not obj.administrateur_general and ship_id_for_user(obj.user) == ship_id_for_user(request.user)
        )
        return technique_sur_son_batiment or dans_la_matrice

