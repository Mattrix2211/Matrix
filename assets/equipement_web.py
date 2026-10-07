"""Équiper le navire depuis le catalogue : le bord choisit un article et indique combien
il en a ; Matrix crée autant de fiches matériel pré-remplies (mêmes droits que
la création d'un matériel : seuil `asset_ecriture_simple`, périmètre de l'appelant)."""
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import Count
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views import View

from accounts.models import AuditLog
from matrix.core.equipage import equipage_a_terre_lecture_seule
from matrix.core.mixins import build_scope_q
from matrix.core.role_thresholds import niveau_requis_pour
from matrix.core.roles import user_role_level
from matrix.core.saisie import entier_ou_none
from matrix.core.scopes import ship_id_for_user
from org.models import Section, Sector

from .models import ArticleCatalogue, Asset, AssetFolder, AssetType, Location

ETAPES = ["Quantité et rattachement", "Vérification"]


def quantite_maximale():
    return getattr(settings, "CATALOGUE_QUANTITE_MAX", 200)


def peut_equiper(user):
    """Même seuil (configurable par navire) que la création d'un matériel ; refus à terre."""
    return (user_role_level(user) >= niveau_requis_pour(user, "asset_ecriture_simple")
            and not equipage_a_terre_lecture_seule(user))


def exemplaires_scope(user):
    """Matériels du navire de l'utilisateur ; sans navire, bâtiments de son périmètre."""
    ship_id = ship_id_for_user(user)
    if ship_id:
        return Asset.objects.filter(ship_id=ship_id)
    return Asset.objects.filter(build_scope_q(user, ""))


def exemplaires_a_bord(user, article_ids):
    """{article: nombre d'exemplaires à bord} pour les articles donnés."""
    lignes = (exemplaires_scope(user).filter(article_catalogue_id__in=list(article_ids))
              .values("article_catalogue_id").annotate(n=Count("pk")))
    return {ligne["article_catalogue_id"]: ligne["n"] for ligne in lignes}


def exemplaires_a_bord_liste(user, article):
    return (exemplaires_scope(user).filter(article_catalogue=article)
            .select_related("ship", "sector", "location").order_by("ship__name", "internal_id", "created_at"))


def secteurs_equipables(user):
    """Secteurs où l'utilisateur peut rattacher du matériel (son périmètre)."""
    filtre = build_scope_q(user, {
        "ship_id": "service__ship_id", "service_id": "service_id",
        "sector_id": "id", "section_id": "sections__id"})
    return (Sector.objects.filter(filtre, archived=False, service__archived=False, service__ship__archived=False)
            .select_related("service__ship").distinct().order_by("service__ship__name", "service__name", "name"))


def sections_equipables(user, secteur):
    filtre = build_scope_q(user, {
        "ship_id": "sector__service__ship_id", "service_id": "sector__service_id",
        "sector_id": "sector_id", "section_id": "id"})
    return Section.objects.filter(filtre, sector=secteur, archived=False).order_by("name")


def type_materiel(article, secteur):
    """Type du secteur portant le nom de la catégorie, sinon le premier du secteur,
    sinon créé à partir de la catégorie (le type est obligatoire sur un matériel)."""
    types = AssetType.objects.filter(sector=secteur)
    return (types.filter(name__iexact=article.categorie.nom).first()
            or types.order_by("name").first()
            or AssetType.objects.create(sector=secteur, name=article.categorie.nom, category=article.categorie.nom))


def creer_exemplaires(user, article, quantite, secteur, section=None, location=None):
    """Crée `quantite` fiches matériel pré-remplies depuis l'article, en une transaction."""
    with transaction.atomic():
        modele = dict(
            asset_type=type_materiel(article, secteur), designation=article.designation,
            marque=article.marque, reference=article.reference, nno=article.nno,
            ship=secteur.service.ship, service=secteur.service, sector=secteur, section=section,
            location=location, folder=AssetFolder.objects.filter(name__iexact=article.categorie.nom).first(),
            article_catalogue=article, created_by=user, updated_by=user)
        exemplaires = Asset.objects.bulk_create([Asset(**modele) for _ in range(quantite)])
        AuditLog.objects.create(
            actor=user, action="catalogue.equipement",
            details=f"{quantite} × « {article.designation} » ({article.pk}) — {secteur.service.ship.name} / {secteur.name}")
    return exemplaires


