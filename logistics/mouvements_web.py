"""Fiche d'une pièce en stock : historique des mouvements et saisie manuelle (entrée, inventaire, correction)."""
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.shortcuts import redirect, render
from django.views import View

from matrix.core.mixins import build_scope_q
from matrix.core.role_thresholds import niveau_requis_pour
from matrix.core.roles import niveau_ecriture

from .models import MouvementStock, StockPiece
from .stock import MotifRequis, StockInsuffisant, enregistrer_mouvement

TYPES_MANUELS = (MouvementStock.ENTREE, MouvementStock.INVENTAIRE, MouvementStock.CORRECTION)


def _quantite_saisie(type_mouvement, brut):
    """Quantité saisie validée selon le type, ou None si elle est invalide."""
    try:
        quantite = int(brut)
    except (TypeError, ValueError):
        return None
    if type_mouvement == MouvementStock.ENTREE:
        return quantite if quantite > 0 else None
    if type_mouvement == MouvementStock.INVENTAIRE:
        return quantite if quantite >= 0 else None
    return quantite if quantite != 0 else None


class StockPieceMouvementsView(LoginRequiredMixin, View):
    template_name = "logistics/stock_mouvements.html"

    def _piece(self, request, pk):
        piece = StockPiece.objects.select_related("ship", "sector").filter(build_scope_q(request.user, ""), pk=pk).first()
        if piece is None:
            raise Http404
        return piece

    def get(self, request, pk):
        piece = self._piece(request, pk)
        mouvements = piece.mouvements.select_related("auteur", "ticket").order_by("-created_at", "-pk")
        jauge = min(round(piece.quantite / piece.quantite_minimale * 100), 100) if piece.quantite_minimale else 100
        return render(request, self.template_name, {
            "piece": piece, "mouvements": mouvements, "jauge_pct": jauge,
            "peut_gerer": niveau_ecriture(request.user) >= niveau_requis_pour(request.user, "stock_ecriture"),
        })

    def post(self, request, pk):
        if niveau_ecriture(request.user) < niveau_requis_pour(request.user, "stock_ecriture"):
            raise PermissionDenied
        piece = self._piece(request, pk)
        type_mouvement = request.POST.get("type")
        quantite = _quantite_saisie(type_mouvement, request.POST.get("quantite"))
        if type_mouvement not in TYPES_MANUELS:
            messages.error(request, "Type de mouvement inconnu.")
        elif quantite is None:
            messages.error(request, "Quantité invalide : entier positif pour une entrée, effectif compté (0 ou plus) pour un "
                                    "inventaire, variation non nulle pour une correction.")
        else:
            try:
                mouvement = enregistrer_mouvement(request.user, piece, type_mouvement, quantite, motif=request.POST.get("motif", ""))
            except MotifRequis:
                messages.error(request, "Le motif est obligatoire pour un inventaire ou une correction.")
            except StockInsuffisant as exc:
                messages.error(request, f"Stock insuffisant : {exc.disponible} unité(s) disponible(s) pour {exc.reference}, "
                                        "la correction rendrait le stock négatif.")
            else:
                messages.success(request, f"{mouvement.get_type_display()} enregistré : stock de {piece.reference} = {mouvement.solde_apres}.")
        return redirect("stock-piece-mouvements", pk=piece.pk)
