from django.contrib.auth import get_user_model
from rest_framework import viewsets, permissions
from rest_framework.exceptions import PermissionDenied, ValidationError
from .models import Ship, Service, Sector, Section, SectorConfig
from .serializers import ShipSerializer, ServiceSerializer, SectorSerializer, SectionSerializer, SectorConfigSerializer
from matrix.core.equipage import tracer_changement_equipage
from matrix.core.mixins import EcritureTraceeMixin
from matrix.core.permissions import RolePermission
from matrix.core.role_thresholds import niveau_requis_pour
from matrix.core.roles import user_role_level

class DefaultPermission(permissions.IsAuthenticated):
    pass


def _is_master_admin(user):
    """Vrai si l'utilisateur a un accès multi-navires (flotte entière) : superutilisateur
    ou rôle MASTER_ADMIN (administrateur général, seul niveau au-dessus de ADMIN_NAVIRE
    dans la hiérarchie). Tous les autres rôles (ADMIN_NAVIRE compris) sont rattachés à
    un navire précis et ne doivent gérer que celui-ci.
    """
    if getattr(user, "is_superuser", False):
        return True
    profile = getattr(user, "profile", None)
    return bool(profile and profile.role == "MASTER_ADMIN")


def _user_ship_id(user):
    """Renvoie l'id du navire de l'utilisateur, ou None si aucun navire rattaché."""
    profile = getattr(user, "profile", None)
    ship = getattr(profile, "ship", None)
    return ship.id if ship else None


class StructureViewSet(EcritureTraceeMixin, viewsets.ModelViewSet):
    """Écriture de la structure du bâtiment : seuil de rôle configurable par unité
    (clé « structure_navire_ecriture »), objets bornés à l'unité de l'appelant et
    chaque création, modification ou suppression tracée."""

    permission_classes = [RolePermission]
    role_threshold_action_write = "structure_navire_ecriture"
    domaine_audit = "org"


def _controler_double_equipage(navire, actif):
    """Bascule explicite du double équipage : jamais d'élévation implicite des droits d'écriture."""
    if actif:
        if not navire.equipage_a_bord:
            raise ValidationError(
                {"double_equipage": "Renseignez d'abord l'équipage à bord (administration) avant d'activer le double équipage."}
            )
        return
    a_terre = get_user_model().objects.filter(is_active=True, profile__ship=navire).exclude(
        profile__equipage__in=["", navire.equipage_a_bord]
    ).count()
    if a_terre:
        raise ValidationError({
            "double_equipage": (
                f"{a_terre} marin(s) de l'équipage à terre retrouveraient un droit d'écriture : "
                "rattachez-les d'abord à l'équipage à bord ou retirez leur équipage."
            )
        })


class ShipViewSet(StructureViewSet):
    queryset = Ship.objects.all().order_by("name")
    serializer_class = ShipSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if _is_master_admin(user):
            return qs
        ship_id = _user_ship_id(user)
        if ship_id is None:
            return Ship.objects.none()
        return qs.filter(id=ship_id)

    def perform_create(self, serializer):
        if not _is_master_admin(self.request.user):
            raise PermissionDenied("Vous ne pouvez pas créer d'unité.")
        super().perform_create(serializer)

    def perform_update(self, serializer):
        user = self.request.user
        navire = serializer.instance
        if not _is_master_admin(user) and navire.id != _user_ship_id(user):
            raise PermissionDenied("Vous ne pouvez modifier que votre unité.")
        donnees = serializer.validated_data
        if donnees.get("equipage_a_bord", navire.equipage_a_bord) != navire.equipage_a_bord:
            raise PermissionDenied("L'équipage à bord change par une relève validée par les deux commandants.")
        sensibles = [c for c in ("double_equipage", "archived") if c in donnees and donnees[c] != getattr(navire, c)]
        if sensibles and user_role_level(user) < niveau_requis_pour(user, "unite_administration"):
            raise PermissionDenied("Archiver une unité ou changer son double équipage est réservé à l'administration.")
        if "double_equipage" in sensibles:
            _controler_double_equipage(navire, donnees["double_equipage"])
        avant = (navire.double_equipage, navire.equipage_a_bord)
        super().perform_update(serializer)
        tracer_changement_equipage(user, serializer.instance, avant)

    def perform_destroy(self, instance):
        # Suppression en cascade de tout le bâtiment : administrateur général seulement.
        if not _is_master_admin(self.request.user):
            raise PermissionDenied("Vous ne pouvez pas supprimer d'unité.")
        super().perform_destroy(instance)

class ServiceViewSet(StructureViewSet):
    queryset = Service.objects.select_related("ship").all().order_by("ship__name", "name")
    serializer_class = ServiceSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if _is_master_admin(user):
            return qs
        ship_id = _user_ship_id(user)
        if ship_id is None:
            return Service.objects.none()
        return qs.filter(ship_id=ship_id)

    def perform_create(self, serializer):
        if not _is_master_admin(self.request.user):
            ship = serializer.validated_data.get("ship")
            user_ship_id = _user_ship_id(self.request.user)
            if not user_ship_id or not ship or ship.id != user_ship_id:
                raise PermissionDenied("Service hors de l'unité autorisée.")
        super().perform_create(serializer)

    def perform_update(self, serializer):
        if not _is_master_admin(self.request.user):
            ship = serializer.validated_data.get("ship") or getattr(self.get_object(), "ship", None)
            user_ship_id = _user_ship_id(self.request.user)
            if not user_ship_id or not ship or ship.id != user_ship_id:
                raise PermissionDenied("Service hors de l'unité autorisée.")
        super().perform_update(serializer)

    def perform_destroy(self, instance):
        if not _is_master_admin(self.request.user):
            user_ship_id = _user_ship_id(self.request.user)
            if not user_ship_id or instance.ship_id != user_ship_id:
                raise PermissionDenied("Service hors de l'unité autorisée.")
        super().perform_destroy(instance)

