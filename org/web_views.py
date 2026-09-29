"""Page web « Équipages » : configuration du double équipage et relève à bord /
à terre (FREMM, PSP, BSAM). Réservée aux rôles atteignant le seuil configurable
« equipage_gestion » (COMMANDANT et ADMIN_NAVIRE par défaut)."""
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View

from matrix.core.scopes import is_master_admin, ship_id_for_user

from . import equipages
from .equipages import peut_gerer_equipages
from .models import Ship, SynthesePassation


def _syntheses_visibles(user):
    """Synthèses des bâtiments dont l'utilisateur est membre (tous les membres,
    équipage à bord ou à terre) ; toutes pour l'administrateur général."""
    syntheses = SynthesePassation.objects.select_related("ship", "equipage_montant", "equipage_descendant")
    if is_master_admin(user):
        return syntheses
    return syntheses.filter(ship_id=ship_id_for_user(user))


class PassationsView(LoginRequiredMixin, View):
    """Liste des synthèses de passation, ouverte à tous les membres du navire."""

    def get(self, request):
        return render(request, "org/passations.html", {"syntheses": _syntheses_visibles(request.user)})


class PassationDetailView(LoginRequiredMixin, View):
    def get(self, request, pk):
        synthese = get_object_or_404(_syntheses_visibles(request.user), pk=pk)
        return render(request, "org/passation_detail.html", {"synthese": synthese, "c": synthese.contenu})


class EquipagesView(LoginRequiredMixin, View):
    template_name = "org/equipages.html"

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated and not peut_gerer_equipages(request.user):
            return HttpResponseForbidden()
        return super().dispatch(request, *args, **kwargs)

    def _navire(self, request, source):
        if is_master_admin(request.user):
            return Ship.objects.filter(pk=source.get("ship") or source.get("ship_id") or 0).first()
        return Ship.objects.filter(pk=ship_id_for_user(request.user)).first()

    def get(self, request):
        ship = self._navire(request, request.GET)
        contexte = equipages.contexte_page(ship)
        if is_master_admin(request.user):
            contexte["ships"] = Ship.objects.filter(archived=False).order_by("name")
        return render(request, self.template_name, contexte)

    def post(self, request):
        action = request.POST.get("action")
        ship = self._navire(request, request.POST)
        if action not in equipages.ACTIONS:
            return HttpResponseForbidden()
        equipages.traiter_action(request, action)
        suite = f"?ship={ship.pk}" if ship and is_master_admin(request.user) else ""
        return redirect(f"/equipages/{suite}")
