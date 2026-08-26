from django.urls import path
from .web_views import UserDirectoryView, MonProfilView

urlpatterns = [
    path("", UserDirectoryView.as_view(), name="user-directory"),
    path("profil/", MonProfilView.as_view(), name="mon-profil"),
]
