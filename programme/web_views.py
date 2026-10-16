"""Interface web du programme du bâtiment : liste, saisie, fiche et réglages (délégations, types)."""
from datetime import datetime, timedelta

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ValidationError
from django.http import Http404, HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views import View

from annonces.services import cibles_autorisees
from matrix.core.saisie import entier_ou_none
from taches.services import taches_visibles

from . import services
from .models import DelegationProgramme, EvenementProgramme

User = get_user_model()
JOURS_PASSES = 7


def _erreurs(request, exc):
    if isinstance(exc, PermissionError):
        messages.error(request, str(exc))
    else:
        for liste in getattr(exc, "message_dict", {"": exc.messages}).values():
            for erreur in liste:
                messages.error(request, erreur)


def _horodatage(saisie):
    """datetime-local (AAAA-MM-JJTHH:MM) en datetime avec fuseau, ou None si vide."""
    saisie = (saisie or "").strip()
    if not saisie:
        return None
    try:
        return timezone.make_aware(datetime.strptime(saisie, "%Y-%m-%dT%H:%M"))
    except ValueError:
        raise ValidationError("Indiquez une date et une heure valides.")


def _evenement(request, pk):
    evenement = get_object_or_404(EvenementProgramme.objects.select_related("type", "auteur", "ship", "service", "sector", "section"), pk=pk)
    if not services.evenements_visibles(request.user).filter(pk=pk).exists():
        raise Http404
    return evenement


class ProgrammeIndexView(LoginRequiredMixin, View):
    def get(self, request):
        depuis = timezone.now() - timedelta(days=JOURS_PASSES)
        evenements = list(services.evenements_visibles(request.user).filter(debut__gte=depuis).select_related("type", "auteur"))
        maintenant = timezone.now()
        return render(request, "programme/index.html", {
            "a_venir": [e for e in evenements if e.debut >= maintenant or (e.fin and e.fin >= maintenant)],
            "recents": [e for e in evenements if not (e.debut >= maintenant or (e.fin and e.fin >= maintenant))],
            "peut_saisir": services.peut_saisir(request.user),
            "peut_regler": services.peut_deleguer(request.user) or services.peut_configurer_types(request.user),
        })


class EvenementNouveauView(LoginRequiredMixin, View):
    def _contexte(self, request):
        navire = services.chaine(request.user)[0]
        return {"types": services.types_du_navire(navire), "cibles": cibles_autorisees(request.user)}

    def get(self, request):
        if not services.peut_saisir(request.user):
            raise Http404
        return render(request, "programme/nouveau.html", self._contexte(request))

    def post(self, request):
        try:
            evenement = services.creer_evenement(
                request.user, request.POST.get("titre", ""), request.POST.get("type") or None,
                _horodatage(request.POST.get("debut")), _horodatage(request.POST.get("fin")),
                request.POST.get("cible", ""), request.POST.get("lieu", ""), request.POST.get("description", ""),
                request.POST.get("equipage", ""),
            )
        except (PermissionError, ValidationError) as exc:
            _erreurs(request, exc)
            return redirect("evenement-nouveau")
        messages.success(request, "Événement ajouté au programme.")
        return redirect("evenement-detail", pk=evenement.pk)


class EvenementDetailView(LoginRequiredMixin, View):
    def get(self, request, pk):
        evenement = _evenement(request, pk)
        gerer = services.peut_gerer(request.user, evenement)
        deja = evenement.taches.values_list("pk", flat=True)
        return render(request, "programme/detail.html", {
            "evenement": evenement, "peut_gerer": gerer,
            "taches": evenement.taches.filter(pk__in=taches_visibles(request.user).values("pk")).select_related("assigne"),
            "taches_liables": taches_visibles(request.user).exclude(pk__in=deja).filter(statut__in=("A_FAIRE", "EN_COURS", "BLOQUEE"))[:50] if gerer else [],
            "debut_saisie": timezone.localtime(evenement.debut).strftime("%Y-%m-%dT%H:%M"),
            "fin_saisie": timezone.localtime(evenement.fin).strftime("%Y-%m-%dT%H:%M") if evenement.fin else "",
        })


class EvenementActionView(LoginRequiredMixin, View):
    def post(self, request, pk):
        evenement = _evenement(request, pk)
        action = request.POST.get("action")
        try:
            if action == "modifier":
                services.modifier_evenement(
                    request.user, evenement, request.POST.get("titre", ""), _horodatage(request.POST.get("debut")),
                    _horodatage(request.POST.get("fin")), request.POST.get("lieu", ""), request.POST.get("description", ""))
                messages.success(request, "Événement mis à jour.")
            elif action == "annuler":
                services.annuler_evenement(request.user, evenement)
                messages.success(request, "Événement annulé : le public visé est prévenu.")
            elif action == "lier_tache":
                services.lier_tache(request.user, evenement, request.POST.get("tache"))
            else:
                return HttpResponseBadRequest("Action inconnue.")
        except (PermissionError, ValidationError) as exc:
            _erreurs(request, exc)
        return redirect("evenement-detail", pk=evenement.pk)


class ProgrammeReglagesView(LoginRequiredMixin, View):
    """Délégations de saisie (état-major) et types d'événements (administrateur du bâtiment)."""

    def _navire(self, request):
        return services.chaine(request.user)[0]

    def get(self, request):
        deleguer, types = services.peut_deleguer(request.user), services.peut_configurer_types(request.user)
        if not (deleguer or types):
            raise Http404
        navire = self._navire(request)
        delegues = DelegationProgramme.objects.filter(ship_id=navire).select_related("user")
        return render(request, "programme/reglages.html", {
            "peut_deleguer": deleguer, "peut_types": types, "delegations": delegues,
            "candidats": User.objects.filter(profile__ship_id=navire, is_active=True).exclude(
                pk__in=delegues.values_list("user_id", flat=True)).order_by("username") if deleguer else [],
            "types": services.types_du_navire(navire, seulement_actifs=False) if types else [],
        })

    def post(self, request):
        action = request.POST.get("action")
        try:
            if action == "deleguer":
                cible = User.objects.filter(pk=entier_ou_none(request.POST.get("user"))).first()
                if cible is None:
                    raise ValidationError("Marin introuvable.")
                services.deleguer(request.user, cible)
            elif action == "retirer":
                services.retirer_delegation(request.user, request.POST.get("delegation"))
            elif action == "type_ajouter":
                services.ajouter_type(request.user, request.POST.get("nom", ""), request.POST.get("couleur", ""))
            elif action == "type_basculer":
                services.basculer_type(request.user, request.POST.get("type"))
            else:
                return HttpResponseBadRequest("Action inconnue.")
        except (PermissionError, ValidationError) as exc:
            _erreurs(request, exc)
        return redirect("programme-reglages")
