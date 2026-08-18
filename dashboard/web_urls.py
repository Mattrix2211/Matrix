from django.urls import path

from .web_views import VueFlotteView

urlpatterns = [
    path("flotte/", VueFlotteView.as_view(), name="vue-flotte"),
]
