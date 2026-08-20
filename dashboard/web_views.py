"""Vue web de la page d'accueil — tableau de bord + espace personnel du marin.

Principe fondamental n°3 (CLAUDE.md) : chaque marin voit SES tâches, SES
formations, SES maintenances assignées, dès la connexion, sans avoir à
chercher. Cette vue construit le contexte de l'accueil pour ça, en plus
des graphiques Chart.js déjà en place (T5) et du bouton "Générer le bilan"
(T10), qui restent inchangés.
"""
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.db.models import Count, F, Q
from django.utils import timezone
from django.views.generic import TemplateView

from logistics.models import CorrectiveTicket, STATUTS_TICKET_OUVERTS, StockPiece
from maintenance.models import MaintenanceOccurrence
from matrix.core.roles import RoleLevel, user_role_level
from matrix.core.scopes import is_master_admin, ship_id_for_user
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

        # Formations où le marin est inscrit par un référent (attendees) OU où
        # il a réservé sa place lui-même en libre-service (reservations, cf.
        # T-FORM réservation) — les deux mécanismes doivent apparaître dans
        # son espace personnel, d'où le OU plutôt qu'un simple filtre.
        mes_formations = list(
            TrainingSession.objects.select_related("course")
            .filter(Q(attendees=self.request.user) | Q(reservations=self.request.user), status="PLANNED")
            .distinct()
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


class VueFlotteView(LoginRequiredMixin, TemplateView):
    """Vue agrégée du navire — réservée à CHEF_SERVICE et aux rôles supérieurs.

    Contrairement à TableauDeBordView (espace personnel du marin, principe
    fondamental n°3 de CLAUDE.md), cette vue donne aux chefs une photo
    d'ensemble de leur navire : maintenances en retard, tickets correctifs
    ouverts par statut, pièces de stock sous seuil. Aucune donnée nouvelle,
    aucun nouveau système de périmètre : les mêmes requêtes que
    notify_overdue_occurrences, CorrectiveOpenChartView et notify_low_stock
    (notifications/tasks.py, dashboard/views.py), simplement agrégées et
    scopées au navire (matrix.core.scopes.ship_id_for_user) plutôt qu'envoyées
    en notification individuelle.
    """

    template_name = "dashboard/flotte.html"

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated and user_role_level(request.user) < RoleLevel.CHEF_SERVICE:
            raise PermissionDenied("Réservé aux chefs de service et rôles supérieurs.")
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        contexte = super().get_context_data(**kwargs)
        user = self.request.user

        # Accès flotte entière réservé à MASTER_ADMIN (cf. org/views.py::_is_master_admin,
        # même règle) : tous les autres rôles, ADMIN_NAVIRE compris, sont bornés à leur
        # propre navire.
        flotte_entiere = is_master_admin(user)
        navire_id = None if flotte_entiere else ship_id_for_user(user)

        if not flotte_entiere and navire_id is None:
            # Profil sans navire renseigné : rien à agréger, message clair plutôt
            # qu'une page vide sans explication.
            contexte["aucun_navire"] = True
            contexte["flotte_entiere"] = False
            contexte["maintenances_en_retard"] = 0
            contexte["tickets_par_statut"] = []
            contexte["total_tickets_ouverts"] = 0
            contexte["pieces_sous_seuil"] = []
            return contexte

        # Une occurrence porte soit sur du matériel mobile (asset), soit sur une
        # installation fixe (installation_maintenance) — jamais les deux à la fois,
        # même logique que MaintenanceOccurrenceViewSet.get_scoped_filters().
        filtre_occurrence = Q()
        filtre_ticket = Q()
        filtre_stock = Q()
        if not flotte_entiere:
            filtre_occurrence = Q(asset__ship_id=navire_id) | Q(
                installation_maintenance__installation__ship_id=navire_id
            )
            filtre_ticket = Q(asset__ship_id=navire_id)
            filtre_stock = Q(ship_id=navire_id)

        contexte["maintenances_en_retard"] = MaintenanceOccurrence.objects.filter(
            filtre_occurrence, status="OVERDUE"
        ).count()

        # Une seule requête agrégée par statut, même pattern que
        # dashboard/views.py::CorrectiveOpenChartView.
        totaux_par_statut = dict(
            CorrectiveTicket.objects.filter(filtre_ticket, status__in=STATUTS_TICKET_OUVERTS)
            .values("status")
            .annotate(total=Count("id"))
            .values_list("status", "total")
        )
        libelles_statut = dict(CorrectiveTicket.STATUS)
        tickets_par_statut = [
            {
                "statut": statut,
                "libelle": libelles_statut.get(statut, statut),
                "total": totaux_par_statut.get(statut, 0),
            }
            for statut in STATUTS_TICKET_OUVERTS
        ]

        contexte["tickets_par_statut"] = tickets_par_statut
        contexte["total_tickets_ouverts"] = sum(t["total"] for t in tickets_par_statut)
        contexte["pieces_sous_seuil"] = list(
            StockPiece.objects.filter(filtre_stock, quantite__lt=F("quantite_minimale"))
            .select_related("service", "sector", "section")
            .order_by("reference")
        )
        contexte["aucun_navire"] = False
        contexte["flotte_entiere"] = flotte_entiere
        return contexte
