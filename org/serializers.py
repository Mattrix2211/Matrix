import copy

from django.core.exceptions import ValidationError as DjangoValidationError
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
        # Mêmes règles que l'administration : Service.clean() (poste et équipage
        # de la même unité, poste du même équipage, changement d'équipage sans
        # conflit sur les secteurs, sections et affectations).
        if self.instance is not None:
            candidat = copy.copy(self.instance)
            for champ, valeur in attrs.items():
                setattr(candidat, champ, valeur)
        else:
            candidat = Service(**attrs)
        try:
            candidat.clean()
        except DjangoValidationError as erreur:
            raise serializers.ValidationError(erreur.message_dict)
        # Double équipage : un service appartient obligatoirement à l'un des deux équipages.
        if candidat.ship_id and candidat.ship.double_equipage and candidat.equipage_id is None:
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
