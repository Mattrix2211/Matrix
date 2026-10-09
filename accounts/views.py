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
from matrix.core.mixins import build_scope_q, utilisateurs_visibles_par
from matrix.core.permissions import RolePermission, ManageUsersPermission
from matrix.core.roles import NIVEAU_VISION_COMMANDEMENT, user_role_level
from matrix.core.scopes import is_master_admin, perimetre_navire_q

class DefaultPermission(permissions.IsAuthenticated):
    pass


class UserViewSet(viewsets.ReadOnlyModelViewSet):
    # queryset non filtré conservé uniquement pour que le routeur DRF puisse en
    # déduire le nom de base (basename) — le filtrage réel du périmètre se fait
    # dans get_queryset() ci-dessous, comme pour tout ViewSet scopé de l'appli.
    queryset = User.objects.all().order_by("username")
    serializer_class = UserSerializer
    permission_classes = [DefaultPermission]

    def get_queryset(self):
        return utilisateurs_visibles_par(self.request.user).order_by("username")

class UserProfileViewSet(viewsets.ModelViewSet):
    # queryset non filtré conservé uniquement pour l'inférence du basename par
    # le routeur DRF (même remarque que UserViewSet ci-dessus).
    queryset = UserProfile.objects.select_related("user", "ship", "service", "sector", "section").all()
    serializer_class = UserProfileSerializer
    permission_classes = [ManageUsersPermission]
    # Le profil est créé avec le compte : ni création ni suppression par l'API.
    http_method_names = ["get", "put", "patch", "head", "options"]

    def get_queryset(self):
        # Même périmètre de lecture que UserViewSet ci-dessus, traduit sur
        # UserProfile lui-même (qui porte directement les 4 champs de
        # périmètre, contrairement à User).
        qs = UserProfile.objects.select_related("user", "ship", "service", "sector", "section").all()
        if is_master_admin(self.request.user):
            return qs
        if user_role_level(self.request.user) >= NIVEAU_VISION_COMMANDEMENT:
            return qs.filter(perimetre_navire_q(self.request.user, ""))
        return qs.filter(build_scope_q(self.request.user, ""))


# Les trois ViewSets ci-dessous exposent des référentiels GLOBAUX, communs à
# toute la flotte (grades, spécialités, disponibilité des rôles) — pas de
# rattachement navire/service/secteur/section sur ces modèles, donc aucun
# scoping à appliquer ici (audit sécurité scoping API, tâche Notion « Audit
# complet du scoping par périmètre ») : contrairement à GradeChoice/
# SpecialityChoice/RoleAvailability, un profil utilisateur ou une affectation
# EST rattaché à un navire précis, mais la LISTE des grades/spécialités
# possibles est partagée par tous les bords. L'écriture reste réservée à
# MASTER_ADMIN (référentiel commun à toute la flotte, pas à modifier par bord).
class GradeChoiceViewSet(viewsets.ModelViewSet):
    queryset = GradeChoice.objects.all().order_by("name")
    serializer_class = GradeChoiceSerializer
    permission_classes = [RolePermission]
    # Seuil de portée GLOBALE (flotte entière, pas par navire) : ce
    # référentiel n'est rattaché à aucun navire précis, cf.
    # matrix/core/role_thresholds.py (referentiel_global_ecriture).
    role_threshold_action_write = "referentiel_global_ecriture"


class SpecialityChoiceViewSet(viewsets.ModelViewSet):
    queryset = SpecialityChoice.objects.all().order_by("name")
    serializer_class = SpecialityChoiceSerializer
    permission_classes = [RolePermission]
    role_threshold_action_write = "referentiel_global_ecriture"


class RoleAvailabilityViewSet(viewsets.ModelViewSet):
    queryset = RoleAvailability.objects.all().order_by("code")
    serializer_class = RoleAvailabilitySerializer
    permission_classes = [RolePermission]
    role_threshold_action_write = "referentiel_global_ecriture"
