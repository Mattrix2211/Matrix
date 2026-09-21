from django.contrib import admin

from matrix.core.admin import AdminScopedMixin

from .models import PointControle, Ronde, RondeModele


class PointControleInline(admin.TabularInline):
    model = PointControle
    extra = 0


@admin.register(RondeModele)
class RondeModeleAdmin(AdminScopedMixin, admin.ModelAdmin):
    list_display = ("nom", "ship", "service", "sector", "periodicite_jours", "actif", "version")
    list_filter = ("actif", "ship", "service", "sector")
    inlines = [PointControleInline]


@admin.register(Ronde)
class RondeAdmin(admin.ModelAdmin):
    list_display = ("nom", "date_prevue", "statut", "realisee_par")
    list_filter = ("statut",)
