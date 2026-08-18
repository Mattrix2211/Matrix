from django.urls import path
from .web_views import (
    TicketListView, TicketDetailView, TicketAssignView, TicketTransitionView, PartRequestCreateView,
    PartLineItemCreateView, PartLineItemUpdateStatusView, StockPieceListView,
)

urlpatterns = [
    path('tickets/', TicketListView.as_view(), name='ticket-list'),
    path('tickets/<uuid:pk>/', TicketDetailView.as_view(), name='ticket-detail'),
    path('tickets/<uuid:pk>/assign/', TicketAssignView.as_view(), name='ticket-assign'),
    path('tickets/<uuid:pk>/transition/', TicketTransitionView.as_view(), name='ticket-transition'),
    path('tickets/<uuid:pk>/part-request/create/', PartRequestCreateView.as_view(), name='part-request-create'),
    path('part-request/<int:pr_id>/line/create/', PartLineItemCreateView.as_view(), name='part-line-create'),
    path('part-line/<int:line_id>/status/', PartLineItemUpdateStatusView.as_view(), name='part-line-status'),
    path('stock/', StockPieceListView.as_view(), name='stock-piece-list'),
]
