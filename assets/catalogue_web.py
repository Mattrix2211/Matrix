"""Écran web du catalogue de matériel de la flotte : lecture pour tout connecté,
écriture réservée aux responsables de la spécialité (même règle que l'API)."""
import uuid
from urllib.parse import quote

from django import forms
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views import View

from accounts.models import AuditLog, SpecialityChoice
from matrix.core.equipage import equipage_a_terre_lecture_seule
from matrix.core.icones import ICONES
from matrix.core.recherche import normaliser
from matrix.core.saisie import entier_ou_none
from matrix.core.scopes import is_master_admin

from . import fiche_flotte, fiche_validation as validation
from .catalogue_photo import valider_photo
from .equipement_web import exemplaires_a_bord, exemplaires_a_bord_liste, peut_equiper
from .models import ArticleCatalogue, CategorieCatalogue
from .permissions import peut_gerer_catalogue
from .proposition_article import peut_proposer

# Icônes proposées pour une catégorie (concepts de matrix/core/icones.py).
ICONES_CATEGORIE = [
    ("materiel", "Matériel"), ("installation", "Installation"), ("piece", "Pièce"),
    ("logistique", "Stock"), ("maintenance", "Maintenance"), ("formation", "Formation"),
    ("garde", "Sécurité"), ("navire", "Navire"), ("configuration", "Réglages"),
]


def specialites_gerees(user):
    """Spécialités où l'utilisateur peut écrire dans le catalogue."""
    actives = SpecialityChoice.objects.filter(active=True)
    if is_master_admin(user):
        return actives
    return actives.filter(responsables__user=user)


def journaliser(user, verbe, objet):
    """Trace l'écriture dans l'AuditLog (verbe : creation, modification, archivage, suppression)."""
    AuditLog.objects.create(
        actor=user, action=f"catalogue.{verbe}",
        details=f"{objet._meta.verbose_name} « {objet} » ({objet.pk})")


def _uuid_ou_none(valeur):
    try:
        return uuid.UUID(str(valeur))
    except ValueError:
        return None


def _icone(categorie):
    return categorie.icone if categorie.icone in ICONES else "materiel"


def _chemin(categorie):
    """Catégories de la racine jusqu'à `categorie` incluse."""
    chemin = []
    while categorie is not None:
        chemin.insert(0, categorie)
        categorie = categorie.parent
    return chemin


