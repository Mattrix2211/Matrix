from django.urls import path
from .web_views import UserDirectoryView, MonProfilView, BasculerThemeView

urlpatterns = [
    path("", UserDirectoryView.as_view(), name="user-directory"),
    path("profil/", MonProfilView.as_view(), name="mon-profil"),
    path("theme/", BasculerThemeView.as_view(), name="basculer-theme"),
]
