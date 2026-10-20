from django.contrib import admin

from matrix.core.admin import AdminScopedMixin

from .models import (
    ChefDeListe,
    CreneauQuart,
    CreneauServiceGarde,
    EchangeService,
    FeuilleService,
    FonctionFeuilleService,
    Quart,
    RubriqueEnTeteFeuilleService,
    ServiceGarde,
    VersionFeuilleService,
    VersionQuart,
    VersionServiceGarde,
)


@admin.register(ChefDeListe)
class ChefDeListeAdmin(AdminScopedMixin, admin.ModelAdmin):
    list_display = ("user", "ship", "service", "sector", "section")
    list_filter = ("ship", "service", "sector")
    search_fields = ("user__username",)


class TraceCreneauxAdminMixin:
    """Trace (AuditLog + notification) les créneaux ajoutés ou supprimés
    depuis l'admin sur une liste publiée."""

    def save_formset(self, request, form, formset, change):
        if formset.model not in (CreneauQuart, CreneauServiceGarde):
            return super().save_formset(request, form, formset, change)
        liste = form.instance
        instances = formset.save(commit=False)
        for creneau in formset.deleted_objects:
            liste.tracer_modification_creneau(request.user, creneau, ajoute=False)
            creneau.delete()
        for creneau in instances:
            nouveau = creneau._state.adding
            creneau.save()
            if nouveau:
                liste.tracer_modification_creneau(request.user, creneau, ajoute=True)
        formset.save_m2m()


class CreneauQuartInline(admin.TabularInline):
    model = CreneauQuart
    extra = 0


class VersionQuartInline(admin.TabularInline):
    """Historique des versions (cf. quarts/models.py::creer_version) : lecture
    seule, une version ne se corrige jamais après coup — seule une nouvelle
    publication en ajoute une."""
    model = VersionQuart
    extra = 0
    fields = ("numero", "publiee_le", "publiee_par", "creneaux_fige")
    readonly_fields = fields
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Quart)
class QuartAdmin(TraceCreneauxAdminMixin, AdminScopedMixin, admin.ModelAdmin):
    list_display = ("nom", "fonction", "ship", "service", "sector", "section", "date_debut", "date_fin", "statut")
    list_filter = ("statut", "fonction", "ship", "service", "sector")
    inlines = [CreneauQuartInline, VersionQuartInline]


class CreneauServiceGardeInline(admin.TabularInline):
    model = CreneauServiceGarde
    extra = 0


class VersionServiceGardeInline(admin.TabularInline):
    """Historique des versions (cf. quarts/models.py::creer_version) : lecture
    seule, même principe que VersionQuartInline ci-dessus."""
    model = VersionServiceGarde
    extra = 0
    fields = ("numero", "publiee_le", "publiee_par", "creneaux_fige")
    readonly_fields = fields
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(ServiceGarde)
class ServiceGardeAdmin(TraceCreneauxAdminMixin, AdminScopedMixin, admin.ModelAdmin):
    list_display = ("nom", "fonction", "type_service", "ship", "service", "sector", "section", "date_debut", "date_fin", "statut")
    list_filter = ("statut", "fonction", "ship", "service", "sector")
    inlines = [CreneauServiceGardeInline, VersionServiceGardeInline]


@admin.register(EchangeService)
class EchangeServiceAdmin(admin.ModelAdmin):
    list_display = ("demandeur", "cible", "statut", "created_at")
    list_filter = ("statut",)


@admin.register(RubriqueEnTeteFeuilleService)
class RubriqueEnTeteFeuilleServiceAdmin(AdminScopedMixin, admin.ModelAdmin):
    list_display = ("libelle", "ship", "type_saisie", "ordre", "actif")
    list_filter = ("ship", "type_saisie", "actif")


@admin.register(FonctionFeuilleService)
class FonctionFeuilleServiceAdmin(AdminScopedMixin, admin.ModelAdmin):
    list_display = ("libelle", "ship", "poste_recherche", "ordre", "actif")
    list_filter = ("ship", "actif")


class VersionFeuilleServiceInline(admin.TabularInline):
    """Historique des versions (cf. quarts/models.py::FeuilleService.
    creer_version) : lecture seule, même principe que VersionQuartInline
    ci-dessus."""
    model = VersionFeuilleService
    extra = 0
    fields = ("numero", "publiee_le", "publiee_par", "contenu_fige")
    readonly_fields = fields
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(FeuilleService)
class FeuilleServiceAdmin(AdminScopedMixin, admin.ModelAdmin):
    list_display = ("date", "ship", "equipage", "statut", "secteur_redacteur", "service_redacteur")
    list_filter = ("statut", "ship")
    inlines = [VersionFeuilleServiceInline]
