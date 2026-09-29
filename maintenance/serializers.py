from rest_framework import serializers
from .models import MaintenancePlan, MaintenanceOccurrence, MaintenanceExecution, OccurrenceStatusLog

class MaintenancePlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = MaintenancePlan
        fields = (
            "id", "scope", "asset_type", "asset", "name", "every_n_days", "expected_duration_min",
            "checklist_template", "requires_validation", "validation_role",
            "created_by", "updated_by", "created_at", "updated_at",
        )
        read_only_fields = ("id", "created_by", "updated_by", "created_at", "updated_at")

class MaintenanceOccurrenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = MaintenanceOccurrence
        fields = (
            "id", "plan", "asset", "installation_maintenance", "scheduled_for", "status",
            "priority", "assignees", "created_by", "updated_by", "created_at", "updated_at",
        )
        # Le statut ne se modifie jamais via ce endpoint générique (PATCH/PUT) :
        # il doit obligatoirement passer par les actions dédiées start()/complete()
        # du ViewSet, qui appliquent les règles métier (signature de validation sur
        # installation critique, mise à jour de l'échéance...). Sans ce verrou, un
        # PATCH direct sur "status" contournait totalement le contrôle mot de passe
        # de MaintenanceOccurrenceViewSet.complete() (cf. perform_update ci-contre).
        read_only_fields = ["id", "status", "created_by", "updated_by", "created_at", "updated_at"]

class OccurrenceStatusLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = OccurrenceStatusLog
        fields = ("id", "occurrence", "old_status", "new_status", "user", "note", "created_at", "updated_at")
        # Historique : écrit uniquement par start()/complete() côté serveur.
        read_only_fields = fields

class MaintenanceExecutionSerializer(serializers.ModelSerializer):
    class Meta:
        model = MaintenanceExecution
        fields = (
            "id", "occurrence", "started_at", "completed_at", "executed_by", "results",
            "measurements", "conformity", "notes", "valide_par", "date_validation",
            "created_by", "updated_by", "created_at", "updated_at",
        )
        # Horodatages, exécutant et signature de validation sont posés côté
        # serveur (start()/complete()) : jamais forgeables par le client.
        read_only_fields = (
            "id", "started_at", "completed_at", "executed_by", "valide_par", "date_validation",
            "created_by", "updated_by", "created_at", "updated_at",
        )

    def validate_occurrence(self, occurrence):
        if self.instance is not None and occurrence != self.instance.occurrence:
            raise serializers.ValidationError("Une exécution ne peut pas être déplacée vers une autre occurrence.")
        return occurrence
