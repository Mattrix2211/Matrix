import copy

from django.core.exceptions import ValidationError as DjangoValidationError
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
            "id", "name", "code", "type_unite", "classe_navire", "capacite_aviation",
            "double_equipage", "equipage_a_bord", "equipage_releve", "date_releve",
            "archived", "created_at", "updated_at",
        )
        # Le double équipage (activation, équipage à bord, relève) ne se modifie que par
        # les actions tracées de org/equipages.py, jamais par une écriture directe.
        read_only_fields = (
            "id", "double_equipage", "equipage_a_bord", "equipage_releve", "date_releve",
            "created_at", "updated_at",
        )

class ServiceSerializer(ReferencesDansPerimetreMixin, serializers.ModelSerializer):
    references_perimetre = {"ship": (_PERIMETRE_NAVIRE,)}

    class Meta:
        model = Service
        fields = ("id", "ship", "name", "commandant_adjoint", "equipage", "archived", "created_at", "updated_at")
        read_only_fields = ("id", "created_at", "updated_at")

    def validate(self, attrs):
        attrs = super().validate(attrs)
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

class SectorSerializer(ReferencesDansPerimetreMixin, serializers.ModelSerializer):
    references_perimetre = {"service": (_PERIMETRE_SERVICE,)}

    class Meta:
        model = Sector
        fields = ("id", "service", "name", "color", "equipage", "archived", "created_at", "updated_at")
        # L'équipage est copié du service par le serveur.
        read_only_fields = ("id", "equipage", "created_at", "updated_at")

    def validate(self, attrs):
        attrs = super().validate(attrs)
        # Un secteur hérite de l'équipage de son service.
        service = attrs.get("service") or getattr(self.instance, "service", None)
        if service:
            attrs["equipage"] = service.equipage
        return attrs

class SectionSerializer(ReferencesDansPerimetreMixin, serializers.ModelSerializer):
    references_perimetre = {"sector": (_PERIMETRE_SECTEUR,)}

    class Meta:
        model = Section
        fields = ("id", "sector", "name", "equipage", "archived", "created_at", "updated_at")
        # L'équipage est copié du secteur par le serveur.
        read_only_fields = ("id", "equipage", "created_at", "updated_at")

    def validate(self, attrs):
        attrs = super().validate(attrs)
        # Une section hérite de l'équipage de son secteur.
        sector = attrs.get("sector") or getattr(self.instance, "sector", None)
        if sector:
            attrs["equipage"] = sector.equipage
        return attrs

class SectorConfigSerializer(ReferencesDansPerimetreMixin, serializers.ModelSerializer):
    references_perimetre = {"sector": (_PERIMETRE_SECTEUR,)}

    class Meta:
        model = SectorConfig
        fields = (
            "id", "sector", "ui_preferences", "status_overrides", "alert_thresholds",
            "dashboard_widgets", "created_at", "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")
