from django.contrib import admin
from .models import Roles, TypeAbsence, UserProfile

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "role", "administrateur_technique", "fonction_coma", "equipage", "ship", "service", "sector", "section")
    list_filter = ("role", "administrateur_technique", "ship", "service", "sector")
    search_fields = ("user__username", "user__email")

    def formfield_for_choice_field(self, db_field, request, **kwargs):
        if db_field.name == "role":
            kwargs["choices"] = [c for c in Roles.choices if c[0] != Roles.ADMIN_NAVIRE]
        return super().formfield_for_choice_field(db_field, request, **kwargs)


@admin.register(TypeAbsence)
class TypeAbsenceAdmin(admin.ModelAdmin):
    list_display = ("name", "active")
    list_filter = ("active",)
