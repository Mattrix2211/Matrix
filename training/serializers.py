from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers
from .models import TrainingCourse, TrainingRequirement, TrainingSession, TrainingRecord

class TrainingCourseSerializer(serializers.ModelSerializer):
    class Meta:
        model = TrainingCourse
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
