from rest_framework import views, permissions, response
from django.db.models import Count, Q
from django.utils import timezone
from datetime import timedelta
from maintenance.models import MaintenanceOccurrence
from logistics.models import CorrectiveTicket, STATUTS_TICKET_OUVERTS

class PreventiveWeekChartView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        today = timezone.localdate()
        days = [today + timedelta(days=i) for i in range(-3, 4)]
        labels = [d.strftime("%d/%m") for d in days]

        # Une seule requête agrégée : nombre d'occurrences planifiées et réalisées
        # par jour, plutôt qu'une requête .count() par jour et par métrique.
        rows = (
            MaintenanceOccurrence.objects.filter(scheduled_for__in=days)
            .values("scheduled_for")
            .annotate(
                planned=Count("id"),
                done=Count("id", filter=Q(status="DONE")),
            )
        )
        counts_by_day = {row["scheduled_for"]: row for row in rows}
        planned = [counts_by_day.get(d, {}).get("planned", 0) for d in days]
        done = [counts_by_day.get(d, {}).get("done", 0) for d in days]

        return response.Response({
            "labels": labels,
            "datasets": [
                {"label": "Planifié", "data": planned},
                {"label": "Réalisé", "data": done},
            ]
        })

class CorrectiveOpenChartView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        open_statuses = STATUTS_TICKET_OUVERTS

        # Une seule requête agrégée par statut, plutôt qu'une requête .count() par statut.
        rows = (
            CorrectiveTicket.objects.filter(status__in=open_statuses)
            .values("status")
            .annotate(total=Count("id"))
        )
        counts_by_status = {row["status"]: row["total"] for row in rows}
        data = [counts_by_status.get(s, 0) for s in open_statuses]
        libelles = dict(CorrectiveTicket.STATUS)

        return response.Response({
            "labels": [libelles[s] for s in open_statuses],
            "datasets": [{"label": "Tickets ouverts", "data": data}],
        })
