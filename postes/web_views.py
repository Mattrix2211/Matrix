"""Interface web des postes du bord : tableau d'effectifs, création, fiche (formations exigées, titulaires)."""
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ValidationError
from django.http import Http404, HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View

from annonces.services import cibles_autorisees
from matrix.core.saisie import entier_ou_none
from training.models import TrainingCourse

from . import services
from .models import Poste

User = get_user_model()


def _erreurs(request, exc):
    if isinstance(exc, PermissionError):
        messages.error(request, str(exc))
    else:
        for liste in getattr(exc, "message_dict", {"": exc.messages}).values():
            for erreur in liste:
                messages.error(request, erreur)


class PostesIndexView(LoginRequiredMixin, View):
    def get(self, request):
        lignes = services.tableau_effectifs(request.user)
        return render(request, "postes/index.html", {
            "lignes": lignes, "peut_gerer": services.peut_gerer(request.user),
            "total_non_pourvus": sum(l["non_pourvu"] for l in lignes),
            "total_sous_qualifies": sum(l["sous_qualifies"] for l in lignes),
        })


class PosteNouveauView(LoginRequiredMixin, View):
    def get(self, request):
        if not services.peut_gerer(request.user):
            raise Http404
        return render(request, "postes/nouveau.html", {
            "cibles": cibles_autorisees(request.user), "formations": TrainingCourse.objects.order_by("title")})

    def post(self, request):
        effectif = entier_ou_none(request.POST.get("effectif") or 1)
        if effectif is None:
            messages.error(request, "L'effectif doit être un nombre entier.")
            return redirect("poste-nouveau")
        try:
            poste = services.creer_poste(
                request.user, request.POST.get("intitule", ""), request.POST.get("cible", ""),
                effectif, request.POST.get("equipage", ""), request.POST.getlist("formations"))
        except (PermissionError, ValidationError) as exc:
            _erreurs(request, exc)
            return redirect("poste-nouveau")
        messages.success(request, "Poste créé.")
        return redirect("poste-detail", pk=poste.pk)


class PosteDetailView(LoginRequiredMixin, View):
    def _poste(self, request, pk):
        poste = get_object_or_404(Poste.objects.select_related("ship", "service", "sector", "section"), pk=pk)
        if not services.postes_visibles(request.user).filter(pk=pk).exists():
            raise Http404
        return poste

    def get(self, request, pk):
        poste = self._poste(request, pk)
        gerer = services.peut_gerer_poste(request.user, poste)
        ligne = next(l for l in services.tableau_effectifs(request.user) if l["poste"].pk == poste.pk)
        return render(request, "postes/detail.html", {
            "poste": poste, "ligne": ligne, "peut_gerer": gerer,
            "formations": TrainingCourse.objects.order_by("title") if gerer else [],
            "exigees": set(poste.formations.values_list("pk", flat=True)),
            "candidats": User.objects.filter(profile__ship_id=poste.ship_id, is_active=True).exclude(
                affectations_poste__poste=poste).order_by("username") if gerer else [],
        })

    def post(self, request, pk):
        poste = self._poste(request, pk)
        action = request.POST.get("action")
        try:
            if action == "affecter":
                marin = User.objects.filter(pk=request.POST.get("marin") or None).first()
                if marin is None:
                    raise ValidationError("Marin introuvable.")
                services.affecter(request.user, poste, marin)
            elif action == "retirer":
                services.retirer(request.user, poste, get_object_or_404(User, pk=request.POST.get("marin")))
            elif action == "formations":
                services.modifier_formations(request.user, poste, request.POST.getlist("formations"))
            else:
                return HttpResponseBadRequest("Action inconnue.")
        except (PermissionError, ValidationError) as exc:
            _erreurs(request, exc)
        return redirect("poste-detail", pk=poste.pk)
