from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.views import View

from .models import MouvementBatiment
from .mouvements import (
    MouvementImpossible,
    annuler_mouvement,
    declarer_mouvement,
    fonction_habilitee,
    regime_du_batiment,
)


def _instant(texte):
    valeur = parse_datetime((texte or "").strip())
    return timezone.make_aware(valeur) if valeur is not None and timezone.is_naive(valeur) else valeur


class MouvementsBatimentView(LoginRequiredMixin, View):
    """Accostage et appareillage du bâtiment de l'agent : consultation pour tous, déclaration réservée au COMAEQ et au commandant."""

    template_name = "quarts/mouvements.html"

    def _navire(self, request):
        profil = getattr(request.user, "profile", None)
        return profil.ship if profil is not None else None

    def get(self, request):
        ship = self._navire(request)
        if ship is None:
            raise PermissionDenied
        return render(request, self.template_name, {
            "ship": ship,
            "regime": regime_du_batiment(ship),
            "peut_declarer": fonction_habilitee(request.user, ship) is not None,
            "mouvements": MouvementBatiment.objects.filter(ship=ship).select_related("declare_par", "annule_par")[:30],
            "maintenant": timezone.localtime().strftime("%Y-%m-%dT%H:%M"),
        })

    def post(self, request):
        ship = self._navire(request)
        if ship is None or fonction_habilitee(request.user, ship) is None:
            raise PermissionDenied
        action = request.POST.get("action")
        try:
            if action == "declarer":
                instant = _instant(request.POST.get("survenu_le"))
                if instant is None or request.POST.get("type") not in dict(MouvementBatiment.TYPE_CHOICES):
                    raise MouvementImpossible("Le type et la date effective sont obligatoires.")
                declarer_mouvement(request.user, ship, request.POST["type"], instant)
                messages.success(request, "Mouvement enregistré.")
            elif action == "annuler":
                mouvement = get_object_or_404(MouvementBatiment, pk=request.POST.get("mouvement_id"), ship=ship)
                annuler_mouvement(request.user, mouvement, request.POST.get("motif", ""), _instant(request.POST.get("nouveau_survenu_le")))
                messages.success(request, "Déclaration annulée ; les alertes et la situation sont recalculées.")
            else:
                raise MouvementImpossible("Action inconnue.")
        except MouvementImpossible as exc:
            messages.error(request, str(exc))
        return redirect("mouvements-batiment")
