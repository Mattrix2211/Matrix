"""Vue HTML du calendrier central (découpage de calendar_app/views.py)."""
from datetime import datetime, timedelta

from django.contrib.auth import get_user_model
from taches.services import peut_attribuer
from .sources import SOURCES
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.shortcuts import render
from django.utils import timezone
from django.views.generic import TemplateView

from matrix.core.contexte_batiment import referentiel_organisation
from matrix.core.mixins import utilisateurs_visibles_par
from matrix.core.scopes import assignes_equipage_q, equipage_marin_q
from maintenance.models import MaintenanceOccurrence
from logistics.models import CorrectiveTicket
from training.models import TrainingSession
from .evenements_sources import (
    _absences_periode,
    _appliquer_filtres_occurrences,
    _appliquer_filtres_tickets,
    _creneaux_garde_assignes,
    _creneaux_quart_assignes,
    occurrences_visibles,
    sessions_visibles,
    tickets_visibles,
    _evenements_personnels,
)
from .models import PersonalEvent


class CalendarView(LoginRequiredMixin, TemplateView):
    """Calendrier central unique (colonne vertébrale, CLAUDE.md). Maintenance et tickets sont bornés
    au périmètre du marin (ou à ses assignations) ; les sessions de formation suivent l'affectation
    personnelle (cf. sessions_visibles). Les menus navire/service/secteur affinent ce périmètre."""

    template_name = "calendar/index.html"

    def get(self, request, *args, **kwargs):
        view = request.GET.get("view", "month")
        date_str = request.GET.get("date")
        today = timezone.localdate()
        base = today
        if date_str:
            try:
                base = datetime.fromisoformat(date_str).date()
            except Exception:
                base = today

        filters = self._parse_filters(request)

        if view == "day":
            start, end = base, base
        elif view == "week":
            start = base - timedelta(days=base.weekday())
            end = start + timedelta(days=6)
        else:
            start = base.replace(day=1)
            # naïf: aller au mois suivant et reculer d’un jour
            if start.month == 12:
                next_month = start.replace(year=start.year + 1, month=1, day=1)
            else:
                next_month = start.replace(month=start.month + 1, day=1)
            end = next_month - timedelta(days=1)

        events = self._collect_events(request, start, end, filters)

        User = get_user_model()
        ctx = {
            "view": view,
            "date": base,
            "start": start,
            "end": end,
            "events": events,
            **{cle: valeur for cle, valeur in referentiel_organisation(request.user).items() if cle != "sections"},
            "users": utilisateurs_visibles_par(request.user).filter(equipage_marin_q(request.user)).order_by("username"),
            "active_filters": {**filters, "user": request.GET.get("user") or None},
            "peut_equipe": peut_attribuer(request.user),
            "sources": SOURCES,
            "mes_evenements_personnels": PersonalEvent.objects.filter(
                owner=request.user, starts_at__gte=timezone.now()
            ).order_by("starts_at")[:20],
        }
        return render(request, self.template_name, ctx)

    def _parse_filters(self, request):
        return {
            "ship": request.GET.get("ship") or None,
            "service": request.GET.get("service") or None,
            "sector": request.GET.get("sector") or None,
            "user": (request.GET.get("user") if request.GET.get("user") != "equipe" else "") or None,  # « équipe » : API seulement
            "type": request.GET.get("type") or None,
            "status": request.GET.get("status") or None,
        }

    def _collect_events(self, request, start, end, filters):
        events = []
        # Maintenance occurrences (préventif) : matériel mobile (asset) ou installation fixe.
        occ_qs = MaintenanceOccurrence.objects.select_related(
            "asset", "asset__ship", "asset__service", "asset__sector",
            "installation_maintenance", "installation_maintenance__installation",
            "installation_maintenance__installation__ship",
            "installation_maintenance__installation__service",
            "installation_maintenance__installation__sector",
        ).filter(
            assignes_equipage_q(request.user, MaintenanceOccurrence, "assignees"), scheduled_for__range=(start, end)
        )
        occ_qs = _appliquer_filtres_occurrences(occurrences_visibles(request.user, occ_qs), filters)
        for occ in occ_qs:
            events.append({
                "type": "maintenance",
                "title": f"Préventif - {occ.titre_affiche}",
                "start": occ.scheduled_for.isoformat(),
                "end": occ.scheduled_for.isoformat(),
                "url": f"/maintenance/occurrences/{occ.id}/execute/",
                "status": occ.status,
            })

        # Tickets (logistique) planifiés: on affiche tous, ou ceux avec statut PLANNED/IN_REPAIR/TESTING si on avait des dates; ici, on ne dispose pas d’échéance => montrer ouverts
        ticket_qs = CorrectiveTicket.objects.select_related("asset", "installation").exclude(status__in=["CLOSED", "CANCELLED"])  # proxy
        ticket_qs = ticket_qs.filter(assignes_equipage_q(request.user, CorrectiveTicket, "assignees"))
        ticket_qs = _appliquer_filtres_tickets(tickets_visibles(request.user, ticket_qs), filters)
        for t in ticket_qs:
            events.append({
                "type": "ticket",
                "title": f"Ticket - {t.equipement}",
                "start": start.isoformat(),
                "end": end.isoformat(),
                "url": f"/logistics/tickets/{t.pk}/",
                "status": t.status,
            })

        # Sessions de formation : assignées par un référent (attendees),
        # réservées en libre-service par le marin (reservations, cf. T-FORM
        # réservation), OU animées en tant que formateur (instructor) — un
        # marin doit voir les trois sur son calendrier personnel (filtre
        # "Utilisateur" = lui-même), d'où le OU plutôt qu'un simple filtre sur
        # attendees. Même liste de champs que _perimetre_session ci-dessus
        # (utilisée pour l'autorisation de déplacement), pour rester cohérent.
        # Formation désormais globale (plus de secteur, cf. _perimetre_session
        # ci-dessus) : le filtre "sector" du calendrier ne s'applique plus aux
        # sessions de formation, uniquement aux autres types d'événements.
        ses_qs = sessions_visibles(request.user, TrainingSession.objects.select_related("course", "instructor")).filter(
            scheduled_at__date__range=(start, end)
        )
        if filters.get("user"):
            ses_qs = ses_qs.filter(
                Q(attendees__id=filters["user"]) | Q(reservations__id=filters["user"]) | Q(instructor__id=filters["user"])
            ).distinct()
        if filters.get("status"):
            ses_qs = ses_qs.filter(status=filters["status"])
        if filters.get("type") and filters["type"] != "training":
            ses_qs = ses_qs.none()
        for s in ses_qs:
            course_title = getattr(s.course, "title", None) or getattr(s.course, "name", str(s.course))
            events.append({
                "type": "training",
                "title": f"Formation - {course_title}",
                "start": s.scheduled_at.isoformat(),
                "end": s.scheduled_at.isoformat(),
                "url": "/training/",  # placeholder detail si disponible
                "status": s.status,
            })

        # Événements personnels libres : uniquement ceux du marin connecté.
        if not filters.get("type") or filters["type"] == "personal":
            for pe in _evenements_personnels(request.user, start, end):
                events.append({
                    "type": "personal",
                    "title": f"Personnel - {pe.title}",
                    "start": pe.starts_at.isoformat(),
                    "end": pe.ends_at.isoformat() if pe.ends_at else pe.starts_at.isoformat(),
                    "url": "",
                    "status": None,
                })

        # Créneaux de quart/service de garde affectés à un marin, sur les
        # listes déjà publiées (cf. _creneaux_quart_assignes ci-dessus) —
        # même principe que les sessions de formation : affectation
        # personnelle (marin) plutôt que périmètre organisationnel.
        if not filters.get("type") or filters["type"] == "quart":
            quart_qs = _creneaux_quart_assignes(start, end, filters.get("user") or None, request.user)
            for c in quart_qs:
                events.append({
                    "type": "quart",
                    "title": f"Quart - {c.poste}",
                    "start": c.debut.isoformat(),
                    "end": c.fin.isoformat(),
                    "url": f"/quarts/quart/{c.quart_id}/",
                    "status": None,
                })
        if not filters.get("type") or filters["type"] == "service_garde":
            garde_qs = _creneaux_garde_assignes(start, end, filters.get("user") or None, request.user)
            for c in garde_qs:
                events.append({
                    "type": "service_garde",
                    "title": f"Garde - {c.poste}",
                    "start": c.debut.isoformat(),
                    "end": c.fin.isoformat(),
                    "url": f"/quarts/garde/{c.service_garde_id}/",
                    "status": None,
                })
        # Absences/indisponibilités : même principe que les créneaux de
        # quart/garde ci-dessus (affectation personnelle plutôt que
        # périmètre organisationnel, cf. absences/models.py::Absence).
        if not filters.get("type") or filters["type"] == "absence":
            for a in _absences_periode(start, end, filters.get("user") or None, request.user):
                events.append({
                    "type": "absence",
                    "title": f"Absence - {a.type_absence}",
                    "start": a.date_debut.isoformat(),
                    "end": (a.date_fin + timedelta(days=1)).isoformat(),
                    "url": "/absences/",
                    "status": a.statut,
                })
        return events
