from django.urls import path

from .web_views import (
    CompetencyTreeView,
    FormationCommentCreateView,
    FormationDetailView,
    TrainingCourseListView,
    ValiderFormationView,
)

urlpatterns = [
    path("", TrainingCourseListView.as_view(), name="formation-list"),
    path("valider/", ValiderFormationView.as_view(), name="formation-valider"),
    path("arbre-competences/", CompetencyTreeView.as_view(), name="formation-arbre-competences"),
    path("<int:pk>/", FormationDetailView.as_view(), name="formation-detail"),
    path("<int:pk>/commentaire/", FormationCommentCreateView.as_view(), name="formation-commentaire"),
]
