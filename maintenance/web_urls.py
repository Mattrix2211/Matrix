from django.urls import path
from .web_views import (
    OccurrenceExecuteView,
    OccurrenceCommentCreateView,
    MaintenancePlanListView,
    MaintenanceOccurrenceListView,
    MaintenanceOccurrenceSelfAssignView,
)

urlpatterns = [
    path('occurrences/<int:pk>/execute/', OccurrenceExecuteView.as_view(), name='occurrence-execute'),
    path('occurrences/<int:pk>/commentaire/', OccurrenceCommentCreateView.as_view(), name='occurrence-comment-create'),
    path('occurrences/<int:pk>/assigner/', MaintenanceOccurrenceSelfAssignView.as_view(), name='occurrence-self-assign'),
    path('gestion/plans/', MaintenancePlanListView.as_view(), name='maintenance-plans'),
    path('gestion/occurrences/', MaintenanceOccurrenceListView.as_view(), name='maintenance-occurrences'),
]
