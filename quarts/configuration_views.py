"""Écran de configuration des délais d'alerte d'activation d'un bâtiment."""
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.shortcuts import redirect, render
from django.views import View

from accounts.models import AuditLog, Roles
from matrix.core.saisie import entier_ou_none
from quarts.alertes_activation import ECHEANCES_PAR_DEFAUT
from quarts.models import ChefDeListe, ConfigurationActivation

# (minimum, maximum) validés par le PO.
BORNES = {"rappel_minutes": (0, 1440), "alerte_minutes": (0, 120), "escalade_minutes": (1, 240)}
LIBELLES = {
    "rappel_minutes": "Rappel avant la prise d'effet prévue (minutes)",
    "alerte_minutes": "Alerte après la prise d'effet prévue (minutes)",
    "escalade_minutes": "Escalade après l'alerte (minutes)",
    "remplacement_duree_max_heures": "Durée maximale d'un remplacement du chef de liste (heures)",
}
BORNE_REMPLACEMENT = (1, 168)


def droit_sur_les_delais(user, ship):
    """« modifier » (commandant, COMAEQ titulaire), « lire » (commandant en second, administrateur d'unité,
    chef de liste du bâtiment) ou None. Aucun droit par le seul rang hiérarchique ailleurs."""
    profil = getattr(user, "profile", None)
    if ship is None or profil is None or not user.is_active or profil.ship_id != ship.pk:
        return None
    if profil.role == Roles.COMMANDANT or (profil.role == Roles.ETAT_MAJOR and profil.fonction_coma == "COMAEQ"):
        return "modifier"
    if profil.role in (Roles.COMMANDANT_EN_SECOND, Roles.ADMIN_NAVIRE):
        return "lire"
    if ChefDeListe.objects.filter(user=user).exists():
        return "lire"
    return None


class DelaisActivationView(LoginRequiredMixin, View):
    template_name = "quarts/delais_activation.html"

    def _ship(self, request):
        profil = getattr(request.user, "profile", None)
        return profil.ship if profil is not None else None

    def _valeurs(self, ship):
        reglage = ConfigurationActivation.objects.filter(ship=ship).first()
        valeurs = dict(ECHEANCES_PAR_DEFAUT, remplacement_duree_max_heures=72)
        if reglage:
            valeurs = {cle: getattr(reglage, cle) for cle in valeurs}
        return valeurs

    def _rendre(self, request, ship, droit, valeurs, statut=200):
        champs = [
            {"cle": cle, "libelle": LIBELLES[cle], "valeur": valeurs[cle], "min": (BORNES.get(cle) or BORNE_REMPLACEMENT)[0], "max": (BORNES.get(cle) or BORNE_REMPLACEMENT)[1]}
            for cle in (*BORNES, "remplacement_duree_max_heures")
        ]
        return render(request, self.template_name, {"ship": ship, "champs": champs, "peut_modifier": droit == "modifier"}, status=statut)

    def get(self, request):
        ship = self._ship(request)
        droit = droit_sur_les_delais(request.user, ship)
        if droit is None:
            raise Http404("Page introuvable.")
        return self._rendre(request, ship, droit, self._valeurs(ship))

    def post(self, request):
        ship = self._ship(request)
        droit = droit_sur_les_delais(request.user, ship)
        if droit is None:
            raise Http404("Page introuvable.")
        if droit != "modifier":
            raise PermissionDenied
        saisie, erreurs = {}, []
        for cle in (*BORNES, "remplacement_duree_max_heures"):
            valeur = entier_ou_none(request.POST.get(cle))
            mini, maxi = BORNES.get(cle) or BORNE_REMPLACEMENT
            if valeur is None or not mini <= valeur <= maxi:
                erreurs.append(f"{LIBELLES[cle]} : une valeur entière entre {mini} et {maxi} est attendue.")
            saisie[cle] = valeur if valeur is not None else request.POST.get(cle, "")
        if erreurs:
            for erreur in erreurs:
                messages.error(request, erreur)
            return self._rendre(request, ship, droit, saisie, statut=400)
        avant = self._valeurs(ship)
        ConfigurationActivation.objects.update_or_create(ship=ship, defaults=saisie)
        changements = [f"{LIBELLES[c]} : {avant[c]} → {saisie[c]}" for c in saisie if avant[c] != saisie[c]]
        if changements:
            AuditLog.objects.create(
                actor=request.user, action="delais_activation_modifies",
                details=f"Délais d'alerte d'activation de {ship} modifiés. " + " ; ".join(changements) + ".",
            )
        messages.success(request, "Délais enregistrés." if changements else "Aucun changement.")
        return redirect("quarts-delais-activation")
