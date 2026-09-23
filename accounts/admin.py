from django.contrib import admin
from .models import TypeAbsence, UserProfile

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "role", "ship", "service", "sector", "section")
    list_filter = ("role", "ship", "service", "sector")
    search_fields = ("user__username", "user__email")


@admin.register(TypeAbsence)
class TypeAbsenceAdmin(admin.ModelAdmin):
    list_display = ("name", "active")
    list_filter = ("active",)
