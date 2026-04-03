from django.urls import path
from .web_views import UserDirectoryView

urlpatterns = [
    path("", UserDirectoryView.as_view(), name="user-directory"),
]
