from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers
from rest_framework.exceptions import PermissionDenied
from .models import Location, AssetType, ChecklistTemplate, ChecklistItemTemplate, AssetChecklistOverride, Asset, AssetDocument, CategorieCatalogue, ArticleCatalogue
from .permissions import peut_gerer_catalogue
from .catalogue_photo import valider_photo

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
        read_only_fields = ["cle"]

    def validate_template(self, template):
        if template.fiche_id is not None:
            raise serializers.ValidationError("Les lignes d'une version de fiche ne se modifient que par le circuit de validation.")
        return template

class ChecklistTemplateSerializer(serializers.ModelSerializer):
    items = ChecklistItemTemplateSerializer(many=True, read_only=True)

    class Meta:
        model = ChecklistTemplate
        fields = "__all__"
        # Le cycle de vie d'une version de fiche relève du circuit de validation, pas de l'API.
        read_only_fields = ["fiche", "numero", "etat", "redacteur", "role_redacteur", "equipage", "motif_refus", "valide_le"]

class AssetDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = AssetDocument
        fields = "__all__"
        read_only_fields = ["created_by", "updated_by"]

class AssetSerializer(serializers.ModelSerializer):
    class Meta:
        model = Asset
        fields = "__all__"
        # Le lien au catalogue n'est posé que par l'assistant « Équiper le navire ».
        read_only_fields = ["created_by", "updated_by", "article_catalogue"]

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
        mise = attrs["date_mise_en_service"] if "date_mise_en_service" in attrs else (self.instance.date_mise_en_service if self.instance else None)
        peremption = attrs["date_peremption"] if "date_peremption" in attrs else (self.instance.date_peremption if self.instance else None)
        if mise and peremption and peremption < mise:
            raise serializers.ValidationError({"date_peremption": "La péremption ne peut pas précéder la mise en service."})
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


class _CatalogueSerializer(serializers.ModelSerializer):
    """Socle : valide les cycles et refuse d'écrire hors de sa spécialité (403)."""

    def _verifier_droit(self, specialite):
        if not peut_gerer_catalogue(self.context["request"].user, specialite):
            raise PermissionDenied("Vous n'êtes pas responsable de cette spécialité.")

    def validate_photo(self, fichier):
        try:
            return valider_photo(fichier)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.messages)

    def _verifier_modele(self, candidat):
        try:
            candidat.clean()
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.message_dict if hasattr(exc, "message_dict") else exc.messages)


class CategorieCatalogueSerializer(_CatalogueSerializer):
    class Meta:
        model = CategorieCatalogue
        fields = "__all__"
        read_only_fields = ["created_by", "updated_by"]

    def validate(self, attrs):
        i = self.instance
        pk = i.pk if i else None
        parent = attrs["parent"] if "parent" in attrs else (i.parent if i else None)
        specialite = attrs.get("specialite") or (i.specialite if i else None)
        self._verifier_droit(specialite)
        self._verifier_modele(CategorieCatalogue(pk=pk, parent=parent, specialite=specialite))
        return attrs


class ArticleCatalogueSerializer(_CatalogueSerializer):
    specialite = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = ArticleCatalogue
        fields = "__all__"
        read_only_fields = ["created_by", "updated_by"]

    def validate(self, attrs):
        categorie = attrs.get("categorie") or self.instance.categorie
        self._verifier_droit(categorie.specialite)
        return attrs
