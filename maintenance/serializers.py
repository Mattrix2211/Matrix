from rest_framework import serializers
from .models import MaintenancePlan, MaintenanceOccurrence, MaintenanceExecution, OccurrenceStatusLog

class MaintenancePlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = MaintenancePlan
        fields = "__all__"
        read_only_fields = ["created_by", "updated_by"]

class MaintenanceOccurrenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = MaintenanceOccurrence
        fields = "__all__"
        # Le statut ne se modifie jamais via ce endpoint générique (PATCH/PUT) :
        # il doit obligatoirement passer par les actions dédiées start()/complete()
        # du ViewSet, qui appliquent les règles métier (signature de validation sur
        # installation critique, mise à jour de l'échéance...). Sans ce verrou, un
        # PATCH direct sur "status" contournait totalement le contrôle mot de passe
        # de MaintenanceOccurrenceViewSet.complete() (cf. perform_update ci-contre).
        read_only_fields = ["status", "created_by", "updated_by"]

class OccurrenceStatusLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = OccurrenceStatusLog
        fields = "__all__"

class MaintenanceExecutionSerializer(serializers.ModelSerializer):
    class Meta:
        model = MaintenanceExecution
        fields = "__all__"
        # Exécutant et signature de validation sont posés par le serveur.
        read_only_fields = ["executed_by", "valide_par", "date_validation", "created_by", "updated_by", "saisie_origine"]

    def validate(self, attrs):
        # Un compte rendu terminé ne se réécrit pas en silence : la correction passe par l'écran (motif, trace, origine).
        if self.instance is not None and self.instance.completed_at:
            raise serializers.ValidationError("Compte rendu terminé : corrigez-le depuis son écran, avec un motif.")
        return attrs
