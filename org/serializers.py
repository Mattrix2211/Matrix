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

    def validate(self, attrs):
        # Le commandant adjoint d'un service doit appartenir au même navire.
        coma = attrs.get("commandant_adjoint")
        ship = attrs.get("ship") or getattr(self.instance, "ship", None)
        if coma and ship and coma.ship_id != ship.id:
            raise serializers.ValidationError(
                {"commandant_adjoint": "Ce poste (COMAEQ, COMOPS, COMANAV, COMAVIA) n'appartient pas à l'unité du service."}
            )
        return attrs

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
