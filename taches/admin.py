from django.contrib import admin

from .models import ParametresTaches, Tache


@admin.register(Tache)
class TacheAdmin(admin.ModelAdmin):
    list_display = ("titre", "assigne", "echeance", "statut")
    list_filter = ("statut",)


@admin.register(ParametresTaches)
class ParametresTachesAdmin(admin.ModelAdmin):
    list_display = ("__str__",)
