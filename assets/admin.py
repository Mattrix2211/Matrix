from django.contrib import admin
from .models import Location, Deck, AssetType, ChecklistTemplate, ChecklistItemTemplate, AssetChecklistOverride, Asset, AssetDocument, CategorieCatalogue, ArticleCatalogue
from matrix.core.admin import AdminScopedMixin

@admin.register(Location)
class LocationAdmin(AdminScopedMixin, admin.ModelAdmin):
    list_display = ("name", "ship", "parent")
    list_filter = ("ship",)
    search_fields = ("name",)

@admin.register(Deck)
class DeckAdmin(AdminScopedMixin, admin.ModelAdmin):
    list_display = ("name", "ship", "order")
    list_filter = ("ship",)
    ordering = ("ship__name", "order", "name")

class ChecklistItemInline(admin.TabularInline):
    model = ChecklistItemTemplate
    extra = 1

@admin.register(ChecklistTemplate)
class ChecklistTemplateAdmin(admin.ModelAdmin):
    list_display = ("name", "sector", "asset_type")
    list_filter = ("sector",)
    inlines = [ChecklistItemInline]

@admin.register(AssetType)
class AssetTypeAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "sector")
    list_filter = ("sector", "category")

@admin.register(Asset)
class AssetAdmin(AdminScopedMixin, admin.ModelAdmin):
    list_display = ("id", "asset_type", "ship", "service", "sector", "section", "status", "criticality")
    list_filter = ("ship", "service", "sector", "status", "criticality")
    search_fields = ("serial_number", "internal_id")

@admin.register(AssetDocument)
class AssetDocumentAdmin(admin.ModelAdmin):
    list_display = ("asset", "name", "file", "created_at")
    list_filter = ("asset",)

@admin.register(AssetChecklistOverride)
class AssetChecklistOverrideAdmin(admin.ModelAdmin):
    list_display = ("asset", "template")

@admin.register(CategorieCatalogue)
class CategorieCatalogueAdmin(admin.ModelAdmin):
    list_display = ("nom", "parent", "specialite", "ordre", "actif")
    list_filter = ("specialite", "actif")
    search_fields = ("nom",)
    readonly_fields = ("created_by", "updated_by")

    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)

@admin.register(ArticleCatalogue)
class ArticleCatalogueAdmin(admin.ModelAdmin):
    list_display = ("designation", "marque", "reference", "nno", "categorie", "actif")
    list_filter = ("categorie__specialite", "actif")
    search_fields = ("designation", "marque", "reference", "nno")
    readonly_fields = ("created_by", "updated_by")
    save_model = CategorieCatalogueAdmin.save_model
