"""Écrans de la proposition d'un nouvel article au catalogue : rédaction, listes, détail, visas."""
from django import forms
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views import View

from . import proposition_article as circuit
from .catalogue_web import ArticleForm, _uuid_ou_none
from .models import ArticleCatalogue, CategorieCatalogue, PropositionArticle

Etat = PropositionArticle.Etat


def _libelle_categorie(categorie):
    noms = []
    while categorie is not None:
        noms.insert(0, categorie.nom)
        categorie = categorie.parent
    return " › ".join(noms)


class PropositionForm(ArticleForm):
    """Formulaire de l'article proposé (mêmes champs que l'article du catalogue)."""

    class Meta:
        model = PropositionArticle
        fields = ["designation", "categorie", "marque", "reference", "nno", "photo", "duree_vie_mois"]

    def __init__(self, *args, user, categories=None, sans_photo=False, **kwargs):
        super().__init__(*args, user=user, **kwargs)
        if sans_photo:
            del self.fields["photo"]
        qs = categories if categories is not None else CategorieCatalogue.objects.filter(actif=True)
        self.fields["categorie"].queryset = qs.select_related("specialite", "parent__parent")
        self.fields["categorie"].label_from_instance = lambda c: f"{c.specialite.name} › {_libelle_categorie(c)}"
        self.fields["categorie"].help_text = "La catégorie détermine le responsable de spécialité qui vérifiera l'article."

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("designation") and ArticleCatalogue.objects.filter(
                actif=True, designation__iexact=cleaned["designation"], marque__iexact=cleaned.get("marque") or "",
                reference__iexact=cleaned.get("reference") or "").exists():
            self.add_error("designation", "Cet article existe déjà au catalogue : cherchez-le plutôt que de le proposer.")
        return cleaned


def _proposition(request, pk):
    """Proposition visible par l'utilisateur ; sinon 404 (jamais d'indice hors périmètre)."""
    return get_object_or_404(circuit.propositions_visibles(request.user), pk=pk)


def _retour(proposition):
    return redirect("catalogue-proposition", pk=proposition.pk)


class PropositionsView(LoginRequiredMixin, View):
    """« À viser » (mon tour) et « Mes propositions »."""

    def get(self, request):
        visibles = circuit.propositions_visibles(request.user)
        a_viser = circuit.propositions_a_viser(request.user)
        identifiants = {p.pk for p in a_viser}
        mes = list(visibles.filter(created_by=request.user))
        autres = [p for p in visibles.exclude(created_by=request.user) if p.pk not in identifiants]
        return render(request, "assets/catalogue/propositions.html", {
            "a_viser": a_viser, "mes_propositions": mes, "autres": autres,
            "peut_proposer": circuit.peut_proposer(request.user)[0],
        })


class PropositionNouvelleView(LoginRequiredMixin, View):
    def _autoriser(self, request):
        autorise, raison = circuit.peut_proposer(request.user)
        if not autorise:
            raise PermissionDenied(raison)

    def _rendre(self, request, form):
        return render(request, "assets/catalogue/formulaire.html", {
            "form": form, "objet": None, "titre": "Proposer un article au catalogue",
            "introduction": "L'article sera visé par votre hiérarchie, vérifié par le responsable de spécialité, puis publié pour tous les bâtiments.",
            "bouton": "Soumettre la proposition", "annuler": reverse("catalogue-propositions"),
        })

    def get(self, request):
        self._autoriser(request)
        initial = {"designation": request.GET.get("designation", "")[:255], "categorie": _uuid_ou_none(request.GET.get("categorie"))}
        return self._rendre(request, PropositionForm(initial=initial, user=request.user))

    def post(self, request):
        self._autoriser(request)
        form = PropositionForm(request.POST, request.FILES, user=request.user)
        if not form.is_valid():
            return self._rendre(request, form)
        proposition = form.save(commit=False)
        try:
            circuit.soumettre(request.user, proposition)
        except circuit.ErreurCircuit as erreur:
            messages.error(request, str(erreur))
            return self._rendre(request, form)
        messages.success(request, "Proposition soumise : elle suit maintenant le circuit de visas.")
        return _retour(proposition)


class PropositionDetailView(LoginRequiredMixin, View):
    def get(self, request, pk):
        proposition = _proposition(request, pk)
        peut, _ = circuit.peut_agir(request.user, proposition)
        valideurs = circuit.valideurs(proposition) if proposition.etat in circuit.ETAPES else []
        return render(request, "assets/catalogue/proposition.html", {
            "proposition": proposition, "frise": circuit.frise(proposition), "peut_agir": peut,
            "est_verification": proposition.etat == Etat.VERIFICATION,
            "peut_corriger": proposition.etat == Etat.REFUSEE and proposition.created_by_id == request.user.pk
                             and circuit.peut_proposer(request.user)[0],
            "valideurs": valideurs, "blocage": circuit.message_blocage(proposition),
            "evenements": proposition.evenements.select_related("user"),
        })


