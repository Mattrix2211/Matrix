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

class AssetChecklistOverrideSerializer(serializers.ModelSerializer):
    class Meta:
        model = AssetChecklistOverride
        fields = "__all__"
