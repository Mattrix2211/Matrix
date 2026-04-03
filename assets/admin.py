from django.contrib import admin
from .models import Location, AssetType, ChecklistTemplate, ChecklistItemTemplate, AssetChecklistOverride, Asset, AssetDocument
from bordops.core.admin import AdminScopedMixin

@admin.register(Location)
class LocationAdmin(AdminScopedMixin, admin.ModelAdmin):
    list_display = ("name", "ship", "parent")
    list_filter = ("ship",)

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
