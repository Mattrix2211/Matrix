"""Interface web des rondes : tableau du jour, exécution point par point
(HTMX, un clic par point), gestion des modèles et de leurs points."""
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import Max
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View

from accounts.models import AuditLog
from assets.models import Asset, Installation
from org.models import Sector, Service, Ship

from . import services
from .models import PointControle, Ronde, RondeModele
from .services import RondeImpossible


def _exiger_gestion(user):
    if not services.peut_gerer_modeles(user):
        raise PermissionDenied


def _modele_gerable_ou_404(user, pk):
    _exiger_gestion(user)
    return get_object_or_404(services.modeles_gerables(user), pk=pk)


def _audit(user, action, modele, extra=""):
    AuditLog.objects.create(actor=user, action=action, details=f"modele={modele.pk}; nom={modele.nom}{extra}")


class RondesIndexView(LoginRequiredMixin, View):
    """Tableau du jour : mes rondes à faire (en retard en tête), rondes récentes."""

    def get(self, request):
        a_faire = list(services.rondes_du_marin(request.user).order_by("date_prevue"))
        for ronde in a_faire:
            ronde.repondus, ronde.total, ronde.pct, ronde.non_conformes = services.progression(ronde)
        recentes = list(services.rondes_visibles(request.user).filter(statut=Ronde.TERMINEE).order_by("-fin")[:10])
        for ronde in recentes:
            ronde.repondus, ronde.total, ronde.pct, ronde.non_conformes = services.progression(ronde)
        return render(request, "rondes/index.html", {
            "a_faire": a_faire, "recentes": recentes,
            "peut_gerer": services.peut_gerer_modeles(request.user),
        })


class ModeleListView(LoginRequiredMixin, View):
    def get(self, request):
        modeles = services.modeles_visibles(request.user).prefetch_related("points")
        return render(request, "rondes/modeles.html", {
            "modeles": modeles, "peut_gerer": services.peut_gerer_modeles(request.user),
        })


class ModeleFormView(LoginRequiredMixin, View):
    """Création (pk absent) ou modification d'un modèle et de ses points."""

    def _contexte(self, request, modele, valeurs=None):
        equipements_installations = equipements_assets = []
        if modele is not None and modele.ship_id:
            equipements_installations = Installation.objects.filter(ship_id=modele.ship_id).order_by("designation")
            equipements_assets = Asset.objects.filter(ship_id=modele.ship_id)
        return {
            "modele": modele,
            "perimetres": [(v, lib) for v, lib, _ in services.perimetres_gerables(request.user)],
            "valeurs": valeurs or {},
            "installations": equipements_installations, "materiels": equipements_assets,
            "points": modele.points.select_related("installation", "asset") if modele else [],
            "peut_gerer": services.peut_gerer_modeles(request.user)
            and (modele is None or services.modeles_gerables(request.user).filter(pk=modele.pk).exists()),
        }

    def get(self, request, pk=None):
        if pk is None:
            _exiger_gestion(request.user)
            return render(request, "rondes/modele_form.html", self._contexte(request, None))
        modele = get_object_or_404(services.modeles_visibles(request.user), pk=pk)
        return render(request, "rondes/modele_form.html", self._contexte(request, modele))

    def post(self, request, pk=None):
        _exiger_gestion(request.user)
        modele = _modele_gerable_ou_404(request.user, pk) if pk else RondeModele(created_by=request.user)
        donnees = request.POST
        nom = donnees.get("nom", "").strip()
        try:
            periodicite = int(donnees.get("periodicite_jours") or 1)
        except ValueError:
            periodicite = 0
        if not nom or periodicite < 1:
            messages.error(request, "Indiquez un nom et une périodicité d'au moins 1 jour.")
            return render(request, "rondes/modele_form.html", self._contexte(request, modele if pk else None, donnees), status=400)
        if not pk:
            choix = {v: obj for v, _, obj in services.perimetres_gerables(request.user)}.get(donnees.get("perimetre"))
            if choix is None:
                messages.error(request, "Choisissez un périmètre dans votre zone de responsabilité.")
                return render(request, "rondes/modele_form.html", self._contexte(request, None, donnees), status=400)
            modele.rattacher(
                ship=choix if isinstance(choix, Ship) else None,
                service=choix if isinstance(choix, Service) else None,
                sector=choix if isinstance(choix, Sector) else None,
            )
        modele.nom, modele.description = nom, donnees.get("description", "").strip()
        modele.periodicite_jours, modele.actif = periodicite, donnees.get("actif") == "on"
        modele.updated_by = request.user
        with transaction.atomic():
            modele.save()
            _audit(request.user, "save_ronde_modele", modele)
        messages.success(request, "Modèle enregistré.")
        return redirect("ronde-modele", pk=modele.pk)


