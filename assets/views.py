from rest_framework import viewsets, permissions, filters, decorators, response
from .models import Location, AssetType, ChecklistTemplate, ChecklistItemTemplate, AssetChecklistOverride, Asset, AssetDocument
from .serializers import (
    LocationSerializer, AssetTypeSerializer, ChecklistTemplateSerializer, ChecklistItemTemplateSerializer,
    AssetChecklistOverrideSerializer, AssetSerializer, AssetDocumentSerializer
)
from bordops.core.mixins import ScopedQuerySetMixin
from bordops.core.permissions import RolePermission

class DefaultPermission(permissions.IsAuthenticated):
    pass

class LocationViewSet(ScopedQuerySetMixin, viewsets.ModelViewSet):
    queryset = Location.objects.select_related("ship", "parent").all()
    serializer_class = LocationSerializer
    permission_classes = [RolePermission]

class AssetTypeViewSet(ScopedQuerySetMixin, viewsets.ModelViewSet):
    queryset = AssetType.objects.select_related("sector", "sector__service", "sector__service__ship").all()
    serializer_class = AssetTypeSerializer
    permission_classes = [RolePermission]
    filter_backends = [filters.SearchFilter]
    search_fields = ["name", "category"]

class ChecklistTemplateViewSet(ScopedQuerySetMixin, viewsets.ModelViewSet):
    queryset = ChecklistTemplate.objects.select_related("sector", "asset_type").prefetch_related("items").all()
    serializer_class = ChecklistTemplateSerializer
    permission_classes = [RolePermission]

class ChecklistItemTemplateViewSet(viewsets.ModelViewSet):
    queryset = ChecklistItemTemplate.objects.select_related("template").all()
    serializer_class = ChecklistItemTemplateSerializer
    permission_classes = [RolePermission]

class AssetViewSet(ScopedQuerySetMixin, viewsets.ModelViewSet):
    queryset = Asset.objects.select_related("asset_type", "ship", "service", "sector", "section", "location").all()
    serializer_class = AssetSerializer
    permission_classes = [RolePermission]
    filter_backends = [filters.SearchFilter]
    search_fields = ["serial_number", "internal_id"]

    @decorators.action(detail=True, methods=["get"], url_path="qr")
    def qr_code(self, request, pk=None):
        import qrcode
        import io
        asset = self.get_object()
        url = request.build_absolute_uri(f"/api/assets/assets/{asset.pk}/")
        img = qrcode.make(url)
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        # For simplicity, return URL; UI can render <img src="/.../qr/"> later if we expose binary endpoint
        return response.Response({"url": url})

    @decorators.action(detail=True, methods=["get"], url_path="qr_png")
    def qr_png(self, request, pk=None):
        import qrcode
        import io
        from django.http import HttpResponse
        asset = self.get_object()
        url = request.build_absolute_uri(f"/api/assets/assets/{asset.pk}/")
        img = qrcode.make(url)
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return HttpResponse(buf.getvalue(), content_type="image/png")

class AssetDocumentViewSet(viewsets.ModelViewSet):
    queryset = AssetDocument.objects.select_related("asset").all()
    serializer_class = AssetDocumentSerializer
    permission_classes = [RolePermission]

class AssetChecklistOverrideViewSet(viewsets.ModelViewSet):
    queryset = AssetChecklistOverride.objects.select_related("asset", "template").all()
    serializer_class = AssetChecklistOverrideSerializer
    permission_classes = [RolePermission]
