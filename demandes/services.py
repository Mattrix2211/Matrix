"""Règles métier des demandes bord–terre : visibilité, états, interlocuteurs, actions et notifications.

Une demande ne remplace aucun outil officiel : elle suit un échange et ses décisions, sur un objet de Matrix.
"""
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.utils import timezone

from accounts.models import AuditLog
from matrix.core.equipage import equipage_a_terre_lecture_seule
from matrix.core.mixins import build_scope_q
from matrix.core.scopes import equipage_marin_q, marins_hors_equipage
from matrix.core.role_thresholds import niveau_requis_pour
from matrix.core.roles import ROLE_TO_LEVEL, ROLES_SANS_ECRITURE_HERITEE
from notifications.liens import lien_objet
from notifications.models import Notification, NotificationLevel
from notifications.services import traiter_actions
from taches.models import Tache
from taches.services import peut_attribuer, peut_superviser
from threads.models import Message, Thread
from threads.utils import ajouter_commentaire

from .models import Demande

User = get_user_model()

# Objets sur lesquels on peut signaler une difficulté : ceux dont la fiche est accessible par lien.
OBJETS_SIGNALABLES = ("tache", "installation", "asset", "anomalie", "correctiveticket", "trainingcourse")

# Transitions permises : (état de départ) -> états d'arrivée, par rôle dans le dossier.
TRANSITIONS_RESPONSABLE = {
    Demande.ETAT_OUVERT: (Demande.ETAT_EN_TRAITEMENT, Demande.ETAT_EN_ATTENTE, Demande.ETAT_RESOLU),
    Demande.ETAT_EN_TRAITEMENT: (Demande.ETAT_EN_ATTENTE, Demande.ETAT_RESOLU),
    Demande.ETAT_EN_ATTENTE: (Demande.ETAT_EN_TRAITEMENT, Demande.ETAT_RESOLU),
}
TRANSITIONS_DECLARANT = {
    Demande.ETAT_EN_ATTENTE: (Demande.ETAT_OUVERT,),
    Demande.ETAT_RESOLU: (Demande.ETAT_CLOS, Demande.ETAT_OUVERT),
}
LIBELLES = dict(Demande.ETAT_CHOICES)


def _nom(user):
    return (user.get_full_name() or user.username) if user else "un marin supprimé"


def _dans_perimetre_chef(user, demande):
    return Demande.objects.filter(_perimetre_chef(user), pk=demande.pk).exists()


def peut_superviser_perimetre(user, demande):
    """Lecture : chef (seuil des tâches) dont le périmètre couvre le déclarant."""
    return peut_superviser(user) and _dans_perimetre_chef(user, demande)


def _perimetre_chef(user):
    """Périmètre d'un chef : son niveau organisationnel et, à double équipage, son équipage."""
    return build_scope_q(user, "") & equipage_marin_q(user, "declarant__profile__")


def est_acteur(user, demande):
    return user.pk in (demande.declarant_id, demande.responsable_id) or demande.interlocuteurs.filter(pk=user.pk).exists()


def peut_consulter(user, demande):
    return est_acteur(user, demande) or peut_superviser_perimetre(user, demande)


def peut_piloter(user, demande):
    """Responsable ou chef du périmètre (avec droit d'écriture) : ajoute des interlocuteurs, crée des actions, réaffecte."""
    return demande.ouverte and (
        user.pk == demande.responsable_id or (peut_attribuer(user) and _dans_perimetre_chef(user, demande))
    )


def demandes_visibles(user):
    base = Q(declarant=user) | Q(responsable=user) | Q(interlocuteurs=user)
    if peut_superviser(user):
        base |= _perimetre_chef(user)
    return Demande.objects.filter(base).distinct()


def responsables_possibles(declarant):
    """Chefs du navire du déclarant, qui peuvent prendre un dossier en charge."""
    navire = getattr(declarant.profile, "ship_id", None)
    if navire is None:
        return User.objects.none()
    seuil = niveau_requis_pour(declarant, "tache_attribution")
    roles = [code for code, niveau in ROLE_TO_LEVEL.items() if niveau >= seuil and code not in ROLES_SANS_ECRITURE_HERITEE]
    return User.objects.filter(
        profile__ship_id=navire, profile__role__in=roles, is_active=True,
    ).exclude(pk=declarant.pk).order_by("username")


def interlocuteurs_possibles(demande):
    """Marins du navire du déclarant (équipage à terre compris) pas encore sur le dossier."""
    navire = getattr(demande.declarant.profile, "ship_id", None)
    if navire is None:
        return User.objects.none()
    deja = [demande.declarant_id, demande.responsable_id, *demande.interlocuteurs.values_list("pk", flat=True)]
    return User.objects.filter(profile__ship_id=navire, is_active=True).exclude(pk__in=deja).order_by("username")


def trouver_objet(modele, pk, autorises=OBJETS_SIGNALABLES):
    """Objet désigné par « modèle:identifiant » parmi les modèles `autorises`, ou None."""
    if modele not in autorises:
        return None
    type_objet = ContentType.objects.filter(model=modele).first()
    if type_objet is None:
        return None
    try:
        return type_objet.get_object_for_this_type(pk=pk)
    except (ValueError, ValidationError, type_objet.model_class().DoesNotExist):
        return None


