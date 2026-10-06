"""Données de la page « Aujourd'hui » (docs/UX.md §9.1) : « À faire » trié et frise « Ma journée »."""
from datetime import datetime, time, timedelta

from django.db.models import Q
from django.urls import reverse
from django.utils import timezone

from logistics.models import CorrectiveTicket
from maintenance.models import MaintenanceOccurrence
from quarts.models import CreneauQuart, CreneauServiceGarde, ListeServiceAbstract
from rondes.services import rondes_du_marin
from training.models import TrainingSession

STATUTS_MAINTENANCE_TERMINES = ["DONE", "CANCELLED"]
STATUTS_TICKET_TERMINES = ["CLOSED", "CANCELLED"]

DANGER, ATTENTION, NORMAL = "danger", "attention", ""
# Rang d'urgence : le retard passe avant l'attente de validation, puis le reste.
_RANG_NIVEAU = {DANGER: 0, ATTENTION: 1, NORMAL: 2}


def formations_du_marin(user):
    """Séances planifiées où le marin est inscrit, a réservé ou est formateur."""
    return (
        TrainingSession.objects.select_related("course")
        .filter(Q(attendees=user) | Q(reservations=user) | Q(instructor=user), status="PLANNED")
        .distinct()
        .order_by("scheduled_at")
    )


def _entree(objet, titre, detail, url, icone, niveau, criticite, echeance):
    return {
        "objet": objet, "titre": titre, "detail": detail, "url": url, "icone": icone,
        "niveau": niveau, "classes": f"mx-aujourdhui__tache--{niveau}" if niveau else "", "criticite": criticite, "echeance": echeance,
    }


def _echeance(valeur):
    """Date ou datetime ramenée à un datetime pour comparer des échéances de natures différentes."""
    if isinstance(valeur, datetime):
        return timezone.localtime(valeur) if timezone.is_aware(valeur) else valeur
    return timezone.make_aware(datetime.combine(valeur, time.min))


def a_faire(user, aujourdhui):
    """Ce qui demande une intervention du marin, trié : retard, attente, criticité, échéance."""
    entrees = []
    occurrences = (
        MaintenanceOccurrence.objects.select_related("asset", "installation_maintenance__installation")
        .filter(assignees=user).exclude(status__in=STATUTS_MAINTENANCE_TERMINES)
    )
    for occ in occurrences:
        en_retard = occ.status == "OVERDUE" or occ.scheduled_for < aujourdhui
        attente = occ.status == "WAITING_VALIDATION"
        if en_retard:
            detail = f"En retard, prévue le {occ.scheduled_for:%d/%m}"
        elif attente:
            detail = "En attente de validation"
        else:
            detail = f"Prévue le {occ.scheduled_for:%d/%m}"
        entrees.append(_entree(
            occ, occ.titre_affiche, detail, reverse("occurrence-execute", args=[occ.pk]), "maintenance",
            DANGER if en_retard else ATTENTION if attente else NORMAL, occ.priority, _echeance(occ.scheduled_for),
        ))
    tickets = (
        CorrectiveTicket.objects.select_related("asset", "installation")
        .filter(assignees=user).exclude(status__in=STATUTS_TICKET_TERMINES)
    )
    for ticket in tickets:
        entrees.append(_entree(
            ticket, str(ticket.equipement), f"Ticket correctif · {ticket.get_status_display()}",
            reverse("ticket-detail", args=[ticket.pk]), "ticket",
            ATTENTION if ticket.status == "BLOCKED" else NORMAL, ticket.severity,
            _echeance(ticket.planned_for or ticket.reported_at),
        ))
    for ronde in rondes_du_marin(user, aujourdhui):
        en_retard = ronde.statut == "EN_RETARD" or ronde.date_prevue < aujourdhui
        entrees.append(_entree(
            ronde, ronde.nom, "Ronde en retard" if en_retard else "Ronde du jour",
            reverse("ronde-detail", args=[ronde.pk]), "ronde", DANGER if en_retard else NORMAL, 0,
            _echeance(ronde.date_prevue),
        ))
    for session in formations_du_marin(user):
        if timezone.localtime(session.scheduled_at).date() == aujourdhui:
            entrees.append(_entree(
                session, session.course.title, f"Formation · {timezone.localtime(session.scheduled_at):%H:%M}",
                reverse("calendar-index") + f"?view=day&date={aujourdhui:%Y-%m-%d}", "formation", NORMAL, 0,
                _echeance(session.scheduled_at),
            ))
    entrees.sort(key=lambda e: (_RANG_NIVEAU[e["niveau"]], -e["criticite"], e["echeance"]))
    return entrees


def _bornes_du_jour(aujourdhui):
    debut = timezone.make_aware(datetime.combine(aujourdhui, time.min))
    return debut, debut + timedelta(days=1)


def journee(user, aujourdhui, taches):
    """Frise « Ma journée » : quarts, services, formations puis tâches du jour sans heure (`taches` = a_faire)."""
    debut_jour, fin_jour = _bornes_du_jour(aujourdhui)
    points = []
    creneaux = (
        (CreneauQuart.objects.select_related("quart").filter(quart__statut=ListeServiceAbstract.STATUT_PUBLIEE),
         "quart", "Quart"),
        (CreneauServiceGarde.objects.select_related("service_garde").filter(
            service_garde__statut=ListeServiceAbstract.STATUT_PUBLIEE), "garde", "Service"),
    )
    for requete, icone, mot in creneaux:
        for c in requete.filter(marin=user, debut__lt=fin_jour, fin__gt=debut_jour):
            points.append({
                "heure": timezone.localtime(c.debut), "libelle": f"{mot} · {c.poste}", "icone": icone,
                "url": reverse("quarts-index"),
            })
    for session in formations_du_marin(user).filter(scheduled_at__gte=debut_jour, scheduled_at__lt=fin_jour):
        points.append({
            "heure": timezone.localtime(session.scheduled_at), "libelle": f"Formation · {session.course.title}",
            "icone": "formation", "url": reverse("calendar-index") + f"?view=day&date={aujourdhui:%Y-%m-%d}",
        })
    # Sans heure précise : la date seule est connue.
    for entree in taches:
        if entree["icone"] in ("ronde", "maintenance") and entree["echeance"].date() == aujourdhui:
            points.append({
                "heure": None, "libelle": entree["titre"], "icone": entree["icone"], "url": entree["url"],
            })
    points.sort(key=lambda p: (p["heure"] is None, p["heure"] or debut_jour))
    return points
