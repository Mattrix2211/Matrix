"""Service de génération des bilans PDF (rapport de synthèse pour la hiérarchie).

Mode Instantané uniquement pour l'instant (photo de l'état du périmètre au moment
de la génération, sans dates). Le Mode Période (bilan d'activité sur une fenêtre de
dates) fait l'objet d'une tâche séparée.

Réutilise scope_filters_for_user (aucun nouveau système de permission ni de scope).
"""
from datetime import timedelta

import weasyprint
from django.template.loader import render_to_string
from django.utils import timezone

from assets.models import (
    Installation,
    InstallationHourReading,
    InstallationIsolationReading,
    InstallationVibrationReading,
)
from logistics.models import CorrectiveTicket
from maintenance.models import MaintenanceOccurrence
from matrix.core.scopes import scope_filters_for_user
from org.models import Section, Sector, Service, Ship
from training.models import TrainingRecord

# Statuts considérés comme clos : à exclure des listes "en cours"/"ouverts".
STATUTS_TICKET_FERMES = ("CLOSED", "CANCELLED")
STATUTS_OCCURRENCE_TERMINEES = ("DONE", "CANCELLED")

# Fenêtre de "proche expiration" pour les qualifications, alignée sur le plus large
# des seuils déjà utilisés par notifications.tasks.notify_expiring_training (30/60/90 j).
JOURS_ALERTE_QUALIFICATION = 90

MODELES_PERIMETRE = {"ship": Ship, "service": Service, "sector": Sector, "section": Section}


class PerimetreNonAutorise(PermissionError):
    """Levée quand le périmètre demandé pour le bilan ne correspond pas au
    périmètre propre de l'utilisateur connecté (pas de drill-down hiérarchique :
    un utilisateur ne peut générer le bilan que de son propre périmètre)."""


def _dernier_par_installation(queryset, champ_installation="installation_id"):
    """Retourne {installation_id: dernier enregistrement} à partir d'un queryset
    déjà trié du plus récent au plus ancien (ordering par défaut des modèles de
    relevés d'installation)."""
    resultat = {}
    for obj in queryset:
        cle = getattr(obj, champ_installation)
        if cle not in resultat:
            resultat[cle] = obj
    return resultat


def _resoudre_perimetre(scope_type, scope_id):
    """Récupère l'objet (Navire/Service/Secteur/Section) correspondant au
    périmètre demandé, pour affichage dans l'en-tête du bilan."""
    modele = MODELES_PERIMETRE.get(scope_type)
    if modele is None:
        return None
    return modele.objects.filter(pk=scope_id).first()


def construire_contexte_instantane(scope_type: str, scope_id, utilisateur) -> dict:
    """Construit le contexte du bilan PDF Mode Instantané pour le périmètre
    scope_type/scope_id (ex: "sector", 5).

    Le filtrage des données réutilise scope_filters_for_user : le périmètre demandé
    doit correspondre exactement au périmètre propre de l'utilisateur, sinon une
    PerimetreNonAutorise est levée.
    """
    filtre_scope = scope_filters_for_user(utilisateur)
    if not filtre_scope or filtre_scope.get(f"{scope_type}_id") != scope_id:
        raise PerimetreNonAutorise(
            "Le périmètre demandé ne correspond pas au périmètre de l'utilisateur."
        )

    today = timezone.localdate()

    installations = list(
        Installation.objects.filter(**filtre_scope)
        .select_related("ship", "service", "sector", "section")
        .order_by("designation")
    )
    installation_ids = [inst.id for inst in installations]

    derniers_heures = _dernier_par_installation(
        InstallationHourReading.objects.filter(installation_id__in=installation_ids)
    )
    dernieres_visites = _dernier_par_installation(
        InstallationHourReading.objects.filter(
            installation_id__in=installation_ids, is_visit=True
        )
    )
    derniers_vibrations = _dernier_par_installation(
        InstallationVibrationReading.objects.filter(installation_id__in=installation_ids)
    )
    derniers_isolements = _dernier_par_installation(
        InstallationIsolationReading.objects.filter(installation_id__in=installation_ids)
    )

    # Échéances de maintenance (calendaire/compteur) des installations du périmètre,
    # non terminées, triées par date prévue : les retards (date passée) remontent
    # naturellement en premier.
    occurrences = (
        MaintenanceOccurrence.objects.filter(
            installation_maintenance__installation_id__in=installation_ids
        )
        .exclude(status__in=STATUTS_OCCURRENCE_TERMINEES)
        .select_related("installation_maintenance", "installation_maintenance__installation")
        .order_by("scheduled_for")
    )
    echeances = []
    installations_en_retard = set()
    for occ in occurrences:
        en_retard = occ.status == "OVERDUE" or occ.scheduled_for < today
        if en_retard:
            installations_en_retard.add(occ.installation_maintenance.installation_id)
        echeances.append(
            {
                "installation": occ.installation_maintenance.installation,
                "titre": occ.installation_maintenance.title,
                "date_prevue": occ.scheduled_for,
                "statut": occ.get_status_display(),
                "en_retard": en_retard,
            }
        )

    lignes_installations = [
        {
            "installation": inst,
            "statut": "En retard" if inst.id in installations_en_retard else "À jour",
            "derniere_visite": dernieres_visites.get(inst.id),
            "dernier_releve_heures": derniers_heures.get(inst.id),
            "dernier_releve_vibration": derniers_vibrations.get(inst.id),
            "dernier_releve_isolement": derniers_isolements.get(inst.id),
        }
        for inst in installations
    ]

    # Tickets correctifs ouverts sur le matériel mobile du périmètre.
    filtre_tickets = {f"asset__{cle}": valeur for cle, valeur in filtre_scope.items()}
    tickets_ouverts = list(
        CorrectiveTicket.objects.filter(**filtre_tickets)
        .exclude(status__in=STATUTS_TICKET_FERMES)
        .select_related("asset", "asset__asset_type")
        .order_by("reported_at")
    )
    for ticket in tickets_ouverts:
        ticket.anciennete_jours = (timezone.now() - ticket.reported_at).days

    # Qualifications proches d'expiration : TrainingRecord n'a pas de périmètre
    # propre, on le déduit du profil du marin titulaire de la qualification.
    filtre_qualifications = {
        f"user__profile__{cle}": valeur for cle, valeur in filtre_scope.items()
    }
    date_limite = today + timedelta(days=JOURS_ALERTE_QUALIFICATION)
    qualifications_proches_expiration = list(
        TrainingRecord.objects.filter(
            expires_at__gte=today, expires_at__lte=date_limite, **filtre_qualifications
        )
        .select_related("user", "user__profile", "course")
        .order_by("expires_at")
    )

    return {
        "mode": "INSTANTANE",
        "perimetre": _resoudre_perimetre(scope_type, scope_id),
        "genere_par": utilisateur,
        "genere_le": timezone.now(),
        "installations": lignes_installations,
        "echeances": echeances,
        "tickets_ouverts": tickets_ouverts,
        "qualifications_proches_expiration": qualifications_proches_expiration,
    }


def generer_bilan_instantane_pdf(scope_type: str, scope_id, utilisateur) -> bytes:
    """Génère le bilan PDF Mode Instantané pour le périmètre demandé et renvoie
    le contenu binaire du PDF (WeasyPrint, génération 100% côté serveur — aucune
    dépendance CDN, compatible fonctionnement hors-ligne)."""
    contexte = construire_contexte_instantane(scope_type, scope_id, utilisateur)
    html = render_to_string("reports/bilan_instantane.html", contexte)
    return weasyprint.HTML(string=html).write_pdf()
