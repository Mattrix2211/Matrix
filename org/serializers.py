from rest_framework import serializers
from matrix.core.serializers import ReferencesDansPerimetreMixin
from .models import Ship, Service, Sector, Section, SectorConfig

# Chemins de périmètre (matrix.core.mixins.build_scope_q) des objets référencés :
# un marin limité à un service, un secteur ou une section ne peut rattacher un
# objet qu'à l'intérieur de ce périmètre, comme pour la lecture.
_PERIMETRE_NAVIRE = {
    "ship_id": "id", "service_id": "services__id",
    "sector_id": "services__sectors__id", "section_id": "services__sectors__sections__id",
}
_PERIMETRE_SERVICE = {
    "ship_id": "ship_id", "service_id": "id",
    "sector_id": "sectors__id", "section_id": "sectors__sections__id",
}
_PERIMETRE_SECTEUR = {
    "ship_id": "service__ship_id", "service_id": "service_id",
    "sector_id": "id", "section_id": "sections__id",
}


class ShipSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ship
        fields = (
            "id", "name", "code", "type_unite", "classe_navire",
            "double_equipage", "equipage_a_bord", "archived", "created_at", "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")

class ServiceSerializer(ReferencesDansPerimetreMixin, serializers.ModelSerializer):
    references_perimetre = {"ship": (_PERIMETRE_NAVIRE,)}

    class Meta:
        model = Service
        fields = ("id", "ship", "name", "commandant_adjoint", "archived", "created_at", "updated_at")
        # Le commandant adjoint route les visas : réglage administratif, pas via l'API.
        read_only_fields = ("id", "commandant_adjoint", "created_at", "updated_at")

class SectorSerializer(ReferencesDansPerimetreMixin, serializers.ModelSerializer):
    references_perimetre = {"service": (_PERIMETRE_SERVICE,)}

    class Meta:
        model = Sector
        fields = ("id", "service", "name", "color", "archived", "created_at", "updated_at")
        read_only_fields = ("id", "created_at", "updated_at")

class SectionSerializer(ReferencesDansPerimetreMixin, serializers.ModelSerializer):
    references_perimetre = {"sector": (_PERIMETRE_SECTEUR,)}

    class Meta:
        model = Section
        fields = ("id", "sector", "name", "archived", "created_at", "updated_at")
        read_only_fields = ("id", "created_at", "updated_at")

class SectorConfigSerializer(ReferencesDansPerimetreMixin, serializers.ModelSerializer):
    references_perimetre = {"sector": (_PERIMETRE_SECTEUR,)}

    class Meta:
        model = SectorConfig
        fields = (
            "id", "sector", "ui_preferences", "status_overrides", "alert_thresholds",
            "dashboard_widgets", "created_at", "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")
