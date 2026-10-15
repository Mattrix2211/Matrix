"""Interface web de la documentation : bibliothèque, rédaction, fiche versionnée et circuit de validation."""
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ValidationError
from django.http import Http404, HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.dateparse import parse_date
from django.utils.http import url_has_allowed_host_and_scheme
from django.views import View

from annonces.services import cibles_autorisees
from demandes.services import trouver_objet
from matrix.core.saisie import entier_ou_none
from matrix.core.validators import valider_document

from . import services
from .models import Document, VersionDocument
from .services import peut_rediger, peut_valider


def _erreurs(request, exc):
    if isinstance(exc, PermissionError):
        messages.error(request, str(exc))
    else:
        for liste in getattr(exc, "message_dict", {"": exc.messages}).values():
            for erreur in liste:
                messages.error(request, erreur)


def _fichier(request):
    fichier = request.FILES.get("fichier")
    if fichier:
        try:
            valider_document(fichier)
        except ValidationError as exc:
            raise ValidationError(f"Fichier refusé : {' '.join(exc.messages)}")
    return fichier


def _date(saisie):
    saisie = (saisie or "").strip()
    if not saisie:
        return None
    valeur = parse_date(saisie)
    if valeur is None:
        raise ValidationError("Indiquez une date valide.")
    return valeur


class BibliothequeView(LoginRequiredMixin, View):
    def get(self, request):
        recherche = (request.GET.get("q") or "").strip()[:80]
        domaine = (request.GET.get("domaine") or "").strip()
        documents = (services.rechercher(request.user, recherche) if recherche else services.documents_visibles(request.user))
        documents = documents.select_related("ship", "service", "sector", "section").prefetch_related("versions")
        if domaine:
            documents = documents.filter(domaine=domaine)
        documents = list(documents)
        for document in documents:
            document.applicable = next((v for v in document.versions.all() if v.etat == VersionDocument.ETAT_PUBLIEE), None)
            document.en_attente = any(v.etat == VersionDocument.ETAT_SOUMISE for v in document.versions.all())
        domaines = sorted(set(services.documents_visibles(request.user).exclude(domaine="").values_list("domaine", flat=True)))
        return render(request, "documentation/index.html", {
            "documents": documents, "recherche": recherche, "domaine": domaine, "domaines": domaines,
            "peut_rediger": peut_rediger(request.user), "a_reviser": services.a_reviser(request.user)[:5],
        })


class DocumentNouveauView(LoginRequiredMixin, View):
    def get(self, request):
        if not peut_rediger(request.user):
            raise Http404
        return render(request, "documentation/nouveau.html", {
            "cibles": cibles_autorisees(request.user), "origines": Document.ORIGINE_CHOICES})

    def post(self, request):
        try:
            document = services.creer_document(
                request.user, request.POST.get("titre", ""), request.POST.get("cible", ""), request.POST.get("contenu", ""),
                request.POST.get("domaine", ""), request.POST.get("origine", ""), request.POST.get("reference_source", ""),
                request.POST.get("equipage", ""), _date(request.POST.get("prochaine_revision")), _fichier(request))
        except PermissionError as exc:
            _erreurs(request, exc)
            return redirect("document-nouveau")
        except ValidationError as exc:
            _erreurs(request, exc)
            # Le formulaire est réaffiché avec la saisie, sans rien perdre.
            return render(request, "documentation/nouveau.html", {
                "cibles": cibles_autorisees(request.user), "origines": Document.ORIGINE_CHOICES, "saisie": request.POST})
        messages.success(request, "Brouillon enregistré : soumettez-le à validation pour le publier.")
        return redirect("document-detail", pk=document.pk)


class DocumentDetailView(LoginRequiredMixin, View):
    def get(self, request, pk):
        document = get_object_or_404(Document.objects.select_related("ship", "service", "sector", "section"), pk=pk)
        if not services.peut_consulter(request.user, document):
            raise Http404
        versions = list(services.versions_visibles(request.user, document))
        valide = peut_valider(request.user, document)
        return render(request, "documentation/detail.html", {
            "document": document, "versions": versions,
            "applicable": next((v for v in versions if v.etat == VersionDocument.ETAT_PUBLIEE), None),
            "ouvertes": [v for v in versions if v.etat in VersionDocument.ETATS_OUVERTS],
            "historique": [v for v in versions if v.etat not in (VersionDocument.ETAT_PUBLIEE,) + VersionDocument.ETATS_OUVERTS],
            "peut_valider": valide, "moi": request.user,
            "peut_proposer": not document.archive and not document.versions.filter(etat__in=VersionDocument.ETATS_OUVERTS).exists(),
        })


class DocumentActionView(LoginRequiredMixin, View):
    def post(self, request, pk):
        document = get_object_or_404(Document, pk=pk)
        if not services.peut_consulter(request.user, document):
            raise Http404
        action = request.POST.get("action")
        try:
            if action == "proposer":
                services.proposer_amelioration(request.user, document, request.POST.get("contenu", ""), request.POST.get("resume", ""), _fichier(request))
                messages.success(request, "Proposition transmise : la version applicable reste en vigueur jusqu'à validation.")
            elif action in ("soumettre", "valider", "refuser"):
                version = get_object_or_404(VersionDocument, pk=entier_ou_none(request.POST.get("version")), document=document)
                if version.etat == VersionDocument.ETAT_BROUILLON and version.auteur_id != request.user.pk and not peut_valider(request.user, document):
                    raise Http404
                if action == "soumettre":
                    services.soumettre(request.user, version)
                elif action == "valider":
                    services.valider(request.user, version)
                    messages.success(request, "Version publiée : l'ancienne est conservée dans l'historique.")
                else:
                    services.refuser(request.user, version, request.POST.get("motif", ""))
            elif action == "archiver":
                services.archiver(request.user, document)
            else:
                return HttpResponseBadRequest("Action inconnue.")
        except (PermissionError, ValidationError) as exc:
            _erreurs(request, exc)
        return redirect("document-detail", pk=document.pk)


class DocumentLierView(LoginRequiredMixin, View):
    """Associe un document à l'objet de la page d'où part la demande (tâche, installation, formation)."""

    def post(self, request):
        suite = request.POST.get("suite", "")
        retour = suite if url_has_allowed_host_and_scheme(suite, allowed_hosts=None) and suite.startswith("/") else reverse("documentation-index")
        document = get_object_or_404(Document, pk=entier_ou_none(request.POST.get("document")))
        if not services.peut_consulter(request.user, document):
            raise Http404
        modele, _, pk = request.POST.get("objet", "").partition(":")
        objet = trouver_objet(modele, pk)
        try:
            if objet is None:
                raise ValidationError("Élément introuvable.")
            services.lier(request.user, document, objet)
        except (PermissionError, ValidationError) as exc:
            _erreurs(request, exc)
        return redirect(retour)
