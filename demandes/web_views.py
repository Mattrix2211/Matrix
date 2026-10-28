"""Interface web des demandes bord–terre : liste, signalement, fiche avec fil, actions de suivi."""
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ValidationError
from django.http import Http404, HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.dateparse import parse_date
from django.views import View

from notifications.liens import lien_objet
from taches.services import peut_consulter as peut_consulter_tache
from matrix.core.saisie import entier_ou_none
from notifications.services import phrase_prevenus
from threads.utils import commentaires_de

from .models import Demande
from .services import (
    TRANSITIONS_DECLARANT,
    TRANSITIONS_RESPONSABLE,
    ajouter_interlocuteur,
    categories_prevenues,
    changer_etat,
    creer_action,
    creer_demande,
    demandes_recues,
    demandes_visibles,
    interlocuteurs_possibles,
    marins_pour_action,
    peut_consulter,
    peut_piloter,
    reaffecter,
    repondre,
    responsables_possibles,
    trouver_objet,
)

User = get_user_model()
TERMINEES_AFFICHEES = 10


def _erreurs(request, exc):
    if isinstance(exc, PermissionError):
        messages.error(request, str(exc))
    else:
        for liste in getattr(exc, "message_dict", {"": exc.messages}).values():
            for erreur in liste:
                messages.error(request, erreur)


def _nom(user):
    return user.get_full_name() or user.username


def _prevenus(demande, prevenus, acteur):
    return phrase_prevenus(categories_prevenues(demande, prevenus, acteur))


def _demande_visible(request, pk):
    demande = get_object_or_404(Demande.objects.select_related("declarant", "responsable"), pk=pk)
    if not peut_consulter(request.user, demande):
        raise Http404
    return demande


def _date(saisie):
    saisie = saisie.strip()
    if not saisie:
        return None
    valeur = parse_date(saisie)
    if valeur is None:
        raise ValidationError("Indiquez une échéance valide (ou aucune).")
    return valeur


class DemandesIndexView(LoginRequiredMixin, View):
    def get(self, request):
        demandes = list(demandes_visibles(request.user).select_related("declarant", "responsable"))
        ouvertes = [d for d in demandes if d.ouverte]
        moi = request.user.pk
        recues = set(demandes_recues(request.user).values_list("pk", flat=True))
        a_traiter = [
            d for d in ouvertes
            if (d.responsable_id == moi and d.etat != Demande.ETAT_RESOLU)
            or (d.declarant_id == moi and d.etat in (Demande.ETAT_EN_ATTENTE, Demande.ETAT_RESOLU))
            or d.pk in recues
        ]
        return render(request, "demandes/index.html", {
            "a_traiter": a_traiter,
            "mes_signalements": [d for d in ouvertes if d.declarant_id == moi and d not in a_traiter],
            "suivies": [d for d in ouvertes if d.declarant_id != moi and d not in a_traiter],
            "closes": [d for d in demandes if not d.ouverte][:TERMINEES_AFFICHEES],
        })


class DemandeNouvelleView(LoginRequiredMixin, View):
    def _objet(self, request, source):
        modele, _, pk = source.partition(":")
        objet = trouver_objet(modele, pk)
        if objet is None or lien_objet(request.user, objet) is None:
            raise Http404
        return objet

    def get(self, request):
        objet = self._objet(request, request.GET.get("objet", ""))
        return render(request, "demandes/nouvelle.html", {
            "objet": objet, "source": request.GET["objet"], "lien": lien_objet(request.user, objet),
            "responsables": responsables_possibles(request.user),
            "priorites": Demande.PRIORITE_CHOICES,
        })

    def post(self, request):
        source = request.POST.get("objet", "")
        objet = self._objet(request, source)
        try:
            responsable = User.objects.filter(pk=entier_ou_none(request.POST.get("responsable"))).first()
            demande = creer_demande(
                request.user, objet, request.POST.get("titre", ""), request.POST.get("description", ""), responsable,
                _date(request.POST.get("echeance", "")), request.POST.get("priorite") or Demande.PRIORITE_NORMALE,
            )
        except (PermissionError, ValidationError) as exc:
            _erreurs(request, exc)
            return redirect(f"{request.path}?objet={source}")
        messages.success(request, "Difficulté signalée : le responsable est prévenu.")
        return redirect("demande-detail", pk=demande.pk)


