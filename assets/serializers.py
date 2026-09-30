from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers
from matrix.core.scopes import resoudre_affectation_dans_perimetre, scope_filters_for_user
from matrix.core.serializers import ReferencesDansPerimetreMixin
from .models import Location, AssetType, ChecklistTemplate, ChecklistItemTemplate, AssetChecklistOverride, Asset, AssetDocument

# Chemins de périmètre (matrix.core.mixins.build_scope_q) des objets référencés,
# identiques à ceux des ViewSets correspondants (assets/views.py) ; _PERIMETRE_PAR_SECTEUR
# sert aux types d'actif et aux modèles de checklist, rattachés à un secteur.
_PERIMETRE_NAVIRE = {
    "ship_id": "id", "service_id": "services__id",
    "sector_id": "services__sectors__id", "section_id": "services__sectors__sections__id",
}
_PERIMETRE_SECTEUR = {"ship_id": "service__ship_id", "service_id": "service_id", "sector_id": "id"}
_PERIMETRE_LIEU = {
    "ship_id": "ship_id", "service_id": "ship__services__id",
    "sector_id": "ship__services__sectors__id", "section_id": "ship__services__sectors__sections__id",
}
_PERIMETRE_PAR_SECTEUR = {
    "ship_id": "sector__service__ship_id", "service_id": "sector__service_id", "sector_id": "sector_id",
}


class LocationSerializer(ReferencesDansPerimetreMixin, serializers.ModelSerializer):
    references_perimetre = {"ship": (_PERIMETRE_NAVIRE,), "parent": (_PERIMETRE_LIEU,)}

    class Meta:
        model = Location
        fields = ("id", "ship", "name", "parent", "created_at", "updated_at")
        read_only_fields = ("id", "created_at", "updated_at")


class AssetTypeSerializer(ReferencesDansPerimetreMixin, serializers.ModelSerializer):
    references_perimetre = {"sector": (_PERIMETRE_SECTEUR,)}

    class Meta:
        model = AssetType
        fields = ("id", "name", "category", "sector", "created_at", "updated_at")
        read_only_fields = ("id", "created_at", "updated_at")


class ChecklistItemTemplateSerializer(ReferencesDansPerimetreMixin, serializers.ModelSerializer):
    references_perimetre = {"template": (_PERIMETRE_PAR_SECTEUR,)}

    class Meta:
        model = ChecklistItemTemplate
        fields = (
            "id", "template", "label", "field_type", "required", "requires_photo", "unit",
            "choices", "order", "created_at", "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")


class ChecklistTemplateSerializer(ReferencesDansPerimetreMixin, serializers.ModelSerializer):
    items = ChecklistItemTemplateSerializer(many=True, read_only=True)
    references_perimetre = {"sector": (_PERIMETRE_SECTEUR,), "asset_type": (_PERIMETRE_PAR_SECTEUR,)}

    class Meta:
        model = ChecklistTemplate
        fields = ("id", "name", "sector", "asset_type", "items", "created_at", "updated_at")
        read_only_fields = ("id", "created_at", "updated_at")


class AssetDocumentSerializer(ReferencesDansPerimetreMixin, serializers.ModelSerializer):
    references_perimetre = {"asset": ("",)}

    class Meta:
        model = AssetDocument
        fields = ("id", "asset", "file", "name", "created_by", "updated_by", "created_at", "updated_at")
        # created_by/updated_by sont posés côté serveur (AssetDocumentViewSet).
        read_only_fields = ("id", "created_by", "updated_by", "created_at", "updated_at")


class AssetSerializer(ReferencesDansPerimetreMixin, serializers.ModelSerializer):
    # Le parent est un autre matériel, le lieu et le type ont leur propre périmètre.
    references_perimetre = {
        "parent": ("",), "location": (_PERIMETRE_LIEU,), "asset_type": (_PERIMETRE_PAR_SECTEUR,),
    }

    class Meta:
        model = Asset
        fields = (
            "id", "asset_type", "serial_number", "internal_id", "designation", "nno", "reference",
            "marque", "gisement", "local", "photo", "location", "ship", "service", "sector",
            "section", "status", "criticality", "folder", "parent", "plan_deck",
            "position_x", "position_y", "created_by", "updated_by", "created_at", "updated_at",
        )
        # created_by/updated_by sont posés côté serveur (AssetViewSet).
        read_only_fields = ("id", "created_by", "updated_by", "created_at", "updated_at")

    def validate(self, attrs):
        attrs = super().validate(attrs)
        # Le rattachement (navire/service/secteur/section) doit rester dans le
        # périmètre de l'appelant, comme pour l'annuaire (mêmes règles que
        # UserProfileSerializer.validate) ; sans périmètre défini (ex.
        # administrateur général), aucune restriction, comme pour la lecture.
        acting_user = getattr(self.context.get("request"), "user", None)
        champs = ("ship", "service", "sector", "section")
        if acting_user is not None and scope_filters_for_user(acting_user) and any(attrs.get(c) is not None for c in champs):
            ok, *_ = resoudre_affectation_dans_perimetre(
                acting_user, **{f"{c}_id": attrs[c].id if attrs.get(c) is not None else None for c in champs}
            )
            if not ok:
                raise serializers.ValidationError(
                    "Unité, service, secteur ou section invalide, ou hors de votre périmètre."
                )

        # Reproduit ici la règle métier de Asset.clean() (protection anti-cycle
        # sur le rattachement parent/enfant) : AssetViewSet est un ModelViewSet
        # DRF standard qui n'appelle pas full_clean() automatiquement, il faut
        # donc revalider explicitement à ce niveau pour qu'un parent cyclique
        # soit rejeté proprement (400) via l'API, et non provoquer une erreur
        # serveur (500) laissée à Asset.save() (même pattern que
        # training/serializers.py::TrainingRecordSerializer.validate()).
        pk = self.instance.pk if self.instance else None
        parent = attrs["parent"] if "parent" in attrs else (self.instance.parent if self.instance else None)
        candidat = Asset(pk=pk, parent=parent)
        try:
            candidat.clean()
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.message_dict if hasattr(exc, "message_dict") else exc.messages)
        return attrs

class AssetChecklistOverrideSerializer(ReferencesDansPerimetreMixin, serializers.ModelSerializer):
    references_perimetre = {"asset": ("",), "template": (_PERIMETRE_PAR_SECTEUR,)}

    class Meta:
        model = AssetChecklistOverride
        fields = ("id", "asset", "template", "extra_items", "overrides", "created_at", "updated_at")
        read_only_fields = ("id", "created_at", "updated_at")
