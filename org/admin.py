from django.contrib import admin
from .models import Ship, Service, Sector, Section, SectorConfig, RoleThresholdConfig, ModuleActivation

@admin.register(Ship)
class ShipAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "archived", "created_at")
    search_fields = ("name", "code")
    list_filter = ("archived",)

@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ("name", "ship", "archived")
    list_filter = ("ship", "archived")

@admin.register(Sector)
class SectorAdmin(admin.ModelAdmin):
    list_display = ("name", "service", "color", "archived")
    list_filter = ("service", "archived")

@admin.register(Section)
class SectionAdmin(admin.ModelAdmin):
    list_display = ("name", "sector", "archived")
    list_filter = ("sector", "archived")

@admin.register(SectorConfig)
class SectorConfigAdmin(admin.ModelAdmin):
    list_display = ("sector", "created_at")

@admin.register(RoleThresholdConfig)
class RoleThresholdConfigAdmin(admin.ModelAdmin):
    # Interface de gestion réservée aux administrateurs techniques (superusers
    # Django) : l'interface destinée aux ADMIN_NAVIRE/MASTER_ADMIN au quotidien
    # est l'onglet « Sécurité » de /parametre/ (matrix/views.py::SettingsView),
    # pas ce Django admin brut (principe n°2 CLAUDE.md).
    list_display = ("ship", "updated_at")

@admin.register(ModuleActivation)
class ModuleActivationAdmin(admin.ModelAdmin):
    # Même principe que RoleThresholdConfigAdmin ci-dessus : interface de
    # secours technique, l'interface quotidienne est l'onglet « Modules » de
    # /parametre/ (matrix/views.py::SettingsView).
    list_display = ("ship", "module", "active", "updated_at")
    list_filter = ("ship", "module", "active")
