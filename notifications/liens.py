"""Lien direct d'une notification vers l'objet concerné, seulement si le
marin y a accès (périmètre). Aucun lien n'est produit vers un objet interdit.

Chaque type d'objet a un résolveur qui reprend le contrôle d'accès de sa fiche détail.
Une notification sans objet peut porter un chemin interne (`url`) vers une page qui
applique elle-même ses droits."""
import uuid

from django.urls import reverse


def liens_accessibles(request, notifications):
    """Renvoie {id de notification: URL} pour les notifications qui ont une
    cible connue et accessible. Les accès sont vérifiés en une requête par type."""
    liens = {}
    groupes = {}
    for notification in notifications:
        modele = notification.content_type.model if notification.content_type_id else None
        if modele in _RESOLVEURS and notification.object_id:
            groupes.setdefault(modele, {})[notification.pk] = notification.object_id
        elif notification.verb.startswith("Ma journée"):
            # Digest quotidien : pas d'objet unique, on renvoie vers le calendrier
            liens[notification.pk] = reverse("calendar-index")
        elif _chemin_sur(notification.url):
            liens[notification.pk] = notification.url
    for modele, ids in groupes.items():
        liens.update(_RESOLVEURS[modele](request, ids))
    return liens


def _chemin_sur(chemin):
    """Chemin interne uniquement : jamais d'adresse externe ni de schéma."""
    return bool(chemin) and chemin.startswith("/") and not chemin.startswith("//") and "\\" not in chemin


def _uuids(valeurs):
    """Ne garde que les identifiants bien formés (object_id est un texte libre)."""
    retenus = []
    for valeur in valeurs:
        try:
            retenus.append(uuid.UUID(valeur))
        except ValueError:
            pass
    return retenus


def _entiers(valeurs):
    return [int(v) for v in valeurs if str(v).isdigit()]


def _visibles(ids, queryset, construire):
    """{notification: url} pour les objets de `queryset` dont l'identifiant figure dans `ids`."""
    visibles = {str(pk) for pk in queryset.values_list("pk", flat=True)}
    return {n: construire(o) for n, o in ids.items() if o in visibles}


def _installations(request, ids):
    # Même périmètre que la fiche installation
    from assets.web_views import InstallationDetailView

    vue = InstallationDetailView()
    vue.request = request
    return _visibles(ids, vue.get_queryset().filter(pk__in=_uuids(ids.values())),
                     lambda o: reverse("installation-detail", args=[o]))


def _propositions(request, ids):
    # Même périmètre que la page de la proposition d'article
    from assets.proposition_article import propositions_visibles

    return _visibles(ids, propositions_visibles(request.user).filter(pk__in=_uuids(ids.values())),
                     lambda o: reverse("catalogue-proposition", args=[o]))


def _versions(request, ids):
    # Même périmètre que la fiche de maintenance de l'installation
    from assets.fiche_validation import versions_visibles

    visibles = {str(v.pk): v for v in versions_visibles(request.user).filter(pk__in=_entiers(ids.values()))}
    return {
        n: f"{reverse('fiche-detail', args=[visibles[o].fiche_id])}?v={visibles[o].numero}"
        for n, o in ids.items() if o in visibles
    }


def _fiches(request, ids):
    # Même périmètre que la page de la fiche
    from assets.fiche_validation import fiches_visibles

    return _visibles(ids, fiches_visibles(request.user).filter(pk__in=_entiers(ids.values())),
                     lambda o: reverse("fiche-detail", args=[o]))


def _taches(request, ids):
    # Même périmètre que la fiche de la tâche
    from taches.services import taches_visibles

    return _visibles(ids, taches_visibles(request.user).filter(pk__in=_entiers(ids.values())),
                     lambda o: reverse("tache-detail", args=[o]))


def _rondes(request, ids):
    from rondes.services import rondes_visibles

    return _visibles(ids, rondes_visibles(request.user).filter(pk__in=_entiers(ids.values())),
                     lambda o: reverse("ronde-detail", args=[o]))


def _occurrences(request, ids):
    # Même contrôle que la page de compte rendu : périmètre, puis assigné ou niveau suffisant
    from maintenance.models import MaintenanceOccurrence
    from matrix.core.mixins import build_scope_q
    from matrix.core.role_thresholds import niveau_requis_pour
    from matrix.core.roles import user_role_level

    occurrences = MaintenanceOccurrence.objects.filter(
        build_scope_q(request.user, "asset__", "installation_maintenance__installation__"),
        pk__in=_entiers(ids.values()),
    )
    if user_role_level(request.user) < niveau_requis_pour(request.user, "maintenance_occurrence_gestion_tiers"):
        occurrences = occurrences.filter(assignees=request.user)
    return _visibles(ids, occurrences, lambda o: reverse("occurrence-execute", args=[o]))


def _echanges(request, ids):
    # Visible du demandeur, de la cible ou du chef de liste habilité
    from quarts.echanges import peut_valider_echange
    from quarts.models import EchangeService

    visibles = {
        str(e.pk) for e in EchangeService.objects.filter(pk__in=_entiers(ids.values()))
        if request.user.pk in (e.demandeur_id, e.cible_id) or peut_valider_echange(request.user, e)
    }
    return {n: reverse("echanges-index") for n, o in ids.items() if o in visibles}


def _anomalies(request, ids):
    from logistics.anomalie_views import anomalies_visibles

    return _visibles(ids, anomalies_visibles(request.user).filter(pk__in=_entiers(ids.values())),
                     lambda o: reverse("anomalie-detail", args=[o]))


def _tickets(request, ids):
    from logistics.models import CorrectiveTicket
    from matrix.core.mixins import build_scope_q

    tickets = CorrectiveTicket.objects.filter(
        build_scope_q(request.user, "asset__", "installation__"), pk__in=_uuids(ids.values()))
    return _visibles(ids, tickets, lambda o: reverse("ticket-detail", args=[o]))


def _absences(request, ids):
    from absences.services import absences_visibles

    visibles = {str(pk) for pk in absences_visibles(request.user).filter(
        pk__in=_entiers(ids.values())).values_list("pk", flat=True)}
    return {n: reverse("absences-index") for n, o in ids.items() if o in visibles}


def _formations(request, ids, vers_cours=lambda o: o):
    # Même catalogue que la fiche formation
    from training.web_views import TrainingCourseListView

    vue = TrainingCourseListView()
    vue.request, vue.args, vue.kwargs = request, (), {}
    cours = {n: vers_cours(o) for n, o in ids.items()}
    visibles = {str(pk) for pk in vue.get_queryset().filter(pk__in=_entiers(cours.values())).values_list("pk", flat=True)}
    return {n: reverse("formation-detail", args=[c]) for n, c in cours.items() if c in visibles}


def _seances(request, ids):
    from training.models import TrainingSession

    cours = dict(TrainingSession.objects.filter(pk__in=_entiers(ids.values())).values_list("pk", "course_id"))
    return _formations(request, ids, lambda o: str(cours.get(int(o), "")) if str(o).isdigit() else "")


_RESOLVEURS = {
    "installation": _installations,
    "propositionarticle": _propositions,
    "checklisttemplate": _versions,
    "installationmaintenance": _fiches,
    "tache": _taches,
    "ronde": _rondes,
    "maintenanceoccurrence": _occurrences,
    "echangeservice": _echanges,
    "anomalie": _anomalies,
    "correctiveticket": _tickets,
    "absence": _absences,
    "trainingcourse": _formations,
    "trainingsession": _seances,
}
