from django.urls import path

from .web_views import MesAbsencesView

urlpatterns = [
    path("", MesAbsencesView.as_view(), name="absences-index"),
]
