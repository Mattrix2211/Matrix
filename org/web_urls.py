from django.urls import path

from .web_views import EquipagesView, PassationDetailView, PassationsView

urlpatterns = [
    path("", EquipagesView.as_view(), name="equipages"),
    path("passations/", PassationsView.as_view(), name="passations"),
    path("passations/<int:pk>/", PassationDetailView.as_view(), name="passation_detail"),
]
