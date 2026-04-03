from django.contrib import admin
from .models import TrainingCourse, TrainingRequirement, TrainingSession, TrainingRecord

@admin.register(TrainingCourse)
class TrainingCourseAdmin(admin.ModelAdmin):
    list_display = ("title", "sector", "validity_days")
    list_filter = ("sector",)

@admin.register(TrainingRequirement)
class TrainingRequirementAdmin(admin.ModelAdmin):
    list_display = ("course", "applies_to_role", "applies_to_ship", "applies_to_service", "applies_to_sector", "applies_to_section", "required")
    list_filter = ("applies_to_role", "required")

@admin.register(TrainingSession)
class TrainingSessionAdmin(admin.ModelAdmin):
    list_display = ("course", "scheduled_at", "instructor", "status")
    list_filter = ("status",)

@admin.register(TrainingRecord)
class TrainingRecordAdmin(admin.ModelAdmin):
    list_display = ("user", "course", "completed_at", "expires_at")
    list_filter = ("completed_at", "expires_at")
