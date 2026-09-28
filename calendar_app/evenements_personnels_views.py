"""Création, modification et suppression des événements personnels libres du
marin — découpage de calendar_app/views.py."""
from datetime import datetime, timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseBadRequest
from django.shortcuts import redirect, get_object_or_404
from django.utils import timezone

from .models import PersonalEvent


def _parse_personal_event_datetime(date_str):
    """Convertit la valeur du champ datetime-local du formulaire en date/heure
    « aware », en tenant compte du fuseau horaire local du bord."""
    naive_dt = datetime.fromisoformat(date_str)
    if timezone.is_aware(naive_dt):
        return naive_dt
    return timezone.make_aware(naive_dt)


@login_required
def personal_event_save(request):
    """Crée ou modifie un événement personnel libre du marin connecté.
    Un identifiant présent dans le formulaire déclenche une modification
    (limitée aux événements dont il est propriétaire), son absence une
    création — un seul formulaire suffit pour les deux usages."""
    if request.method != "POST":
        return HttpResponseBadRequest("POST required")
    titre = (request.POST.get("title") or "").strip()
    date_str = request.POST.get("starts_at") or ""
    fin_str = request.POST.get("ends_at") or ""
    note = (request.POST.get("note") or "").strip()
    event_id = request.POST.get("id") or None

    if not titre or not date_str:
        messages.error(request, "Le titre et la date sont obligatoires.")
        return redirect("calendar-index")
    try:
        starts_at = _parse_personal_event_datetime(date_str)
    except ValueError:
        messages.error(request, "Date invalide.")
        return redirect("calendar-index")

    ends_at = None
    if fin_str:
        try:
            ends_at = _parse_personal_event_datetime(fin_str)
        except ValueError:
            messages.error(request, "Date de fin invalide.")
            return redirect("calendar-index")
        if ends_at <= starts_at:
            messages.error(request, "La date de fin doit être postérieure à la date de début.")
            return redirect("calendar-index")

    if event_id:
        evenement = get_object_or_404(PersonalEvent, pk=event_id, owner=request.user)
        ancien_debut = evenement.starts_at
        evenement.title = titre
        evenement.starts_at = starts_at
        # Le formulaire de modification (modale) ne propose pas encore de
        # champ de date de fin : on ne l'écrase donc que si elle est
        # explicitement fournie, pour ne pas effacer une durée déjà réglée
        # par glisser-redimensionnement (eventResize) sur le calendrier.
        if fin_str:
            evenement.ends_at = ends_at
        elif evenement.ends_at:
            # Seule la date de début a été modifiée via la modale : on
            # décale la date de fin du même delta pour conserver la durée
            # existante, au lieu de la laisser figée (ce qui produirait une
            # incohérence ends_at < starts_at en base, cf. régression
            # signalée par le QA).
            evenement.ends_at = evenement.ends_at + (starts_at - ancien_debut)
        evenement.note = note
        evenement.save(update_fields=["title", "starts_at", "ends_at", "note"])
        messages.success(request, "Événement personnel modifié.")
    else:
        if not ends_at:
            # Champ de fin facultatif (formulaire de création rapide, comme
            # le calendrier Apple) : une durée par défaut d'une heure est
            # appliquée si l'utilisateur ne la renseigne pas, plutôt que de
            # bloquer la création ou de créer un événement sans durée.
            ends_at = starts_at + timedelta(hours=1)
        PersonalEvent.objects.create(
            owner=request.user, title=titre, starts_at=starts_at, ends_at=ends_at, note=note,
        )
        messages.success(request, "Événement personnel ajouté à votre calendrier.")
    return redirect("calendar-index")


@login_required
def personal_event_delete(request, pk):
    """Supprime un événement personnel — réservé à son propriétaire."""
    if request.method != "POST":
        return HttpResponseBadRequest("POST required")
    evenement = get_object_or_404(PersonalEvent, pk=pk, owner=request.user)
    evenement.delete()
    messages.success(request, "Événement personnel supprimé.")
    return redirect("calendar-index")
