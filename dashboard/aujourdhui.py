"""Données de la page « Aujourd'hui » (docs/UX.md §9.1) : « À faire » trié, frise « Ma journée » et bloc « Supervision »."""
from datetime import datetime, time, timedelta
from types import SimpleNamespace

from django.db.models import Count, Q
from django.urls import reverse
from django.utils import timezone

from assets.fiche_validation import versions_a_viser
from assets.models import Asset, Installation
from assets.proposition_article import propositions_a_viser
from annonces.services import a_lire as annonces_a_lire
from demandes.models import Demande
from logistics.models import STATUTS_ANOMALIE_OUVERTS, Anomalie, CorrectiveTicket
from maintenance.models import MaintenanceOccurrence
from matrix.core.mixins import build_scope_q, utilisateurs_visibles_par
from matrix.core.role_thresholds import niveau_requis_pour
from matrix.core.roles import user_role_level
from notifications.liens import liens_accessibles
from notifications.models import Notification
from threads.mentions import PREFIXE_MENTION
from matrix.core.scopes import assignes_equipage_q, is_master_admin, navire_q, scope_filters_for_user
from quarts.echanges import peut_valider_echange
from quarts.models import CreneauQuart, CreneauServiceGarde, EchangeService, ListeServiceAbstract
from rondes.services import rondes_du_marin
from taches.services import taches_a_suivre
from training.models import CandidatureFormation, TrainingCourse, TrainingRecord, TrainingSession, dossiers_formation_visibles_q
from training.services import qualifications_validees_de

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


def qualifications_a_renouveler(user, aujourdhui):
    """Dernière qualification de chaque formation, expirée ou échue dans la fenêtre d'alerte."""
    return [q for q in qualifications_validees_de(user, aujourdhui) if q.badge_libelle != "À jour"]


def demandes_a_traiter(user):
    """Dossiers où `user` doit agir : responsable (hors résolu), ou déclarant quand on attend sa réponse ou sa clôture."""
    return [
        d for d in Demande.objects.filter(Q(responsable=user) | Q(declarant=user)).exclude(etat=Demande.ETAT_CLOS)
        if (d.responsable_id == user.pk and d.etat != Demande.ETAT_RESOLU)
        or (d.declarant_id == user.pk and d.etat in (Demande.ETAT_EN_ATTENTE, Demande.ETAT_RESOLU))
    ]


def reponses_attendues(user):
    """Mentions sans réponse du marin, avec leur lien quand l'objet lui est accessible."""
    alertes = list(
        Notification.objects.filter(user=user, action_requise=True, traitee_le__isnull=True,
                                    verb__startswith=PREFIXE_MENTION)
        .select_related("content_type").order_by("-created_at")
    )
    liens = liens_accessibles(SimpleNamespace(user=user), alertes)
    return [(alerte, liens[alerte.pk]) for alerte in alertes if alerte.pk in liens and alerte.target is not None]


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
        attente = occ.status == "WAITING_VALIDATION"
        # L'attente de validation prime : le retard n'est plus du ressort de l'exécutant.
        en_retard = not attente and (occ.status == "OVERDUE" or occ.scheduled_for < aujourdhui)
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
    for tache in taches_a_suivre(user):
        propre = tache.assigne_id == user.pk
        en_retard = tache.en_retard_au(aujourdhui)
        if propre:
            detail = "Tâche en retard" if en_retard else f"Tâche · {tache.get_statut_display()}"
        else:
            detail = f"Blocage à lever · {tache.assigne.get_full_name() or tache.assigne.username}"
        faits, total = tache.avancement_checklist
        if total:
            detail += f" · checklist {faits}/{total}"
        entrees.append(_entree(
            tache, tache.titre, detail, reverse("tache-detail", args=[tache.pk]), "tache",
            DANGER if en_retard and propre else ATTENTION if not propre else NORMAL, 4 if tache.priorite == tache.PRIORITE_URGENTE else 0, _echeance(tache.echeance) if tache.echeance else None,
        ))
    for session in formations_du_marin(user):
        if timezone.localtime(session.scheduled_at).date() == aujourdhui:
            entrees.append(_entree(
                session, session.course.title, f"Formation · {timezone.localtime(session.scheduled_at):%H:%M}",
                reverse("calendar-index") + f"?view=day&date={aujourdhui:%Y-%m-%d}", "formation", NORMAL, 0,
                _echeance(session.scheduled_at),
            ))
    for proposition in propositions_a_viser(user):
        entrees.append(_entree(
            proposition, proposition.designation, f"Proposition d'article · {proposition.get_etat_display()}",
            reverse("catalogue-proposition", args=[proposition.pk]), "catalogue", ATTENTION, 0,
            _echeance(proposition.updated_at),
        ))
    for version in versions_a_viser(user):
        entrees.append(_entree(
            version, version.name, f"Fiche à valider · {version.get_etat_display()}",
            f"{reverse('fiche-detail', args=[version.fiche_id])}?v={version.numero}", "document", ATTENTION, 0,
            _echeance(version.updated_at),
        ))
    for annonce in annonces_a_lire(user, aujourdhui):
        entrees.append(_entree(
            annonce, annonce.titre, f"Annonce · {annonce.get_niveau_display()}{' · accusé requis' if annonce.accuse_requis else ''}",
            reverse("annonce-detail", args=[annonce.pk]), "annonce",
            DANGER if annonce.niveau == "danger" else ATTENTION if annonce.niveau == "warning" or annonce.accuse_requis else NORMAL,
            4 if annonce.niveau == "danger" else 0, _echeance(annonce.date_effet),
        ))
    for demande in demandes_a_traiter(user):
        entrees.append(_entree(
            demande, demande.titre, f"Demande · {demande.get_etat_display()}", reverse("demande-detail", args=[demande.pk]),
            "discussion", ATTENTION if demande.etat == demande.ETAT_EN_ATTENTE else NORMAL,
            4 if demande.priorite == demande.PRIORITE_URGENTE else 0, _echeance(demande.echeance or demande.updated_at),
        ))
    for qualification in qualifications_a_renouveler(user, aujourdhui):
        expiree = qualification.expires_at < aujourdhui
        entrees.append(_entree(
            qualification, qualification.course.title,
            f"Qualification {'expirée' if expiree else 'à renouveler'} · échéance {qualification.expires_at:%d/%m/%Y}",
            reverse("formation-detail", args=[qualification.course_id]), "formation",
            DANGER if expiree else ATTENTION, 0, _echeance(qualification.expires_at),
        ))
    for alerte, url in reponses_attendues(user):
        entrees.append(_entree(
            alerte, str(alerte.target), alerte.verb.removeprefix(f"{PREFIXE_MENTION} : "), url, "discussion",
            ATTENTION, 0, _echeance(alerte.created_at),
        ))
    # Sans échéance : après les autres à criticité égale.
    entrees.sort(key=lambda e: (_RANG_NIVEAU[e["niveau"]], -e["criticite"], e["echeance"] is None, e["echeance"] or 0))
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
        if entree["icone"] in ("ronde", "maintenance", "tache") and entree["echeance"] and entree["echeance"].date() == aujourdhui:
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


