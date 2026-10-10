"""Échanges de tours de service (quarts/web_views.py).

Sous-domaine extrait lors du découpage du fichier (tâche Notion « [ARCH]
Découper quarts/web_views.py (1086 lignes) par sous-domaine »,
quarts/web_views.py ayant dépassé 800 lignes) : un marin propose l'échange
de son tour contre celui d'un collègue sur une même liste de garde ; le
collègue accepte ou refuse, puis le chef de liste valide ou rejette (cf.
quarts/echanges.py pour le détail du workflow).

Refactor pur : reproduit exactement le comportement d'origine. La fonction
_peut_lire_liste reste partagée avec quarts/listes_views.py (voir
quarts/web_views.py, import circulaire volontaire déjà en place pour
dashboard/web_views.py avant ce découpage)."""
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponseBadRequest
from django.shortcuts import redirect, render
from django.views import View

from .echanges import (
    EchangeImpossible,
    accepter_echange,
    annuler_echange,
    peut_valider_echange,
    proposer_echange,
    refuser_echange,
    rejeter_echange,
    valider_echange,
)
from .models import EchangeService, ServiceGarde
from .web_views import _peut_lire_liste


def _afficher_problemes(request, exc):
    for probleme in exc.problemes:
        messages.error(request, probleme)


class ProposerEchangeView(LoginRequiredMixin, View):
    """Demande d'échange lancée depuis un tour de la fiche d'une liste de
    gardes : le marin choisit le tour d'un collègue (une seule étape)."""

    def post(self, request, pk):
        liste = ServiceGarde.objects.filter(pk=pk).first()
        if liste is None or not _peut_lire_liste(request.user, liste):
            return HttpResponseBadRequest("Liste introuvable ou hors de votre périmètre.")
        mon_tour = liste.creneaux.filter(pk=request.POST.get("creneau_id")).first()
        son_tour = liste.creneaux.filter(pk=request.POST.get("cible_creneau_id")).first()
        if mon_tour is None or son_tour is None:
            messages.error(request, "Choisissez votre tour et le tour contre lequel l'échanger.")
            return redirect("garde-detail", pk=liste.pk)
        try:
            echange = proposer_echange(request.user, mon_tour, son_tour, request.POST.get("motif", ""))
        except EchangeImpossible as exc:
            _afficher_problemes(request, exc)
            return redirect("garde-detail", pk=liste.pk)
        messages.success(request, f"Demande envoyée à {echange.cible.get_full_name() or echange.cible.username}.")
        return redirect("echanges-index")


def _echanges_visibles(user):
    """Un marin ne voit que ses propres demandes ; un chef de liste voit en
    plus celles des listes qu'il gère."""
    echanges = EchangeService.objects.select_related(
        "demandeur", "cible", "decide_par", "creneau_demandeur__service_garde", "creneau_cible__service_garde"
    ).prefetch_related("evenements__acteur")
    return [
        e for e in echanges
        if user.pk in (e.demandeur_id, e.cible_id) or peut_valider_echange(user, e)
    ]


def _etapes(echange):
    """Frise de progression d'un échange (composant visuel) : chaque étape est
    « fait », « courant », « echec » ou « vide »."""
    libelles = ("Demande envoyée", "Accord du marin", "Validation du chef", "Échange effectué")
    # (nombre d'étapes faites, étape en échec ou None) selon le statut
    faites, echec = {
        echange.STATUT_DEMANDE: (1, None),
        echange.STATUT_ACCEPTE: (2, None),
        echange.STATUT_VALIDE: (4, None),
        echange.STATUT_REFUSE: (1, 1),
        echange.STATUT_REJETE: (2, 2),
        echange.STATUT_ANNULE: (1, 1 if not echange.accepte_le else 2),
    }[echange.statut]
    etapes = []
    for i, libelle in enumerate(libelles):
        if i < faites:
            etat = "fait"
        elif echec is not None and i == echec:
            etat = "echec"
        elif echec is None and i == faites:
            etat = "courant"
        else:
            etat = "vide"
        etapes.append({"libelle": libelle, "etat": etat})
    return etapes


def _grouper_echanges(echanges, user):
    """Annote chaque échange des actions possibles pour `user` et les range en
    « à traiter », « en cours » et « terminés »."""
    for e in echanges:
        e.peut_repondre = e.statut == e.STATUT_DEMANDE and e.cible_id == user.pk
        e.peut_annuler = e.en_cours and e.demandeur_id == user.pk
        e.peut_trancher = e.statut == e.STATUT_ACCEPTE and peut_valider_echange(user, e)
        e.etapes = _etapes(e)
    return {
        "a_traiter": [e for e in echanges if e.peut_repondre or e.peut_trancher],
        "en_cours": [e for e in echanges if e.en_cours and not (e.peut_repondre or e.peut_trancher)],
        "termines": [e for e in echanges if not e.en_cours],
    }


class EchangesIndexView(LoginRequiredMixin, View):
    template_name = "quarts/echanges.html"

    def get(self, request):
        return render(request, self.template_name, _grouper_echanges(_echanges_visibles(request.user), request.user))


class EchangeActionView(LoginRequiredMixin, View):
    """Actions du workflow sur un échange : accepter/refuser (marin sollicité),
    annuler (demandeur), valider/rejeter (chef de liste)."""

    ACTIONS = {
        "accepter": (accepter_echange, False, "Échange accepté : le chef de liste a été prévenu."),
        "refuser": (refuser_echange, True, "Échange refusé."),
        "annuler": (annuler_echange, True, "Demande annulée."),
        "valider": (valider_echange, False, "Échange validé : les deux calendriers sont à jour."),
        "rejeter": (rejeter_echange, True, "Échange refusé : les tours restent inchangés."),
    }

    def post(self, request, pk, action):
        echange = next((e for e in _echanges_visibles(request.user) if e.pk == pk), None)
        if echange is None or action not in self.ACTIONS:
            return HttpResponseBadRequest("Échange introuvable ou hors de votre périmètre.")
        fonction, avec_motif, succes = self.ACTIONS[action]
        try:
            if avec_motif:
                fonction(echange, request.user, request.POST.get("motif", ""))
            else:
                fonction(echange, request.user)
        except EchangeImpossible as exc:
            _afficher_problemes(request, exc)
        else:
            messages.success(request, succes)
        return redirect("echanges-index")
