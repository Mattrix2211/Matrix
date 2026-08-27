from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers
from .models import ReferentFormation, TrainingCourse, TrainingRequirement, TrainingSession, TrainingRecord

class TrainingCourseSerializer(serializers.ModelSerializer):
    class Meta:
        model = TrainingCourse
        fields = "__all__"
        # `gere_par_le_bord` et `statut_validation` sont exclusivement
        # pilotés par le Circuit C (chef de secteur -> chef de service,
        # training/web_views.py::TrainingCourseListView._proposer_formation_bord
        # et suivants), qui applique un contrôle de périmètre organisationnel
        # que l'API ne reproduit pas ici — les rendre en lecture seule évite
        # qu'un utilisateur autorisé à écrire sur ce ViewSet (CHEF_SECTION+,
        # cf. RolePermission.min_level_write) ne contourne ce circuit en
        # posant directement statut_validation="ACTIVE" via l'API (faille
        # signalée par le Tech Lead, tâche Notion Circuit C). Une formation
        # créée via l'API reste donc toujours « organisme » (valeurs par
        # défaut du modèle : gere_par_le_bord=False, statut_validation=ACTIVE).
        read_only_fields = ["gere_par_le_bord", "statut_validation"]

class ReferentFormationSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReferentFormation
        fields = "__all__"

class TrainingRequirementSerializer(serializers.ModelSerializer):
    class Meta:
        model = TrainingRequirement
        fields = "__all__"

class TrainingSessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = TrainingSession
        fields = "__all__"

class TrainingRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = TrainingRecord
        fields = "__all__"

    def validate(self, attrs):
        # Reproduit ici la règle métier de TrainingRecord.clean() (formations
        # prérequises non validées) : le ViewSet DRF n'appelle pas full_clean()
        # automatiquement, il faut donc revalider explicitement à ce niveau pour
        # que la règle s'applique aussi via l'API, pas seulement via l'admin.
        instance = TrainingRecord(**{**{
            "user": getattr(self.instance, "user", None),
            "course": getattr(self.instance, "course", None),
            "completed_at": getattr(self.instance, "completed_at", None),
        }, **attrs})
        try:
            instance.clean()
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.message_dict if hasattr(exc, "message_dict") else exc.messages)
        return attrs
