from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers
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
        fields = "__all__"

    def validate(self, attrs):
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
