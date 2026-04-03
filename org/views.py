from rest_framework import viewsets, permissions
from rest_framework.exceptions import PermissionDenied
from .models import Ship, Service, Sector, Section, SectorConfig
from .serializers import ShipSerializer, ServiceSerializer, SectorSerializer, SectionSerializer, SectorConfigSerializer
from bordops.core.permissions import RolePermission

class DefaultPermission(permissions.IsAuthenticated):
    pass

def _is_admin_navire(user):
    profile = getattr(user, "profile", None)
    return bool(profile and profile.role == "ADMIN_NAVIRE")


class ShipViewSet(viewsets.ModelViewSet):
    queryset = Ship.objects.all().order_by("name")
    serializer_class = ShipSerializer
    permission_classes = [RolePermission]

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if _is_admin_navire(user):
            ship = getattr(user.profile, "ship", None)
            if ship is None:
                return Ship.objects.none()
            return qs.filter(id=ship.id)
        return qs

    def perform_create(self, serializer):
        # ADMIN_NAVIRE ne peut pas créer de nouveaux navires
        if _is_admin_navire(self.request.user):
            raise PermissionDenied("Vous ne pouvez pas créer de navire.")
        serializer.save()

    def perform_update(self, serializer):
        # ADMIN_NAVIRE ne peut modifier que son propre navire
        if _is_admin_navire(self.request.user):
            instance = self.get_object()
            user_ship = getattr(self.request.user.profile, "ship", None)
            if not user_ship or instance.id != user_ship.id:
                raise PermissionDenied("Vous ne pouvez modifier que votre navire.")
        serializer.save()

class ServiceViewSet(viewsets.ModelViewSet):
    queryset = Service.objects.select_related("ship").all().order_by("ship__name", "name")
    serializer_class = ServiceSerializer
    permission_classes = [RolePermission]

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if _is_admin_navire(user):
            ship = getattr(user.profile, "ship", None)
            if ship is None:
                return Service.objects.none()
            return qs.filter(ship_id=ship.id)
        return qs

    def perform_create(self, serializer):
        if _is_admin_navire(self.request.user):
            ship = serializer.validated_data.get("ship")
            user_ship = getattr(self.request.user.profile, "ship", None)
            if not user_ship or not ship or ship.id != user_ship.id:
                raise PermissionDenied("Service hors du navire autorisé.")
        serializer.save()

    def perform_update(self, serializer):
        if _is_admin_navire(self.request.user):
            ship = serializer.validated_data.get("ship") or getattr(self.get_object(), "ship", None)
            user_ship = getattr(self.request.user.profile, "ship", None)
            if not user_ship or not ship or ship.id != user_ship.id:
                raise PermissionDenied("Service hors du navire autorisé.")
        serializer.save()

class SectorViewSet(viewsets.ModelViewSet):
    queryset = Sector.objects.select_related("service", "service__ship").all().order_by("service__name", "name")
    serializer_class = SectorSerializer
    permission_classes = [RolePermission]

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if _is_admin_navire(user):
            ship = getattr(user.profile, "ship", None)
            if ship is None:
                return Sector.objects.none()
            return qs.filter(service__ship_id=ship.id)
        return qs

    def perform_create(self, serializer):
        if _is_admin_navire(self.request.user):
            service = serializer.validated_data.get("service")
            user_ship = getattr(self.request.user.profile, "ship", None)
            if not user_ship or not service or service.ship_id != user_ship.id:
                raise PermissionDenied("Secteur hors du navire autorisé.")
        serializer.save()

    def perform_update(self, serializer):
        if _is_admin_navire(self.request.user):
            service = serializer.validated_data.get("service") or getattr(self.get_object(), "service", None)
            user_ship = getattr(self.request.user.profile, "ship", None)
            if not user_ship or not service or service.ship_id != user_ship.id:
                raise PermissionDenied("Secteur hors du navire autorisé.")
        serializer.save()

class SectionViewSet(viewsets.ModelViewSet):
    queryset = Section.objects.select_related("sector", "sector__service", "sector__service__ship").all().order_by("sector__name", "name")
    serializer_class = SectionSerializer
    permission_classes = [RolePermission]

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if _is_admin_navire(user):
            ship = getattr(user.profile, "ship", None)
            if ship is None:
                return Section.objects.none()
            return qs.filter(sector__service__ship_id=ship.id)
        return qs

    def perform_create(self, serializer):
        if _is_admin_navire(self.request.user):
            sector = serializer.validated_data.get("sector")
            user_ship = getattr(self.request.user.profile, "ship", None)
            if not user_ship or not sector or sector.service.ship_id != user_ship.id:
                raise PermissionDenied("Section hors du navire autorisé.")
        serializer.save()

    def perform_update(self, serializer):
        if _is_admin_navire(self.request.user):
            sector = serializer.validated_data.get("sector") or getattr(self.get_object(), "sector", None)
            user_ship = getattr(self.request.user.profile, "ship", None)
            if not user_ship or not sector or sector.service.ship_id != user_ship.id:
                raise PermissionDenied("Section hors du navire autorisé.")
        serializer.save()

class SectorConfigViewSet(viewsets.ModelViewSet):
    queryset = SectorConfig.objects.select_related("sector").all()
    serializer_class = SectorConfigSerializer
    permission_classes = [RolePermission]
