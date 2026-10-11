"""Règles métier de la documentation : ciblage, circuit proposer → valider → publier, versions et liens contextuels."""
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.db.models import Exists, OuterRef, Q
from django.utils import timezone

from accounts.models import AuditLog
from annonces.services import cible_permise, cibles_autorisees, filtre_ciblage, filtre_gestion, resoudre_cible
from matrix.core.equipage import equipage_a_terre_lecture_seule
from matrix.core.role_thresholds import niveau_requis_pour, seuil_role
from matrix.core.roles import user_role_level
from notifications.liens import lien_objet
from notifications.models import Notification, NotificationLevel
from notifications.services import creer_notifications_en_masse, traiter_actions

from .models import Document, LienDocument, VersionDocument

User = get_user_model()
JOURS_ALERTE_REVISION = 30


def _nom(user):
    return (user.get_full_name() or user.username) if user else "un marin supprimé"


def _noeud(document):
    for modele in ("section", "sector", "service"):
        if getattr(document, f"{modele}_id"):
            return f"{modele}:{getattr(document, f'{modele}_id')}"
    return f"ship:{document.ship_id}"


def peut_rediger(user):
    return (
        not equipage_a_terre_lecture_seule(user)
        and user_role_level(user) >= niveau_requis_pour(user, "documentation_redaction")
        and bool(cibles_autorisees(user))
    )


def peut_valider(user, document):
    return (
        not equipage_a_terre_lecture_seule(user)
        and user_role_level(user) >= niveau_requis_pour(user, "documentation_validation")
        and cible_permise(user, _noeud(document))
    )


def _gere(user):
    """Q (sur Document) des documents du périmètre de rédaction ou de validation de `user`."""
    if user_role_level(user) < min(niveau_requis_pour(user, "documentation_redaction"), niveau_requis_pour(user, "documentation_validation")):
        return Q(pk__in=[])
    return filtre_gestion(user)


def documents_visibles(user):
    """Documents publiés qui visent `user` ; l'auteur d'une version et les gestionnaires voient aussi les autres."""
    publiee = Exists(VersionDocument.objects.filter(document=OuterRef("pk"), etat=VersionDocument.ETAT_PUBLIEE))
    lecteur = Q(archive=False) & filtre_ciblage(user)
    return Document.objects.filter(
        (lecteur & Q(pk__in=Document.objects.filter(publiee).values("pk"))) | _gere(user) | Q(versions__auteur=user)
    ).distinct()


def peut_consulter(user, document):
    return documents_visibles(user).filter(pk=document.pk).exists()


def versions_visibles(user, document):
    """Version applicable et historique pour tous ; brouillons, propositions et refus pour l'auteur et les gestionnaires."""
    versions = document.versions.all()
    if peut_valider(user, document) or Document.objects.filter(_gere(user), pk=document.pk).exists():
        return versions
    return versions.filter(Q(etat__in=(VersionDocument.ETAT_PUBLIEE, VersionDocument.ETAT_OBSOLETE)) | Q(auteur=user))


def _tracer(version, acteur, action):
    AuditLog.objects.create(
        actor=acteur, action=f"document_{action}", details=f"document={version.document_id}; version={version.numero}")


def valideurs(document):
    """Marins du bâtiment habilités à valider ce document (sauf l'éventuel auteur, exclu à l'usage)."""
    seuil = seuil_role("documentation_validation", document.ship_id)
    return [
        u for u in User.objects.filter(profile__ship_id=document.ship_id, is_active=True)
        if user_role_level(u) >= seuil and peut_valider(u, document)
    ]


def _notifier_valideurs(version):
    document = version.document
    creer_notifications_en_masse(
        Notification(
            user=u, level=NotificationLevel.WARNING, target=document, action_requise=True,
            verb=f"Document à valider : « {document.titre} » v{version.numero}, proposé par {_nom(version.auteur)}.",
        ) for u in valideurs(document) if u.pk != version.auteur_id
    )


def _controles(titre, contenu, fichier):
    if not titre.strip():
        raise ValidationError("Le titre est obligatoire.")
    if not contenu.strip() and not fichier:
        raise ValidationError("Rédigez le contenu ou joignez un fichier.")


def creer_document(user, titre, cible, contenu, domaine="", origine=Document.ORIGINE_LOCALE, reference_source="",
                   equipage="", prochaine_revision=None, fichier=None):
    if not peut_rediger(user):
        raise PermissionError("Vous ne pouvez pas rédiger de document.")
    if not cible_permise(user, cible):
        raise PermissionError("Ce public est hors de votre périmètre.")
    _controles(titre, contenu, fichier)
    if origine not in dict(Document.ORIGINE_CHOICES):
        origine = Document.ORIGINE_LOCALE
    if origine == Document.ORIGINE_OFFICIELLE and not reference_source.strip():
        raise ValidationError("Une procédure officielle cite sa source (référence du texte).")
    document = Document.objects.create(
        titre=titre.strip(), domaine=domaine.strip(), origine=origine, reference_source=reference_source.strip(),
        equipage=equipage.strip(), prochaine_revision=prochaine_revision, created_by=user, updated_by=user,
        **resoudre_cible(cible),
    )
    version = VersionDocument.objects.create(document=document, numero=1, contenu=contenu.strip(), fichier=fichier, auteur=user)
    _tracer(version, user, "cree")
    return document


def soumettre(user, version):
    if version.etat != VersionDocument.ETAT_BROUILLON:
        raise ValidationError("Seul un brouillon peut être soumis.")
    if user.pk != version.auteur_id and not peut_valider(user, version.document):
        raise PermissionError("Seul l'auteur peut soumettre ce brouillon.")
    version.etat = VersionDocument.ETAT_SOUMISE
    version.save(update_fields=["etat", "updated_at"])
    _tracer(version, user, "soumis")
    _notifier_valideurs(version)