class DemandeDetailView(LoginRequiredMixin, View):
    def get(self, request, pk):
        demande = _demande_visible(request, pk)
        moi = request.user.pk
        transitions = set()
        if moi == demande.responsable_id:
            transitions |= set(TRANSITIONS_RESPONSABLE.get(demande.etat, ()))
        if moi == demande.declarant_id:
            transitions |= set(TRANSITIONS_DECLARANT.get(demande.etat, ()))
        piloter = peut_piloter(request.user, demande)
        return render(request, "demandes/detail.html", {
            "demande": demande,
            "commentaires": commentaires_de(demande),
            "interlocuteurs": demande.interlocuteurs.all(),
            "actions": [(t, peut_consulter_tache(request.user, t)) for t in demande.actions.select_related("assigne")],
            "objet": demande.objet,
            "lien_objet": lien_objet(request.user, demande.objet) if demande.objet else None,
            "transitions": [(code, libelle) for code, libelle in Demande.ETAT_CHOICES if code in transitions],
            "peut_piloter": piloter,
            "candidats": interlocuteurs_possibles(demande) if piloter else [],
            "responsables": responsables_possibles(demande.declarant) if piloter else [],
            "marins": marins_pour_action(demande) if piloter else [],
            "peut_repondre": demande.etat != Demande.ETAT_CLOS,
        })


class DemandeActionView(LoginRequiredMixin, View):
    """Changement d'état, réaffectation, interlocuteur et action décidée dans le dossier."""

    def post(self, request, pk):
        demande = _demande_visible(request, pk)
        action = request.POST.get("action")
        try:
            if action == "etat":
                prevenus = changer_etat(demande, request.user, request.POST.get("etat", ""), request.POST.get("note", ""))
                messages.success(request, "État du dossier mis à jour." + _prevenus(demande, prevenus, request.user))
            elif action == "reaffecter":
                nouveau = User.objects.filter(pk=entier_ou_none(request.POST.get("responsable"))).first()
                if nouveau is None:
                    raise ValidationError("Responsable introuvable.")
                prevenus = reaffecter(demande, request.user, nouveau)
                messages.success(request, f"Dossier confié à {_nom(nouveau)}." + _prevenus(demande, prevenus, request.user))
            elif action == "interlocuteur":
                cible = User.objects.filter(pk=entier_ou_none(request.POST.get("interlocuteur"))).first()
                if cible is None:
                    raise ValidationError("Interlocuteur introuvable.")
                prevenus = ajouter_interlocuteur(demande, request.user, cible)
                messages.success(request, f"{_nom(cible)} ajouté au dossier." + _prevenus(demande, prevenus, request.user))
            elif action == "creer_action":
                assigne = User.objects.filter(pk=entier_ou_none(request.POST.get("assigne"))).first()
                if assigne is None:
                    raise ValidationError("Indiquez le marin qui réalisera l'action.")
                creer_action(demande, request.user, assigne, request.POST.get("titre", ""), _date(request.POST.get("echeance", "")))
                messages.success(request, "Action assignée.")
            else:
                return HttpResponseBadRequest("Action inconnue.")
        except (PermissionError, ValidationError) as exc:
            _erreurs(request, exc)
        return redirect("demande-detail", pk=demande.pk)


class DemandeCommentaireView(LoginRequiredMixin, View):
    """Réponse dans le fil : ouverte aux acteurs du dossier, même à terre (cf. middleware)."""

    def post(self, request, pk):
        demande = _demande_visible(request, pk)
        try:
            prevenus = repondre(demande, request.user, request.POST.get("body", ""))
            messages.success(request, "Message publié." + _prevenus(demande, prevenus, request.user))
        except (PermissionError, ValidationError) as exc:
            _erreurs(request, exc)
        return redirect("demande-detail", pk=demande.pk)
