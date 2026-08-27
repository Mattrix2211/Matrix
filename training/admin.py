from django.contrib import admin
from .models import (
    CandidatureFormation,
    DemandePlace,
    PersonnelBRH,
    PlaceAffectee,
    ReferentFormation,
    TrainingCourse,
    TrainingRequirement,
    TrainingSession,
    TrainingRecord,
    ReferentFormationNavire,
)

@admin.register(TrainingCourse)
class TrainingCourseAdmin(admin.ModelAdmin):
    # Formation désormais globale (plus de "sector") : filtre/tri par
    # catégorie (domaine métier), seul regroupement encore pertinent.
    list_display = ("title", "category", "validity_days")
    list_filter = ("category",)
    filter_horizontal = ("prerequisites",)

@admin.register(ReferentFormation)
class ReferentFormationAdmin(admin.ModelAdmin):
    list_display = ("course", "ship", "user")
    list_filter = ("ship",)

@admin.register(ReferentFormationNavire)
class ReferentFormationNavireAdmin(admin.ModelAdmin):
    list_display = ("ship", "user")

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

@admin.register(DemandePlace)
class DemandePlaceAdmin(admin.ModelAdmin):
    list_display = ("course", "ship", "nb_places_demandees", "nb_places_attribuees", "session", "statut")
    list_filter = ("statut", "ship")

@admin.register(PlaceAffectee)
class PlaceAffecteeAdmin(admin.ModelAdmin):
    list_display = ("demande_place", "marin")

@admin.register(PersonnelBRH)
class PersonnelBRHAdmin(admin.ModelAdmin):
    list_display = ("ship", "user")
    list_filter = ("ship",)

@admin.register(CandidatureFormation)
class CandidatureFormationAdmin(admin.ModelAdmin):
    list_display = ("marin", "course", "statut", "hierarchie_validee_par", "brh_validee_par")
    list_filter = ("statut",)
