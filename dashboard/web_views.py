"""Vue web de la page d'accueil — tableau de bord + espace personnel du marin.

Principe fondamental n°3 (CLAUDE.md) : chaque marin voit SES tâches, SES
formations, SES maintenances assignées, dès la connexion, sans avoir à
chercher. Cette vue construit le contexte de l'accueil pour ça, en plus
des graphiques Chart.js déjà en place (T5) et du bouton "Générer le bilan"
(T10), qui restent inchangés.
"""
from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils import timezone
from django.views.generic import TemplateView

from logistics.models import CorrectiveTicket
from maintenance.models import MaintenanceOccurrence
from training.models import TrainingSession

# Occurrences considérées comme terminées : on ne les affiche pas dans "Mes
# maintenances", seules celles qui restent à faire intéressent le marin.
_STATUTS_MAINTENANCE_TERMINES = ["DONE", "CANCELLED"]

# Tickets correctifs considérés comme clos : on ne les affiche pas dans "Mes
# tickets", même logique que _STATUTS_MAINTENANCE_TERMINES ci-dessus.
_STATUTS_TICKET_TERMINES = ["CLOSED", "CANCELLED"]

# Classe de badge Bootstrap par statut d'occurrence — surchargée par
# matrix.css pour respecter la palette du design system (--red, --amber...).
_BADGE_STATUT_MAINTENANCE = {
    "OVERDUE": "bg-danger",
    "WAITING_VALIDATION": "bg-warning",
}


class TableauDeBordView(LoginRequiredMixin, TemplateView):
    """Page d'accueil : graphiques du service + espace personnel du marin connecté."""

    template_name = "dashboard/index.html"

    def get_context_data(self, **kwargs):
        contexte = super().get_context_data(**kwargs)

        mes_maintenances = list(
            MaintenanceOccurrence.objects.select_related(
                "asset",
                "installation_maintenance",
                "installation_maintenance__installation",
            )
            .filter(assignees=self.request.user)
            .exclude(status__in=_STATUTS_MAINTENANCE_TERMINES)
            .order_by("scheduled_for")
        )
        for occurrence in mes_maintenances:
            occurrence.badge_classe = _BADGE_STATUT_MAINTENANCE.get(
                occurrence.status, "bg-secondary"
            )

        mes_formations = list(
            TrainingSession.objects.select_related("course")
            .filter(attendees=self.request.user, status="PLANNED")
            .order_by("scheduled_at")
        )

        mes_tickets = list(
            CorrectiveTicket.objects.select_related("asset")
            .filter(assignees=self.request.user)
            .exclude(status__in=_STATUTS_TICKET_TERMINES)
            .order_by("-severity", "reported_at")
        )

        contexte["mes_maintenances"] = mes_maintenances
        contexte["mes_formations"] = mes_formations
        contexte["mes_tickets"] = mes_tickets
        contexte["aujourdhui"] = timezone.localdate()
        return contexte
