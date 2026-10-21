from django.contrib import admin
from matrix.core.equipage import equipage_a_bord, reprendre_equipage_en_base, tracer_changement_equipage
from .models import Ship, Service, Sector, Section, SectorConfig, RoleThresholdConfig, ModuleActivation

@admin.register(Ship)
class ShipAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "double_equipage", "equipage_actuel", "archived", "created_at")
    search_fields = ("name", "code")
    list_filter = ("archived",)

    @admin.display(description="Équipage actuellement à bord")
    def equipage_actuel(self, obj):
        return equipage_a_bord(obj)

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        if obj is None:
            # Un nouveau bâtiment choisit son fuseau explicitement.
            form.base_fields["fuseau_horaire"].required = True
        return form

    def save_model(self, request, obj, form, change):
        avant = None
        if change:
            ancien = Ship.objects.get(pk=obj.pk)
            avant = (ancien.double_equipage, equipage_a_bord(ancien))
            if "equipage_a_bord" not in form.changed_data:
                # Un formulaire resté ouvert ne doit pas écraser une relève appliquée entre-temps.
                reprendre_equipage_en_base(obj)
        super().save_model(request, obj, form, change)
        if avant:
            tracer_changement_equipage(request.user, obj, avant)

@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ("name", "ship", "commandant_adjoint", "archived")
    list_filter = ("ship", "commandant_adjoint", "archived")

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
