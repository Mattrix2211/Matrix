from django.urls import path

from . import web_views

urlpatterns = [
    path("", web_views.RetexIndexView.as_view(), name="retex-index"),
    path("nouveau/", web_views.RetexNouveauView.as_view(), name="retex-nouveau"),
    path("domaines/", web_views.DomainesView.as_view(), name="retex-domaines"),
    path("<int:pk>/", web_views.RetexDetailView.as_view(), name="retex-detail"),
    path("<int:pk>/action/", web_views.RetexActionView.as_view(), name="retex-action"),
]
