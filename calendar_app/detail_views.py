"""Panneau latéral de détail d'un événement du calendrier (fragment HTMX) : titre, source, date,
responsable, avancement et fil de discussion, sans quitter le planning."""
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.http import Http404
from django.shortcuts import get_object_or_404, render
from django.contrib.auth.decorators import login_required
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from absences.models import Absence
from programme.models import EvenementProgramme
from programme.services import evenements_visibles
from quarts.models import CreneauQuart, CreneauServiceGarde
from taches.models import Tache
from taches.services import avancement_equipe, demarrer, est_chef_de, peut_consulter, peut_gerer, repondre
from threads.utils import ajouter_commentaire, commentaires_de
from training.models import TrainingSession

from .sources import SOURCES

LIBELLE_SOURCE = {s.cle: s.libelle for s in SOURCES}
# Types qui ouvrent un fil de discussion ; formations et absences : détail seul.
TYPES_AVEC_FIL = ("tache", "quart", "service_garde", "programme")


def _nom(user):
    return (user.get_full_name() or user.username) if user else ""


def _creneau(modele, user, pk):
    creneau = get_object_or_404(modele.objects.select_related("marin"), pk=pk)
    if creneau.marin is None or not (creneau.marin_id == user.pk or est_chef_de(user, creneau.marin)):
        raise Http404
    return creneau


def _fiche(type_evenement, user, pk):
    """Objet du panneau et ses libellés ; 404 hors périmètre ou droits (jamais d'indice sur l'existence)."""
    if type_evenement == "tache":
        objet = get_object_or_404(Tache.objects.select_related("assigne", "created_by"), pk=pk)
        if not peut_consulter(user, objet):
            raise Http404
        date = f"Échéance le {objet.echeance:%d/%m/%Y}" if objet.echeance else "Sans échéance"
        return objet, {"titre": objet.titre, "responsable": _nom(objet.assigne), "date": date, "url": reverse("tache-detail", args=[pk])}
    if type_evenement in ("quart", "service_garde"):
        quart = type_evenement == "quart"
        objet = _creneau(CreneauQuart if quart else CreneauServiceGarde, user, pk)
        parent = objet.quart_id if quart else objet.service_garde_id
        return objet, {
            "titre": objet.poste, "responsable": _nom(objet.marin),
            "date": f"Du {timezone.localtime(objet.debut):%d/%m/%Y %H:%M} au {timezone.localtime(objet.fin):%d/%m/%Y %H:%M}",
            "url": reverse("quart-detail" if quart else "garde-detail", args=[parent]),
        }
    if type_evenement == "programme":
        objet = get_object_or_404(evenements_visibles(user).select_related("type", "auteur"), pk=pk, annule=False)
        fin = f" au {timezone.localtime(objet.fin):%d/%m/%Y %H:%M}" if objet.fin else ""
        return objet, {
            "titre": f"{objet.type.nom} - {objet.titre}", "responsable": _nom(objet.auteur),
            "date": f"Du {timezone.localtime(objet.debut):%d/%m/%Y %H:%M}{fin}" if fin else f"Le {timezone.localtime(objet.debut):%d/%m/%Y %H:%M}",
            "url": reverse("evenement-detail", args=[pk]),
        }
    if type_evenement == "training":
        objet = get_object_or_404(TrainingSession.objects.select_related("course", "instructor"), pk=pk)
        return objet, {
            "titre": str(objet.course), "responsable": _nom(objet.instructor),
            "date": f"Le {timezone.localtime(objet.scheduled_at):%d/%m/%Y %H:%M}", "url": "/training/",
        }
    if type_evenement == "absence":
        objet = get_object_or_404(Absence.objects.select_related("marin", "type_absence"), pk=pk)
        if not (objet.marin_id == user.pk or est_chef_de(user, objet.marin)):
            raise Http404
        return objet, {
            "titre": str(objet.type_absence), "responsable": _nom(objet.marin),
            "date": f"Du {objet.date_debut:%d/%m/%Y} au {objet.date_fin:%d/%m/%Y}", "url": reverse("absences-index"),
        }
    raise Http404


def _rendre(request, type_evenement, pk):
    objet, fiche = _fiche(type_evenement, request.user, pk)
    avec_fil = type_evenement in TYPES_AVEC_FIL
    contexte = {
        **fiche, "type": type_evenement, "pk": pk, "source": LIBELLE_SOURCE[type_evenement], "avec_fil": avec_fil,
        "commentaires": commentaires_de(objet) if avec_fil else [],
    }
    if type_evenement == "tache":
        contexte.update({
            "tache": objet,
            "peut_demarrer": request.user.pk == objet.assigne_id and objet.statut == Tache.STATUT_A_FAIRE,
            "avancement": avancement_equipe(request.user) if peut_gerer(request.user, objet) else None,
        })
    return render(request, "calendar/_detail_evenement.html", contexte)


@login_required
def detail_evenement(request, type_evenement, pk):
    return _rendre(request, type_evenement, pk)


@login_required
@require_POST
def detail_commentaire(request, type_evenement, pk):
    """Réponse dans le fil ; le fil d'un objet sans message est créé à la première réponse."""
    if type_evenement not in TYPES_AVEC_FIL:
        raise Http404
    objet, _ = _fiche(type_evenement, request.user, pk)
    corps = request.POST.get("body", "")
    try:
        if type_evenement == "tache":
            repondre(objet, request.user, corps)
        elif corps.strip():
            ajouter_commentaire(objet, request.user, corps.strip())
        else:
            raise ValidationError("Le message ne peut pas être vide.")
    except (PermissionError, ValidationError) as exc:
        messages.error(request, str(exc))
    return _rendre(request, type_evenement, pk)


@login_required
@require_POST
def detail_tache_demarrer(request, pk):
    tache = get_object_or_404(Tache, pk=pk)
    if not peut_consulter(request.user, tache):
        raise Http404
    try:
        demarrer(tache, request.user)
    except (PermissionError, ValidationError) as exc:
        messages.error(request, str(exc))
    return _rendre(request, "tache", pk)
