from django.urls import path

from .web_views import EquipagesView

urlpatterns = [
    path("", EquipagesView.as_view(), name="equipages"),
]
