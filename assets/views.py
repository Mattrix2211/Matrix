from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404
from rest_framework import viewsets, permissions, filters, decorators, response
from .models import Location, AssetType, ChecklistTemplate, ChecklistItemTemplate, AssetChecklistOverride, Asset, AssetDocument, Installation
from .serializers import (
    LocationSerializer, AssetTypeSerializer, ChecklistTemplateSerializer, ChecklistItemTemplateSerializer,
    AssetChecklistOverrideSerializer, AssetSerializer, AssetDocumentSerializer
)
from matrix.core.mixins import ScopedQuerySetMixin, build_scope_q
from matrix.core.permissions import RolePermission
from matrix.core.scopes import scope_filters_for_user

class DefaultPermission(permissions.IsAuthenticated):
    pass


def _construire_qr_png(url):
    """Génère l'image PNG d'un QR code pointant vers l'URL donnée. Factorise le
    code commun entre matériel mobile (Asset) et installation fixe (Installation)."""
    import qrcode
    import io
    img = qrcode.make(url)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()

class LocationViewSet(ScopedQuerySetMixin, viewsets.ModelViewSet):
    queryset = Location.objects.select_related("ship", "parent").all()
    serializer_class = LocationSerializer
    permission_classes = [RolePermission]

    def get_scoped_filters(self):
        # Un lieu (compartiment du navire) n'est rattaché qu'au navire
        # (champ "ship"), jamais à un service/secteur/section précis.
        # Quel que soit le niveau du périmètre de l'utilisateur, on
        # retrouve le navire concerné en remontant la hiérarchie inverse
        # Navire -> Service -> Secteur -> Section (related_names
        # "services"/"sectors"/"sections" définis dans org/models.py).
        return build_scope_q(
            self.request.user,
            {
                "ship_id": "ship_id",
                "service_id": "ship__services__id",
                "sector_id": "ship__services__sectors__id",
                "section_id": "ship__services__sectors__sections__id",
            },
        )

class AssetTypeViewSet(ScopedQuerySetMixin, viewsets.ModelViewSet):
    queryset = AssetType.objects.select_related("sector", "sector__service", "sector__service__ship").all()
    serializer_class = AssetTypeSerializer
    permission_classes = [RolePermission]
    filter_backends = [filters.SearchFilter]
    search_fields = ["name", "category"]

    def get_scoped_filters(self):
        # Un type d'actif est toujours rattaché à un secteur précis (champ
        # obligatoire) : ce n'est pas un référentiel global partagé par
        # toute la flotte. Même traduction de périmètre que
        # MaintenancePlanViewSet (maintenance/views.py) pour son
        # asset_type. Un secteur n'étant jamais découpé par section, un
        # utilisateur au périmètre "section" ne voit aucun type d'actif.
        return build_scope_q(
            self.request.user,
            {
                "ship_id": "sector__service__ship_id",
                "service_id": "sector__service_id",
                "sector_id": "sector_id",
            },
        )

class ChecklistTemplateViewSet(ScopedQuerySetMixin, viewsets.ModelViewSet):
    queryset = ChecklistTemplate.objects.select_related("sector", "asset_type").prefetch_related("items").all()
    serializer_class = ChecklistTemplateSerializer
    permission_classes = [RolePermission]

    def get_scoped_filters(self):
        # Un modèle de checklist est toujours rattaché à un secteur précis
        # (champ obligatoire), au même titre qu'un type d'actif : même
        # traduction de périmètre que AssetTypeViewSet ci-dessus.
        return build_scope_q(
            self.request.user,
            {
                "ship_id": "sector__service__ship_id",
                "service_id": "sector__service_id",
                "sector_id": "sector_id",
            },
        )

