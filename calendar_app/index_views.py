"""Vue HTML du calendrier central (découpage de calendar_app/views.py)."""
from datetime import datetime, timedelta

from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.shortcuts import render
from django.utils import timezone
from django.views.generic import TemplateView

from matrix.core.contexte_batiment import referentiel_organisation
from matrix.core.mixins import utilisateurs_visibles_par
from matrix.core.scopes import equipage_marin_q
from maintenance.models import MaintenanceOccurrence
from logistics.models import CorrectiveTicket
from training.models import TrainingSession
from .evenements_sources import (
    _absences_periode,
    _appliquer_filtres_occurrences,
    _appliquer_filtres_tickets,
    _creneaux_garde_assignes,
    _creneaux_quart_assignes,
    _evenements_personnels,
)
from .models import PersonalEvent


class CalendarView(LoginRequiredMixin, TemplateView):
    """Calendrier central unique (colonne vertébrale, CLAUDE.md) : PAS de
    restriction automatique de périmètre à l'affichage, quel que soit le
    rôle — tout le monde voit tout par défaut ("vue globale"), et bascule en
    "vue personnelle" en choisissant son propre nom dans le filtre
    "Utilisateur" (ou en consultant "Ma journée"/le tableau de bord). C'est
    volontaire : un CHEF_SERVICE planifiant une session de formation doit
    voir TOUTES les sessions déjà programmées sur le calendrier (disponibilité
    des salles/formateurs), pas seulement celles où il est lui-même affecté.

    Sur les autres types d'événements (maintenance, tickets), les menus
    déroulants navire/service/secteur restent en plus disponibles pour
    affiner la vue globale par périmètre organisationnel — mais n'ont plus
    d'effet sur les sessions de formation depuis qu'une formation
    (TrainingCourse) est une fiche globale partagée par tous les navires
    (portabilité des qualifications) : une session de formation ne se
    rattache plus à un périmètre organisationnel précis, seule l'affectation
    personnelle du marin (attendees/reservations/instructor, cf.
    _perimetre_session ci-dessus) a un sens pour elle. La vue globale reste
    donc utile pour la formation comme pour les autres types d'événements —
    seul son critère de filtrage change (affectation personnelle plutôt que
    périmètre organisationnel)."""

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
            "active_filters": filters,
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
            "user": request.GET.get("user") or None,
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
        ).filter(scheduled_for__range=(start, end))
        occ_qs = _appliquer_filtres_occurrences(occ_qs, filters)
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
        ticket_qs = _appliquer_filtres_tickets(ticket_qs, filters)
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
        ses_qs = TrainingSession.objects.select_related("course", "instructor").filter(scheduled_at__date__range=(start, end))
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
