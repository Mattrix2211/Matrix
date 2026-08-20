from django.contrib import admin
from .models import Notification, PushSubscription

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("user", "verb", "level", "is_read", "created_at")
    list_filter = ("level", "is_read")

@admin.register(PushSubscription)
class PushSubscriptionAdmin(admin.ModelAdmin):
    list_display = ("user", "endpoint", "user_agent", "created_at")
    search_fields = ("user__username", "endpoint")
