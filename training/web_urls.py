from django.urls import path

from .web_views import FormationsListView, ValiderFormationView

urlpatterns = [
    path("", FormationsListView.as_view(), name="formations"),
    path("valider/", ValiderFormationView.as_view(), name="formation-valider"),
]
