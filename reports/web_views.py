"""Vue web du bilan PDF (T10) — bouton "Générer le bilan" du tableau de bord.

Pas de sélection de périmètre par l'utilisateur (pas de drill-down, décision
validée sur T8) : le périmètre est déterminé automatiquement à partir du
profil de l'utilisateur connecté (`profile.scope`), identique à celui déjà
utilisé par `scope_filters_for_user`.
"""
from datetime import date

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse
from django.shortcuts import redirect
from django.utils import timezone
from django.views import View

from matrix.core.roles import RoleLevel, user_role_level

from .services import (
    PerimetreNonAutorise,
    generer_bilan_instantane_pdf,
    generer_bilan_periode_pdf,
)


class GenererBilanView(LoginRequiredMixin, View):
    """Génère et renvoie en téléchargement le bilan PDF du périmètre propre de
    l'utilisateur connecté.

    - Sans `date_debut`/`date_fin` : Mode Instantané (photo de l'état actuel).
    - Avec `date_debut` et `date_fin` (format AAAA-MM-JJ) : Mode Période.
    """

    def get(self, request):
        if user_role_level(request.user) < RoleLevel.CHEF_SECTION:
            raise PermissionDenied

        profile = getattr(request.user, "profile", None)
        # UserProfile.scope renvoie (None, None) — et non None — quand aucun
        # périmètre n'est affecté (voir accounts/models.py) : on teste le premier
        # élément du tuple, pas juste sa présence.
        scope = profile.scope if profile else (None, None)
        scope_type, scope_id = scope
        if not scope_type:
            messages.error(
                request,
                "Aucun périmètre (secteur ou section) n'est associé à votre profil : "
                "impossible de générer un bilan.",
            )
            return redirect("home")

        date_debut_str = request.GET.get("date_debut")
        date_fin_str = request.GET.get("date_fin")

        try:
            if date_debut_str and date_fin_str:
                try:
                    date_debut = date.fromisoformat(date_debut_str)
                    date_fin = date.fromisoformat(date_fin_str)
                except ValueError:
                    messages.error(request, "Dates invalides (format attendu : AAAA-MM-JJ).")
                    return redirect("home")
                pdf_bytes = generer_bilan_periode_pdf(
                    scope_type, scope_id, request.user, date_debut, date_fin
                )
                nom_fichier = f"bilan_{scope_type}_{date_debut}_{date_fin}.pdf"
            else:
                pdf_bytes = generer_bilan_instantane_pdf(scope_type, scope_id, request.user)
                nom_fichier = f"bilan_{scope_type}_{timezone.localdate()}.pdf"
        except PerimetreNonAutorise:
            messages.error(
                request, "Vous n'êtes pas autorisé à générer le bilan de ce périmètre."
            )
            return redirect("home")
        except ValueError as exc:
            # Ex : date de début postérieure à la date de fin (voir services.py).
            messages.error(request, str(exc))
            return redirect("home")

        response = HttpResponse(pdf_bytes, content_type="application/pdf")
        response["Content-Disposition"] = f"attachment; filename={nom_fichier}"
        return response
