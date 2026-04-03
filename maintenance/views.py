from rest_framework import viewsets, permissions, decorators, response, status
from django.utils import timezone
from .models import MaintenancePlan, MaintenanceOccurrence, MaintenanceExecution, OccurrenceStatusLog
from .serializers import MaintenancePlanSerializer, MaintenanceOccurrenceSerializer, MaintenanceExecutionSerializer
from matrix.core.mixins import ScopedQuerySetMixin
from matrix.core.permissions import RolePermission
from matrix.core.roles import RoleLevel

class DefaultPermission(permissions.IsAuthenticated):
    pass

class MaintenancePlanViewSet(ScopedQuerySetMixin, viewsets.ModelViewSet):
    queryset = MaintenancePlan.objects.select_related("asset", "asset_type", "checklist_template").all()
    serializer_class = MaintenancePlanSerializer
    permission_classes = [RolePermission]

class MaintenanceOccurrenceViewSet(ScopedQuerySetMixin, viewsets.ModelViewSet):
    queryset = MaintenanceOccurrence.objects.select_related("plan", "asset").all()
    serializer_class = MaintenanceOccurrenceSerializer
    permission_classes = [RolePermission]
    min_role_level_write = RoleLevel.EQUIPIER

    @decorators.action(detail=True, methods=["post"])
    def start(self, request, pk=None):
        occ = self.get_object()
        exec, _ = MaintenanceExecution.objects.get_or_create(occurrence=occ)
        if not exec.started_at:
            exec.started_at = timezone.now()
            exec.save()
        occ.status = "IN_PROGRESS"
        occ.save(update_fields=["status"])
        return response.Response(MaintenanceExecutionSerializer(exec).data)

    @decorators.action(detail=True, methods=["post"])
    def complete(self, request, pk=None):
        occ = self.get_object()
        exec, _ = MaintenanceExecution.objects.get_or_create(occurrence=occ)
        exec.completed_at = timezone.now()
        exec.conformity = request.data.get("conformity", "")
        exec.notes = request.data.get("notes", "")
        exec.results = request.data.get("results", {})
        exec.measurements = request.data.get("measurements", {})
        exec.save()
        occ.status = "DONE" if exec.conformity != "NON_CONFORME" else "WAITING_VALIDATION"
        occ.save(update_fields=["status"])
        return response.Response(MaintenanceExecutionSerializer(exec).data)

class MaintenanceExecutionViewSet(ScopedQuerySetMixin, viewsets.ModelViewSet):
    queryset = MaintenanceExecution.objects.select_related("occurrence", "occurrence__plan").all()
    serializer_class = MaintenanceExecutionSerializer
    permission_classes = [RolePermission]
    min_role_level_write = RoleLevel.EQUIPIER
