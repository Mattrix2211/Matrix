"""Données de la page « Aujourd'hui » (docs/UX.md §9.1) : « À faire » trié, frise « Ma journée » et bloc « Supervision »."""
from datetime import datetime, time, timedelta

from django.db.models import Q
from django.urls import reverse
from django.utils import timezone

from assets.models import Asset
from logistics.models import STATUTS_ANOMALIE_OUVERTS, Anomalie, CorrectiveTicket
from maintenance.models import MaintenanceOccurrence
from matrix.core.mixins import build_scope_q
from matrix.core.role_thresholds import niveau_requis_pour
from matrix.core.roles import user_role_level
from matrix.core.scopes import is_master_admin, scope_filters_for_user
from quarts.models import CreneauQuart, CreneauServiceGarde, ListeServiceAbstract
from rondes.services import rondes_du_marin
from training.models import TrainingCourse, TrainingSession

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
    """Ce qui demande une intervention du marin, trié : retard, attente, criticité (5 = la plus critique), échéance.

    Un chef (seuil de supervision, périmètre non vide) voit aussi les maintenances et tickets non assignés de son périmètre.
    """
    entrees = []
    chef = peut_superviser(user) and bool(scope_filters_for_user(user))
    occurrences = (
        MaintenanceOccurrence.objects.select_related("asset", "installation_maintenance__installation")
        .exclude(status__in=STATUTS_MAINTENANCE_TERMINES)
    )
    tickets = CorrectiveTicket.objects.select_related("asset", "installation").exclude(status__in=STATUTS_TICKET_TERMINES)
    cond_occ, cond_ticket = Q(assignees=user), Q(assignees=user)
    if chef:
        cond_occ |= Q(assignees__isnull=True) & build_scope_q(user, "asset__", "installation_maintenance__installation__")
        cond_ticket |= Q(assignees__isnull=True) & build_scope_q(user, "asset__", "installation__")
    occurrences = occurrences.filter(cond_occ).distinct()
    tickets = tickets.filter(cond_ticket).distinct()
    for occ in occurrences.prefetch_related("assignees"):
        sans_assigne = not occ.assignees.all()
        en_retard = occ.status == "OVERDUE" or occ.scheduled_for < aujourdhui
        attente = occ.status == "WAITING_VALIDATION"
        if en_retard:
            detail = f"En retard, prévue le {occ.scheduled_for:%d/%m}"
        elif attente:
            detail = "En attente de validation"
        else:
            detail = f"Prévue le {occ.scheduled_for:%d/%m}"
        if sans_assigne:
            detail = f"Non assigné · {detail}"
        entrees.append(_entree(
            occ, occ.titre_affiche, detail, reverse("occurrence-execute", args=[occ.pk]), "maintenance",
            DANGER if en_retard else ATTENTION if attente else NORMAL, occ.priority, _echeance(occ.scheduled_for),
        ))
    for ticket in tickets.prefetch_related("assignees"):
        prefixe = "" if ticket.assignees.all() else "Non assigné · "
        entrees.append(_entree(
            ticket, str(ticket.equipement), f"{prefixe}Ticket correctif · {ticket.get_status_display()}",
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


STATUTS_ASSET_INDISPONIBLES = ["OUT_OF_SERVICE", "FAULTY"]
LIGNES_SUPERVISION = 5


def peut_superviser(user):
    """Bloc « Supervision » : seuil de rôle configurable par navire, et un périmètre à superviser."""
    if user_role_level(user) < niveau_requis_pour(user, "supervision_aujourdhui"):
        return False
    return is_master_admin(user) or bool(scope_filters_for_user(user))


def _noms(occurrence):
    noms = [a.last_name or a.get_username() for a in occurrence.assignees.all()]
    return ", ".join(noms) if noms else "non assignée"


def supervision(user, aujourdhui):
    """Retards, validations en attente et indicateurs du périmètre du chef, ou None sans droit de supervision."""
    if not peut_superviser(user):
        return None
    occurrences = (
        MaintenanceOccurrence.objects.filter(
            build_scope_q(user, "asset__", "installation_maintenance__installation__"),
        ).exclude(status__in=STATUTS_MAINTENANCE_TERMINES)
    )
    en_attente = occurrences.filter(status="WAITING_VALIDATION")
    # Une occurrence en attente de validation n'est pas un retard de l'équipe.
    retards = occurrences.filter(Q(status="OVERDUE") | Q(scheduled_for__lt=aujourdhui)).exclude(status="WAITING_VALIDATION")
    retards_total, actives = retards.count(), occurrences.count()
    liaisons = ("asset", "installation_maintenance__installation")
    # Même règle que la fiche d'exécution : assigné, ou seuil de gestion des maintenances d'autrui.
    gere_les_tiers = user_role_level(user) >= niveau_requis_pour(user, "maintenance_occurrence_gestion_tiers")
    lignes_retard = [
        {
            "titre": occ.titre_affiche, "url": reverse("occurrence-execute", args=[occ.pk]),
            "detail": f"Prévue le {occ.scheduled_for:%d/%m} · {_noms(occ)}",
            "peut_valider": gere_les_tiers or user in occ.assignees.all(),
        }
        for occ in retards.select_related(*liaisons).prefetch_related("assignees").order_by("scheduled_for")[:LIGNES_SUPERVISION]
    ]
    lignes_validation = [
        {
            "titre": occ.titre_affiche, "url": reverse("occurrence-execute", args=[occ.pk]),
            "detail": f"Prévue le {occ.scheduled_for:%d/%m}",
            "peut_valider": gere_les_tiers or user in occ.assignees.all(),
        }
        for occ in en_attente.select_related(*liaisons).prefetch_related("assignees").order_by("scheduled_for")[:LIGNES_SUPERVISION]
    ]
    # Import différé : training.web_views est une couche de vues, chargée seulement ici.
    from training.web_views import peut_valider_proposition_bord
    propositions = TrainingCourse.objects.filter(gere_par_le_bord=True, statut_validation="WAITING_VALIDATION")
    if not is_master_admin(user):
        # Bornage au navire du chef : le seuil COMMANDANT+ de la validation ne borne pas lui-même.
        propositions = propositions.filter(updated_by__profile__ship=user.profile.ship)
    formations_a_valider = sum(
        1 for c in propositions.select_related("updated_by__profile") if peut_valider_proposition_bord(user, c.updated_by)
    )
    return {
        "retards": lignes_retard,
        "retards_total": retards_total,
        "retards_pct": round(retards_total / actives * 100) if actives else 0,
        "validations": lignes_validation,
        "validations_total": en_attente.count() + formations_a_valider,
        "formations_a_valider": formations_a_valider,
        "anomalies_ouvertes": Anomalie.objects.filter(build_scope_q(user, ""), statut__in=STATUTS_ANOMALIE_OUVERTS).count(),
        "indisponibles": Asset.objects.filter(build_scope_q(user, ""), status__in=STATUTS_ASSET_INDISPONIBLES).count(),
    }