def _tracer(demande, acteur, action, extra=""):
    AuditLog.objects.create(
        actor=acteur, action=f"demande_{action}", target_user=demande.declarant,
        details=f"demande={demande.pk}; etat={demande.etat}{extra}",
    )


def _message_systeme(demande, corps):
    thread, _ = Thread.objects.get_or_create(
        content_type=ContentType.objects.get_for_model(demande), object_id=str(demande.pk),
    )
    Message.objects.create(thread=thread, author=None, body=corps, is_system=True)


def _notifier(demande, destinataires, verb, niveau=NotificationLevel.INFO, action=False):
    for user in destinataires:
        Notification.objects.create(user=user, verb=verb, level=niveau, target=demande, action_requise=action)


def _autres_acteurs(demande, sauf):
    return [u for u in demande.acteurs() if u.pk != sauf.pk]


def creer_demande(declarant, objet, titre, description, responsable, echeance=None, priorite=Demande.PRIORITE_NORMALE):
    if equipage_a_terre_lecture_seule(declarant):
        raise PermissionError("Votre équipage est à terre : seul l'équipage à bord peut signaler une difficulté.")
    if objet is None or lien_objet(declarant, objet) is None:
        raise PermissionError("Vous n'avez pas accès à cet élément.")
    if not responsables_possibles(declarant).filter(pk=getattr(responsable, "pk", None)).exists():
        raise ValidationError("Désignez un responsable parmi les chefs de votre bâtiment.")
    profil = declarant.profile
    demande = Demande(
        titre=titre.strip(), description=description.strip(), echeance=echeance, priorite=priorite,
        declarant=declarant, responsable=responsable, objet=objet,
        ship=profil.ship, service=profil.service, sector=profil.sector, section=profil.section,
        created_by=declarant, updated_by=declarant,
    )
    demande.full_clean(exclude=["declarant", "responsable", "content_type", "object_id"])
    demande.save()
    _tracer(demande, declarant, "creation")
    _message_systeme(demande, f"{_nom(declarant)} a signalé une difficulté sur « {objet} ». Responsable : {_nom(responsable)}.")
    _notifier(
        demande, [responsable], f"Nouvelle demande de {_nom(declarant)} : « {demande.titre} »",
        NotificationLevel.DANGER if priorite == Demande.PRIORITE_URGENTE else NotificationLevel.WARNING, action=True,
    )
    return demande


def repondre(demande, user, corps):
    if not peut_consulter(user, demande):
        raise PermissionError("Vous n'avez pas accès à cette demande.")
    if demande.etat == Demande.ETAT_CLOS:
        raise ValidationError("Cette demande est close.")
    corps = corps.strip()
    if not corps:
        raise ValidationError("Le message ne peut pas être vide.")
    message = ajouter_commentaire(demande, user, corps)
    cites = set(message.mentions.values_list("pk", flat=True))  # déjà alertés par la mention
    if demande.etat != Demande.ETAT_RESOLU:  # en « résolu », la clôture reste attendue du déclarant
        traiter_actions(demande, [user])
    if user.pk == demande.declarant_id and demande.etat == Demande.ETAT_EN_ATTENTE:
        _changer(demande, user, Demande.ETAT_OUVERT, "Information fournie.")
    attend_le_declarant = demande.etat == Demande.ETAT_EN_ATTENTE
    for destinataire in _autres_acteurs(demande, user):
        if destinataire.pk in cites:
            continue
        _notifier(
            demande, [destinataire], f"{_nom(user)} a répondu sur « {demande.titre} ».",
            NotificationLevel.WARNING if attend_le_declarant and destinataire.pk == demande.declarant_id else NotificationLevel.INFO,
            action=attend_le_declarant and destinataire.pk == demande.declarant_id,
        )


def _changer(demande, user, etat, note=""):
    ancien = demande.etat
    demande.etat = etat
    demande.updated_by = user
    champs = ["etat", "updated_by", "updated_at"]
    if etat == Demande.ETAT_RESOLU:
        demande.resolue_le = timezone.now()
        champs.append("resolue_le")
    demande.save(update_fields=champs)
    _tracer(demande, user, "etat", f"; de={ancien}")
    detail = f" — {note}" if note else ""
    _message_systeme(demande, f"{_nom(user)} : {LIBELLES[ancien]} → {LIBELLES[etat]}{detail}")


