from django.urls import path

from .web_views import GenererBilanView

urlpatterns = [
    path("rapports/bilan/", GenererBilanView.as_view(), name="rapport-bilan"),
]
