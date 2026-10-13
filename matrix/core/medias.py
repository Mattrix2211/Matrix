"""Service des fichiers téléversés (/media/…) : chaque fichier n'est livré que si
l'utilisateur peut consulter l'objet qui le porte, avec la règle de la fiche de cet objet.

Un chemin absent du registre, ou dont l'objet est hors périmètre, répond 404
(jamais d'indice sur l'existence). En production, `MEDIA_ACCEL_REDIRECT`
délègue l'envoi au serveur web une fois l'autorisation donnée (docs/REFERENCE.md)."""
import mimetypes
import posixpath
from dataclasses import dataclass
from functools import lru_cache
from typing import Callable

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import FileResponse, Http404, HttpResponse

from .mixins import build_scope_q
from .scopes import is_master_admin, ship_id_for_user

# Types affichés dans le navigateur ; tout le reste est téléchargé.
_TYPES_EN_LIGNE = ("image/png", "image/jpeg", "image/gif", "image/webp", "application/pdf")


@dataclass(frozen=True)
class FichierProtege:
    prefixe: str  # dossier d'envoi (upload_to)
    modele: type
    champ: str
    autorise: Callable  # (utilisateur, objet) -> bool


def _dans_perimetre(user, modele, pk):
    return modele.objects.filter(build_scope_q(user, ""), pk=pk).exists()


def _tout_connecte(user, objet):
    return True


@lru_cache(maxsize=1)
def registre():
    from assets.models import (
        ArticleCatalogue, Asset, AssetDocument, AssetFolder, CategorieCatalogue, Deck, DocumentInstallation,
        Installation, InstallationEventAttachment, InstallationMaintenanceAttachment, InstallationPart,
        PropositionArticle,
    )
    from assets.proposition_article import propositions_visibles
    from documentation.models import VersionDocument
    from documentation.services import peut_consulter as peut_consulter_document, versions_visibles
    from logistics.anomalie_views import anomalies_visibles
    from logistics.models import Anomalie, StockPiece
    from taches.models import PieceJointeTache
    from taches.services import peut_consulter as peut_consulter_tache
    from threads.models import Attachment
    from threads.views import _filtre_perimetre_threads
    from training.models import TrainingCourse, TrainingRecord, dossiers_formation_visibles_q

    def installation(user, installation_id):
        return _dans_perimetre(user, Installation, installation_id)

    def piece_jointe_fil(user, objet):
        filtre = _filtre_perimetre_threads(user, "message__thread__")
        return filtre is None or Attachment.objects.filter(filtre, pk=objet.pk).exists()

    def version_document(user, objet):
        return peut_consulter_document(user, objet.document) and versions_visibles(user, objet.document).filter(pk=objet.pk).exists()

    def pont(user, objet):
        return is_master_admin(user) or ship_id_for_user(user) == objet.ship_id

    return (
        FichierProtege("taches_pieces_jointes/", PieceJointeTache, "fichier", lambda u, o: peut_consulter_tache(u, o.tache)),
        FichierProtege("documentation/", VersionDocument, "fichier", version_document),
        FichierProtege("asset_photos/", Asset, "photo", lambda u, o: _dans_perimetre(u, Asset, o.pk)),
        FichierProtege("asset_docs/", AssetDocument, "file", lambda u, o: _dans_perimetre(u, Asset, o.asset_id)),
        FichierProtege("installation_photos/", Installation, "photo", lambda u, o: installation(u, o.pk)),
        FichierProtege("installation_docs/", DocumentInstallation, "fichier", lambda u, o: installation(u, o.installation_id)),
        FichierProtege("installation_events/", InstallationEventAttachment, "file",
                       lambda u, o: installation(u, o.event.installation_id)),
        FichierProtege("installation_parts/", InstallationPart, "photo", lambda u, o: installation(u, o.installation_id)),
        # Fiche d'entretien de la flotte (sans installation) : commune à tous les bâtiments.
        FichierProtege("installation_maintenance/", InstallationMaintenanceAttachment, "file",
                       lambda u, o: installation(u, o.maintenance.installation_id) if o.maintenance.installation_id else True),
        FichierProtege("deck_images/", Deck, "image", pont),
        FichierProtege("folder_photos/", AssetFolder, "photo", _tout_connecte),
        FichierProtege("catalogue_categories/", CategorieCatalogue, "photo", _tout_connecte),
        FichierProtege("catalogue_articles/", ArticleCatalogue, "photo", _tout_connecte),
        FichierProtege("catalogue_propositions/", PropositionArticle, "photo",
                       lambda u, o: propositions_visibles(u).filter(pk=o.pk).exists()),
        FichierProtege("stock_photos/", StockPiece, "photo", lambda u, o: _dans_perimetre(u, StockPiece, o.pk)),
        FichierProtege("anomalie_photos/", Anomalie, "photo",
                       lambda u, o: anomalies_visibles(u).filter(pk=o.pk).exists()),
        FichierProtege("thread_attachments/", Attachment, "file", piece_jointe_fil),
        FichierProtege("training_certificates/", TrainingRecord, "attachment",
                       lambda u, o: TrainingRecord.objects.filter(dossiers_formation_visibles_q(u), pk=o.pk).exists()),
        FichierProtege("training_baremes/", TrainingCourse, "bareme", _tout_connecte),
    )


def _chemin_normalise(chemin):
    normalise = posixpath.normpath(chemin)
    if normalise != chemin or normalise.startswith(("/", "..")) or "\\" in chemin or "\0" in chemin:
        raise Http404
    return normalise


@login_required
def servir_media(request, chemin):
    chemin = _chemin_normalise(chemin)
    for entree in registre():
        if not chemin.startswith(entree.prefixe):
            continue
        objets = entree.modele.objects.filter(**{entree.champ: chemin})
        if any(entree.autorise(request.user, objet) for objet in objets):
            return _reponse(chemin, getattr(objets[0], entree.champ))
    raise Http404


def _reponse(chemin, fichier):
    type_mime = mimetypes.guess_type(chemin)[0] or "application/octet-stream"
    en_ligne = type_mime in _TYPES_EN_LIGNE
    if settings.MEDIA_ACCEL_REDIRECT:
        reponse = HttpResponse(content_type=type_mime)
        reponse["X-Accel-Redirect"] = f"{settings.MEDIA_ACCEL_REDIRECT.rstrip('/')}/{chemin}"
        if not en_ligne:
            reponse["Content-Disposition"] = "attachment"
    else:
        try:
            reponse = FileResponse(fichier.open("rb"), as_attachment=not en_ligne, filename=posixpath.basename(chemin),
                                   content_type=type_mime)
        except FileNotFoundError:
            raise Http404
    reponse["X-Content-Type-Options"] = "nosniff"
    reponse["Cache-Control"] = "private"
    return reponse
