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
        # Double équipage : un service appartient obligatoirement à l'un des deux équipages.
        equipage = attrs.get("equipage", getattr(self.instance, "equipage", None))
        if equipage and ship and equipage.ship_id != ship.id:
            raise serializers.ValidationError({"equipage": "Cet équipage n'appartient pas à l'unité du service."})
        if ship and ship.double_equipage and equipage is None:
            raise serializers.ValidationError({"equipage": "Choisissez l'équipage du service."})
        return attrs

class SectorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Sector
        fields = "__all__"

    def validate(self, attrs):
        # Un secteur hérite de l'équipage de son service.
        service = attrs.get("service") or getattr(self.instance, "service", None)
        if service:
            attrs["equipage"] = service.equipage
        return attrs

class SectionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Section
        fields = "__all__"

    def validate(self, attrs):
        # Une section hérite de l'équipage de son secteur.
        sector = attrs.get("sector") or getattr(self.instance, "sector", None)
        if sector:
            attrs["equipage"] = sector.equipage
        return attrs

class SectorConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = SectorConfig
        fields = "__all__"
