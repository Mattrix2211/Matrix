"""Tableau de bord personnel du marin (dashboard/web_views.py).

Sous-domaine extrait lors du découpage du fichier (tâche Notion « [ARCH]
Découper dashboard/web_views.py (1063 lignes) par sous-domaine »,
dashboard/web_views.py ayant dépassé 800 lignes) : la page d'accueil de
Matrix, construite autour du principe fondamental n°3 (CLAUDE.md) — chaque
marin voit SES tâches, SES formations, SES maintenances assignées, dès la
connexion, sans avoir à chercher.

Refactor pur : reproduit exactement le comportement d'origine. La constante
_STATUTS_MAINTENANCE_TERMINES reste partagée avec les autres sous-domaines
(voir dashboard/web_views.py) et est importée depuis ce module central."""
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.utils import timezone
from django.views.generic import TemplateView

from logistics.models import CorrectiveTicket
from maintenance.models import MaintenanceOccurrence
from quarts.services import compteur_equite_marin, feuille_service_du_jour_pour
from rondes.services import rondes_du_marin
from training.models import TrainingSession
from training.services import qualifications_validees_de

from .web_views import _STATUTS_MAINTENANCE_TERMINES

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

        # Formations où le marin est inscrit par un référent (attendees), où il
        # a réservé sa place lui-même en libre-service (reservations, cf.
        # T-FORM réservation), OU où il est le formateur (instructor) de la
        # session — les trois cas doivent apparaître dans son espace
        # personnel : un formateur doit voir dans SON tableau de bord les
        # sessions qu'il anime, même s'il n'y est pas lui-même stagiaire
        # (cf. tâche Notion « Calendrier de formation piloté par l'affectation
        # personnelle »). D'où le OU plutôt qu'un simple filtre.
        mes_formations = list(
            TrainingSession.objects.select_related("course")
            .filter(
                Q(attendees=self.request.user)
                | Q(reservations=self.request.user)
                | Q(instructor=self.request.user),
                status="PLANNED",
            )
            .distinct()
            .order_by("scheduled_at")
        )
        for session in mes_formations:
            session.est_formateur = session.instructor_id == self.request.user.id

        mes_tickets = list(
            CorrectiveTicket.objects.select_related("asset", "installation")
            .filter(assignees=self.request.user)
            .exclude(status__in=_STATUTS_TICKET_TERMINES)
            .order_by("-severity", "reported_at")
        )

        aujourdhui = timezone.localdate()

        # Formations déjà validées par le marin (TrainingRecord), avec leur
        # date d'expiration et leur badge de statut — jusqu'ici cette
        # information n'apparaissait que sous forme de notification
        # ponctuelle (notify_expiring_training, notifications/tasks.py) qui
        # disparaît une fois passée, sans vue d'ensemble permanente dans
        # l'espace personnel du marin. Requête factorisée dans
        # training/services.py (réutilisée à l'identique par « Mon profil »,
        # accounts/web_views.py).
        mes_qualifications = qualifications_validees_de(self.request.user, aujourdhui)

        # Compteur d'équité des services de garde (Phase 2, tâche Notion
        # « Services/gardes : compteur d'équité par marin ») : transparence du
        # marin sur SA propre situation (mois en cours + année en cours),
        # jamais celle des autres — les compteurs détaillés du périmètre
        # entier restent réservés au chef de liste, sur la fiche de la liste
        # (quarts/web_views.py::_DetailListeViewBase).
        contexte["mes_compteurs_equite_garde"] = compteur_equite_marin(self.request.user, aujourdhui=aujourdhui)

        # Feuille de service quotidienne (Phase 2, tâche Notion « Feuille de
        # service quotidienne — personnel de service et en-tête (à quai) ») :
        # affichée sur l'accueil uniquement si publiée, avec mise en évidence
        # si le marin connecté est lui-même de service ce jour-là.
        contexte["feuille_service_du_jour"] = feuille_service_du_jour_pour(self.request.user, aujourdhui)

        # Rondes à faire aujourd'hui (ou en retard) : assignées au marin ou de son périmètre.
        contexte["mes_rondes"] = list(rondes_du_marin(self.request.user, aujourdhui)[:10])
        contexte["mes_maintenances"] = mes_maintenances
        contexte["mes_formations"] = mes_formations
        contexte["mes_tickets"] = mes_tickets
        contexte["mes_qualifications"] = mes_qualifications
        contexte["aujourdhui"] = aujourdhui
        return contexte
