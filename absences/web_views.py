"""Interface web du module Absences (Phase 2, VISION §7) : un marin déclare
sa propre absence, un chef (CHEF_SECTION+) déclare/valide celles de son
périmètre. Écran volontairement minimal (une seule page) : le modèle est
avant tout consommé par quarts/echanges.py (analyser_echange) et le
calendrier personnel (calendar_app), pas pensé comme un module autonome
riche pour cette première itération (cf. docstring de absences/models.py)."""
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ValidationError
from django.http import HttpResponseBadRequest
from django.shortcuts import redirect, render
from django.utils.dateparse import parse_date
from django.views import View

from accounts.models import TypeAbsence
from matrix.core.roles import RoleLevel, user_role_level

from .models import Absence
from .services import (
    absences_visibles,
    declarer_absence,
    marins_de_mon_perimetre,
    peut_valider_absence,
    valider_absence,
)

User = get_user_model()


class MesAbsencesView(LoginRequiredMixin, View):
    template_name = "absences/index.html"

    def get(self, request):
        return render(request, self.template_name, self._contexte(request))

    def _contexte(self, request):
        absences = list(
            absences_visibles(request.user)
            .select_related("marin", "type_absence", "validee_par")
            .order_by("-date_debut")
        )
        for absence in absences:
            absence.peut_valider = peut_valider_absence(request.user, absence)
        chef = user_role_level(request.user) >= RoleLevel.CHEF_SECTION
        return {
            "mes_absences": [a for a in absences if a.marin_id == request.user.pk],
            "absences_equipe": [a for a in absences if a.marin_id != request.user.pk],
            "types_absence": TypeAbsence.objects.filter(active=True).order_by("name"),
            "marins_perimetre": marins_de_mon_perimetre(request.user) if chef else User.objects.none(),
            "peut_declarer_pour_autrui": chef,
        }

    def post(self, request):
        action = request.POST.get("action")
        if action == "declarer":
            return self._declarer(request)
        if action == "valider":
            return self._valider(request)
        return HttpResponseBadRequest("Action inconnue.")

    def _declarer(self, request):
        marin = User.objects.filter(pk=request.POST.get("marin_id") or request.user.pk).first()
        type_absence = TypeAbsence.objects.filter(pk=request.POST.get("type_absence"), active=True).first()
        date_debut = parse_date(request.POST.get("date_debut", ""))
        date_fin = parse_date(request.POST.get("date_fin", ""))
        if marin is None or type_absence is None or not date_debut or not date_fin:
            messages.error(request, "Le marin, le type et la période (début et fin) sont obligatoires.")
            return redirect("absences-index")
        try:
            declarer_absence(
                request.user, marin, type_absence, date_debut, date_fin,
                motif=request.POST.get("motif", ""),
            )
        except PermissionError:
            messages.error(request, "Vous ne pouvez pas déclarer d'absence pour ce marin.")
        except ValidationError as exc:
            for erreurs in exc.message_dict.values():
                for erreur in erreurs:
                    messages.error(request, erreur)
        else:
            messages.success(request, "Absence enregistrée.")
        return redirect("absences-index")

    def _valider(self, request):
        absence = Absence.objects.filter(pk=request.POST.get("absence_id")).first()
        if absence is None:
            messages.error(request, "Absence introuvable.")
            return redirect("absences-index")
        try:
            valider_absence(absence, request.user)
        except PermissionError:
            messages.error(request, "Vous ne pouvez pas valider cette absence.")
        else:
            messages.success(request, "Absence validée.")
        return redirect("absences-index")
