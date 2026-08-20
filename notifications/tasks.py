from celery import shared_task
from django.core.management import call_command
from django.db.models import F, Q
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone
from datetime import timedelta
from .models import Notification
from training.models import TrainingRecord
from maintenance.models import MaintenanceOccurrence
from logistics.models import StockPiece
from accounts.models import UserProfile, Roles
from assets.models import Installation, InstallationMaintenance, ModeDeclenchement
from assets.trend import jours_avant_franchissement_seuil

@shared_task
def notify_expiring_training(days_list=(30, 60, 90)):
    today = timezone.localdate()
    for days in days_list:
        target = today + timedelta(days=days)
        for rec in TrainingRecord.objects.filter(expires_at=target).select_related('user', 'course'):
            Notification.objects.get_or_create(
                user=rec.user,
                verb=f"Formation '{rec.course.title}' expire dans {days} jours"
            )
    return {"status": "ok"}

@shared_task
def notify_overdue_occurrences():
    occurrences = MaintenanceOccurrence.objects.filter(status='OVERDUE').select_related(
        'plan'
    ).prefetch_related('assignees')
    for occ in occurrences:
        for u in occ.assignees.all():
            Notification.objects.get_or_create(user=u, verb=f"Occurrence en retard: {occ.id}")
    return {"status": "ok"}

@shared_task
def notify_low_stock():
    """Alerte les chefs concernés dès qu'une pièce de stock passe sous son seuil minimal.

    Le destinataire est déterminé à partir du périmètre de la pièce (service/secteur/
    section) : chef de service dont le service correspond, chef de secteur dont le
    secteur correspond, et chef de section dont la section correspond si la pièce en
    a une (section optionnelle, comme sur Installation/Asset).

    Déduplication : une seule notification active par pièce et par destinataire tant
    qu'elle n'a pas été résolue - pas de rappel quotidien pour une même pièce déjà sous
    le seuil.

    Cycle de vie de l'alerte : dès qu'une pièce repasse au-dessus (ou à l'égal) de son
    seuil minimal, la notification active liée à cette pièce est résolue (même pattern
    que l'action "marquer comme lue" côté utilisateur : aucune autre partie du code ne
    supprime réellement une Notification en base). Une fois résolue, une nouvelle
    rupture recrée bien une alerte, puisque la déduplication ne porte que sur les
    notifications encore actives.
    """
    piece_ct = ContentType.objects.get_for_model(StockPiece)

    # Pièces redevenues conformes : on résout leurs notifications actives pour
    # permettre une nouvelle alerte en cas de re-rupture future.
    for piece in StockPiece.objects.filter(quantite__gte=F("quantite_minimale")):
        Notification.objects.filter(
            content_type=piece_ct, object_id=str(piece.pk), is_read=False
        ).update(is_read=True)

    for piece in StockPiece.objects.filter(quantite__lt=F("quantite_minimale")).select_related(
        "service", "sector", "section"
    ):
        scope_filter = Q(role=Roles.CHEF_SERVICE, service=piece.service) | Q(
            role=Roles.CHEF_SECTEUR, sector=piece.sector
        )
        if piece.section_id:
            scope_filter |= Q(role=Roles.CHEF_SECTION, section=piece.section)

        verb = f"Stock sous le seuil : {piece.reference} - {piece.designation} ({piece.quantite}/{piece.quantite_minimale})"
        for profile in UserProfile.objects.filter(scope_filter).select_related("user"):
            Notification.objects.get_or_create(
                user=profile.user,
                content_type=piece_ct,
                object_id=str(piece.pk),
                is_read=False,
                defaults={"verb": verb},
            )
    return {"status": "ok"}

@shared_task
def generate_installation_notifications(days: int = 7):
    """Alerte les marins des échéances de vibration/isolement des installations fixes.

    Enveloppe la commande de gestion du même nom (qui porte la logique métier et ses
    tests) afin de la rendre planifiable quotidiennement via Celery Beat.
    """
    call_command("generate_installation_notifications", days=days)
    return {"status": "ok"}

@shared_task
def generate_installation_maintenance_notifications(days: int = 7):
    """Alerte les marins des échéances d'entretien (calendaire/compteur) des
    maintenances d'installations fixes.

    Enveloppe la commande de gestion du même nom (qui porte la logique métier et ses
    tests) afin de la rendre planifiable quotidiennement via Celery Beat.
    """
    call_command("generate_installation_maintenance_notifications", days=days)
    return {"status": "ok"}


