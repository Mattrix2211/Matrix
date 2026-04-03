from rest_framework import views, permissions, response
from django.utils import timezone
from datetime import timedelta
from maintenance.models import MaintenanceOccurrence
from logistics.models import CorrectiveTicket

class PreventiveWeekChartView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        today = timezone.localdate()
        days = [today + timedelta(days=i) for i in range(-3, 4)]
        labels = [d.strftime("%d/%m") for d in days]
        planned = [MaintenanceOccurrence.objects.filter(scheduled_for=d).count() for d in days]
        done = [MaintenanceOccurrence.objects.filter(scheduled_for=d, status="DONE").count() for d in days]
        return response.Response({
            "labels": labels,
            "datasets": [
                {"label": "Planifié", "data": planned, "backgroundColor": "#0d6efd"},
                {"label": "Réalisé", "data": done, "backgroundColor": "#198754"},
            ]
        })

class CorrectiveOpenChartView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        open_statuses = ["REPORTED", "DIAGNOSED", "WAITING_PARTS", "PLANNED", "IN_REPAIR", "TESTING"]
        data = [CorrectiveTicket.objects.filter(status=s).count() for s in open_statuses]
        return response.Response({
            "labels": open_statuses,
            "datasets": [
                {"label": "Tickets ouverts", "data": data, "backgroundColor": ["#0d6efd", "#6c757d", "#ffc107", "#0dcaf0", "#20c997", "#6610f2"]}
            ]
        })
