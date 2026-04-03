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

class OccurrenceStatusLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = OccurrenceStatusLog
        fields = "__all__"

class MaintenanceExecutionSerializer(serializers.ModelSerializer):
    class Meta:
        model = MaintenanceExecution
        fields = "__all__"
