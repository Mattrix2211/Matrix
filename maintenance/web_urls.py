from django.urls import path
from .tournee_web import TourneeImprimerView, TourneeSaisieView
from .web_views import (
    OccurrenceExecuteView,
    OccurrenceImprimerView,
    OccurrenceCommentCreateView,
    MaintenancePlanListView,
    MaintenanceOccurrenceListView,
    MaintenanceOccurrenceSelfAssignView,
)

urlpatterns = [
    path('occurrences/<int:pk>/execute/', OccurrenceExecuteView.as_view(), name='occurrence-execute'),
    path('occurrences/<int:pk>/imprimer/', OccurrenceImprimerView.as_view(), name='occurrence-imprimer'),
    path('occurrences/tournee/', TourneeSaisieView.as_view(), name='tournee-saisie'),
    path('occurrences/tournee/imprimer/', TourneeImprimerView.as_view(), name='tournee-imprimer'),
    path('occurrences/imprimer/', OccurrenceImprimerView.as_view(), name='occurrences-imprimer'),
    path('occurrences/<int:pk>/commentaire/', OccurrenceCommentCreateView.as_view(), name='occurrence-comment-create'),
    path('occurrences/<int:pk>/assigner/', MaintenanceOccurrenceSelfAssignView.as_view(), name='occurrence-self-assign'),
    path('gestion/plans/', MaintenancePlanListView.as_view(), name='maintenance-plans'),
    path('gestion/occurrences/', MaintenanceOccurrenceListView.as_view(), name='maintenance-occurrences'),
]