class PointActionView(LoginRequiredMixin, View):
    """Ajout, modification, suppression et déplacement d'un point de contrôle.
    Chaque changement incrémente la version du modèle : les rondes déjà
    créées gardent leur propre copie des points."""

    def post(self, request, pk, action, point_pk=None):
        modele = _modele_gerable_ou_404(request.user, pk)
        point = get_object_or_404(modele.points, pk=point_pk) if point_pk else None
        with transaction.atomic():
            if action in ("ajouter", "modifier"):
                point = self._enregistrer(request, modele, point)
                if point is None:
                    return redirect("ronde-modele", pk=modele.pk)
            elif action == "supprimer" and point:
                point.delete()
            elif action in ("monter", "descendre") and point:
                self._deplacer(modele, point, -1 if action == "monter" else 1)
            else:
                raise PermissionDenied
            modele.version += 1
            modele.save(update_fields=["version", "updated_at"])
            _audit(request.user, "ronde_point_" + action, modele, f"; version={modele.version}")
        return redirect("ronde-modele", pk=modele.pk)

    def _enregistrer(self, request, modele, point):
        donnees = request.POST
        libelle = donnees.get("libelle", "").strip()
        if not libelle:
            messages.error(request, "Le libellé du point est obligatoire.")
            return None
        installation = materiel = None
        type_eq, _, id_eq = donnees.get("equipement", "").partition(":")
        try:
            if type_eq == "installation":
                installation = Installation.objects.get(pk=id_eq, ship_id=modele.ship_id)
            elif type_eq == "asset":
                materiel = Asset.objects.get(pk=id_eq, ship_id=modele.ship_id)
        except (Installation.DoesNotExist, Asset.DoesNotExist, ValueError, ValidationError):
            messages.error(request, "Équipement introuvable dans l'unité de cette ronde.")
            return None
        try:
            gravite = min(max(int(donnees.get("gravite") or 3), 1), 5)
        except ValueError:
            gravite = 3
        if point is None:
            dernier = modele.points.aggregate(m=Max("ordre"))["m"] or 0
            point = PointControle(modele=modele, ordre=dernier + 1)
        point.libelle, point.consigne = libelle, donnees.get("consigne", "").strip()
        point.installation, point.asset = installation, materiel
        point.avec_mesure = donnees.get("avec_mesure") == "on"
        point.unite_mesure = donnees.get("unite_mesure", "").strip() if point.avec_mesure else ""
        point.gravite = gravite
        point.save()
        return point

    def _deplacer(self, modele, point, sens):
        points = list(modele.points.all())
        i = points.index(point)
        j = i + sens
        if 0 <= j < len(points):
            points[i], points[j] = points[j], points[i]
            for ordre, p in enumerate(points, start=1):
                if p.ordre != ordre:
                    p.ordre = ordre
                    p.save(update_fields=["ordre", "updated_at"])


class LancerRondeView(LoginRequiredMixin, View):
    """Lance une ronde maintenant (ou reprend celle déjà ouverte du modèle)."""

    def post(self, request, pk):
        modele = get_object_or_404(services.modeles_visibles(request.user), pk=pk, actif=True)
        ronde = services.ronde_ouverte_du_modele(modele)
        if ronde is None:
            try:
                ronde = services.creer_ronde(modele, acteur=request.user)
            except RondeImpossible as erreur:
                messages.error(request, str(erreur))
                return redirect("ronde-modele", pk=modele.pk)
        return redirect("ronde-detail", pk=ronde.pk)


def _ronde_visible_ou_404(user, pk):
    return get_object_or_404(services.rondes_visibles(user), pk=pk)


def _contexte_ronde(ronde):
    resultats = list(ronde.resultats.select_related("installation", "asset", "anomalie", "saisi_par"))
    repondus, total, pct, non_conformes = services.progression(ronde)
    return {
        "ronde": ronde, "resultats": resultats, "repondus": repondus, "total": total, "pct": pct,
        "non_conformes": non_conformes, "conformes": repondus - non_conformes,
    }


class RondeDetailView(LoginRequiredMixin, View):
    """Exécution (ronde ouverte) ou historique en lecture seule (terminée)."""

    def get(self, request, pk):
        ronde = _ronde_visible_ou_404(request.user, pk)
        return render(request, "rondes/ronde.html", _contexte_ronde(ronde))


class ResultatView(LoginRequiredMixin, View):
    """Réponse à un point. Avec HTMX, ne renvoie que la carte du point et la
    jauge mise à jour ; sans, redirige vers la ronde."""

    def post(self, request, pk, resultat_pk):
        ronde = _ronde_visible_ou_404(request.user, pk)
        resultat = get_object_or_404(ronde.resultats, pk=resultat_pk)
        erreur = anomalie = None
        try:
            anomalie = services.enregistrer_resultat(
                resultat, request.user, request.POST.get("resultat", ""),
                request.POST.get("mesure", ""), request.POST.get("commentaire", ""),
            )
        except RondeImpossible as exc:
            erreur = str(exc)
        if request.headers.get("HX-Request"):
            ronde.refresh_from_db()
            resultat.refresh_from_db()
            contexte = _contexte_ronde(ronde)
            contexte.update({"r": resultat, "erreur": erreur, "anomalie_creee": anomalie})
            # Toujours 200 : HTMX n'échange pas le contenu d'une réponse 4xx.
            return render(request, "rondes/_point_reponse.html", contexte)
        if erreur:
            messages.error(request, erreur)
        return redirect("ronde-detail", pk=ronde.pk)


class TerminerRondeView(LoginRequiredMixin, View):
    def post(self, request, pk):
        ronde = _ronde_visible_ou_404(request.user, pk)
        try:
            non_conformes = services.terminer_ronde(ronde, request.user)
        except RondeImpossible as erreur:
            messages.error(request, str(erreur))
        else:
            messages.success(
                request,
                "Ronde terminée : tout est conforme." if not non_conformes
                else f"Ronde terminée : {non_conformes} point(s) non conforme(s), anomalie(s) transmise(s).",
            )
        return redirect("ronde-detail", pk=ronde.pk)