def qualifications_equipe(user, aujourdhui, navire=None):
    """Qualifications expirées ou à renouveler des marins du périmètre du chef (hors lui-même), bornées à `navire` si donné."""
    from notifications.tasks import JOURS_ALERTE_EXPIRATION_FORMATION

    limite = aujourdhui + timedelta(days=max(JOURS_ALERTE_EXPIRATION_FORMATION))
    derniere = {}
    dossiers = TrainingRecord.objects.filter(dossiers_formation_visibles_q(user),
                                             user__in=utilisateurs_visibles_par(user).filter(is_active=True).exclude(pk=user.pk))
    if navire is not None:
        dossiers = dossiers.filter(navire_q(navire.pk, "user__profile__"))
    for q in dossiers.select_related("user", "course").order_by("-completed_at", "-created_at"):
        derniere.setdefault((q.user_id, q.course_id), q)
    echues = sorted((q for q in derniere.values() if q.expires_at <= limite), key=lambda q: q.expires_at)
    return [
        {"titre": q.course.title, "url": reverse("formation-detail", args=[q.course_id]), "expiree": q.expires_at < aujourdhui,
         "detail": f"{q.user.get_full_name() or q.user.get_username()} · {'expirée' if q.expires_at < aujourdhui else 'échéance'} le {q.expires_at:%d/%m/%Y}"}
        for q in echues
    ]


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
            assignes_equipage_q(user, MaintenanceOccurrence, "assignees"),
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
    from training.web_views import (
        NIVEAU_REQUIS_VALIDATION_HIERARCHIE_CANDIDATURE, _marins_perimetre_hierarchie, peut_valider_proposition_bord,
    )
    propositions = TrainingCourse.objects.filter(gere_par_le_bord=True, statut_validation="WAITING_VALIDATION")
    if not is_master_admin(user):
        # Bornage au navire du chef : le seuil COMMANDANT+ de la validation ne borne pas lui-même.
        propositions = propositions.filter(updated_by__profile__ship=user.profile.ship)
    formations_a_valider = sum(
        1 for c in propositions.select_related("updated_by__profile") if peut_valider_proposition_bord(user, c.updated_by)
    )
    echanges = EchangeService.objects.filter(statut=EchangeService.STATUT_ACCEPTE).select_related(
        "creneau_demandeur__service_garde", "creneau_cible__service_garde"
    )
    echanges_a_valider = sum(1 for e in echanges if peut_valider_echange(user, e))
    candidatures_a_valider = (
        CandidatureFormation.objects.filter(
            statut="PENDING_APPROVAL", hierarchie_validee_par__isnull=True,
            marin_id__in=_marins_perimetre_hierarchie(user).values("pk"),
        ).count()
        if user_role_level(user) >= NIVEAU_REQUIS_VALIDATION_HIERARCHIE_CANDIDATURE else 0
    )
    # Installation sans statut propre : une installation critique dont une échéance est en retard compte comme indisponible.
    installations_en_retard = Installation.objects.filter(
        build_scope_q(user, ""), critique=True, maintenances__occurrences__in=occurrences.filter(status="OVERDUE")
    ).distinct().count()
    materiels = dict(
        Asset.objects.filter(build_scope_q(user, ""), status__in=STATUTS_ASSET_INDISPONIBLES)
        .values("status").annotate(n=Count("pk")).values_list("status", "n")
    )
    qualifications = qualifications_equipe(user, aujourdhui)
    return {
        "qualifications": qualifications[:LIGNES_SUPERVISION],
        "qualifications_total": len(qualifications),
        "retards": lignes_retard,
        "retards_total": retards_total,
        "retards_pct": round(retards_total / actives * 100) if actives else 0,
        "validations": lignes_validation,
        "validations_total": en_attente.count() + formations_a_valider + echanges_a_valider + candidatures_a_valider,
        "formations_a_valider": formations_a_valider,
        "echanges_a_valider": echanges_a_valider,
        "candidatures_a_valider": candidatures_a_valider,
        "installations_en_retard": installations_en_retard,
        "anomalies_ouvertes": Anomalie.objects.filter(build_scope_q(user, ""), statut__in=STATUTS_ANOMALIE_OUVERTS).count(),
        "hors_service": materiels.get("OUT_OF_SERVICE", 0),
        "defectueux": materiels.get("FAULTY", 0),
    }
