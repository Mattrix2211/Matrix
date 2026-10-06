"""Centre de notifications (docs/UX.md §23) : panneau latéral de la barre
supérieure. Chaque marin ne voit et ne modifie que ses propres notifications."""
from django.contrib.auth.decorators import login_required
from django.db.models import Case, IntegerField, Value, When
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from django.utils.timesince import timesince
from django.views.decorators.http import require_GET, require_POST

from .liens import liens_accessibles
from .models import Notification, NotificationLevel

LIMITE_AFFICHEE = 50

# Gravité décroissante : critique, attention, information
_RANG_NIVEAU = Case(
    When(level=NotificationLevel.DANGER, then=Value(0)),
    When(level=NotificationLevel.WARNING, then=Value(1)),
    default=Value(2),
    output_field=IntegerField(),
)


def _date_relative(date):
    if (timezone.now() - date).total_seconds() < 60:
        return "à l'instant"
    return "il y a " + timesince(date).split(",")[0]


def _non_lues(user):
    return Notification.objects.filter(user=user, is_read=False).count()


def _contexte_liste(request, **extra):
    """Liste triée par niveau puis date décroissante."""
    notifications = list(
        Notification.objects.filter(user=request.user)
        .select_related("content_type")
        .annotate(rang=_RANG_NIVEAU)
        .order_by("rang", "-created_at")[:LIMITE_AFFICHEE]
    )
    liens = liens_accessibles(request, notifications)
    for notification in notifications:
        notification.lien = liens.get(notification.pk)
        notification.date_relative = _date_relative(notification.created_at)
    return {"notifications": notifications, "non_lues": _non_lues(request.user), **extra}


def _rendre_liste(request):
    """Après une action : la liste, et le compteur de la barre en échange hors-bande."""
    return render(request, "notifications/_liste.html", _contexte_liste(request, oob=True))


@login_required
@require_GET
def panneau(request):
    return render(request, "notifications/_panneau.html", _contexte_liste(request))


@login_required
@require_GET
def compteur(request):
    return render(request, "notifications/_compteur.html", {"non_lues": _non_lues(request.user)})


@login_required
@require_POST
def marquer_lue(request, pk):
    notification = get_object_or_404(Notification, pk=pk, user=request.user)
    if not notification.is_read:
        notification.is_read = True
        notification.save(update_fields=["is_read"])
    return _rendre_liste(request)


@login_required
@require_POST
def tout_marquer_lu(request):
    Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
    return _rendre_liste(request)