def proposer_amelioration(user, document, contenu, resume="", fichier=None):
    """Tout marin qui voit le document propose une nouvelle version ; l'ancienne reste applicable jusqu'à validation."""
    if not peut_consulter(user, document):
        raise PermissionError("Vous n'avez pas accès à ce document.")
    if equipage_a_terre_lecture_seule(user):
        raise PermissionError("Votre équipage est à terre : la proposition est réservée à l'équipage à bord.")
    if document.archive:
        raise ValidationError("Ce document est archivé.")
    if document.versions.filter(etat__in=VersionDocument.ETATS_OUVERTS).exists():
        raise ValidationError("Une proposition est déjà en cours de validation.")
    _controles(document.titre, contenu, fichier)
    numero = (document.versions.order_by("-numero").values_list("numero", flat=True).first() or 0) + 1
    version = VersionDocument.objects.create(
        document=document, numero=numero, contenu=contenu.strip(), fichier=fichier, resume=resume.strip()[:300],
        etat=VersionDocument.ETAT_SOUMISE, auteur=user)
    _tracer(version, user, "propose")
    _notifier_valideurs(version)
    return version


def valider(user, version):
    document = version.document
    if version.etat != VersionDocument.ETAT_SOUMISE:
        raise ValidationError("Cette version n'est pas soumise à validation.")
    if not peut_valider(user, document):
        raise PermissionError("Vous ne pouvez pas valider ce document.")
    if user.pk == version.auteur_id:
        raise PermissionError("Une version ne se valide pas soi-même.")
    document.versions.filter(etat=VersionDocument.ETAT_PUBLIEE).update(etat=VersionDocument.ETAT_OBSOLETE)
    version.etat, version.valide_par, version.valide_le = VersionDocument.ETAT_PUBLIEE, user, timezone.now()
    version.date_effet = timezone.localdate()
    version.save()
    _tracer(version, user, "publie")
    traiter_actions(document)
    if version.auteur_id:
        Notification.objects.create(
            user=version.auteur, level=NotificationLevel.INFO, target=document,
            verb=f"Votre version {version.numero} de « {document.titre} » est publiée.")


def refuser(user, version, motif):
    if version.etat != VersionDocument.ETAT_SOUMISE:
        raise ValidationError("Cette version n'est pas soumise à validation.")
    if not peut_valider(user, version.document):
        raise PermissionError("Vous ne pouvez pas valider ce document.")
    if not motif.strip():
        raise ValidationError("Indiquez le motif du refus.")
    version.etat, version.motif_refus, version.valide_par, version.valide_le = (
        VersionDocument.ETAT_REFUSEE, motif.strip(), user, timezone.now())
    version.save()
    _tracer(version, user, "refuse")
    traiter_actions(version.document)
    if version.auteur_id:
        Notification.objects.create(
            user=version.auteur, level=NotificationLevel.WARNING, target=version.document,
            verb=f"Votre version {version.numero} de « {version.document.titre} » est refusée : {version.motif_refus}")


def archiver(user, document):
    if not peut_valider(user, document):
        raise PermissionError("Vous ne pouvez pas archiver ce document.")
    document.archive, document.updated_by = True, user
    document.save(update_fields=["archive", "updated_by", "updated_at"])
    traiter_actions(document)
    AuditLog.objects.create(actor=user, action="document_archive", details=f"document={document.pk}")


def lier(user, document, objet):
    """Affiche le document au contexte d'un objet (tâche, installation, formation) auquel `user` accède."""
    if not (peut_valider(user, document) or Document.objects.filter(_gere(user), pk=document.pk).exists()):
        raise PermissionError("Vous ne pouvez pas lier ce document.")
    if lien_objet(user, objet) is None:
        raise PermissionError("Vous n'avez pas accès à cet élément.")
    LienDocument.objects.get_or_create(
        document=document, content_type=ContentType.objects.get_for_model(objet), object_id=str(objet.pk))


def documents_associes(user, objet):
    """Documents applicables liés à `objet`, que `user` peut lire."""
    liens = LienDocument.objects.filter(
        content_type=ContentType.objects.get_for_model(objet), object_id=str(objet.pk)).values("document_id")
    publiee = Exists(VersionDocument.objects.filter(document=OuterRef("pk"), etat=VersionDocument.ETAT_PUBLIEE))
    return documents_visibles(user).filter(pk__in=liens, archive=False).filter(publiee)


def a_reviser(user):
    """Documents du périmètre de `user` dont la révision est échue ou proche (gestionnaires seulement)."""
    limite = timezone.localdate() + timedelta(days=JOURS_ALERTE_REVISION)
    return Document.objects.filter(_gere(user), archive=False, prochaine_revision__isnull=False, prochaine_revision__lte=limite).order_by("prochaine_revision")


def peut_gerer_liens(user):
    return peut_rediger(user) or user_role_level(user) >= niveau_requis_pour(user, "documentation_validation")


def documents_liables(user, objet):
    """Documents publiés que `user` gère et qui ne sont pas encore liés à `objet`."""
    deja = LienDocument.objects.filter(
        content_type=ContentType.objects.get_for_model(objet), object_id=str(objet.pk)).values("document_id")
    publiee = Exists(VersionDocument.objects.filter(document=OuterRef("pk"), etat=VersionDocument.ETAT_PUBLIEE))
    return list(Document.objects.filter(_gere(user), archive=False).filter(publiee).exclude(pk__in=deja)[:50])
