"""Compléter les exemplaires : saisie en grille (façon tableur) du n° de série, du n° de bord, de
l'emplacement et des dates (mise en service, dernier contrôle, péremption) des fiches créées depuis le catalogue. Mêmes droits que la modification d'un matériel
(seuil `asset_ecriture_simple`, périmètre de l'appelant, refus à terre) ; chaque ligne postée est
revalidée par identifiant côté serveur et l'enregistrement est tout ou rien."""
import calendar
import uuid

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views import View

from accounts.models import AuditLog
from matrix.core.mixins import build_scope_q
from matrix.core.saisie import date_fr_ou_none, formater_date_fr

from .equipement_web import peut_equiper, quantite_maximale
from .models import ArticleCatalogue, Asset, Location

# Les colonnes texte portent le nom du champ du matériel ; « emplacement » est résolu par nom sur le navire.
COLONNES = [
    {"nom": "serial_number", "libelle": "N° de série"},
    {"nom": "internal_id", "libelle": "N° de bord"},
    {"nom": "emplacement", "libelle": "Emplacement"},
    {"nom": "local", "libelle": "Local"},
    {"nom": "gisement", "libelle": "Gisement"},
    {"nom": "date_mise_en_service", "libelle": "Mise en service", "type": "date"},
    {"nom": "date_dernier_controle", "libelle": "Dernier contrôle", "type": "date"},
    {"nom": "date_peremption", "libelle": "Péremption", "type": "date"},
]
NOMS = [c["nom"] for c in COLONNES]
TEXTES = ("serial_number", "internal_id", "local", "gisement")
DATES = ("date_mise_en_service", "date_dernier_controle", "date_peremption")
LIBELLES = {c["nom"]: c["libelle"] for c in COLONNES}


def _valeurs(asset):
    return {
        "serial_number": asset.serial_number, "internal_id": asset.internal_id,
        "emplacement": asset.location.name if asset.location else "",
        "local": asset.local, "gisement": asset.gisement,
        **{nom: formater_date_fr(getattr(asset, nom)) for nom in DATES},
    }


def _ajouter_mois(date, mois):
    """Date décalée de `mois` mois, ramenée au dernier jour du mois cible si besoin."""
    total = date.year * 12 + date.month - 1 + mois
    annee, mois_cible = divmod(total, 12)
    return date.replace(year=annee, month=mois_cible + 1,
                        day=min(date.day, calendar.monthrange(annee, mois_cible + 1)[1]))


