from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers
from matrix.core.scopes import resoudre_affectation_dans_perimetre, scope_filters_for_user
from .models import Location, AssetType, ChecklistTemplate, ChecklistItemTemplate, AssetChecklistOverride, Asset, AssetDocument

class LocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Location
        fields = "__all__"

class AssetTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = AssetType
        fields = "__all__"

class ChecklistItemTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChecklistItemTemplate
        fields = "__all__"

class ChecklistTemplateSerializer(serializers.ModelSerializer):
    items = ChecklistItemTemplateSerializer(many=True, read_only=True)

    class Meta:
        model = ChecklistTemplate
        fields = "__all__"

class AssetDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = AssetDocument
        fields = "__all__"

class AssetSerializer(serializers.ModelSerializer):
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

class AssetChecklistOverrideSerializer(serializers.ModelSerializer):
    class Meta:
        model = AssetChecklistOverride
        fields = "__all__"
