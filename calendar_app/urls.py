from django.urls import path
from .views import CalendarView, calendar_events, calendar_event_move
from .ical_views import user_ical_feed

urlpatterns = [
    path('', CalendarView.as_view(), name='calendar-index'),
    path('events/', calendar_events, name='calendar-events'),
    path('events/move/', calendar_event_move, name='calendar-event-move'),
    path('ical/my/', user_ical_feed, name='calendar-ical-my'),
]
