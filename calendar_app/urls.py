from django.urls import path
from .views import (
    CalendarView,
    calendar_events,
    calendar_event_move,
    personal_event_save,
    personal_event_delete,
)
from .detail_views import detail_commentaire, detail_evenement, detail_tache_demarrer
from .ical_views import user_ical_feed

urlpatterns = [
    path('', CalendarView.as_view(), name='calendar-index'),
    path('events/', calendar_events, name='calendar-events'),
    path('events/move/', calendar_event_move, name='calendar-event-move'),
    path('personnel/enregistrer/', personal_event_save, name='calendar-personal-save'),
    path('personnel/<int:pk>/supprimer/', personal_event_delete, name='calendar-personal-delete'),
    path('detail/tache/<int:pk>/demarrer/', detail_tache_demarrer, name='calendar-detail-demarrer'),
    path('detail/<str:type_evenement>/<int:pk>/', detail_evenement, name='calendar-detail'),
    path('detail/<str:type_evenement>/<int:pk>/commentaire/', detail_commentaire, name='calendar-detail-commentaire'),
    path('ical/my/', user_ical_feed, name='calendar-ical-my'),
]
