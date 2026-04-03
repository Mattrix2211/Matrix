from django.contrib import admin
from .models import CorrectiveTicket, TicketStatusLog, PartRequest, PartLineItem
from bordops.core.admin import AdminScopedMixin

@admin.register(CorrectiveTicket)
class CorrectiveTicketAdmin(AdminScopedMixin, admin.ModelAdmin):
    list_display = ("id", "asset", "status", "severity", "reported_at")
    list_filter = ("status", "severity")
    search_fields = ("id", "description")

@admin.register(TicketStatusLog)
class TicketStatusLogAdmin(admin.ModelAdmin):
    list_display = ("ticket", "old_status", "new_status", "created_at", "user")

class PartLineItemInline(admin.TabularInline):
    model = PartLineItem
    extra = 1

@admin.register(PartRequest)
class PartRequestAdmin(admin.ModelAdmin):
    list_display = ("ticket", "requested_by", "needed_by_date", "status")
    inlines = [PartLineItemInline]
