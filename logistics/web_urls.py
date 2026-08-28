from django.urls import path
from .web_views import (
    TicketListView, TicketDetailView, TicketCreateView, TicketAssignView, TicketTransitionView,
    TicketCommentCreateView, PartRequestCreateView,
    PartLineItemCreateView, PartLineItemUpdateStatusView, StockPieceListView,
    TicketStockPrelevementView,
)

urlpatterns = [
    path('tickets/', TicketListView.as_view(), name='ticket-list'),
    path('tickets/creer/<uuid:asset_pk>/', TicketCreateView.as_view(), name='ticket-create'),
    path('tickets/<uuid:pk>/', TicketDetailView.as_view(), name='ticket-detail'),
    path('tickets/<uuid:pk>/assign/', TicketAssignView.as_view(), name='ticket-assign'),
    path('tickets/<uuid:pk>/transition/', TicketTransitionView.as_view(), name='ticket-transition'),
    path('tickets/<uuid:pk>/commentaire/', TicketCommentCreateView.as_view(), name='ticket-comment-create'),
    path('tickets/<uuid:pk>/part-request/create/', PartRequestCreateView.as_view(), name='part-request-create'),
    path('tickets/<uuid:pk>/prelever-stock/', TicketStockPrelevementView.as_view(), name='ticket-stock-prelevement'),
    path('part-request/<int:pr_id>/line/create/', PartLineItemCreateView.as_view(), name='part-line-create'),
    path('part-line/<int:line_id>/status/', PartLineItemUpdateStatusView.as_view(), name='part-line-status'),
    path('stock/', StockPieceListView.as_view(), name='stock-piece-list'),
]
