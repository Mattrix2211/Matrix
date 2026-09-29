from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers
from .models import ReferentFormation, TrainingCourse, TrainingRequirement, TrainingSession, TrainingRecord

class TrainingCourseSerializer(serializers.ModelSerializer):
    class Meta:
        model = TrainingCourse
        fields = "__all__"
        # `gere_par_le_bord` et `statut_validation` sont exclusivement
        # pilotés par le Circuit C (chef de secteur -> chef de service,
        # training/formation_bord_actions.py::_action_proposer_formation_bord
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
        fields = ("id", "course", "ship", "user", "created_at", "updated_at")
        read_only_fields = ("id", "created_at", "updated_at")

class TrainingRequirementSerializer(serializers.ModelSerializer):
    class Meta:
        model = TrainingRequirement
        fields = "__all__"

class TrainingSessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = TrainingSession
        fields = (
            "id", "course", "scheduled_at", "instructor", "attendees", "capacite_max",
            "reservations", "location", "status", "created_at", "updated_at",
        )
        # Les réservations sont libre-service (training/session_actions.py :
        # un marin ne réserve que pour lui-même, avec contrôle de capacité,
        # de prérequis...) : jamais modifiables via ce endpoint générique.
        read_only_fields = ("id", "reservations", "created_at", "updated_at")

class TrainingRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = TrainingRecord
        fields = (
            "id", "user", "course", "completed_at", "expires_at", "validated_by", "attachment",
            "created_by", "updated_by", "created_at", "updated_at",
        )
        # Le valideur est toujours l'utilisateur connecté (TrainingRecordViewSet).
        read_only_fields = ("id", "validated_by", "created_by", "updated_by", "created_at", "updated_at")

    def validate(self, attrs):
        # Le marin d'un enregistrement ne change jamais : la permission ne
        # contrôle que le marin d'origine, réaffecter le dossier à un autre
        # marin certifierait sa formation sans contrôle de son navire.
        if self.instance is not None and "user" in attrs and attrs["user"] != self.instance.user:
            raise serializers.ValidationError(
                {"user": "Un enregistrement de formation ne peut pas être réaffecté à un autre marin."}
            )
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