class ArticleEquiperView(LoginRequiredMixin, View):
    """Assistant : quantité et rattachement, puis vérification et création."""
    template_name = "assets/catalogue/equiper.html"

    def _article(self, pk):
        return get_object_or_404(
            ArticleCatalogue.objects.select_related("categorie"), pk=pk, actif=True, categorie__actif=True)

    def _emplacements(self, secteurs):
        navires = {s.service.ship_id for s in secteurs}
        return Location.objects.filter(ship_id__in=navires).select_related("ship").order_by("ship__name", "name")

    def _afficher(self, request, article, secteurs, etape, valeurs, statut=200):
        secteur = next((s for s in secteurs if str(s.pk) == valeurs.get("secteur")), None)
        contexte = {
            "article": article, "etapes": ETAPES, "etape": etape, "valeurs": valeurs,
            "secteurs": secteurs, "quantite_max": quantite_maximale(),
            "sections": sections_equipables(request.user, secteur) if secteur else [],
            "emplacements": self._emplacements(secteurs),
            "plusieurs_navires": len({s.service.ship_id for s in secteurs}) > 1,
        }
        if etape == 2:
            contexte["synthese"] = {
                "secteur": secteur, "section": next((s for s in contexte["sections"] if str(s.pk) == valeurs.get("section")), None),
                "emplacement": next((e for e in contexte["emplacements"] if str(e.pk) == valeurs.get("emplacement")), None),
                "quantite": int(valeurs["quantite"]),
            }
            contexte["exemplaires"] = range(1, min(contexte["synthese"]["quantite"], 10) + 1)
        return render(request, self.template_name, contexte, status=statut)

    def _controler(self, request, secteurs, valeurs):
        """Renvoie (erreur, objets validés) ; les identifiants postés sont revalidés dans le périmètre."""
        try:
            quantite = int(valeurs.get("quantite", ""))
        except ValueError:
            return "Indiquez le nombre d'exemplaires.", None
        if quantite < 1:
            return "Le nombre d'exemplaires doit être d'au moins 1.", None
        if quantite > quantite_maximale():
            return f"Au plus {quantite_maximale()} exemplaires à la fois.", None
        secteur = next((s for s in secteurs if str(s.pk) == valeurs.get("secteur")), None)
        if secteur is None:
            return "Choisissez un secteur de votre périmètre.", None
        section = None
        if valeurs.get("section"):
            section = next((s for s in sections_equipables(request.user, secteur) if str(s.pk) == valeurs["section"]), None)
            if section is None:
                return "Section hors de votre périmètre.", None
        emplacement = None
        if valeurs.get("emplacement"):
            emplacement = Location.objects.filter(pk=entier_ou_none(valeurs["emplacement"]) or 0,
                                                  ship=secteur.service.ship).first()
            if emplacement is None:
                return "Emplacement inconnu sur ce navire.", None
        return None, (quantite, secteur, section, emplacement)

    def _preparer(self, request, pk):
        if not peut_equiper(request.user):
            raise PermissionDenied
        secteurs = list(secteurs_equipables(request.user))
        if not secteurs:
            raise PermissionDenied
        return self._article(pk), secteurs

    def get(self, request, pk):
        article, secteurs = self._preparer(request, pk)
        profil = getattr(request.user, "profile", None)
        propre = next((s for s in secteurs if profil and s.pk == profil.sector_id), None)
        secteur = propre or (secteurs[0] if len(secteurs) == 1 else None)
        return self._afficher(request, article, secteurs, 1, {
            "quantite": "1", "secteur": str(secteur.pk) if secteur else "",
            "section": str(profil.section_id) if profil and profil.section_id else ""})

    def post(self, request, pk):
        article, secteurs = self._preparer(request, pk)
        valeurs = dict(request.POST.items())
        etape = 2 if valeurs.get("etape") == "2" else 1
        if valeurs.get("action") == "precedent":
            return self._afficher(request, article, secteurs, 1, valeurs)
        erreur, objets = self._controler(request, secteurs, valeurs)
        if erreur:
            messages.error(request, erreur)
            return self._afficher(request, article, secteurs, 1, valeurs, 400)
        if etape == 1:
            return self._afficher(request, article, secteurs, 2, valeurs)
        quantite, secteur, section, emplacement = objets
        creer_exemplaires(request.user, article, quantite, secteur, section, emplacement)
        messages.success(
            request, f"{quantite} exemplaire{'s' if quantite > 1 else ''} de « {article.designation} » ajouté{'s' if quantite > 1 else ''} au matériel : "
                     "complétez les numéros de série, emplacements et dates depuis la liste du matériel.")
        return redirect(reverse("catalogue-article", args=[article.pk]))
