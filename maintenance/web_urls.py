from django.urls import path
from .web_views import OccurrenceExecuteView

urlpatterns = [
    path('occurrences/<int:pk>/execute/', OccurrenceExecuteView.as_view(), name='occurrence-execute'),
]