class _ExemplairesGrilleView(LoginRequiredMixin, View):
    template_name = "assets/catalogue/exemplaires.html"

    def lot(self, request, **kwargs):
        """Exemplaires modifiables du lot, déjà limités au périmètre de l'appelant."""
        raise NotImplementedError

    def contexte_lot(self, **kwargs):
        raise NotImplementedError

    def retour(self, **kwargs):
        raise NotImplementedError

    def _base(self, request):
        return Asset.objects.filter(build_scope_q(request.user, ""), article_catalogue__isnull=False)

    def _lot(self, request, **kwargs):
        return (self.lot(request, **kwargs).select_related("ship", "location", "asset_type", "article_catalogue")
                .order_by("ship__name", "designation", "created_at", "pk"))

    def _verifier_droit(self, request):
        if not peut_equiper(request.user):
            raise PermissionDenied

    def _afficher(self, request, assets, valeurs=None, erreurs=None, statut=200, **kwargs):
        plusieurs_navires = len({a.ship_id for a in assets}) > 1
        lignes = [{
            "cle": str(a.pk),
            "libelle": f"{a.designation or a.asset_type.name}" + (f" · {a.ship.name}" if plusieurs_navires else ""),
            "valeurs": (valeurs or {}).get(str(a.pk)) or _valeurs(a),
            "erreurs": (erreurs or {}).get(str(a.pk), {}),
        } for a in assets]
        contexte = {"colonnes": COLONNES, "lignes": lignes, "maximum": quantite_maximale()}
        contexte.update(self.contexte_lot(**kwargs))
        return render(request, self.template_name, contexte, status=statut)

    def get(self, request, **kwargs):
        self._verifier_droit(request)
        return self._afficher(request, list(self._lot(request, **kwargs)[:quantite_maximale()]), **kwargs)

    def post(self, request, **kwargs):
        self._verifier_droit(request)
        postes = {}
        for cle, valeur in request.POST.items():
            identifiant, _, colonne = cle.rpartition("__")
            if colonne in NOMS:
                postes.setdefault(identifiant, {})[colonne] = valeur.strip()
        ids = set()
        for identifiant in postes:
            try:
                ids.add(uuid.UUID(identifiant))
            except ValueError:
                messages.error(request, "Ligne inconnue : aucune modification enregistrée.")
                return self._afficher(request, list(self._lot(request, **kwargs)[:quantite_maximale()]), statut=400, **kwargs)
        # Chaque ligne est revalidée par identifiant dans le lot et le périmètre.
        assets = list(self._lot(request, **kwargs).filter(pk__in=ids)) if ids else []
        if len(assets) != len(ids) or len(ids) > quantite_maximale():
            messages.error(request, "Un exemplaire est introuvable ou hors de votre périmètre : aucune modification enregistrée.")
            return self._afficher(request, list(self._lot(request, **kwargs)[:quantite_maximale()]), statut=400, **kwargs)
        valeurs = {str(a.pk): {**_valeurs(a), **postes[str(a.pk)]} for a in assets}
        erreurs = self._controler(assets, valeurs)
        if erreurs:
            messages.error(request, "Corrigez les cellules signalées : rien n'a été enregistré.")
            return self._afficher(request, assets, valeurs, erreurs, 400, **kwargs)
        modifies = self._enregistrer(request.user, assets, valeurs)
        if modifies:
            messages.success(request, f"{len(modifies)} exemplaire{'s' if len(modifies) > 1 else ''} mis à jour.")
            if any(ligne.get("_proposee") for ligne in valeurs.values()):
                messages.info(request, "Péremption calculée d'après la durée de vie type de l'article "
                                       "pour les lignes laissées vides : modifiez-la si besoin.")
            doublons = self._doublons(modifies)
            if doublons:
                messages.warning(request, "N° de série en double sur ce navire pour le même article : "
                                          f"{', '.join(sorted(doublons))} (enregistrés, à vérifier).")
        else:
            messages.info(request, "Aucune modification à enregistrer.")
        return redirect(self.retour(**kwargs))

    def _controler(self, assets, valeurs):
        """Erreurs par ligne et par colonne ; les emplacements se lisent par nom, sur le navire de la ligne."""
        lieux = {}
        for lieu in Location.objects.filter(ship_id__in={a.ship_id for a in assets}):
            lieux.setdefault((lieu.ship_id, lieu.name.lower()), []).append(lieu)
        erreurs = {}
        for asset in assets:
            ligne = valeurs[str(asset.pk)]
            for nom in TEXTES:
                if len(ligne[nom]) > 255:
                    erreurs.setdefault(str(asset.pk), {})[nom] = "255 caractères au plus."
            for nom in DATES:
                try:
                    ligne["_" + nom] = date_fr_ou_none(ligne[nom])
                except ValueError:
                    erreurs.setdefault(str(asset.pk), {})[nom] = "Date invalide : saisissez jj/mm/aaaa."
            mise, peremption = ligne.get("_date_mise_en_service"), ligne.get("_date_peremption")
            if mise and peremption and peremption < mise:
                erreurs.setdefault(str(asset.pk), {})["date_peremption"] = "Péremption antérieure à la mise en service."
            if ligne["emplacement"]:
                trouves = lieux.get((asset.ship_id, ligne["emplacement"].lower()), [])
                if len(trouves) != 1:
                    erreurs.setdefault(str(asset.pk), {})["emplacement"] = (
                        "Emplacement inconnu sur ce navire." if not trouves else "Emplacement ambigu : précisez-le.")
                else:
                    ligne["_lieu"] = trouves[0]
        return erreurs

    def _enregistrer(self, user, assets, valeurs):
        """Met à jour les seules lignes modifiées, en une transaction, avec trace d'audit."""
        modifies, traces = [], []
        for asset in assets:
            ligne = valeurs[str(asset.pk)]
            lieu = ligne.get("_lieu")
            changements = []
            for nom in TEXTES:
                if getattr(asset, nom) != ligne[nom]:
                    changements.append(f"{LIBELLES[nom]} « {getattr(asset, nom)} » -> « {ligne[nom]} »")
                    setattr(asset, nom, ligne[nom])
            if lieu != asset.location:
                changements.append(f"Emplacement « {asset.location or ''} » -> « {lieu or ''} »")
                asset.location = lieu
            mise_modifiee = asset.date_mise_en_service != ligne["_date_mise_en_service"]
            for nom in DATES:
                if getattr(asset, nom) != ligne["_" + nom]:
                    changements.append(f"{LIBELLES[nom]} « {formater_date_fr(getattr(asset, nom))} » -> « {ligne[nom]} »")
                    setattr(asset, nom, ligne["_" + nom])
            # Péremption proposée : mise en service modifiée, péremption vide, durée de vie type connue.
            duree = asset.article_catalogue.duree_vie_mois if asset.article_catalogue else None
            if duree and mise_modifiee and asset.date_mise_en_service and not asset.date_peremption:
                asset.date_peremption = _ajouter_mois(asset.date_mise_en_service, duree)
                ligne["_proposee"] = True
                changements.append(f"{LIBELLES['date_peremption']} proposée : « {formater_date_fr(asset.date_peremption)} »")
            if changements:
                asset.updated_by = user
                modifies.append(asset)
                traces.append(AuditLog(actor=user, action="catalogue.exemplaire",
                                       details=f"id={asset.pk} : " + " ; ".join(changements)))
        with transaction.atomic():
            for asset in modifies:
                asset.save(update_fields=["serial_number", "internal_id", "local", "gisement", "location",
                                          *DATES, "updated_by", "updated_at"])
            AuditLog.objects.bulk_create(traces)
        return modifies

    def _doublons(self, modifies):
        """N° de série présents plusieurs fois pour un même article sur un même navire (non bloquant :
        deux fournisseurs peuvent réutiliser une numérotation)."""
        series = {a.serial_number for a in modifies if a.serial_number}
        if not series:
            return set()
        lignes = (Asset.objects.filter(
            serial_number__in=series, ship_id__in={a.ship_id for a in modifies},
            article_catalogue_id__in={a.article_catalogue_id for a in modifies})
            .values("ship_id", "article_catalogue_id", "serial_number").annotate(n=Count("pk")).filter(n__gt=1))
        touches = {(a.ship_id, a.article_catalogue_id, a.serial_number) for a in modifies}
        return {ligne["serial_number"] for ligne in lignes
                if (ligne["ship_id"], ligne["article_catalogue_id"], ligne["serial_number"]) in touches}


