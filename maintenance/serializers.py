from rest_framework import serializers
from .models import MaintenancePlan, MaintenanceOccurrence, MaintenanceExecution, OccurrenceStatusLog

class MaintenancePlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = MaintenancePlan
        fields = "__all__"

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
        read_only_fields = ["status"]

class OccurrenceStatusLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = OccurrenceStatusLog
        fields = "__all__"

class MaintenanceExecutionSerializer(serializers.ModelSerializer):
    class Meta:
        model = MaintenanceExecution
        fields = "__all__"
