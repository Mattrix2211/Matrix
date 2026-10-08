"""Historique d'un équipement : frise des comptes rendus et séries de relevés, en lecture pour tout le périmètre."""
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.paginator import Paginator
from django.http import Http404
from django.shortcuts import render
from django.urls import reverse
from django.views import View

from assets.models import Asset, Installation
from matrix.core.mixins import build_scope_q

from . import historique

PAR_PAGE = 20
LONGUEUR_GAMME = 255


class HistoriqueEquipementView(LoginRequiredMixin, View):
    """Frise chronologique (filtrable par gamme) et relevés (tableau et graphique de tendance) d'un équipement."""
    template_name = "maintenance/historique.html"
    materiel = False

    def get(self, request, pk):
        modele = Asset if self.materiel else Installation
        equipement = modele.objects.filter(build_scope_q(request.user, "")).filter(pk=pk).first()
        if equipement is None:
            raise Http404("Équipement introuvable")
        installation, asset = (None, equipement) if self.materiel else (equipement, None)
        gamme = request.GET.get("gamme", "").replace("\x00", "")[:LONGUEUR_GAMME]
        anomalies = request.GET.get("anomalies") == "1"
        vue = "releves" if request.GET.get("vue") == "releves" else "frise"
        sources = historique.sources_de(installation, asset)
        contexte = {
            "equipement": equipement, "materiel": self.materiel, "vue": vue, "gamme": gamme,
            "gammes": historique.gammes_de(sources), "anomalies": anomalies,
            "retour_url": reverse("asset-detail" if self.materiel else "installation-detail", args=[equipement.pk]),
            "nouveau_correctif_url": f"{reverse('correctif-nouveau')}?{'asset' if self.materiel else 'installation'}={equipement.pk}",
        }
        if vue == "frise":
            page = Paginator(historique.frise(sources, request.user, gamme, anomalies), PAR_PAGE).get_page(request.GET.get("page"))
            contexte.update(page=page, entrees=page.object_list)
        else:
            contexte["series"] = [s for s in historique.series(sources) if not gamme or s["gamme"] == gamme]
        return render(request, self.template_name, contexte)
