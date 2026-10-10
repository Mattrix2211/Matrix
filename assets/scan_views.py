"""Vues du scan QR et du contrôle visuel (assets/web_views.py).

Sous-domaine extrait lors du re-découpage du fichier (tâche Notion « [ARCH]
Découper training/web_views.py et re-découper assets/web_views.py »,
assets/web_views.py ayant regrossi au-delà de 800 lignes) : le point d'entrée
du QR code apposé sur un équipement (matériel mobile OU installation fixe) et
le déclenchement d'un contrôle visuel, regroupés ici car tous deux résolvent
un équipement scanné pour ouvrir directement une occurrence de maintenance.

Refactor pur : reproduit exactement le comportement d'origine, aucun import
depuis assets/web_views.py n'est nécessaire (aucune dépendance croisée)."""
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.http import HttpResponseBadRequest, JsonResponse
from django.shortcuts import redirect
from django.utils import timezone
from django.views.generic import View

from matrix.core.roles import RoleLevel, user_role_level
from matrix.core.scopes import scope_filters_for_user
from maintenance.models import MaintenanceOccurrence, MaintenancePlan

from .models import Asset, Installation

# Statuts d'occurrence considérés comme terminés pour le scan QR : une occurrence
# déjà DONE ou CANCELLED ne doit plus être proposée au marin qui scanne
# l'équipement (même logique que dashboard/web_views.py, symbole privé non
# réimporté ici puisqu'il appartient à un autre module).
_STATUTS_OCCURRENCE_TERMINES = ("DONE", "CANCELLED")


class StartVisualCheckView(LoginRequiredMixin, View):
    def post(self, request, pk):
        if user_role_level(request.user) < RoleLevel.CHEF_SECTION:
            raise PermissionDenied
        # Périmètre : même filtre que ScanQRView (scope_filters_for_user) — sans
        # lui, un chef de section connaissant l'identifiant d'un matériel d'un
        # autre navire pouvait déclencher un contrôle visuel dessus (T-SEC).
        filtres = scope_filters_for_user(request.user)
        assets = Asset.objects.filter(**filtres) if filtres else Asset.objects.all()
        try:
            asset = assets.get(pk=pk)
        except Asset.DoesNotExist:
            return HttpResponseBadRequest('Matériel introuvable ou hors de votre périmètre.')
        plan = MaintenancePlan.objects.filter(scope='ASSET_TYPE', asset_type=asset.asset_type).first()
        name = plan.name if plan else 'Contrôle visuel'
        occ, _ = MaintenanceOccurrence.objects.get_or_create(
            plan=plan if plan else None,
            asset=asset,
            scheduled_for=timezone.localdate(),
            defaults={"status": "ASSIGNED"}
        )
        if request.headers.get('HX-Request'):
            return JsonResponse({"occurrence_id": occ.id, "status": occ.status, "execute_url": f"/maintenance/occurrences/{occ.id}/execute/"})
        return redirect(f"/maintenance/occurrences/{occ.id}/execute/")


class ScanQRView(LoginRequiredMixin, View):
    """Point d'entrée du QR code apposé sur un équipement (matériel mobile ou
    installation fixe) — workflow « Scan QR → occurrence du jour → checklist »
    (CLAUDE.md). Résout l'équipement scanné (même identifiant pour Asset et
    Installation, on essaie l'un puis l'autre), puis :
    - s'il existe une occurrence de maintenance planifiée aujourd'hui et
      assignée au marin connecté sur cet équipement, ouvre directement la
      checklist guidée d'exécution (aucune recherche à faire au poste) ;
    - sinon, affiche la fiche de l'équipement, d'où une anomalie peut être
      signalée en un clic.
    """

    def get(self, request, pk):
        # Périmètre : réutilise scope_filters_for_user (même système que
        # ScopedQuerySetMixin côté API) — un équipement hors périmètre est
        # traité comme introuvable, pas de nouveau contrôle d'accès.
        filtres = scope_filters_for_user(request.user)
        assets = Asset.objects.filter(**filtres) if filtres else Asset.objects.all()
        asset = assets.filter(pk=pk).first()
        if asset is not None:
            return self._rediriger(request, asset=asset)
        installations = Installation.objects.filter(**filtres) if filtres else Installation.objects.all()
        installation = installations.filter(pk=pk).first()
        if installation is not None:
            return self._rediriger(request, installation=installation)

        # Ni Asset ni Installation dans le périmètre de l'utilisateur : au
        # lieu de laisser Django renvoyer sa page 404 technique (brute, en
        # anglais en debug), on distingue deux cas et on redirige vers le
        # tableau de bord avec un message clair en français. On ne révèle
        # jamais le nom/navire de l'équipement d'un autre bâtiment : le
        # message reste générique dans le cas « hors périmètre ».
        existe_hors_perimetre = (
            Asset.objects.filter(pk=pk).exists() or Installation.objects.filter(pk=pk).exists()
        )
        if existe_hors_perimetre:
            messages.error(
                request,
                "Cet équipement n'appartient pas à votre navire, vous ne pouvez pas y accéder.",
            )
        else:
            messages.error(request, "QR code invalide ou équipement introuvable.")
        return redirect('home')

    def _rediriger(self, request, asset=None, installation=None):
        occurrences_du_jour = MaintenanceOccurrence.objects.filter(
            scheduled_for=timezone.localdate(), assignees=request.user
        ).exclude(status__in=_STATUTS_OCCURRENCE_TERMINES)
        if asset is not None:
            occurrence = occurrences_du_jour.filter(asset=asset).first()
        else:
            occurrence = occurrences_du_jour.filter(installation_maintenance__installation=installation).first()
        if occurrence is not None:
            return redirect('occurrence-execute', pk=occurrence.pk)
        if asset is not None:
            return redirect('asset-detail', pk=asset.pk)
        return redirect('installation-detail', pk=installation.pk)
