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
from matrix.core.roles import RoleLevel, user_role_level
from matrix.core.scopes import is_master_admin, perimetre_navire_q

class DefaultPermission(permissions.IsAuthenticated):
    pass


def _utilisateurs_visibles_par(user):
    """Périmètre de lecture des comptes utilisateurs, aligné sur celui déjà
    appliqué à l'annuaire web (UserDirectoryView, accounts/web_views.py) :
    - MASTER_ADMIN (ou un superutilisateur) voit la flotte entière ;
    - COMMANDANT et ADMIN_NAVIRE, rattachés à un navire précis (cf.
      matrix/core/scopes.py::is_master_admin), voient tout le personnel de
      LEUR navire, à n'importe quel niveau de rattachement (navire/service/
      secteur/section) ;
    - les autres rôles restent restreints à leur périmètre hiérarchique
      habituel (build_scope_q).
    Avant correction, un COMMANDANT (ou au-dessus) voyait le personnel de
    tous les navires de la flotte (fuite de données inter-navire, audit
    sécurité du 2026-08-29).

    User ne porte pas directement les 4 champs de périmètre — c'est son
    profil qui les porte — d'où le préfixe "profile__" passé aux filtres.
    """
    if is_master_admin(user):
        return User.objects.all()
    if user_role_level(user) >= RoleLevel.COMMANDANT:
        return User.objects.filter(perimetre_navire_q(user, "profile__"))
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
        if is_master_admin(self.request.user):
            return qs
        if user_role_level(self.request.user) >= RoleLevel.COMMANDANT:
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
