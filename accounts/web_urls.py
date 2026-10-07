from django.urls import path
from .web_views import UserDirectoryView, UserFormView, MonProfilView, BasculerThemeView, ChoisirBatimentView, MemoriserBarreLateraleView

urlpatterns = [
    path("", UserDirectoryView.as_view(), name="user-directory"),
    path("nouveau/", UserFormView.as_view(), name="user-create"),
    path("<int:pk>/modifier/", UserFormView.as_view(), name="user-edit"),
    path("profil/", MonProfilView.as_view(), name="mon-profil"),
    path("theme/", BasculerThemeView.as_view(), name="basculer-theme"),
    path("batiment/", ChoisirBatimentView.as_view(), name="choisir-batiment"),
    path("barre-laterale/", MemoriserBarreLateraleView.as_view(), name="memoriser-barre-laterale"),
]
