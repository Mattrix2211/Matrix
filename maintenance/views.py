from rest_framework import viewsets, permissions, decorators, response, status
from django.utils import timezone
from .models import (
    MaintenancePlan,
    MaintenanceOccurrence,
    MaintenanceExecution,
    OccurrenceStatusLog,
    mettre_a_jour_echeance_installation,
)
from .serializers import MaintenancePlanSerializer, MaintenanceOccurrenceSerializer, MaintenanceExecutionSerializer
from matrix.core.mixins import ScopedQuerySetMixin, build_scope_q
from matrix.core.permissions import RolePermission
from matrix.core.roles import RoleLevel

class DefaultPermission(permissions.IsAuthenticated):
    pass

class MaintenancePlanViewSet(ScopedQuerySetMixin, viewsets.ModelViewSet):
    queryset = MaintenancePlan.objects.select_related("asset", "asset_type", "checklist_template").all()
    serializer_class = MaintenancePlanSerializer
    permission_classes = [RolePermission]

    def get_scoped_filters(self):
        # Un plan porte soit sur un actif précis (asset, qui porte lui-même
        # les 4 champs de périmètre), soit sur un type d'actif (asset_type,
        # rattaché uniquement à un secteur — un type n'est jamais propre à
        # une section précise).
        return build_scope_q(
            self.request.user,
            "asset__",
            {
                "ship_id": "asset_type__sector__service__ship_id",
                "service_id": "asset_type__sector__service_id",
                "sector_id": "asset_type__sector_id",
            },
        )

class MaintenanceOccurrenceViewSet(ScopedQuerySetMixin, viewsets.ModelViewSet):
    queryset = MaintenanceOccurrence.objects.select_related("plan", "asset", "installation_maintenance").all()
    serializer_class = MaintenanceOccurrenceSerializer
    permission_classes = [RolePermission]
    min_role_level_write = RoleLevel.EQUIPIER

    def get_scoped_filters(self):
        # Une occurrence porte soit sur du matériel mobile (asset), soit sur
        # une installation fixe (installation_maintenance) — jamais les deux
        # à la fois (contrainte occurrence_liee_a_asset_xor_installation).
        return build_scope_q(
            self.request.user,
            "asset__",
            "installation_maintenance__installation__",
        )

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
        if occ.status == "DONE":
            mettre_a_jour_echeance_installation(occ)
        return response.Response(MaintenanceExecutionSerializer(exec).data)

class MaintenanceExecutionViewSet(ScopedQuerySetMixin, viewsets.ModelViewSet):
    queryset = MaintenanceExecution.objects.select_related("occurrence", "occurrence__plan").all()
    serializer_class = MaintenanceExecutionSerializer
    permission_classes = [RolePermission]
    min_role_level_write = RoleLevel.EQUIPIER

    def get_scoped_filters(self):
        # Une exécution ne porte pas elle-même le périmètre : on le
        # retrouve via son occurrence, elle-même rattachée à un matériel
        # mobile ou à une installation fixe (cf. MaintenanceOccurrenceViewSet).
        return build_scope_q(
            self.request.user,
            "occurrence__asset__",
            "occurrence__installation_maintenance__installation__",
        )
