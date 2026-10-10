"""Interface web des tâches : liste, fiche avec fil contextuel, actions de suivi."""
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ValidationError
from django.http import Http404, HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.dateparse import parse_date
from django.views import View

from threads.utils import commentaires_de

from .models import Tache
from .services import (
    ajouter_participant,
    avancement_equipe,
    creer_tache,
    demarrer,
    interlocuteurs_possibles,
    marins_assignables,
    peut_consulter,
    peut_gerer,
    rendre_compte,
    reprendre,
    repondre,
    signaler_blocage,
    taches_visibles,
)

User = get_user_model()


def _erreurs(request, exc):
    if isinstance(exc, PermissionError):
        messages.error(request, str(exc))
    else:
        for liste in getattr(exc, "message_dict", {"": exc.messages}).values():
            for erreur in liste:
                messages.error(request, erreur)


def _tache_visible(request, pk):
    tache = get_object_or_404(Tache.objects.select_related("assigne", "created_by"), pk=pk)
    if not peut_consulter(request.user, tache):
        raise Http404
    return tache


class TachesIndexView(LoginRequiredMixin, View):
    def get(self, request):
        taches = list(taches_visibles(request.user).select_related("assigne"))
        ouvertes = [t for t in taches if t.ouverte]
        return render(request, "taches/index.html", {
            "mes_taches": [t for t in ouvertes if t.assigne_id == request.user.pk],
            "suivies": [t for t in ouvertes if t.assigne_id != request.user.pk],
            "terminees": sorted((t for t in taches if not t.ouverte), key=lambda t: t.terminee_le or t.updated_at, reverse=True)[:10],
            "marins": marins_assignables(request.user),
            "avancement": avancement_equipe(request.user),
            "aujourdhui": timezone.localdate(),
        })

    def post(self, request):
        # Sans marin désigné, la tâche est celle de l'utilisateur lui-même.
        assigne = User.objects.filter(pk=request.POST["assigne"]).first() if request.POST.get("assigne") else request.user
        echeance = parse_date(request.POST.get("echeance", ""))
        if assigne is None or echeance is None or not request.POST.get("titre", "").strip():
            messages.error(request, "Le titre, le marin et l'échéance sont obligatoires.")
            return redirect("taches-index")
        try:
            tache = creer_tache(
                request.user, assigne, request.POST["titre"], echeance, request.POST.get("description", ""),
                priorite=request.POST.get("priorite", Tache.PRIORITE_NORMALE), partagee=request.POST.get("partagee") == "on",
            )
        except (PermissionError, ValidationError) as exc:
            _erreurs(request, exc)
            return redirect("taches-index")
        messages.success(request, "Tâche créée." if tache.personnelle else "Tâche attribuée.")
        return redirect("tache-detail", pk=tache.pk)


class TacheDetailView(LoginRequiredMixin, View):
    def get(self, request, pk):
        tache = _tache_visible(request, pk)
        gerer = peut_gerer(request.user, tache)
        return render(request, "taches/detail.html", {
            "tache": tache,
            "commentaires": commentaires_de(tache),
            "participants": tache.participants.all(),
            "est_assigne": request.user.pk == tache.assigne_id,
            "peut_gerer": gerer,
            "interlocuteurs": interlocuteurs_possibles(tache) if gerer else [],
            "en_retard": tache.ouverte and tache.echeance < timezone.localdate(),
        })


class TacheActionView(LoginRequiredMixin, View):
    """Actions de suivi : démarrer, bloquer, rendre compte, lever le blocage, ajouter un interlocuteur."""

    def post(self, request, pk):
        tache = _tache_visible(request, pk)
        action = request.POST.get("action")
        try:
            if action == "demarrer":
                demarrer(tache, request.user)
            elif action == "bloquer":
                signaler_blocage(tache, request.user, request.POST.get("motif", ""))
            elif action == "rendre_compte":
                rendre_compte(tache, request.user, request.POST.get("compte_rendu", ""))
            elif action == "reprendre":
                reprendre(tache, request.user)
            elif action == "interlocuteur":
                cible = User.objects.filter(pk=request.POST.get("interlocuteur")).first()
                if cible is None:
                    raise ValidationError("Interlocuteur introuvable.")
                ajouter_participant(tache, request.user, cible)
            else:
                return HttpResponseBadRequest("Action inconnue.")
        except (PermissionError, ValidationError) as exc:
            _erreurs(request, exc)
        return redirect("tache-detail", pk=tache.pk)


class TacheCommentaireView(LoginRequiredMixin, View):
    """Réponse dans le fil : ouverte aux interlocuteurs, même à terre (cf. middleware)."""

    def post(self, request, pk):
        tache = _tache_visible(request, pk)
        try:
            repondre(tache, request.user, request.POST.get("body", ""))
        except (PermissionError, ValidationError) as exc:
            _erreurs(request, exc)
        return redirect("tache-detail", pk=tache.pk)