class PropositionModifierView(LoginRequiredMixin, View):
    """Le rédacteur corrige une proposition renvoyée et la soumet de nouveau."""

    def _charger(self, request, pk):
        proposition = get_object_or_404(PropositionArticle, pk=pk, created_by=request.user)
        if proposition.etat != Etat.REFUSEE:
            raise PermissionDenied("Seule une proposition renvoyée peut être corrigée.")
        return proposition

    def _rendre(self, request, form, proposition):
        return render(request, "assets/catalogue/formulaire.html", {
            "form": form, "objet": proposition, "titre": "Corriger la proposition",
            "introduction": f"Motif du renvoi : {proposition.motif_refus}",
            "bouton": "Soumettre à nouveau", "annuler": reverse("catalogue-proposition", args=[proposition.pk]),
        })

    def get(self, request, pk):
        proposition = self._charger(request, pk)
        return self._rendre(request, PropositionForm(instance=proposition, user=request.user), proposition)

    def post(self, request, pk):
        proposition = self._charger(request, pk)
        form = PropositionForm(request.POST, request.FILES, instance=proposition, user=request.user)
        if not form.is_valid():
            return self._rendre(request, form, proposition)
        form.save(commit=False)
        try:
            circuit.resoumettre(request.user, proposition.pk, form)
        except circuit.ErreurCircuit as erreur:
            messages.error(request, str(erreur))
            return self._rendre(request, form, proposition)
        messages.success(request, "Proposition soumise à nouveau.")
        return _retour(proposition)


class _ActionView(LoginRequiredMixin, View):
    """POST d'une étape : l'étape attendue vient du formulaire affiché, pour refuser un envoi périmé."""

    def post(self, request, pk):
        proposition = _proposition(request, pk)
        etape = request.POST.get("etape", "")
        try:
            self.agir(request, proposition, etape)
        except circuit.ErreurCircuit as erreur:
            messages.error(request, str(erreur))
        return _retour(proposition)


class PropositionViserView(_ActionView):
    def agir(self, request, proposition, etape):
        circuit.viser(request.user, proposition.pk, etape)
        messages.success(request, "Visa enregistré.")


class PropositionRefuserView(_ActionView):
    def agir(self, request, proposition, etape):
        circuit.refuser(request.user, proposition.pk, etape, request.POST.get("motif"))
        messages.success(request, "Proposition renvoyée au rédacteur.")


class PropositionVerifierView(LoginRequiredMixin, View):
    """Le responsable de spécialité corrige l'article, puis le transmet ou le renvoie."""

    def _charger(self, request, pk):
        proposition = _proposition(request, pk)
        if proposition.etat != Etat.VERIFICATION or not circuit.peut_agir(request.user, proposition)[0]:
            raise PermissionDenied("Cette vérification n'est pas à votre charge.")
        return proposition

    def _rendre(self, request, form, proposition):
        return render(request, "assets/catalogue/formulaire.html", {
            "form": form, "objet": proposition, "titre": "Vérifier l'article proposé",
            "introduction": "Corrigez si besoin la désignation, la catégorie ou les références, puis transmettez à votre chef.",
            "bouton": "Vérifier et transmettre", "annuler": reverse("catalogue-proposition", args=[proposition.pk]),
            "etape": Etat.VERIFICATION,
        })

    def _formulaire(self, request, proposition, *donnees):
        categories = CategorieCatalogue.objects.filter(
            actif=True, specialite__responsables__user=request.user).distinct()
        return PropositionForm(*donnees, instance=proposition, user=request.user, categories=categories, sans_photo=True)

    def get(self, request, pk):
        proposition = self._charger(request, pk)
        return self._rendre(request, self._formulaire(request, proposition), proposition)

    def post(self, request, pk):
        proposition = self._charger(request, pk)
        form = self._formulaire(request, proposition, request.POST)
        if not form.is_valid():
            return self._rendre(request, form, proposition)
        form.save(commit=False)
        try:
            circuit.verifier(request.user, proposition.pk, form)
        except circuit.ErreurCircuit as erreur:
            messages.error(request, str(erreur))
            return _retour(proposition)
        messages.success(request, "Article vérifié et transmis.")
        return _retour(proposition)
