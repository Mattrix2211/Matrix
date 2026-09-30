from rest_framework import serializers

from matrix.core.scopes import marins_hors_equipage
from matrix.core.serializers import ReferencesDansPerimetreMixin
from .models import MaintenancePlan, MaintenanceOccurrence, MaintenanceExecution, OccurrenceStatusLog

# Périmètre d'un plan, d'un type d'actif et d'un modèle de checklist : mêmes
# chemins que MaintenancePlanViewSet et les ViewSets d'assets.
_PERIMETRE_PAR_SECTEUR = {
    "ship_id": "sector__service__ship_id", "service_id": "sector__service_id", "sector_id": "sector_id",
}
_PERIMETRE_PLAN = (
    "asset__",
    {
        "ship_id": "asset_type__sector__service__ship_id",
        "service_id": "asset_type__sector__service_id",
        "sector_id": "asset_type__sector_id",
    },
)


class MaintenancePlanSerializer(ReferencesDansPerimetreMixin, serializers.ModelSerializer):
    references_perimetre = {
        "asset_type": (_PERIMETRE_PAR_SECTEUR,), "checklist_template": (_PERIMETRE_PAR_SECTEUR,),
    }

    class Meta:
        model = MaintenancePlan
        fields = (
            "id", "scope", "asset_type", "asset", "name", "every_n_days", "expected_duration_min",
            "checklist_template", "requires_validation", "validation_role",
            "created_by", "updated_by", "created_at", "updated_at",
        )
        read_only_fields = ("id", "created_by", "updated_by", "created_at", "updated_at")

class MaintenanceOccurrenceSerializer(ReferencesDansPerimetreMixin, serializers.ModelSerializer):
    references_perimetre = {"plan": _PERIMETRE_PLAN}

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

    def validate_assignees(self, assignees):
        # Double équipage : l'occurrence appartient au bâtiment, mais on ne
        # l'assigne qu'à des marins de son propre équipage.
        request = self.context.get("request")
        if request is not None and marins_hors_equipage(request.user, assignees):
            raise serializers.ValidationError("Une occurrence ne peut être assignée qu'à des marins de votre équipage.")
        return assignees

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
