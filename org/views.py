from rest_framework import viewsets, permissions
from rest_framework.exceptions import PermissionDenied
from .models import Ship, Service, Sector, Section, SectorConfig
from .serializers import ShipSerializer, ServiceSerializer, SectorSerializer, SectionSerializer, SectorConfigSerializer
from matrix.core.permissions import RolePermission

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


class ShipViewSet(viewsets.ModelViewSet):
    queryset = Ship.objects.all().order_by("name")
    serializer_class = ShipSerializer
    permission_classes = [RolePermission]

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
        # Seul un administrateur général peut créer un nouveau navire dans la flotte.
        if not _is_master_admin(self.request.user):
            raise PermissionDenied("Vous ne pouvez pas créer d'unité.")
        serializer.save()

    def perform_update(self, serializer):
        # Un utilisateur non administrateur général ne peut modifier que son propre navire.
        if not _is_master_admin(self.request.user):
            instance = self.get_object()
            user_ship_id = _user_ship_id(self.request.user)
            if not user_ship_id or instance.id != user_ship_id:
                raise PermissionDenied("Vous ne pouvez modifier que votre unité.")
        serializer.save()

class ServiceViewSet(viewsets.ModelViewSet):
    queryset = Service.objects.select_related("ship").all().order_by("ship__name", "name")
    serializer_class = ServiceSerializer
    permission_classes = [RolePermission]

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
        serializer.save()

    def perform_update(self, serializer):
        if not _is_master_admin(self.request.user):
            ship = serializer.validated_data.get("ship") or getattr(self.get_object(), "ship", None)
            user_ship_id = _user_ship_id(self.request.user)
            if not user_ship_id or not ship or ship.id != user_ship_id:
                raise PermissionDenied("Service hors de l'unité autorisée.")
        serializer.save()

class SectorViewSet(viewsets.ModelViewSet):
    queryset = Sector.objects.select_related("service", "service__ship").all().order_by("service__name", "name")
    serializer_class = SectorSerializer
    permission_classes = [RolePermission]

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
        serializer.save()

    def perform_update(self, serializer):
        if not _is_master_admin(self.request.user):
            service = serializer.validated_data.get("service") or getattr(self.get_object(), "service", None)
            user_ship_id = _user_ship_id(self.request.user)
            if not user_ship_id or not service or service.ship_id != user_ship_id:
                raise PermissionDenied("Secteur hors de l'unité autorisée.")
        serializer.save()

class SectionViewSet(viewsets.ModelViewSet):
    queryset = Section.objects.select_related("sector", "sector__service", "sector__service__ship").all().order_by("sector__name", "name")
    serializer_class = SectionSerializer
    permission_classes = [RolePermission]

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
        serializer.save()

    def perform_update(self, serializer):
        if not _is_master_admin(self.request.user):
            sector = serializer.validated_data.get("sector") or getattr(self.get_object(), "sector", None)
            user_ship_id = _user_ship_id(self.request.user)
            if not user_ship_id or not sector or sector.service.ship_id != user_ship_id:
                raise PermissionDenied("Section hors de l'unité autorisée.")
        serializer.save()

class SectorConfigViewSet(viewsets.ModelViewSet):
    queryset = SectorConfig.objects.select_related("sector").all()
    serializer_class = SectorConfigSerializer
    permission_classes = [RolePermission]

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
        serializer.save()

    def perform_update(self, serializer):
        if not _is_master_admin(self.request.user):
            sector = serializer.validated_data.get("sector") or getattr(self.get_object(), "sector", None)
            user_ship_id = _user_ship_id(self.request.user)
            if not user_ship_id or not sector or sector.service.ship_id != user_ship_id:
                raise PermissionDenied("Configuration hors de l'unité autorisée.")
        serializer.save()
