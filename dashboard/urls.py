from django.urls import path
from .views import PreventiveWeekChartView, CorrectiveOpenChartView

urlpatterns = [
    path('preventive_week/', PreventiveWeekChartView.as_view()),
    path('corrective_open/', CorrectiveOpenChartView.as_view()),
]
