from django.contrib import admin
from .models import MaintenancePlan, MaintenanceOccurrence, MaintenanceExecution, OccurrenceStatusLog

@admin.register(MaintenancePlan)
class MaintenancePlanAdmin(admin.ModelAdmin):
    list_display = ("name", "scope", "asset_type", "asset", "every_n_days", "requires_validation")
    list_filter = ("scope", "requires_validation")

@admin.register(MaintenanceOccurrence)
class MaintenanceOccurrenceAdmin(admin.ModelAdmin):
    list_display = ("plan", "asset", "scheduled_for", "status", "priority")
    list_filter = ("status", "scheduled_for", "priority")

@admin.register(MaintenanceExecution)
class MaintenanceExecutionAdmin(admin.ModelAdmin):
    list_display = ("occurrence", "started_at", "completed_at", "conformity")
    list_filter = ("conformity",)

@admin.register(OccurrenceStatusLog)
class OccurrenceStatusLogAdmin(admin.ModelAdmin):
    list_display = ("occurrence", "old_status", "new_status", "created_at", "user")
