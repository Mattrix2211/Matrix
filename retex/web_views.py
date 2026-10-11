"""Interface web du RETEX : liste, proposition depuis une source, décision, actions et domaines."""
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ValidationError
from django.http import Http404, HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.dateparse import parse_date
from django.views import View

from annonces.services import chaine
from notifications.liens import lien_objet

from . import services
from .models import Retex

User = get_user_model()


def _erreurs(request, exc):
    if isinstance(exc, PermissionError):
        messages.error(request, str(exc))
    else:
        for liste in getattr(exc, "message_dict", {"": exc.messages}).values():
            for erreur in liste:
                messages.error(request, erreur)


def _retex(request, pk):
    retex = get_object_or_404(Retex.objects.select_related("domaine", "auteur", "decide_par", "document"), pk=pk)
    if not services.peut_consulter(request.user, retex):
        raise Http404
    return retex


class RetexIndexView(LoginRequiredMixin, View):
    def get(self, request):
        liste = services.retex_visibles(request.user)
        ship = chaine(request.user)[0]
        return render(request, "retex/index.html", {
            "a_examiner": [r for r in liste if r.etat == Retex.ETAT_PROPOSE and services.peut_valider(request.user, r)],
            "retex": liste,
            "peut_configurer": ship is not None and services.peut_valider(request.user, Retex(ship_id=ship)),
        })


class RetexNouveauView(LoginRequiredMixin, View):
    def _source(self, request, brut):
        modele, _, pk = (brut or "").partition(":")
        if not modele:
            return None
        source = services.source_de(modele, pk)
        if source is None or lien_objet(request.user, source) is None:
            raise Http404
        return source

    def get(self, request):
        ship = chaine(request.user)[0]
        if ship is None:
            raise Http404
        brut = request.GET.get("source", "")
        source = self._source(request, brut)
        return render(request, "retex/nouveau.html", {
            "domaines": services.domaines_du_navire(ship), "diffusions": Retex.DIFFUSION_CHOICES,
            "source": source, "source_ref": brut, "lien_source": lien_objet(request.user, source) if source else "",
            "constat_initial": getattr(source, "description", "") if source else "",
        })

    def post(self, request):
        brut = request.POST.get("source", "")
        try:
            retex = services.proposer(
                request.user, request.POST.get("titre", ""), request.POST.get("constat", ""), request.POST.get("enseignement", ""),
                request.POST.get("domaine"), request.POST.get("organisme", ""), request.POST.get("causes", ""),
                request.POST.get("recommandation", ""), request.POST.get("portee", ""), request.POST.get("diffusion", ""),
                self._source(request, brut))
        except (PermissionError, ValidationError) as exc:
            _erreurs(request, exc)
            return redirect(f"{request.path}?source={brut}" if brut else request.path)
        messages.success(request, "RETEX proposé : les habilités du bâtiment sont prévenus.")
        return redirect("retex-detail", pk=retex.pk)


class RetexDetailView(LoginRequiredMixin, View):
    def get(self, request, pk):
        retex = _retex(request, pk)
        decider = services.peut_valider(request.user, retex)
        return render(request, "retex/detail.html", {
            "retex": retex, "peut_decider": decider,
            "lien_source": lien_objet(request.user, retex.source) if retex.source else "",
            "actions": retex.taches.select_related("assigne"),
            "marins": User.objects.filter(profile__ship_id=retex.ship_id, is_active=True).order_by("username") if decider else [],
            "valideurs": services.valideurs(retex)[:5] if decider or request.user.pk == retex.auteur_id else [],
        })


class RetexActionView(LoginRequiredMixin, View):
    def post(self, request, pk):
        retex = _retex(request, pk)
        action = request.POST.get("action")
        try:
            if action == "valider":
                services.valider(request.user, retex, request.POST.get("motif", ""))
                messages.success(request, "RETEX validé et publié dans la documentation.")
            elif action == "refuser":
                services.refuser(request.user, retex, request.POST.get("motif", ""))
            elif action == "clore":
                services.clore(request.user, retex)
            elif action == "creer_action":
                assigne = User.objects.filter(pk=request.POST.get("assigne") or None).first()
                if assigne is None:
                    raise ValidationError("Indiquez le marin responsable de l'action.")
                saisie = (request.POST.get("echeance") or "").strip()
                echeance = parse_date(saisie) if saisie else None
                if saisie and echeance is None:
                    raise ValidationError("Indiquez une échéance valide (ou aucune).")
                services.creer_action(request.user, retex, assigne, request.POST.get("titre", ""), echeance)
                messages.success(request, "Action assignée.")
            else:
                return HttpResponseBadRequest("Action inconnue.")
        except (PermissionError, ValidationError) as exc:
            _erreurs(request, exc)
        return redirect("retex-detail", pk=retex.pk)


class DomainesView(LoginRequiredMixin, View):
    def get(self, request):
        ship = chaine(request.user)[0]
        if ship is None or not services.peut_valider(request.user, Retex(ship_id=ship)):
            raise Http404
        return render(request, "retex/domaines.html", {"domaines": services.domaines_du_navire(ship, seulement_actifs=False)})

    def post(self, request):
        try:
            services.ajouter_domaine(request.user, request.POST.get("nom", ""), request.POST.get("coma", ""), request.POST.get("organisme", ""))
        except (PermissionError, ValidationError) as exc:
            _erreurs(request, exc)
        return redirect("retex-domaines")