class ChecklistItemTemplateViewSet(ScopedQuerySetMixin, viewsets.ModelViewSet):
    queryset = ChecklistItemTemplate.objects.select_related("template").all()
    serializer_class = ChecklistItemTemplateSerializer
    permission_classes = [RolePermission]

    def get_scoped_filters(self):
        # Une ligne de checklist n'est rattachée qu'indirectement à un
        # secteur, via son modèle de checklist (template) — même traduction
        # de périmètre que ChecklistTemplateViewSet ci-dessus, préfixée par
        # la relation "template__".
        return build_scope_q(
            self.request.user,
            {
                "ship_id": "template__sector__service__ship_id",
                "service_id": "template__sector__service_id",
                "sector_id": "template__sector_id",
            },
        )

class AssetViewSet(ScopedQuerySetMixin, viewsets.ModelViewSet):
    queryset = Asset.objects.select_related("asset_type", "ship", "service", "sector", "section", "location").all()
    serializer_class = AssetSerializer
    permission_classes = [RolePermission]
    filter_backends = [filters.SearchFilter]
    search_fields = ["serial_number", "internal_id"]

    @decorators.action(detail=True, methods=["get"], url_path="qr")
    def qr_code(self, request, pk=None):
        # Le QR pointe vers la vue web /scan/<uuid>/ (checklist du jour ou fiche
        # équipement), pas vers l'API JSON brute — inutilisable au poste de travail.
        asset = self.get_object()
        url = request.build_absolute_uri(f"/scan/{asset.pk}/")
        return response.Response({"url": url})

    @decorators.action(detail=True, methods=["get"], url_path="qr_png")
    def qr_png(self, request, pk=None):
        asset = self.get_object()
        url = request.build_absolute_uri(f"/scan/{asset.pk}/")
        return HttpResponse(_construire_qr_png(url), content_type="image/png")

class AssetDocumentViewSet(ScopedQuerySetMixin, viewsets.ModelViewSet):
    queryset = AssetDocument.objects.select_related("asset").all()
    serializer_class = AssetDocumentSerializer
    permission_classes = [RolePermission]

    def get_scoped_filters(self):
        # Un document n'est rattaché qu'indirectement à un navire/service/
        # secteur/section, via le matériel mobile auquel il appartient (le
        # champ "asset" porte lui-même les 4 niveaux) : même principe que
        # LocationViewSet.get_scoped_filters ci-dessus, préfixé par "asset__".
        return build_scope_q(self.request.user, "asset__")

class AssetChecklistOverrideViewSet(ScopedQuerySetMixin, viewsets.ModelViewSet):
    queryset = AssetChecklistOverride.objects.select_related("asset", "template").all()
    serializer_class = AssetChecklistOverrideSerializer
    permission_classes = [RolePermission]

    def get_scoped_filters(self):
        # Une personnalisation de checklist est rattachée à un matériel
        # mobile précis (champ "asset", qui porte lui-même les 4 niveaux de
        # périmètre) : même traduction que AssetDocumentViewSet ci-dessus.
        return build_scope_q(self.request.user, "asset__")


def _installation_scopee_ou_404(request, pk):
    """Récupère une installation par pk en appliquant le périmètre de
    l'utilisateur (scope_filters_for_user, même système que ScopedQuerySetMixin
    côté DRF) — une installation hors périmètre est traitée comme introuvable."""
    filtres = scope_filters_for_user(request.user)
    queryset = Installation.objects.filter(**filtres) if filtres else Installation.objects.all()
    return get_object_or_404(queryset, pk=pk)


@login_required
def installation_qr_code(request, pk):
    """Équivalent de AssetViewSet.qr_code pour une installation fixe : renvoie
    l'URL du QR (vue web /scan/<uuid>/), en JSON."""
    installation = _installation_scopee_ou_404(request, pk)
    url = request.build_absolute_uri(f"/scan/{installation.pk}/")
    return JsonResponse({"url": url})


@login_required
def installation_qr_png(request, pk):
    """Équivalent de AssetViewSet.qr_png pour une installation fixe : renvoie
    l'image PNG du QR à imprimer/apposer sur l'installation."""
    installation = _installation_scopee_ou_404(request, pk)
    url = request.build_absolute_uri(f"/scan/{installation.pk}/")
    return HttpResponse(_construire_qr_png(url), content_type="image/png")
