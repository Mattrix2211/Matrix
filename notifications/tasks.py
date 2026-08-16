from celery import shared_task
from django.db.models import F, Q
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone
from datetime import timedelta
from .models import Notification
from training.models import TrainingRecord
from maintenance.models import MaintenanceOccurrence
from logistics.models import StockPiece
from accounts.models import UserProfile, Roles

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
    for occ in MaintenanceOccurrence.objects.filter(status='OVERDUE').select_related('plan'):
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

    Déduplication : une seule notification par pièce et par destinataire tant qu'elle
    n'a pas été purgée — pas de rappel quotidien pour une même pièce déjà sous le seuil.
    """
    piece_ct = ContentType.objects.get_for_model(StockPiece)
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
                defaults={"verb": verb},
            )
    return {"status": "ok"}
