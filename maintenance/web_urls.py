from django.urls import path
from .correctif_web import CompteRenduCorrectifView
from .historique_web import HistoriqueEquipementView
from .tournee_web import TourneeImprimerView, TourneeSaisieView
from .web_views import (
    OccurrenceExecuteView,
    OccurrenceImprimerView,
    OccurrenceSignalerFicheView,
    OccurrenceCommentCreateView,
    MaintenancePlanListView,
    MaintenanceOccurrenceListView,
    MaintenanceOccurrenceSelfAssignView,
)

urlpatterns = [
    path('occurrences/<int:pk>/execute/', OccurrenceExecuteView.as_view(), name='occurrence-execute'),
    path('occurrences/<int:pk>/signaler-fiche/', OccurrenceSignalerFicheView.as_view(), name='occurrence-signaler-fiche'),
    path('occurrences/<int:pk>/imprimer/', OccurrenceImprimerView.as_view(), name='occurrence-imprimer'),
    path('occurrences/tournee/', TourneeSaisieView.as_view(), name='tournee-saisie'),
    path('occurrences/tournee/imprimer/', TourneeImprimerView.as_view(), name='tournee-imprimer'),
    path('occurrences/imprimer/', OccurrenceImprimerView.as_view(), name='occurrences-imprimer'),
    path('occurrences/<int:pk>/commentaire/', OccurrenceCommentCreateView.as_view(), name='occurrence-comment-create'),
    path('occurrences/<int:pk>/assigner/', MaintenanceOccurrenceSelfAssignView.as_view(), name='occurrence-self-assign'),
    path('correctifs/nouveau/', CompteRenduCorrectifView.as_view(), name='correctif-nouveau'),
    path('correctifs/<uuid:ticket_pk>/compte-rendu/', CompteRenduCorrectifView.as_view(), name='correctif-compte-rendu'),
    path('historique/installation/<uuid:pk>/', HistoriqueEquipementView.as_view(), name='historique-installation'),
    path('historique/materiel/<uuid:pk>/', HistoriqueEquipementView.as_view(materiel=True), name='historique-materiel'),
    path('gestion/plans/', MaintenancePlanListView.as_view(), name='maintenance-plans'),
    path('gestion/occurrences/', MaintenanceOccurrenceListView.as_view(), name='maintenance-occurrences'),
]
