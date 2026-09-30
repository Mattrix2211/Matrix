"""Synthèse de passation à la relève d'un bâtiment à double équipage.

À chaque relève (immédiate, ou planifiée arrivée à échéance), l'équipage montant
reçoit l'état du BÂTIMENT au moment de la relève : maintenances en cours ou en
retard, anomalies et tickets correctifs ouverts, stock sous seuil. Le contenu est
figé dans `SynthesePassation` (consultable ensuite) et signalé par une
`Notification`. Aucune donnée n'est dupliquée : on relit maintenance et logistics.

Idempotence : une seule synthèse par (bâtiment, équipage montant, date de relève).
Les imports des autres apps sont faits dans les fonctions pour éviter les imports
circulaires au chargement (org est importé très tôt)."""
import logging

from django.contrib.contenttypes.models import ContentType
from django.db import IntegrityError, transaction
from django.db.models import F, Q
from django.utils import timezone

from accounts.models import AuditLog

from .models import Ship, SynthesePassation

journal = logging.getLogger(__name__)

# Au-delà, la liste détaillée est tronquée ; les compteurs restent exacts.
MAX_ELEMENTS = 30
STATUTS_MAINTENANCE_A_TRANSMETTRE = ("IN_PROGRESS", "WAITING_VALIDATION", "OVERDUE")


def _rubrique(elements, **extras):
    return {"total": len(elements), "elements": elements[:MAX_ELEMENTS], **extras}


def construire_contenu(ship):
    """État du bâtiment à l'instant présent, sous forme structurée (JSON)."""
    from logistics.models import (
        STATUTS_ANOMALIE_OUVERTS, STATUTS_TICKET_OUVERTS, Anomalie, CorrectiveTicket, StockPiece,
    )
    from maintenance.models import MaintenanceOccurrence

    occurrences = list(
        MaintenanceOccurrence.objects.filter(status__in=STATUTS_MAINTENANCE_A_TRANSMETTRE)
        .filter(Q(asset__ship=ship) | Q(installation_maintenance__installation__ship=ship))
        .select_related("asset", "installation_maintenance__installation")
        .order_by("scheduled_for")
    )
    maintenances = [
        {
            "libelle": occ.titre_affiche, "statut": occ.status, "statut_libelle": occ.get_status_display(),
            "echeance": occ.scheduled_for.isoformat(), "en_retard": occ.status == "OVERDUE",
        }
        for occ in occurrences
    ]
    anomalies = [
        {"libelle": a.titre, "statut_libelle": a.get_statut_display(), "gravite": a.gravite}
        for a in Anomalie.objects.filter(ship=ship, statut__in=STATUTS_ANOMALIE_OUVERTS).order_by("-gravite", "-created_at")
    ]
    tickets = [
        {
            "libelle": f"{t.equipement} : {t.description[:80]}", "statut_libelle": t.get_status_display(),
            "gravite": t.severity,
        }
        for t in CorrectiveTicket.objects.filter(status__in=STATUTS_TICKET_OUVERTS)
        .filter(Q(asset__ship=ship) | Q(installation__ship=ship))
        .select_related("asset", "installation").order_by("-severity", "-reported_at")
    ]
    pieces = [
        {
            "libelle": str(p), "quantite": p.quantite, "minimum": p.quantite_minimale, "critique": p.est_critique,
        }
        for p in StockPiece.objects.filter(ship=ship, quantite__lt=F("quantite_minimale")).order_by("reference")
    ]
    pieces.sort(key=lambda p: not p["critique"])
    return {
        "genere_le": timezone.now().isoformat(),
        "maintenances": _rubrique(maintenances, en_retard=sum(m["en_retard"] for m in maintenances)),
        "anomalies": _rubrique(anomalies),
        "tickets": _rubrique(tickets),
        "stock": _rubrique(pieces, critiques=sum(p["critique"] for p in pieces)),
    }


def _niveau(contenu):
    from notifications.models import NotificationLevel

    if contenu["maintenances"]["en_retard"] or contenu["stock"]["critiques"]:
        return NotificationLevel.DANGER
    if any(contenu[cle]["total"] for cle in ("maintenances", "anomalies", "tickets", "stock")):
        return NotificationLevel.WARNING
    return NotificationLevel.INFO


def _notifier(synthese):
    from accounts.models import UserProfile
    from notifications.models import Notification
    from notifications.services import creer_notifications_en_masse

    contenu = synthese.contenu
    verb = (
        f"Passation {synthese.ship.name} du {synthese.date_releve:%d/%m/%Y} : "
        f"{contenu['maintenances']['total']} maintenance(s), {contenu['anomalies']['total']} anomalie(s), "
        f"{contenu['tickets']['total']} ticket(s), {contenu['stock']['total']} pièce(s) sous seuil"
    )
    type_synthese = ContentType.objects.get_for_model(SynthesePassation)
    niveau = _niveau(contenu)
    profils = UserProfile.objects.filter(equipage=synthese.equipage_montant, user__is_active=True)
    creer_notifications_en_masse([
        Notification(
            user_id=p.user_id, verb=verb, level=niveau,
            content_type=type_synthese, object_id=str(synthese.pk),
        )
        for p in profils
    ])


def generer_synthese(ship, montant, descendant, jour=None):
    """Produit (une seule fois) la synthèse de passation de cette relève et
    notifie l'équipage montant. Renvoie (synthèse, créée)."""
    jour = jour or timezone.localdate()
    try:
        with transaction.atomic():
            synthese, creee = SynthesePassation.objects.get_or_create(
                ship=ship, equipage_montant=montant, date_releve=jour,
                defaults={"equipage_descendant": descendant, "contenu": construire_contenu(ship)},
            )
    except IntegrityError:
        # Course avec un autre déclenchement : la synthèse existe déjà.
        return SynthesePassation.objects.get(ship=ship, equipage_montant=montant, date_releve=jour), False
    if creee:
        _notifier(synthese)
        AuditLog.objects.create(
            action="synthese_passation",
            details=f"navire={ship.name}; synthèse de passation générée pour l'équipage {montant.nom} au {jour.isoformat()}",
        )
    return synthese, creee


def appliquer_releves_echues(jour=None):
    """Bascule les relèves planifiées arrivées à échéance et produit leur
    synthèse. Idempotent : sans relève échue, ne fait rien."""
    jour = jour or timezone.localdate()
    nb = 0
    ships = Ship.objects.filter(double_equipage=True, equipage_releve__isnull=False, date_releve__lte=jour)
    for ship in ships.select_related("equipage_a_bord", "equipage_releve"):
        try:
            # Bascule, synthèse et notifications sont indissociables : en cas
            # d'échec, la relève reste planifiée et sera retentée au prochain passage.
            with transaction.atomic():
                montant, descendant = ship.equipage_releve, ship.equipage_a_bord
                date_releve = ship.date_releve
                ship.equipage_a_bord, ship.equipage_releve = montant, None
                ship.save(update_fields=["equipage_a_bord", "equipage_releve", "updated_at"])
                AuditLog.objects.create(
                    action="equipage_releve",
                    details=(
                        f"navire={ship.name}; {descendant.nom if descendant else 'aucun'} -> {montant.nom} "
                        f"au {date_releve.isoformat()} (relève planifiée appliquée automatiquement)"
                    ),
                )
                generer_synthese(ship, montant, descendant, date_releve)
        except Exception:
            journal.exception("Relève planifiée du navire %s non appliquée : elle sera retentée.", ship.name)
            continue
        nb += 1
    return nb
