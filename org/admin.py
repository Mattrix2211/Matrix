from django.contrib import admin, messages

from accounts.models import AuditLog
from matrix.core.equipage import equipage_a_bord, tracer_changement_equipage
from . import structure_services
from .models import (
    ModuleActivation, ReferenceBatiment, RoleThresholdConfig, Section, Sector, SectorConfig, Service, Ship, TypeBatiment,
)

class SuppressionSureAdmin(admin.ModelAdmin):
    """Suppression d'unité par l'administration : même règle que partout ailleurs (refus si référencée, trace)."""

    def delete_model(self, request, obj):
        try:
            structure_services.supprimer(obj, request.user)
        except structure_services.SuppressionRefusee as erreur:
            self.message_user(request, str(erreur), level=messages.ERROR)

    def delete_queryset(self, request, queryset):
        for obj in queryset:
            self.delete_model(request, obj)


@admin.register(Ship)
class ShipAdmin(SuppressionSureAdmin):
    list_display = ("name", "code", "numero_coque", "type_batiment", "double_equipage", "equipage_actuel", "archived", "created_at")
    search_fields = ("name", "code", "numero_coque", "trigramme")
    list_filter = ("archived", "type_batiment")

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
                equipage_a_bord(obj)
        super().save_model(request, obj, form, change)
        if avant:
            tracer_changement_equipage(request.user, obj, avant)

@admin.register(Service)
class ServiceAdmin(SuppressionSureAdmin):
    list_display = ("name", "ship", "commandant_adjoint", "archived")
    list_filter = ("ship", "commandant_adjoint", "archived")

@admin.register(Sector)
class SectorAdmin(SuppressionSureAdmin):
    list_display = ("name", "service", "color", "archived")
    list_filter = ("service", "archived")

@admin.register(Section)
class SectionAdmin(SuppressionSureAdmin):
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


@admin.register(TypeBatiment)
class TypeBatimentAdmin(admin.ModelAdmin):
    list_display = ("code", "libelle", "ordre", "avec_silhouette", "actif")
    list_filter = ("actif",)
    search_fields = ("code", "libelle")

    @admin.display(boolean=True, description="Silhouette")
    def avec_silhouette(self, obj):
        return bool(obj.silhouette)


@admin.register(ReferenceBatiment)
class ReferenceBatimentAdmin(admin.ModelAdmin):
    list_display = ("nom", "numero_coque", "trigramme", "type_batiment", "port_base", "statut", "famille", "archive")
    list_filter = ("statut", "famille", "type_batiment", "archive")
    search_fields = ("nom", "numero_coque", "trigramme", "port_base")
    actions = ("archiver", "restaurer")

    @staticmethod
    def _tracer(request, reference, action, details=""):
        AuditLog.objects.create(
            actor=request.user, action=f"referentiel_batiment_{action}",
            details=f"{reference} (id={reference.pk}){' : ' + details if details else ''}",
        )

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        if not change:
            self._tracer(request, obj, "cree")
        elif {"archive", "statut", "numero_coque", "nom", "port_base"} & set(form.changed_data):
            self._tracer(request, obj, "modifie", ", ".join(
                f"{champ} -> {form.cleaned_data.get(champ)}" for champ in form.changed_data if champ in ("archive", "statut", "numero_coque", "nom", "port_base")
            ))

    @admin.action(description="Archiver les bâtiments sélectionnés (retirés du service)")
    def archiver(self, request, queryset):
        for reference in queryset.filter(archive=False):
            reference.archive = True
            reference.save(update_fields=["archive", "updated_at"])
            self._tracer(request, reference, "archive")

    @admin.action(description="Restaurer les bâtiments sélectionnés")
    def restaurer(self, request, queryset):
        for reference in queryset.filter(archive=True):
            reference.archive = False
            reference.save(update_fields=["archive", "updated_at"])
            self._tracer(request, reference, "restaure")
