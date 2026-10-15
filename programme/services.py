"""Règles métier du programme du bâtiment : droits de saisie et délégation, types, ciblage, notifications."""
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.utils import timezone

from accounts.models import AuditLog
from annonces.services import chaine, cible_permise, cibles_autorisees, destinataires, filtre_ciblage, resoudre_cible
from matrix.core.equipage import equipage_a_terre_lecture_seule
from matrix.core.role_thresholds import niveau_requis_pour
from matrix.core.roles import user_role_level
from matrix.core.saisie import verifier_longueurs
from notifications.models import Notification, NotificationLevel
from notifications.services import creer_notifications_en_masse
from taches.services import taches_visibles

from .models import DelegationProgramme, EvenementProgramme, TypeProgramme

User = get_user_model()

TYPES_PAR_DEFAUT = (
    ("Escale", "#198754"), ("Arrêt technique", "#dc3545"), ("Exercice", "#fd7e14"), ("Réunion", "#0d6efd"),
)


def _nom(user):
    return (user.get_full_name() or user.username) if user else "un marin supprimé"


def _navire_id(user):
    return chaine(user)[0]


def types_du_navire(ship_id, seulement_actifs=True):
    """Types du navire ; ceux par défaut sont créés au premier accès (jamais sans bâtiment)."""
    if ship_id is None:
        return TypeProgramme.objects.none()
    if not TypeProgramme.objects.filter(ship_id=ship_id).exists():
        for nom, couleur in TYPES_PAR_DEFAUT:
            TypeProgramme.objects.create(ship_id=ship_id, nom=nom, couleur=couleur)
    types = TypeProgramme.objects.filter(ship_id=ship_id)
    return types.filter(actif=True) if seulement_actifs else types


def est_etat_major(user):
    return user_role_level(user) >= niveau_requis_pour(user, "programme_saisie")


def peut_saisir(user):
    if equipage_a_terre_lecture_seule(user) or not cibles_autorisees(user):
        return False
    navire = _navire_id(user)
    return est_etat_major(user) or DelegationProgramme.objects.filter(user=user, ship_id=navire).exists()


def peut_deleguer(user):
    return est_etat_major(user) and not equipage_a_terre_lecture_seule(user) and _navire_id(user) is not None


def peut_configurer_types(user):
    return user_role_level(user) >= niveau_requis_pour(user, "programme_types") and _navire_id(user) is not None


def _tracer(evenement, acteur, action):
    AuditLog.objects.create(actor=acteur, action=f"programme_{action}", details=f"evenement={evenement.pk}")


def _notifier(evenement, verb, niveau):
    creer_notifications_en_masse(
        Notification(user=u, verb=verb, level=niveau, target=evenement)
        for u in destinataires(evenement).exclude(pk=evenement.auteur_id)
    )


def _validations(titre, debut, fin):
    if not titre.strip():
        raise ValidationError("Le titre est obligatoire.")
    if debut is None:
        raise ValidationError("Indiquez la date de début.")
    if fin and fin < debut:
        raise ValidationError("La fin précède le début.")


def creer_evenement(auteur, titre, type_id, debut, fin, cible, lieu="", description="", equipage=""):
    if not peut_saisir(auteur):
        raise PermissionError("Vous ne pouvez pas saisir le programme du bâtiment.")
    if not cible_permise(auteur, cible):
        raise PermissionError("Ce public est hors de votre périmètre.")
    _validations(titre, debut, fin)
    verifier_longueurs(EvenementProgramme, titre=titre.strip(), lieu=lieu.strip(), equipage=equipage.strip())
    champs = resoudre_cible(cible)
    type_evenement = types_du_navire(champs["ship"].pk).filter(pk=type_id).first()
    if type_evenement is None:
        raise ValidationError("Choisissez un type d'événement.")
    evenement = EvenementProgramme.objects.create(
        titre=titre.strip(), description=description.strip(), type=type_evenement, debut=debut, fin=fin,
        lieu=lieu.strip(), equipage=equipage.strip(), auteur=auteur, created_by=auteur, updated_by=auteur, **champs,
    )
    _tracer(evenement, auteur, "cree")
    _notifier(evenement, f"Programme : {evenement.titre}, le {timezone.localtime(debut):%d/%m à %H:%M}.", NotificationLevel.INFO)
    return evenement


def peut_gerer(user, evenement):
    """L'auteur, ou l'état-major du bâtiment, tant qu'il garde le droit de saisie."""
    return peut_saisir(user) and (evenement.auteur_id == user.pk or (est_etat_major(user) and _navire_id(user) == evenement.ship_id))


