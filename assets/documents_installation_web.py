"""Documents d'une installation (plans, notices, procédures) : ajout, suppression et téléchargement.
Lecture selon le périmètre ; ajout au seuil `installation_ecriture_simple`, suppression au seuil
`installation_gestion_avancee` (configurables par navire) ; refus à terre ; tout est tracé dans l'AuditLog."""
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied, ValidationError
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect
from django.views import View

from accounts.models import AuditLog
from matrix.core.equipage import equipage_a_terre_lecture_seule
from matrix.core.mixins import build_scope_q
from matrix.core.role_thresholds import niveau_requis_pour
from matrix.core.roles import user_role_level

from .fichiers import valider_document
from .models import DocumentInstallation, Installation


def peut_ajouter_document(user):
    return (user_role_level(user) >= niveau_requis_pour(user, "installation_ecriture_simple")
            and not equipage_a_terre_lecture_seule(user))


def peut_supprimer_document(user):
    return (user_role_level(user) >= niveau_requis_pour(user, "installation_gestion_avancee")
            and not equipage_a_terre_lecture_seule(user))


class _DocumentInstallationView(LoginRequiredMixin, View):
    http_method_names = ["post"]

    def installation(self, request, pk):
        """Installation du périmètre de l'appelant ; hors périmètre, elle est introuvable."""
        return get_object_or_404(Installation.objects.filter(build_scope_q(request.user, "")), pk=pk)

    def retour(self, installation):
        return redirect("installation-detail", pk=installation.pk)


class DocumentInstallationAjouterView(_DocumentInstallationView):
    def post(self, request, pk):
        installation = self.installation(request, pk)
        if not peut_ajouter_document(request.user):
            raise PermissionDenied
        fichier = request.FILES.get("fichier")
        titre = request.POST.get("titre", "").strip() or (fichier.name if fichier else "")
        type_document = request.POST.get("type_document", "")
        if type_document not in dict(DocumentInstallation.TYPES):
            type_document = "autre"
        try:
            if not fichier:
                raise ValidationError("Choisissez un fichier.")
            if len(titre) > 255:
                raise ValidationError("Titre trop long (255 caractères au plus).")
            valider_document(fichier)
        except ValidationError as erreur:
            messages.error(request, " ".join(erreur.messages))
            return self.retour(installation)
        document = DocumentInstallation.objects.create(
            installation=installation, titre=titre, type_document=type_document, fichier=fichier,
            notes=request.POST.get("notes", "").strip(), created_by=request.user, updated_by=request.user)
        AuditLog.objects.create(actor=request.user, action="installation.document_ajout",
                                details=f"installation={installation.pk} document={document.pk} titre={titre}")
        messages.success(request, "Document ajouté.")
        return self.retour(installation)


class DocumentInstallationSupprimerView(_DocumentInstallationView):
    def post(self, request, pk, document_pk):
        installation = self.installation(request, pk)
        if not peut_supprimer_document(request.user):
            raise PermissionDenied
        document = get_object_or_404(installation.documents, pk=document_pk)
        AuditLog.objects.create(actor=request.user, action="installation.document_suppression",
                                details=f"installation={installation.pk} document={document.pk} titre={document.titre}")
        document.fichier.delete(save=False)
        document.delete()
        messages.success(request, "Document supprimé.")
        return self.retour(installation)


class DocumentInstallationTelechargerView(_DocumentInstallationView):
    http_method_names = ["get"]

    def get(self, request, pk, document_pk):
        installation = self.installation(request, pk)
        document = get_object_or_404(installation.documents, pk=document_pk)
        try:
            reponse = FileResponse(document.fichier.open("rb"), as_attachment=True)
        except FileNotFoundError:
            raise Http404("Fichier introuvable.")
        # Téléchargement forcé : jamais d'affichage en ligne, donc pas de contenu actif servi depuis notre domaine.
        reponse["X-Content-Type-Options"] = "nosniff"
        return reponse
