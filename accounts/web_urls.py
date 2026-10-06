from django.urls import path
from .web_views import UserDirectoryView, MonProfilView, BasculerThemeView, ChoisirBatimentView, MemoriserBarreLateraleView

urlpatterns = [
    path("", UserDirectoryView.as_view(), name="user-directory"),
    path("profil/", MonProfilView.as_view(), name="mon-profil"),
    path("theme/", BasculerThemeView.as_view(), name="basculer-theme"),
    path("batiment/", ChoisirBatimentView.as_view(), name="choisir-batiment"),
    path("barre-laterale/", MemoriserBarreLateraleView.as_view(), name="memoriser-barre-laterale"),
]