def modifier_evenement(user, evenement, titre, debut, fin, lieu="", description=""):
    if not peut_gerer(user, evenement) or evenement.annule:
        raise PermissionError("Vous ne pouvez pas modifier cet événement.")
    _validations(titre, debut, fin)
    verifier_longueurs(EvenementProgramme, titre=titre.strip(), lieu=lieu.strip())
    horaire_change = (evenement.debut, evenement.fin) != (debut, fin)
    evenement.titre, evenement.debut, evenement.fin = titre.strip(), debut, fin
    evenement.lieu, evenement.description, evenement.updated_by = lieu.strip(), description.strip(), user
    evenement.save()
    _tracer(evenement, user, "modifie")
    if horaire_change:
        _notifier(evenement, f"Horaire modifié : {evenement.titre}, désormais le {timezone.localtime(debut):%d/%m à %H:%M}.", NotificationLevel.WARNING)


def annuler_evenement(user, evenement):
    if not peut_gerer(user, evenement):
        raise PermissionError("Vous ne pouvez pas annuler cet événement.")
    evenement.annule, evenement.updated_by = True, user
    evenement.save(update_fields=["annule", "updated_by", "updated_at"])
    _tracer(evenement, user, "annule")
    _notifier(evenement, f"Annulé : {evenement.titre}.", NotificationLevel.WARNING)


def lier_tache(user, evenement, tache_id):
    """Rattache une tâche préparatoire (visible de l'utilisateur) à l'événement."""
    if not peut_gerer(user, evenement):
        raise PermissionError("Vous ne pouvez pas modifier cet événement.")
    tache = taches_visibles(user).filter(pk=tache_id).first()
    if tache is None:
        raise ValidationError("Tâche introuvable.")
    evenement.taches.add(tache)
    _tracer(evenement, user, "tache")


def evenements_visibles(user):
    """Événements qui visent `user`, ou qu'il a saisis ; l'état-major voit tout son bâtiment."""
    ship = chaine(user)[0]
    visees = filtre_ciblage(user)
    filtre = visees | Q(auteur=user)
    if ship and est_etat_major(user):
        filtre |= Q(ship_id=ship)
    return EvenementProgramme.objects.filter(filtre).distinct()


def evenements_periode(user, debut, fin):
    """Événements non annulés de `user` qui chevauchent [debut, fin] (dates)."""
    return evenements_visibles(user).filter(
        annule=False, debut__date__lte=fin).filter(Q(fin__isnull=True, debut__date__gte=debut) | Q(fin__date__gte=debut)).select_related("type")


def deleguer(user, cible):
    if not peut_deleguer(user):
        raise PermissionError("Seul l'état-major peut déléguer la saisie du programme.")
    navire = _navire_id(user)
    if cible.profile.ship_id != navire:
        raise ValidationError("Ce marin n'appartient pas à votre bâtiment.")
    DelegationProgramme.objects.get_or_create(ship_id=navire, user=cible, defaults={"accordee_par": user})
    AuditLog.objects.create(actor=user, action="programme_delegation", target_user=cible, details="accordée")


def retirer_delegation(user, delegation_id):
    if not peut_deleguer(user):
        raise PermissionError("Seul l'état-major peut retirer une délégation.")
    delegation = DelegationProgramme.objects.filter(pk=delegation_id, ship_id=_navire_id(user)).first()
    if delegation:
        AuditLog.objects.create(actor=user, action="programme_delegation", target_user=delegation.user, details="retirée")
        delegation.delete()


def ajouter_type(user, nom, couleur):
    if not peut_configurer_types(user):
        raise PermissionError("Vous ne pouvez pas configurer les types.")
    nom = nom.strip()
    if not nom:
        raise ValidationError("Indiquez le nom du type.")
    if not (couleur.startswith("#") and len(couleur) == 7):
        couleur = "#0d6efd"
    navire = _navire_id(user)
    verifier_longueurs(TypeProgramme, nom=nom)
    types_du_navire(navire)
    TypeProgramme.objects.update_or_create(ship_id=navire, nom=nom, defaults={"couleur": couleur, "actif": True})


def basculer_type(user, type_id):
    if not peut_configurer_types(user):
        raise PermissionError("Vous ne pouvez pas configurer les types.")
    type_evenement = TypeProgramme.objects.filter(pk=type_id, ship_id=_navire_id(user)).first()
    if type_evenement:
        type_evenement.actif = not type_evenement.actif
        type_evenement.save(update_fields=["actif", "updated_at"])