class ArticleExemplairesView(_ExemplairesGrilleView):
    """Exemplaires d'un article à bord."""

    def _article(self, pk):
        return get_object_or_404(ArticleCatalogue.objects.select_related("categorie"), pk=pk)

    def lot(self, request, pk):
        return self._base(request).filter(article_catalogue_id=pk)

    def contexte_lot(self, pk):
        article = self._article(pk)
        return {"titre": f"Compléter les exemplaires : {article.designation}", "article": article,
                "cle_brouillon": f"catalogue:exemplaires:{article.pk}",
                "retour_url": reverse("catalogue-article", args=[article.pk])}

    def retour(self, pk):
        return reverse("catalogue-article", args=[pk])

    def get(self, request, pk):
        self._article(pk)
        return super().get(request, pk=pk)

    def post(self, request, pk):
        self._article(pk)
        return super().post(request, pk=pk)


class ExemplairesIncompletsView(_ExemplairesGrilleView):
    """Tous les exemplaires du navire auxquels il manque un n° de série, un n° de bord ou un emplacement."""

    def lot(self, request):
        return self._base(request).filter(
            Q(serial_number="") | Q(internal_id="") | Q(location__isnull=True))

    def contexte_lot(self):
        return {"titre": "Exemplaires à compléter", "article": None, "cle_brouillon": "catalogue:exemplaires:incomplets",
                "retour_url": reverse("catalogue")}

    def retour(self):
        return reverse("catalogue-exemplaires-incomplets")
