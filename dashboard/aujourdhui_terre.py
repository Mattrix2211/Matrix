"""« Aujourd'hui » de l'utilisateur à terre : vue flotte, « À faire » puis un bâtiment par carte (docs/UX.md §9.3)."""
from django.db.models import Count, Q
from django.db.models.functions import Coalesce
from django.urls import reverse

from assets.models import Asset
from dashboard.aujourdhui import STATUTS_ASSET_INDISPONIBLES, STATUTS_MAINTENANCE_TERMINES
from logistics.models import STATUTS_ANOMALIE_OUVERTS, Anomalie, CorrectiveTicket
from maintenance.models import MaintenanceOccurrence
from matrix.core.contexte_batiment import batiments_du_perimetre
from training.models import navire_de

# Le navire d'une occurrence passe par le matériel ou par l'installation.
_NAVIRE_OCCURRENCE = Coalesce("asset__ship_id", "installation_maintenance__installation__ship_id")


def batiments_suivis(user):
    """Bâtiments suivis par un utilisateur à terre : sans rattachement à un bâtiment, mais avec un périmètre."""
    if navire_de(user) is not None:
        return []
    return list(batiments_du_perimetre(user))


def _par_navire(requete, champ_navire):
    return dict(requete.values_list(champ_navire).annotate(n=Count("pk")).values_list(champ_navire, "n"))


def a_faire_terre(batiments):
    """Validations de maintenance en attente (à titre d'information) et tickets bloqués des bâtiments suivis."""
    ids = [b.pk for b in batiments]
    entrees = []
    en_attente = (
        MaintenanceOccurrence.objects.annotate(navire=_NAVIRE_OCCURRENCE)
        .filter(navire__in=ids, status="WAITING_VALIDATION")
        .select_related("asset", "installation_maintenance__installation")
        .order_by("scheduled_for")
    )
    for occ in en_attente:
        # Le suivi à terre est en consultation : la validation reste à bord, donc aucun bouton.
        entrees.append({
            "titre": occ.titre_affiche, "detail": f"En attente de validation · prévue le {occ.scheduled_for:%d/%m}",
            "url": None, "libelle": "", "icone": "maintenance",
            "classes": "mx-aujourdhui__tache--attention",
        })
    tickets = (
        CorrectiveTicket.objects.filter(Q(asset__ship_id__in=ids) | Q(installation__ship_id__in=ids), status="BLOCKED")
        .select_related("asset", "installation").order_by("reported_at")
    )
    for ticket in tickets:
        entrees.append({
            "titre": str(ticket.equipement), "detail": "Ticket bloqué : à commenter",
            "url": reverse("ticket-detail", args=[ticket.pk]), "libelle": "Commenter", "icone": "ticket",
            "classes": "mx-aujourdhui__tache--attention",
        })
    return entrees


def cartes_batiments(batiments, aujourdhui):
    """Une carte par bâtiment : badges d'état (retards, anomalies ouvertes, indisponibilités)."""
    ids = [b.pk for b in batiments]
    occurrences = (
        MaintenanceOccurrence.objects.annotate(navire=_NAVIRE_OCCURRENCE)
        .filter(navire__in=ids).exclude(status__in=STATUTS_MAINTENANCE_TERMINES + ["WAITING_VALIDATION"])
        .filter(Q(status="OVERDUE") | Q(scheduled_for__lt=aujourdhui))
    )
    retards = _par_navire(occurrences, "navire")
    anomalies = _par_navire(Anomalie.objects.filter(ship_id__in=ids, statut__in=STATUTS_ANOMALIE_OUVERTS), "ship_id")
    bloques = _par_navire(
        CorrectiveTicket.objects.annotate(navire=Coalesce("asset__ship_id", "installation__ship_id"))
        .filter(navire__in=ids, status="BLOCKED"), "navire",
    )
    indisponibles = _par_navire(Asset.objects.filter(ship_id__in=ids, status__in=STATUTS_ASSET_INDISPONIBLES), "ship_id")
    cartes = []
    for batiment in batiments:
        compteurs = (
            (retards.get(batiment.pk, 0), "danger", "en retard"),
            (anomalies.get(batiment.pk, 0), "attention", "anomalie(s) ouverte(s)"),
            (indisponibles.get(batiment.pk, 0), "danger", "indisponible(s)"),
            (bloques.get(batiment.pk, 0), "attention", "ticket(s) bloqué(s)"),
        )
        badges = [{"etat": etat, "libelle": f"{nombre} {texte}"} for nombre, etat, texte in compteurs if nombre]
        cartes.append({"batiment": batiment, "badges": badges or [{"etat": "ok", "libelle": "Rien à signaler"}]})
    return cartes
