from django.contrib import admin
from .models import Ship, Service, Sector, Section, SectorConfig
from django.contrib import admin
from django.db import models
from django.apps import apps

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

DynamicFieldDefinition = apps.get_model('org', 'DynamicFieldDefinition')

@admin.register(DynamicFieldDefinition)
class DynamicFieldDefinitionAdmin(admin.ModelAdmin):
    list_display = ("name", "label", "type", "sector", "applies_to", "required")
    list_filter = ("sector", "type", "required")