class SectorViewSet(StructureViewSet):
    queryset = Sector.objects.select_related("service", "service__ship").all().order_by("service__name", "name")
    serializer_class = SectorSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if _is_master_admin(user):
            return qs
        ship_id = _user_ship_id(user)
        if ship_id is None:
            return Sector.objects.none()
        return qs.filter(service__ship_id=ship_id)

    def perform_create(self, serializer):
        if not _is_master_admin(self.request.user):
            service = serializer.validated_data.get("service")
            user_ship_id = _user_ship_id(self.request.user)
            if not user_ship_id or not service or service.ship_id != user_ship_id:
                raise PermissionDenied("Secteur hors de l'unité autorisée.")
        super().perform_create(serializer)

    def perform_update(self, serializer):
        if not _is_master_admin(self.request.user):
            service = serializer.validated_data.get("service") or getattr(self.get_object(), "service", None)
            user_ship_id = _user_ship_id(self.request.user)
            if not user_ship_id or not service or service.ship_id != user_ship_id:
                raise PermissionDenied("Secteur hors de l'unité autorisée.")
        super().perform_update(serializer)

    def perform_destroy(self, instance):
        if not _is_master_admin(self.request.user):
            user_ship_id = _user_ship_id(self.request.user)
            if not user_ship_id or instance.service.ship_id != user_ship_id:
                raise PermissionDenied("Secteur hors de l'unité autorisée.")
        super().perform_destroy(instance)

class SectionViewSet(StructureViewSet):
    queryset = Section.objects.select_related("sector", "sector__service", "sector__service__ship").all().order_by("sector__name", "name")
    serializer_class = SectionSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if _is_master_admin(user):
            return qs
        ship_id = _user_ship_id(user)
        if ship_id is None:
            return Section.objects.none()
        return qs.filter(sector__service__ship_id=ship_id)

    def perform_create(self, serializer):
        if not _is_master_admin(self.request.user):
            sector = serializer.validated_data.get("sector")
            user_ship_id = _user_ship_id(self.request.user)
            if not user_ship_id or not sector or sector.service.ship_id != user_ship_id:
                raise PermissionDenied("Section hors de l'unité autorisée.")
        super().perform_create(serializer)

    def perform_update(self, serializer):
        if not _is_master_admin(self.request.user):
            sector = serializer.validated_data.get("sector") or getattr(self.get_object(), "sector", None)
            user_ship_id = _user_ship_id(self.request.user)
            if not user_ship_id or not sector or sector.service.ship_id != user_ship_id:
                raise PermissionDenied("Section hors de l'unité autorisée.")
        super().perform_update(serializer)

    def perform_destroy(self, instance):
        if not _is_master_admin(self.request.user):
            user_ship_id = _user_ship_id(self.request.user)
            if not user_ship_id or instance.sector.service.ship_id != user_ship_id:
                raise PermissionDenied("Section hors de l'unité autorisée.")
        super().perform_destroy(instance)

class SectorConfigViewSet(StructureViewSet):
    queryset = SectorConfig.objects.select_related("sector").all()
    serializer_class = SectorConfigSerializer

    def get_queryset(self):
        # Même périmètre "navire" que les ViewSets d'organisation ci-dessus
        # (Ship/Service/Sector/Section) : la configuration d'un secteur
        # (préférences d'affichage, seuils d'alerte, widgets du tableau de
        # bord) n'était filtrée par AUCUN périmètre avant cette correction —
        # n'importe quel utilisateur authentifié pouvait lire, et tout
        # utilisateur au seuil d'écriture générique (CHEF_SECTION+) modifier,
        # la configuration d'un secteur appartenant à un AUTRE navire (audit
        # sécurité scoping API, tâche Notion « Audit complet du scoping par
        # périmètre »).
        qs = super().get_queryset()
        user = self.request.user
        if _is_master_admin(user):
            return qs
        ship_id = _user_ship_id(user)
        if ship_id is None:
            return SectorConfig.objects.none()
        return qs.filter(sector__service__ship_id=ship_id)

    def perform_create(self, serializer):
        if not _is_master_admin(self.request.user):
            sector = serializer.validated_data.get("sector")
            user_ship_id = _user_ship_id(self.request.user)
            if not user_ship_id or not sector or sector.service.ship_id != user_ship_id:
                raise PermissionDenied("Configuration hors de l'unité autorisée.")
        super().perform_create(serializer)

    def perform_update(self, serializer):
        if not _is_master_admin(self.request.user):
            sector = serializer.validated_data.get("sector") or getattr(self.get_object(), "sector", None)
            user_ship_id = _user_ship_id(self.request.user)
            if not user_ship_id or not sector or sector.service.ship_id != user_ship_id:
                raise PermissionDenied("Configuration hors de l'unité autorisée.")
        super().perform_update(serializer)

    def perform_destroy(self, instance):
        if not _is_master_admin(self.request.user):
            user_ship_id = _user_ship_id(self.request.user)
            if not user_ship_id or instance.sector.service.ship_id != user_ship_id:
                raise PermissionDenied("Configuration hors de l'unité autorisée.")
        super().perform_destroy(instance)