def _destinataires_installation(installation):
    """Chefs concernés par une installation (même construction que le
    scope_filter de notify_low_stock : chef de service/secteur dont le
    périmètre correspond, et chef de section si l'installation en a une)."""
    scope_filter = Q(role=Roles.CHEF_SERVICE, service=installation.service) | Q(
        role=Roles.CHEF_SECTEUR, sector=installation.sector
    )
    if installation.section_id:
        scope_filter |= Q(role=Roles.CHEF_SECTION, section=installation.section)
    return UserProfile.objects.filter(scope_filter).select_related("user")


def _signaler_ou_resoudre_derive(content_type, object_id, destinataires, verb, en_derive):
    """Crée/maintient ou résout une alerte de dérive, selon le même cycle de vie
    que notify_low_stock : une notification active tant que la dérive persiste,
    résolue (is_read=True) dès qu'elle disparaît (pas de rappel à chaque
    exécution pour la même dérive déjà signalée)."""
    if not en_derive:
        Notification.objects.filter(
            content_type=content_type, object_id=object_id, is_read=False
        ).update(is_read=True)
        return
    for profile in destinataires:
        Notification.objects.get_or_create(
            user=profile.user,
            content_type=content_type,
            object_id=object_id,
            is_read=False,
            defaults={"verb": verb},
        )


@shared_task
def detect_installation_drift():
    """Détecte une dérive sur les relevés techniques des installations fixes
    (isolement en Ohms, heures de marche vs seuil d'entretien compteur), par
    régression linéaire simple sur les derniers relevés (assets/trend.py), et
    alerte les chefs concernés AVANT le franchissement réel du seuil.

    Portée : uniquement l'isolement et les heures de marche, qui sont des
    grandeurs continues avec un seuil numérique - la vibration (état qualitatif
    A/B/C) n'a pas de seuil numérique franchissable par régression et n'est
    donc pas concernée ici.

    Le seuil d'isolement (Installation.isolation_seuil_ohms) est optionnel et
    propre à chaque installation : sans seuil renseigné, aucune dérive n'est
    calculée. Le seuil des heures de marche est celui déjà défini sur chaque
    InstallationMaintenance en mode compteur (seuil_heures + derniere_echeance_heures).

    Même cycle de vie que notify_low_stock : une notification active par
    installation/entretien tant que la dérive persiste, résolue dès qu'elle
    disparaît (valeurs stabilisées, améliorées, ou seuil retiré).
    """
    inst_ct = ContentType.objects.get_for_model(Installation)
    maint_ct = ContentType.objects.get_for_model(InstallationMaintenance)

    for installation in Installation.objects.select_related("service", "sector", "section").prefetch_related(
        "isolation_readings", "maintenances", "hour_readings"
    ):
        # Isolement (Ohms) : dérive à la baisse vers le seuil minimal.
        object_id = f"{installation.id}:DERIVE_ISOLEMENT"
        jours = None
        if installation.isolation_seuil_ohms:
            releves = [(r.date, float(r.ohms)) for r in installation.isolation_readings.all()]
            jours = jours_avant_franchissement_seuil(
                releves, float(installation.isolation_seuil_ohms), sens="BAISSE"
            )
        verb = f"Dérive détectée sur l'isolement de {installation.designation} : seuil estimé atteint dans {jours} j"
        _signaler_ou_resoudre_derive(
            inst_ct, object_id, _destinataires_installation(installation), verb, jours is not None
        )

        # Heures de marche : dérive à la hausse vers le seuil de chaque entretien au compteur.
        releves_heures = [(r.date, float(r.hours)) for r in installation.hour_readings.all()]
        for maintenance in installation.maintenances.all():
            if maintenance.mode_declenchement not in (ModeDeclenchement.COMPTEUR, ModeDeclenchement.LES_DEUX):
                continue
            if not maintenance.seuil_heures:
                continue
            seuil = float(maintenance.derniere_echeance_heures or 0) + float(maintenance.seuil_heures)
            jours = jours_avant_franchissement_seuil(releves_heures, seuil, sens="HAUSSE")
            object_id = f"{maintenance.id}:DERIVE_HEURES"
            verb = (
                f"Dérive détectée sur les heures de marche de {installation.designation} : "
                f"entretien '{maintenance.title}' - seuil estimé atteint dans {jours} j"
            )
            _signaler_ou_resoudre_derive(
                maint_ct, object_id, _destinataires_installation(installation), verb, jours is not None
            )

    return {"status": "ok"}
