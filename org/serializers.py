from rest_framework import serializers
from .models import Ship, Service, Sector, Section, SectorConfig

class ShipSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ship
        fields = "__all__"

class ServiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Service
        fields = "__all__"
        # Le commandant adjoint route les visas : réglage administratif, pas via l'API.
        read_only_fields = ("commandant_adjoint",)

class SectorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Sector
        fields = "__all__"

class SectionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Section
        fields = "__all__"

class SectorConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = SectorConfig
        fields = "__all__"
