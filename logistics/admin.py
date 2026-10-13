from django.contrib import admin
from .models import CorrectiveTicket, TicketStatusLog, PartRequest, PartLineItem, StockPiece, MouvementStock
from matrix.core.admin import AdminScopedMixin

@admin.register(CorrectiveTicket)
class CorrectiveTicketAdmin(AdminScopedMixin, admin.ModelAdmin):
    list_display = ("id", "asset", "status", "severity", "reported_at", "valide_par", "date_validation")
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

@admin.register(StockPiece)
class StockPieceAdmin(AdminScopedMixin, admin.ModelAdmin):
    list_display = ("reference", "designation", "quantite", "quantite_minimale", "quantite_critique", "emplacement", "ship", "service", "sector", "section", "installation", "asset")
    list_filter = ("ship", "service", "sector")
    search_fields = ("reference", "designation", "emplacement")
    # La quantité ne se modifie que par un mouvement de stock.
    readonly_fields = ("quantite",)


@admin.register(MouvementStock)
class MouvementStockAdmin(admin.ModelAdmin):
    list_display = ("created_at", "piece", "type", "quantite", "solde_apres", "auteur", "motif")
    list_filter = ("type",)
    search_fields = ("piece__reference", "motif")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