class _FormBootstrap(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for champ in self.fields.values():
            classe = "form-select" if isinstance(champ.widget, forms.Select) else "form-control"
            champ.widget.attrs["class"] = classe


class _PhotoMixin:
    def clean_photo(self):
        return valider_photo(self.cleaned_data.get("photo"))


class CategorieForm(_PhotoMixin, _FormBootstrap):
    icone = forms.ChoiceField(choices=[("", "Par défaut")] + ICONES_CATEGORIE, required=False, label="Icône")

    class Meta:
        model = CategorieCatalogue
        fields = ["nom", "parent", "specialite", "ordre", "icone", "photo"]

    def __init__(self, *args, user, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["specialite"].queryset = specialites_gerees(user)
        self.fields["parent"].queryset = CategorieCatalogue.objects.filter(
            actif=True, specialite__in=specialites_gerees(user)).exclude(pk=self.instance.pk)

    def clean(self):
        cleaned = super().clean()
        # unique_together ignore parent NULL : doublon de racine vérifié ici.
        if cleaned.get("nom") and cleaned.get("parent") is None and CategorieCatalogue.objects.filter(
                parent=None, nom=cleaned["nom"]).exclude(pk=self.instance.pk).exists():
            self.add_error("nom", "Une catégorie racine porte déjà ce nom.")
        return cleaned


class ArticleForm(_PhotoMixin, _FormBootstrap):
    caracteristiques_texte = forms.CharField(
        label="Caractéristiques", required=False, widget=forms.Textarea(attrs={"rows": 4}),
        help_text="Une par ligne, sous la forme « nom : valeur ».")

    class Meta:
        model = ArticleCatalogue
        fields = ["designation", "categorie", "marque", "reference", "nno", "photo", "duree_vie_mois"]

    def __init__(self, *args, user, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["categorie"].queryset = CategorieCatalogue.objects.filter(
            actif=True, specialite__in=specialites_gerees(user))
        if self.instance.pk:
            self.fields["caracteristiques_texte"].initial = "\n".join(
                f"{k} : {v}" for k, v in self.instance.caracteristiques.items())

    def clean_caracteristiques_texte(self):
        resultat = {}
        for ligne in self.cleaned_data["caracteristiques_texte"].splitlines():
            if not ligne.strip():
                continue
            cle, separateur, valeur = ligne.partition(":")
            if not separateur or not cle.strip():
                raise forms.ValidationError(f"Ligne invalide : « {ligne.strip()} » (format attendu : nom : valeur).")
            resultat[cle.strip()] = valeur.strip()
        return resultat

    def save(self, commit=True):
        self.instance.caracteristiques = self.cleaned_data["caracteristiques_texte"]
        return super().save(commit=commit)


class CatalogueView(LoginRequiredMixin, View):
    """Tuiles de catégories, cartes d'articles, recherche (fragment HTMX) et filtre de spécialité."""

    def get(self, request):
        q = normaliser(request.GET.get("q"))
        specialite = SpecialityChoice.objects.filter(pk=entier_ou_none(request.GET.get("specialite")) or 0).first()
        categorie_id = _uuid_ou_none(request.GET.get("categorie"))
        categorie = (CategorieCatalogue.objects.select_related("parent", "specialite")
                     .filter(pk=categorie_id, actif=True).first() if categorie_id else None)
        if categorie:
            specialite = categorie.specialite
        articles = ArticleCatalogue.objects.filter(actif=True).select_related("categorie")
        tuiles = []
        if q:
            articles = articles.filter(
                Q(designation__icontains=q) | Q(marque__icontains=q) | Q(reference__icontains=q) | Q(nno__icontains=q))
            if specialite:
                articles = articles.filter(categorie__specialite=specialite)
        else:
            categories = CategorieCatalogue.objects.filter(actif=True, parent=categorie).annotate(
                nb_articles=Count("articles", filter=Q(articles__actif=True), distinct=True),
                nb_sous=Count("enfants", filter=Q(enfants__actif=True), distinct=True))
            if specialite and not categorie:
                categories = categories.filter(specialite=specialite)
            tuiles = list(categories.select_related("specialite"))
            for t in tuiles:
                t.icone_affichee = _icone(t)
            articles = articles.filter(categorie=categorie) if categorie else articles.none()
        articles = list(articles)
        compteurs = exemplaires_a_bord(request.user, [a.pk for a in articles])
        for a in articles:
            a.nb_a_bord = compteurs.get(a.pk, 0)
        gerees = specialites_gerees(request.user)
        contexte = {
            "q": q, "categorie": categorie, "categorie_id": str(categorie.pk) if categorie else "", "specialite": specialite,
            "chemin": _chemin(categorie), "tuiles": tuiles, "articles": articles,
            "specialites": SpecialityChoice.objects.filter(categories_catalogue__actif=True).distinct().order_by("name"),
            "peut_creer_categorie": (peut_gerer_catalogue(request.user, categorie.specialite) if categorie
                                     else (peut_gerer_catalogue(request.user, specialite) if specialite else gerees.exists())),
            "peut_creer_article": bool(categorie) and peut_gerer_catalogue(request.user, categorie.specialite),
            "peut_modifier": bool(categorie) and peut_gerer_catalogue(request.user, categorie.specialite),
            "peut_proposer": peut_proposer(request.user)[0],
            "url_proposer": reverse("catalogue-proposition-nouvelle") + (f"?designation={quote(q)}" if q else ""),
        }
        gabarit = "assets/catalogue/_contenu.html" if request.headers.get("HX-Request") else "assets/catalogue/index.html"
        return render(request, gabarit, contexte)


class ArticleCatalogueDetailView(LoginRequiredMixin, View):
    def get(self, request, pk):
        article = get_object_or_404(ArticleCatalogue.objects.select_related("categorie__parent", "categorie__specialite"), pk=pk)
        duree = article.duree_vie_mois
        peut = peut_gerer_catalogue(request.user, article.specialite)
        exemplaires = list(exemplaires_a_bord_liste(request.user, article))
        mode, _ = validation.mode_redaction_flotte(request.user, article.specialite.pk)
        a_terre = equipage_a_terre_lecture_seule(request.user)
        visibles = validation.versions_visibles(request.user).values("pk")
        return render(request, "assets/catalogue/fiche.html", {
            "article": article, "chemin": _chemin(article.categorie),
            "fiches": fiche_flotte.fiches_de_categorie(article.categorie),
            "fiches_en_cours": fiche_flotte.propositions_en_cours(article.categorie).filter(pk__in=visibles),
            "peut_proposer_fiche": mode is not None and not a_terre, "fiche_directe": mode == validation.DIRECT,
            "peut_modifier": peut, "exemplaires": exemplaires,
            "peut_equiper": article.actif and peut_equiper(request.user),
            "action": {"libelle": "Modifier", "icone": "modification", "url": reverse("catalogue-article-modifier", args=[article.pk])} if peut else None,
            "duree_vie": None if not duree else (
                f"{duree} mois" + (f" ({duree // 12} an{'s' if duree // 12 > 1 else ''})" if duree % 12 == 0 and duree >= 12 else "")),
        })


class _EcritureCatalogueView(LoginRequiredMixin, View):
    """Formulaire de création ou de modification ; les droits sont revérifiés ici."""
    modele = None
    classe_form = None
    libelle = ""

    def _objet(self, pk):
        return get_object_or_404(self.modele, pk=pk) if pk else None

    def _retour(self, objet):
        raise NotImplementedError

    def _initial(self, request):
        return {}

    def _autoriser(self, request, objet):
        if objet is None:
            if not specialites_gerees(request.user).exists():
                raise PermissionDenied
        elif not peut_gerer_catalogue(request.user, objet.specialite):
            raise PermissionDenied

    def _rendre(self, request, form, objet):
        return render(request, "assets/catalogue/formulaire.html", {
            "form": form, "objet": objet, "titre": f"{'Modifier' if objet else 'Nouvel'} {self.libelle}",
            "annuler": self._retour(objet) if objet else reverse("catalogue"),
        })

    def get(self, request, pk=None):
        objet = self._objet(pk)
        self._autoriser(request, objet)
        return self._rendre(request, self.classe_form(instance=objet, initial=self._initial(request), user=request.user), objet)

    def post(self, request, pk=None):
        objet = self._objet(pk)
        self._autoriser(request, objet)
        form = self.classe_form(request.POST, request.FILES, instance=objet, user=request.user)
        if not form.is_valid():
            return self._rendre(request, form, objet)
        enregistre = form.save(commit=False)
        if not peut_gerer_catalogue(request.user, enregistre.specialite):
            raise PermissionDenied
        if objet is None:
            enregistre.created_by = request.user
        enregistre.updated_by = request.user
        enregistre.save()
        journaliser(request.user, "creation" if objet is None else "modification", enregistre)
        messages.success(request, f"{self.libelle.capitalize()} enregistré.")
        return redirect(self._retour(enregistre))


class CategorieEcritureView(_EcritureCatalogueView):
    modele = CategorieCatalogue
    classe_form = CategorieForm
    libelle = "catégorie"

    def _retour(self, objet):
        return f"{reverse('catalogue')}?categorie={objet.pk}"

    def _initial(self, request):
        return {"parent": _uuid_ou_none(request.GET.get("parent")),
                "specialite": entier_ou_none(request.GET.get("specialite"))}


class ArticleEcritureView(_EcritureCatalogueView):
    modele = ArticleCatalogue
    classe_form = ArticleForm
    libelle = "article"

    def _retour(self, objet):
        return reverse("catalogue-article", args=[objet.pk])

    def _initial(self, request):
        return {"categorie": _uuid_ou_none(request.GET.get("categorie"))}


class _ArchiverView(LoginRequiredMixin, View):
    """Archive (actif=False) ; jamais de suppression depuis l'écran."""
    modele = None

    def refus(self, objet):
        return ""

    def post(self, request, pk):
        objet = get_object_or_404(self.modele, pk=pk)
        if not peut_gerer_catalogue(request.user, objet.specialite):
            raise PermissionDenied
        motif = self.refus(objet)
        if motif:
            messages.error(request, motif)
            return redirect(self.retour(objet, archive=False))
        objet.actif = False
        objet.updated_by = request.user
        objet.save(update_fields=["actif", "updated_by", "updated_at"])
        journaliser(request.user, "archivage", objet)
        messages.success(request, f"« {objet} » est archivé.")
        return redirect(self.retour(objet, archive=True))


class CategorieArchiverView(_ArchiverView):
    modele = CategorieCatalogue

    def refus(self, objet):
        if objet.articles.filter(actif=True).exists() or objet.enfants.filter(actif=True).exists():
            return "Archivez d'abord les articles et sous-catégories de cette catégorie."
        return ""

    def retour(self, objet, archive):
        cible = objet.parent_id if archive else objet.pk
        return f"{reverse('catalogue')}?categorie={cible}" if cible else reverse("catalogue")


class ArticleArchiverView(_ArchiverView):
    modele = ArticleCatalogue

    def retour(self, objet, archive):
        return f"{reverse('catalogue')}?categorie={objet.categorie_id}"