def changer_etat(demande, user, etat, note=""):
    if etat not in LIBELLES:
        raise ValidationError("État inconnu.")
    permis = set()
    if user.pk == demande.responsable_id:
        permis |= set(TRANSITIONS_RESPONSABLE.get(demande.etat, ()))
    if user.pk == demande.declarant_id:
        permis |= set(TRANSITIONS_DECLARANT.get(demande.etat, ()))
    if etat not in permis:
        raise PermissionError("Ce changement d'état ne vous est pas ouvert.")
    note = note.strip()
    if etat == Demande.ETAT_EN_ATTENTE and not note:
        raise ValidationError("Précisez l'information attendue du déclarant.")
    _changer(demande, user, etat, note)
    if note:
        ajouter_commentaire(demande, user, note)
    prevenus = set()
    if etat == Demande.ETAT_EN_ATTENTE:
        _notifier(demande, [demande.declarant], f"Information attendue sur « {demande.titre} » : {note}",
                  NotificationLevel.WARNING, action=True)
        prevenus.add(demande.declarant_id)
    elif etat == Demande.ETAT_RESOLU:
        traiter_actions(demande, [demande.responsable])
        _notifier(demande, [demande.declarant], f"« {demande.titre} » est résolue : confirmez la clôture.",
                  NotificationLevel.WARNING, action=True)
        prevenus.add(demande.declarant_id)
    elif etat == Demande.ETAT_OUVERT:
        _notifier(demande, [demande.responsable], f"{_nom(user)} rouvre « {demande.titre} ».",
                  NotificationLevel.WARNING, action=True)
        prevenus.add(demande.responsable_id)
    elif etat == Demande.ETAT_CLOS:
        traiter_actions(demande)
    if etat == Demande.ETAT_EN_TRAITEMENT:
        traiter_actions(demande, [demande.responsable])
    for autre in _autres_acteurs(demande, user):
        if autre.pk not in prevenus:
            _notifier(demande, [autre], f"« {demande.titre} » : {LIBELLES[etat]}.")


def reaffecter(demande, user, nouveau):
    if not peut_piloter(user, demande):
        raise PermissionError("Seul le responsable ou un chef du périmètre peut réaffecter.")
    if not responsables_possibles(demande.declarant).filter(pk=nouveau.pk).exists():
        raise ValidationError("Désignez un chef du bâtiment.")
    ancien = demande.responsable
    traiter_actions(demande, [ancien])
    demande.responsable, demande.updated_by = nouveau, user
    demande.save(update_fields=["responsable", "updated_by", "updated_at"])
    _tracer(demande, user, "reaffectation", f"; ancien={ancien.pk}")
    _message_systeme(demande, f"{_nom(user)} confie le dossier à {_nom(nouveau)}.")
    _notifier(demande, [nouveau], f"{_nom(user)} vous confie « {demande.titre} ».", NotificationLevel.WARNING, action=True)


def ajouter_interlocuteur(demande, user, cible):
    if not peut_piloter(user, demande):
        raise PermissionError("Seul le responsable ou un chef du périmètre peut ajouter un interlocuteur.")
    if not interlocuteurs_possibles(demande).filter(pk=cible.pk).exists():
        raise ValidationError("Cet interlocuteur n'appartient pas au bâtiment du dossier.")
    demande.interlocuteurs.add(cible)
    _tracer(demande, user, "interlocuteur")
    _message_systeme(demande, f"{_nom(user)} a ajouté {_nom(cible)} au dossier.")
    _notifier(demande, [cible], f"{_nom(user)} vous a ajouté à « {demande.titre} ».", NotificationLevel.WARNING)


def creer_action(demande, user, assigne, titre, echeance=None):
    """Action décidée dans le dossier : une tâche assignée, liée à la demande."""
    if not peut_piloter(user, demande):
        raise PermissionError("Seul le responsable ou un chef du périmètre peut assigner une action.")
    navire = getattr(demande.declarant.profile, "ship_id", None)
    if not User.objects.filter(pk=assigne.pk, profile__ship_id=navire, is_active=True).exists():
        raise ValidationError("Choisissez un marin du bâtiment.")
    if marins_hors_equipage(demande.declarant, [assigne]):
        raise ValidationError("Choisissez un marin de l'équipage du déclarant.")
    if equipage_a_terre_lecture_seule(assigne):
        raise ValidationError("Ce marin est à terre : assignez l'action à l'équipage à bord.")
    tache = Tache(
        titre=titre.strip(), echeance=echeance, assigne=assigne, demande=demande, created_by=user, updated_by=user,
        description=f"Action décidée dans la demande « {demande.titre} ».",
    )
    tache.full_clean(exclude=["assigne", "demande"])
    tache.save()
    _tracer(demande, user, "action", f"; tache={tache.pk}")
    delai = f", échéance {echeance:%d/%m/%Y}" if echeance else ""
    _message_systeme(demande, f"{_nom(user)} assigne l'action « {tache.titre} » à {_nom(assigne)}{delai}.")
    Notification.objects.create(
        user=assigne, verb=f"{_nom(user)} vous assigne « {tache.titre} » (demande « {demande.titre} »)",
        level=NotificationLevel.WARNING, target=tache, action_requise=True,
    )
    return tache


def action_terminee(tache):
    """Une action du dossier est faite : le fil et le responsable en sont informés."""
    demande = tache.demande
    _message_systeme(demande, f"Action terminée : « {tache.titre} » ({_nom(tache.assigne)}).")
    _notifier(demande, [demande.responsable], f"Action terminée sur « {demande.titre} » : {tache.titre}.")
