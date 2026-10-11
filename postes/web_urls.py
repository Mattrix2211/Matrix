from django.urls import path

from . import web_views

urlpatterns = [
    path("", web_views.PostesIndexView.as_view(), name="postes-index"),
    path("nouveau/", web_views.PosteNouveauView.as_view(), name="poste-nouveau"),
    path("<int:pk>/", web_views.PosteDetailView.as_view(), name="poste-detail"),
]
