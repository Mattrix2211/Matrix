"""Interface web des annonces : fil des annonces, publication, fiche avec accusé et suivi de lecture."""
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ValidationError
from django.http import Http404, HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.dateparse import parse_date
from django.views import View

from notifications.models import NotificationLevel

from .models import Annonce
from .services import (
    accuser,
    annonces_gerees,
    annonces_visibles,
    archiver,
    cibles_autorisees,
    lecture_de,
    marquer_lue,
    modifier,
    peut_consulter,
    peut_gerer,
    peut_publier,
    publier,
    suivi_lecture,
)


def _erreurs(request, exc):
    if isinstance(exc, PermissionError):
        messages.error(request, str(exc))
    else:
        for liste in getattr(exc, "message_dict", {"": exc.messages}).values():
            for erreur in liste:
                messages.error(request, erreur)


def _date(saisie, defaut=None):
    saisie = (saisie or "").strip()
    if not saisie:
        return defaut
    valeur = parse_date(saisie)
    if valeur is None:
        raise ValidationError("Indiquez une date valide.")
    return valeur


def _annonce(request, pk):
    annonce = get_object_or_404(Annonce.objects.select_related("auteur", "ship", "service", "sector", "section"), pk=pk)
    if not peut_consulter(request.user, annonce):
        raise Http404
    return annonce


class AnnoncesIndexView(LoginRequiredMixin, View):
    def get(self, request):
        niveau = request.GET.get("niveau", "")
        aujourdhui = timezone.localdate()
        visibles = (annonces_visibles(request.user) | annonces_gerees(request.user)).distinct().select_related("auteur")
        if niveau in NotificationLevel.values:
            visibles = visibles.filter(niveau=niveau)
        else:
            niveau = ""
        actives = [a for a in visibles if a.active_au(aujourdhui)]
        lues = {l.annonce_id: l for l in request.user.lectures_annonces.all()}
        for annonce in actives:
            lecture = lues.get(annonce.pk)
            annonce.a_accuser = annonce.accuse_requis and annonce.auteur_id != request.user.pk and not (
                lecture and lecture.accuse and lecture.version_lue >= annonce.version)
            annonce.non_lue = lecture is None and annonce.auteur_id != request.user.pk
        return render(request, "annonces/index.html", {
            "annonces": actives,
            "programmees": [a for a in visibles if not a.archivee and a.date_effet > aujourdhui],
            "archives": [a for a in visibles if a.archivee or (a.date_fin and a.date_fin < aujourdhui)][:20],
            "niveau": niveau, "niveaux": NotificationLevel.choices,
            "peut_publier": peut_publier(request.user),
        })


class AnnonceNouvelleView(LoginRequiredMixin, View):
    def _contexte(self, request):
        return {"cibles": cibles_autorisees(request.user), "niveaux": NotificationLevel.choices,
                "aujourdhui": timezone.localdate()}

    def get(self, request):
        if not peut_publier(request.user):
            raise Http404
        return render(request, "annonces/nouvelle.html", self._contexte(request))

    def post(self, request):
        try:
            annonce = publier(
                request.user, request.POST.get("titre", ""), request.POST.get("corps", ""),
                request.POST.get("niveau", ""), request.POST.get("cible", ""), request.POST.get("equipage", ""),
                bool(request.POST.get("accuse_requis")), _date(request.POST.get("date_effet")), _date(request.POST.get("date_fin")),
            )
        except (PermissionError, ValidationError) as exc:
            _erreurs(request, exc)
            return redirect("annonce-nouvelle")
        messages.success(request, "Annonce publiée.")
        return redirect("annonce-detail", pk=annonce.pk)


class AnnonceDetailView(LoginRequiredMixin, View):
    def get(self, request, pk):
        annonce = _annonce(request, pk)
        gerer = peut_gerer(request.user, annonce)
        lecture = lecture_de(request.user, annonce)
        if annonce.auteur_id != request.user.pk:
            marquer_lue(request.user, annonce)
        suivi = suivi_lecture(annonce) if gerer else []
        return render(request, "annonces/detail.html", {
            "annonce": annonce, "peut_gerer": gerer, "suivi": suivi,
            "accuse_fait": bool(lecture and lecture.accuse and lecture.version_lue >= annonce.version),
            "peut_accuser": annonce.accuse_requis and annonce.auteur_id != request.user.pk and not annonce.archivee,
            "versions": annonce.versions.all(),
            "compte": {etat: sum(1 for l in suivi if l["etat"] == etat) for etat in ("Accusé", "Lu")},
            "compte_non_lus": sum(1 for l in suivi if l["etat"] == "Non lu"),
            "niveaux": NotificationLevel.choices,
        })


class AnnonceActionView(LoginRequiredMixin, View):
    def post(self, request, pk):
        annonce = _annonce(request, pk)
        action = request.POST.get("action")
        try:
            if action == "accuser":
                accuser(request.user, annonce)
                messages.success(request, "Prise de connaissance enregistrée.")
            elif action == "modifier":
                modifier(request.user, annonce, request.POST.get("titre", ""), request.POST.get("corps", ""),
                         request.POST.get("niveau", ""), _date(request.POST.get("date_fin")))
                messages.success(request, "Annonce mise à jour : nouvelle version publiée.")
            elif action == "archiver":
                archiver(request.user, annonce)
                messages.success(request, "Annonce archivée.")
            else:
                return HttpResponseBadRequest("Action inconnue.")
        except (PermissionError, ValidationError) as exc:
            _erreurs(request, exc)
        return redirect("annonce-detail", pk=annonce.pk)
