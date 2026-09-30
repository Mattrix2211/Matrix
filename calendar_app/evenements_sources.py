"""Sources d'événements du calendrier central : requêtes communes (filtres,
périmètre, créneaux, absences, rondes, événements personnels) et agrégation
personnelle d'une journée. Partagé par la vue HTML (index_views.py), l'API
JSON FullCalendar (api_views.py) et le digest « Ma journée »
(notifications.tasks) — découpage de calendar_app/views.py par sous-domaine."""
from django.db.models import Q

from maintenance.models import MaintenanceOccurrence
from training.models import TrainingSession
from quarts.models import CreneauQuart, CreneauServiceGarde, Quart, ServiceGarde
from quarts.services import feuille_service_du_jour_pour
from rondes.services import rondes_ouvertes_du_marin
from absences.models import Absence
from matrix.core.roles import RoleLevel
from matrix.core.scopes import equipage_marin_q
from .models import PersonalEvent


def _appliquer_filtres_occurrences(qs, filters):
    """Applique les filtres navire/service/secteur/assigné choisis dans les
    menus déroulants du calendrier à un queryset d'occurrences de
    maintenance. Le périmètre (navire/service/secteur) est porté soit par
    l'actif mobile (asset), soit par l'installation fixe liée
    (installation_maintenance) — d'où le OU entre les deux chemins.
    Fonction commune à CalendarView (vue HTML) et calendar_events (API JSON
    consommée par FullCalendar), pour ne pas dupliquer cette logique."""
    if filters.get("ship"):
        qs = qs.filter(
            Q(asset__ship_id=filters["ship"])
            | Q(installation_maintenance__installation__ship_id=filters["ship"])
        )
    if filters.get("service"):
        qs = qs.filter(
            Q(asset__service_id=filters["service"])
            | Q(installation_maintenance__installation__service_id=filters["service"])
        )
    if filters.get("sector"):
        qs = qs.filter(
            Q(asset__sector_id=filters["sector"])
            | Q(installation_maintenance__installation__sector_id=filters["sector"])
        )
    if filters.get("user"):
        qs = qs.filter(assignees__id=filters["user"])
    return qs


def _creneaux_quart_assignes(start, end, user=None, pour=None):
    """Créneaux de quart affectés à un marin, sur la période donnée, dont la
    liste (Quart) est déjà PUBLIÉE — une liste en brouillon reste une
    préparation interne au chef de liste, jamais montrée sur le calendrier
    personnel avant publication (cf. Quart.publier, quarts/models.py). Un
    créneau sans marin affecté n'apparaît jamais ici (pas encore une
    affectation personnelle). `user` restreint à un seul marin (vue
    personnelle) ; laissé à None, tous les créneaux affectés de la période
    sont renvoyés (vue globale), même principe que les sessions de formation
    (cf. _perimetre_session ci-dessus : l'affectation personnelle prime sur
    le périmètre organisationnel pour ce type d'événement)."""
    qs = CreneauQuart.objects.select_related("quart", "marin").filter(
        quart__statut=Quart.STATUT_PUBLIEE, marin__isnull=False, debut__date__range=(start, end)
    )
    if user is not None:
        qs = qs.filter(marin=user)
    elif pour is not None:
        # Vue d'équipe : double équipage, seul l'équipage de `pour` est montré.
        qs = qs.filter(equipage_marin_q(pour, "marin__profile__"))
    return qs


def _creneaux_garde_assignes(start, end, user=None, pour=None):
    """Équivalent de _creneaux_quart_assignes pour les services de garde
    (ServiceGarde/CreneauServiceGarde) — même logique, factorisée en deux
    fonctions distinctes (pas une seule générique) pour rester cohérente avec
    la décision de garder Quart et ServiceGarde comme deux modèles Django
    distincts (cf. docstring de quarts/models.py)."""
    qs = CreneauServiceGarde.objects.select_related("service_garde", "marin").filter(
        service_garde__statut=ServiceGarde.STATUT_PUBLIEE, marin__isnull=False, debut__date__range=(start, end)
    )
    if user is not None:
        qs = qs.filter(marin=user)
    elif pour is not None:
        # Vue d'équipe : double équipage, seul l'équipage de `pour` est montré.
        qs = qs.filter(equipage_marin_q(pour, "marin__profile__"))
    return qs


def _absences_periode(start, end, user=None, pour=None):
    """Absences (déclarées ou validées) chevauchant la période [start, end],
    même principe que _creneaux_quart_assignes/_creneaux_garde_assignes
    ci-dessus : `user` restreint à un seul marin (vue personnelle), laissé à
    None pour la vue globale (cf. absences/models.py::Absence)."""
    qs = Absence.objects.select_related("marin", "type_absence").filter(
        date_debut__lte=end, date_fin__gte=start
    )
    if user is not None:
        qs = qs.filter(marin=user)
    elif pour is not None:
        # Vue d'équipe : double équipage, seul l'équipage de `pour` est montré.
        qs = qs.filter(equipage_marin_q(pour, "marin__profile__"))
    return qs


