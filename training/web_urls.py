from django.urls import path

from .web_views import CompetencyTreeView, TrainingCourseListView

urlpatterns = [
    path("", TrainingCourseListView.as_view(), name="formation-list"),
    path("arbre-competences/", CompetencyTreeView.as_view(), name="formation-arbre-competences"),
]
