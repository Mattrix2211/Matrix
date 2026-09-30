from django.contrib import admin
from .models import Notification, PushSubscription

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("user", "verb", "level", "is_read", "created_at")
    list_filter = ("level", "is_read")

@admin.register(PushSubscription)
class PushSubscriptionAdmin(admin.ModelAdmin):
    """L'endpoint et les clés de chiffrement sont des secrets d'abonnement :
    jamais affichés en entier, jamais utilisés pour la recherche."""
    list_display = ("user", "endpoint_tronque", "user_agent", "created_at")
    search_fields = ("user__username",)
    # Les clés p256dh/auth et l'endpoint complet ne sont pas exposés sur la page de détail.
    fields = ("user", "endpoint_tronque", "user_agent", "created_at")
    readonly_fields = ("user", "endpoint_tronque", "user_agent", "created_at")

    def has_add_permission(self, request):
        # Un abonnement ne se crée que depuis le navigateur du marin.
        return False

    @admin.display(description="Point d'accès (tronqué)")
    def endpoint_tronque(self, obj):
        # Même convention que PushSubscription.__str__ : 40 caractères.
        return f"{obj.endpoint[:40]}…"
