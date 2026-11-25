from django.urls import path
from .web_views import UserDirectoryView, UserFormView, MonProfilView, BasculerThemeView, ChoisirBatimentView, MemoriserBarreLateraleView, EnregistrerPreferenceView, FonctionsAConfirmerView, VerificationsIdentiteView

urlpatterns = [
    path("", UserDirectoryView.as_view(), name="user-directory"),
    path("fonctions-a-confirmer/", FonctionsAConfirmerView.as_view(), name="fonctions-a-confirmer"),
    path("verifications/", VerificationsIdentiteView.as_view(), name="verifications-identite"),
    path("nouveau/", UserFormView.as_view(), name="user-create"),
    path("<int:pk>/modifier/", UserFormView.as_view(), name="user-edit"),
    path("profil/", MonProfilView.as_view(), name="mon-profil"),
    path("theme/", BasculerThemeView.as_view(), name="basculer-theme"),
    path("batiment/", ChoisirBatimentView.as_view(), name="choisir-batiment"),
    path("barre-laterale/", MemoriserBarreLateraleView.as_view(), name="memoriser-barre-laterale"),
    path("preferences/", EnregistrerPreferenceView.as_view(), name="enregistrer-preference"),
]