def _rondes_a_faire(user, start, end):
    """Rondes ouvertes du marin (assignées à lui, ou non assignées et dans son
    périmètre) prévues sur la période — même principe que les autres
    affectations personnelles du calendrier."""
    return rondes_ouvertes_du_marin(user).filter(date_prevue__range=(start, end))


def _evenements_personnels(user, start, end):
    """Événements personnels libres (rappels, notes) créés par l'utilisateur,
    dans la période affichée. Toujours restreints à leur propriétaire, quels
    que soient les filtres navire/service/secteur/utilisateur appliqués : un
    événement personnel n'a aucune portée organisationnelle, il n'est visible
    que par son créateur."""
    return PersonalEvent.objects.filter(owner=user, starts_at__date__range=(start, end))


def evenements_utilisateur_jour(user, day):
    """Événements de calendrier concernant précisément `user` pour le jour
    `day` : maintenances assignées, formations (assignées par un référent,
    réservées en libre-service, ou animées en tant que formateur), événements
    personnels libres. Même logique de filtrage que le filtre "user" de
    calendar_events/_collect_events (assignees, attendees | reservations |
    instructor, owner) — réutilisée ici par le digest quotidien « Ma
    journée »/« Ma journée de demain » (notifications.tasks) pour ne pas
    dupliquer l'agrégation. Le formateur d'une session doit voir sa journée
    de formation dans son digest même s'il n'est pas lui-même stagiaire."""
    maintenances = list(
        MaintenanceOccurrence.objects.filter(scheduled_for=day, assignees=user)
        .select_related("asset", "installation_maintenance__installation")
        .distinct()
    )
    formations = list(
        TrainingSession.objects.filter(scheduled_at__date=day)
        .filter(Q(attendees=user) | Q(reservations=user) | Q(instructor=user))
        .select_related("course")
        .distinct()
    )
    personnels = list(_evenements_personnels(user, day, day))
    # Créneaux de quart/service de garde assignés à `user` ce jour-là, cf.
    # _creneaux_quart_assignes/_creneaux_garde_assignes ci-dessus — même
    # agrégation que le calendrier personnel (calendar_events), pas de
    # système parallèle.
    creneaux = list(_creneaux_quart_assignes(day, day, user)) + list(_creneaux_garde_assignes(day, day, user))
    rondes = list(_rondes_a_faire(user, day, day))
    absences = list(_absences_periode(day, day, user))
    # Feuille de service quotidienne (Phase 2, tâche Notion « Feuille de
    # service quotidienne ») : mise en évidence dans « Ma journée » si le
    # marin est lui-même de service ce jour-là — cf. quarts/services.py.
    feuille_service = feuille_service_du_jour_pour(user, day)
    return {
        "maintenances": maintenances, "formations": formations, "personnels": personnels,
        "creneaux": creneaux, "rondes": rondes, "absences": absences, "feuille_service": feuille_service,
    }


def _peut_agir_occurrence(occ, user, ids_perimetre, niveau_role):
    """Vrai si `user` a le droit d'ouvrir/exécuter cette occurrence de
    maintenance depuis le popover du calendrier — RIGOUREUSEMENT la même
    règle que OccurrenceExecuteView (maintenance/web_views.py) : appartenir
    au périmètre de l'occurrence (matériel mobile ou installation fixe), ET
    (être assigné à l'occurrence OU être CHEF_SECTION et au-dessus). Ne
    duplique pas cette logique côté JavaScript : le booléen calculé ici est
    simplement transmis tel quel au calendrier via extendedProps."""
    if occ.id not in ids_perimetre:
        return False
    return niveau_role >= RoleLevel.CHEF_SECTION or user in occ.assignees.all()


def _peut_agir_ticket(ticket, ids_perimetre, niveau_role):
    """Vrai si l'utilisateur a le droit de faire transitionner ce ticket
    correctif depuis le popover du calendrier — même règle que
    TicketTransitionView/TicketAssignView (logistics/web_views.py) :
    appartenir au périmètre du ticket (matériel mobile) ET être CHEF_SECTION
    et au-dessus."""
    return ticket.pk in ids_perimetre and niveau_role >= RoleLevel.CHEF_SECTION


def _appliquer_filtres_tickets(qs, filters):
    """Applique les filtres navire/service/secteur choisis dans les menus
    déroulants du calendrier à un queryset de tickets correctifs. Fonction
    commune à CalendarView et calendar_events, pour ne pas dupliquer cette
    logique."""
    if filters.get("ship"):
        qs = qs.filter(Q(asset__ship_id=filters["ship"]) | Q(installation__ship_id=filters["ship"]))
    if filters.get("service"):
        qs = qs.filter(Q(asset__service_id=filters["service"]) | Q(installation__service_id=filters["service"]))
    if filters.get("sector"):
        qs = qs.filter(Q(asset__sector_id=filters["sector"]) | Q(installation__sector_id=filters["sector"]))
    return qs
