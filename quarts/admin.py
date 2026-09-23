from django.contrib import admin

from matrix.core.admin import AdminScopedMixin

from .models import ChefDeListe, CreneauQuart, CreneauServiceGarde, EchangeService, Quart, ServiceGarde


@admin.register(ChefDeListe)
class ChefDeListeAdmin(AdminScopedMixin, admin.ModelAdmin):
    list_display = ("user", "ship", "service", "sector", "section")
    list_filter = ("ship", "service", "sector")
    search_fields = ("user__username",)


class CreneauQuartInline(admin.TabularInline):
    model = CreneauQuart
    extra = 0


@admin.register(Quart)
class QuartAdmin(AdminScopedMixin, admin.ModelAdmin):
    list_display = ("nom", "fonction", "ship", "service", "sector", "section", "date_debut", "date_fin", "statut")
    list_filter = ("statut", "fonction", "ship", "service", "sector")
    inlines = [CreneauQuartInline]


class CreneauServiceGardeInline(admin.TabularInline):
    model = CreneauServiceGarde
    extra = 0


@admin.register(ServiceGarde)
class ServiceGardeAdmin(AdminScopedMixin, admin.ModelAdmin):
    list_display = ("nom", "fonction", "type_service", "ship", "service", "sector", "section", "date_debut", "date_fin", "statut")
    list_filter = ("statut", "fonction", "ship", "service", "sector")
    inlines = [CreneauServiceGardeInline]


@admin.register(EchangeService)
class EchangeServiceAdmin(admin.ModelAdmin):
    list_display = ("demandeur", "cible", "statut", "created_at")
    list_filter = ("statut",)
