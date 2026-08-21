from django.urls import path

from .web_views import CompetencyTreeView, TrainingCourseListView, ValiderFormationView

urlpatterns = [
    path("", TrainingCourseListView.as_view(), name="formation-list"),
    path("valider/", ValiderFormationView.as_view(), name="formation-valider"),
    path("arbre-competences/", CompetencyTreeView.as_view(), name="formation-arbre-competences"),
]
