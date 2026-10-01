"""Page « Organisation d'alerte » d'un navire (scénarios sécurité / protection-défense
et postes exprimés en fonctions de service). Toute modification passe par
quarts/alertes.py : validée directement si l'auteur est l'autorité configurée,
sinon proposée et notifiée à cette autorité."""
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.http import HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views import View

from matrix.core.saisie import entier_ou_none
from org.models import CommandantAdjoint

from .alertes import (
    peut_proposer_organisation_alerte,
    peut_valider_organisation_alerte,
    proposer_modification,
    refuser,
    valider,
)
from .feuille_service_views import _navires_disponibles_feuille_service
from .models import FonctionFeuilleService, ModificationOrganisationAlerte as Modification, ScenarioAlerte

LIGNES_VIDES = 3


class OrganisationAlerteView(LoginRequiredMixin, View):
    template_name = "quarts/organisation_alerte.html"

    def _ship(self, request):
        pk = request.GET.get("ship") or request.POST.get("ship")
        return get_object_or_404(_navires_disponibles_feuille_service(request.user), pk=pk)

    def get(self, request):
        ship = self._ship(request)
        peut_valider = peut_valider_organisation_alerte(request.user, ship)
        peut_proposer = peut_proposer_organisation_alerte(request.user, ship)
        if not (peut_valider or peut_proposer):
            raise PermissionDenied
        modifications = ship.modifications_alerte.select_related("proposee_par", "decidee_par", "scenario")
        return render(request, self.template_name, {
            "ship": ship,
            "navires": _navires_disponibles_feuille_service(request.user),
            "scenarios": ship.scenarios_alerte.prefetch_related("postes"),
            "fonctions": FonctionFeuilleService.objects.filter(ship=ship, actif=True),
            "familles": ScenarioAlerte.FAMILLE_CHOICES,
            "sigles": CommandantAdjoint.Sigle.choices,
            "lignes_vides": range(LIGNES_VIDES),
            "en_attente": modifications.filter(statut=Modification.STATUT_EN_ATTENTE),
            "historique": modifications.exclude(statut=Modification.STATUT_EN_ATTENTE)[:15],
            "peut_valider": peut_valider,
            "peut_proposer": peut_proposer,
        })

    def _lire_formulaire(self, request):
        """Définition du scénario saisie : une ligne vide de poste est ignorée."""
        post = request.POST
        postes = []
        for libelle, fonction, obligatoire in zip(
            post.getlist("poste_libelle"), post.getlist("poste_fonction"), post.getlist("poste_obligatoire"),
        ):
            if libelle.strip():
                postes.append({
                    "libelle": libelle.strip(), "fonction_id": entier_ou_none(fonction),
                    "obligatoire": obligatoire != "0", "ordre": len(postes),
                })
        return {
            "libelle": post.get("libelle", "").strip(), "famille": post.get("famille", ""),
            "adjoint_sigle": post.get("adjoint_sigle", ""), "ordre": entier_ou_none(post.get("ordre")) or 0,
            "actif": "actif" in post, "postes": postes,
        }

    def post(self, request):
        ship = self._ship(request)
        action = request.POST.get("action")
        retour = redirect(f"{reverse('feuille-service-alertes')}?ship={ship.pk}")
        if action in ("valider", "refuser"):
            if not peut_valider_organisation_alerte(request.user, ship):
                raise PermissionDenied
            modification = get_object_or_404(
                Modification, pk=entier_ou_none(request.POST.get("pk")) or 0, ship=ship,
                statut=Modification.STATUT_EN_ATTENTE,
            )
            if action == "valider":
                erreur = valider(modification, request.user)
                if erreur:
                    messages.error(request, erreur)
                else:
                    messages.success(request, "Modification validée et appliquée.")
                return retour
            motif = request.POST.get("motif", "").strip()
            if not motif:
                messages.error(request, "Un motif est obligatoire pour refuser une modification.")
            else:
                refuser(modification, request.user, motif)
                messages.info(request, "Modification refusée.")
            return retour

        if action not in ("enregistrer", "supprimer"):
            return HttpResponseBadRequest("Action inconnue.")
        if not peut_proposer_organisation_alerte(request.user, ship):
            raise PermissionDenied
        scenario = None
        if request.POST.get("scenario_id"):
            scenario = get_object_or_404(ship.scenarios_alerte, pk=entier_ou_none(request.POST["scenario_id"]) or 0)
        if action == "supprimer":
            if scenario is None:
                return HttpResponseBadRequest("Scénario introuvable.")
            modification, erreur = proposer_modification(
                request.user, ship, Modification.ACTION_SUPPRIMER, scenario=scenario,
            )
        else:
            modification, erreur = proposer_modification(
                request.user, ship,
                Modification.ACTION_MODIFIER if scenario else Modification.ACTION_CREER,
                self._lire_formulaire(request), scenario,
            )
        if erreur:
            messages.error(request, erreur)
        elif modification.statut == Modification.STATUT_VALIDEE:
            messages.success(request, "Organisation d'alerte mise à jour.")
        else:
            messages.info(request, "Modification proposée : elle s'appliquera une fois validée par l'autorité du bord.")
        return retour
