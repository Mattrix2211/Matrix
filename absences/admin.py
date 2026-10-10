from django.contrib import admin

from .models import Absence


@admin.register(Absence)
class AbsenceAdmin(admin.ModelAdmin):
    list_display = ("marin", "type_absence", "date_debut", "date_fin", "statut")
    list_filter = ("statut", "type_absence")
    search_fields = ("marin__username", "marin__first_name", "marin__last_name")
    autocomplete_fields = ("marin",)
