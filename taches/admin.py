from django.contrib import admin

from .models import Tache


@admin.register(Tache)
class TacheAdmin(admin.ModelAdmin):
    list_display = ("titre", "assigne", "echeance", "statut")
    list_filter = ("statut",)
