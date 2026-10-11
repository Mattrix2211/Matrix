from django.urls import path

from . import web_views

urlpatterns = [
    path("", web_views.BibliothequeView.as_view(), name="documentation-index"),
    path("nouveau/", web_views.DocumentNouveauView.as_view(), name="document-nouveau"),
    path("lier/", web_views.DocumentLierView.as_view(), name="document-lier"),
    path("<int:pk>/", web_views.DocumentDetailView.as_view(), name="document-detail"),
    path("<int:pk>/action/", web_views.DocumentActionView.as_view(), name="document-action"),
]
