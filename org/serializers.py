from rest_framework import serializers
from matrix.core.equipage import equipage_a_bord
from matrix.core.serializers import ReferencesDansPerimetreMixin
from .archivage import erreur_changement
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


class ArchivageValidationMixin:
    """Archiver une unité occupée, ou créer / réactiver sous une unité archivée, est refusé (règle de org/archivage.py)."""

    def validate(self, attrs):
        attrs = super().validate(attrs)
        modele = self.Meta.model
        if self.instance is not None:
            unite = modele.objects.get(pk=self.instance.pk)
            for champ, valeur in attrs.items():
                setattr(unite, champ, valeur)
        else:
            unite = modele(**{k: v for k, v in attrs.items() if k in {f.name for f in modele._meta.concrete_fields}})
        message = erreur_changement(unite, unite.archived, self.instance)
        if message:
            raise serializers.ValidationError({"archived" if "archived" in attrs else "detail": message})
        return attrs


class EquipageABordField(serializers.CharField):
    """Lecture par l'accesseur unique : les relèves échues sont appliquées avant d'exposer l'équipage."""

    def get_attribute(self, instance):
        return equipage_a_bord(instance)


class ShipSerializer(ArchivageValidationMixin, serializers.ModelSerializer):
    equipage_a_bord = EquipageABordField(max_length=8, required=False, allow_blank=True)

    class Meta:
        model = Ship
        fields = (
            "id", "name", "code", "type_unite", "classe_navire",
            "double_equipage", "equipage_a_bord", "fuseau_horaire", "archived", "created_at", "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")

    def update(self, instance, validated_data):
        # L'équipage à bord change par relève : jamais réécrit par une instance lue avant.
        validated_data.pop("equipage_a_bord", None)
        for champ, valeur in validated_data.items():
            setattr(instance, champ, valeur)
        instance.save(update_fields=[*validated_data, "updated_at"])
        equipage_a_bord(instance)
        return instance

class ServiceSerializer(ArchivageValidationMixin, ReferencesDansPerimetreMixin, serializers.ModelSerializer):
    references_perimetre = {"ship": (_PERIMETRE_NAVIRE,)}

    class Meta:
        model = Service
        fields = ("id", "ship", "name", "commandant_adjoint", "archived", "created_at", "updated_at")
        # Le commandant adjoint route les visas : réglage administratif, pas via l'API.
        read_only_fields = ("id", "commandant_adjoint", "created_at", "updated_at")

class SectorSerializer(ArchivageValidationMixin, ReferencesDansPerimetreMixin, serializers.ModelSerializer):
    references_perimetre = {"service": (_PERIMETRE_SERVICE,)}

    class Meta:
        model = Sector
        fields = ("id", "service", "name", "color", "archived", "created_at", "updated_at")
        read_only_fields = ("id", "created_at", "updated_at")

class SectionSerializer(ArchivageValidationMixin, ReferencesDansPerimetreMixin, serializers.ModelSerializer):
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
