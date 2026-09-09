from django.urls import path

from .web_views import (
    ChefDeListeReglagesView,
    ListeIndexView,
    QuartDetailView,
    ServiceGardeDetailView,
)

urlpatterns = [
    path("", ListeIndexView.as_view(), name="quarts-index"),
    path("reglages/", ChefDeListeReglagesView.as_view(), name="quarts-reglages"),
    path("quart/<int:pk>/", QuartDetailView.as_view(), name="quart-detail"),
    path("garde/<int:pk>/", ServiceGardeDetailView.as_view(), name="garde-detail"),
]
