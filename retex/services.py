"""Règles métier du RETEX : proposition depuis une source, routage par domaine, décision, publication et actions."""
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.utils import timezone

from accounts.models import AuditLog
from annonces.services import chaine
from demandes.services import OBJETS_SIGNALABLES
from documentation.models import Document, VersionDocument
from matrix.core.equipage import equipage_a_terre_lecture_seule
from matrix.core.role_thresholds import niveau_requis_pour, seuil_role
from matrix.core.roles import user_role_level
from notifications.liens import lien_objet
from notifications.models import Notification, NotificationLevel
from notifications.services import creer_notifications_en_masse, traiter_actions
from taches.models import Tache

from .models import DomaineRetex, Retex

User = get_user_model()
OBJETS_RETEX = (*OBJETS_SIGNALABLES, "demande")

# Routage du cadrage métier : domaine du bord → COMA référent → organisme habituel.
DOMAINES_PAR_DEFAUT = (
    ("Opérations et missions", "COMOPS", "ALFAN / Entraînement"),
    ("Technique, sécurité matérielle, MCO", "COMANAV", "SSF / ERO / IRB puis ERDT / IRDT"),
    ("Service courant, protection, vie à bord", "COMAEQ", "ALFAN / Exploitation"),
    ("Aviation", "COMAVIA", "ALFAN / Exploitation"),
)


def _nom(user):
    return (user.get_full_name() or user.username) if user else "un marin supprimé"


def domaines_du_navire(ship_id, seulement_actifs=True):
    if not DomaineRetex.objects.filter(ship_id=ship_id).exists():
        for nom, coma, organisme in DOMAINES_PAR_DEFAUT:
            DomaineRetex.objects.create(ship_id=ship_id, nom=nom, coma=coma, organisme=organisme)
    domaines = DomaineRetex.objects.filter(ship_id=ship_id)
    return domaines.filter(actif=True) if seulement_actifs else domaines


def peut_valider(user, retex):
    return (
        not equipage_a_terre_lecture_seule(user)
        and chaine(user)[0] == retex.ship_id
        and user_role_level(user) >= niveau_requis_pour(user, "retex_validation")
    )


def valideurs(retex):
    """Habilités du bâtiment ; ceux dont la fonction cite le COMA référent du domaine passent en premier."""
    seuil = seuil_role("retex_validation", retex.ship_id)
    habilites = [u for u in User.objects.filter(profile__ship_id=retex.ship_id, is_active=True)
                 if user_role_level(u) >= seuil and not equipage_a_terre_lecture_seule(u)]
    coma = retex.domaine.coma.lower()
    habilites.sort(key=lambda u: (coma not in (u.profile.fonction_service or "").lower(), u.username))
    return habilites


def peut_consulter(user, retex):
    return user.pk == retex.auteur_id or peut_valider(user, retex) or (
        retex.etat == Retex.ETAT_VALIDE and chaine(user)[0] == retex.ship_id)


def retex_visibles(user):
    ship = chaine(user)[0]
    return [r for r in Retex.objects.select_related("domaine", "auteur").filter(ship_id=ship) if peut_consulter(user, r)] if ship else []


def _tracer(retex, acteur, action):
    AuditLog.objects.create(actor=acteur, action=f"retex_{action}", details=f"retex={retex.pk}")


def proposer(user, titre, constat, enseignement, domaine_id, organisme="", causes="", recommandation="", portee="",
             diffusion="BATIMENT", source=None):
    ship = chaine(user)[0]
    if ship is None:
        raise PermissionError("Vous n'êtes rattaché à aucun bâtiment.")
    if equipage_a_terre_lecture_seule(user):
        raise PermissionError("Votre équipage est à terre : la proposition est réservée à l'équipage à bord.")
    if source is not None and lien_objet(user, source) is None:
        raise PermissionError("Vous n'avez pas accès à cette source.")
    domaine = domaines_du_navire(ship).filter(pk=domaine_id or None).first()
    if domaine is None:
        raise ValidationError("Choisissez le domaine du RETEX.")
    if not titre.strip() or not constat.strip() or not enseignement.strip():
        raise ValidationError("Le titre, le constat et l'enseignement sont obligatoires.")
    retex = Retex(
        titre=titre.strip(), constat=constat.strip(), causes=causes.strip(), enseignement=enseignement.strip(),
        recommandation=recommandation.strip(), portee=portee.strip(), domaine=domaine, ship_id=ship, auteur=user,
        organisme=(organisme or domaine.organisme).strip(), created_by=user, updated_by=user,
        diffusion=diffusion if diffusion in dict(Retex.DIFFUSION_CHOICES) else "BATIMENT",
    )
    if source is not None:
        retex.source, retex.source_libelle = source, str(source)[:200]
    retex.save()
    _tracer(retex, user, "propose")
    creer_notifications_en_masse(
        Notification(
            user=u, level=NotificationLevel.WARNING, target=retex, action_requise=True,
            verb=f"RETEX à examiner ({domaine.coma or domaine.nom}) : « {retex.titre} », proposé par {_nom(user)}.")
        for u in valideurs(retex) if u.pk != user.pk)
    return retex


def _publier(retex, decideur):
    """Le RETEX validé devient un document de la base de connaissances du bâtiment, déjà publié."""
    contenu = f"Constat\n{retex.constat}\n\n"
    if retex.causes:
        contenu += f"Causes et analyses\n{retex.causes}\n\n"
    contenu += f"Enseignement\n{retex.enseignement}"
    if retex.recommandation:
        contenu += f"\n\nRecommandation\n{retex.recommandation}"
    document = Document.objects.create(
        titre=f"RETEX : {retex.titre}", domaine="RETEX", origine=Document.ORIGINE_LOCALE, ship_id=retex.ship_id,
        created_by=decideur, updated_by=decideur,
        reference_source=f"RETEX validé le {timezone.localdate():%d/%m/%Y}" + (f" ; source : {retex.source_libelle}" if retex.source_libelle else ""))
    VersionDocument.objects.create(
        document=document, numero=1, contenu=contenu, etat=VersionDocument.ETAT_PUBLIEE, auteur=retex.auteur,
        valide_par=decideur, valide_le=timezone.now(), date_effet=timezone.localdate())
    retex.document = document


def valider(user, retex, motif=""):
    if retex.etat != Retex.ETAT_PROPOSE:
        raise ValidationError("Ce RETEX a déjà été décidé.")
    if not peut_valider(user, retex):
        raise PermissionError("Vous ne pouvez pas valider ce RETEX.")
    retex.etat, retex.decide_par, retex.decide_le, retex.motif_decision = Retex.ETAT_VALIDE, user, timezone.now(), motif.strip()
    _publier(retex, user)
    retex.save()
    _tracer(retex, user, "valide")
    traiter_actions(retex)
    if retex.auteur_id:
        Notification.objects.create(
            user=retex.auteur, level=NotificationLevel.INFO, target=retex.document or retex,
            verb=f"Votre RETEX « {retex.titre} » est validé et publié dans la documentation.")


def refuser(user, retex, motif):
    if retex.etat != Retex.ETAT_PROPOSE:
        raise ValidationError("Ce RETEX a déjà été décidé.")
    if not peut_valider(user, retex):
        raise PermissionError("Vous ne pouvez pas décider de ce RETEX.")
    if not motif.strip():
        raise ValidationError("Indiquez le motif du refus.")
    retex.etat, retex.decide_par, retex.decide_le, retex.motif_decision = Retex.ETAT_REFUSE, user, timezone.now(), motif.strip()
    retex.save()
    _tracer(retex, user, "refuse")
    traiter_actions(retex)
    if retex.auteur_id:
        Notification.objects.create(
            user=retex.auteur, level=NotificationLevel.WARNING, target=retex,
            verb=f"Votre RETEX « {retex.titre} » est refusé : {retex.motif_decision}")


def creer_action(user, retex, assigne, titre, echeance=None):
    """Action décidée : une tâche assignée et suivie, liée au RETEX."""
    if retex.etat != Retex.ETAT_VALIDE or not peut_valider(user, retex):
        raise PermissionError("Seule une décision de validation permet d'assigner une action.")
    if not User.objects.filter(pk=assigne.pk, profile__ship_id=retex.ship_id, is_active=True).exists() or equipage_a_terre_lecture_seule(assigne):
        raise ValidationError("Choisissez un marin du bâtiment, à bord.")
    tache = Tache(titre=titre.strip(), echeance=echeance, assigne=assigne, created_by=user, updated_by=user,
                  description=f"Action issue du RETEX « {retex.titre} ».")
    tache.full_clean(exclude=["assigne", "demande"])
    tache.save()
    retex.taches.add(tache)
    _tracer(retex, user, "action")
    Notification.objects.create(
        user=assigne, level=NotificationLevel.WARNING, target=tache, action_requise=True,
        verb=f"{_nom(user)} vous assigne « {tache.titre} » (RETEX « {retex.titre} »)")
    return tache


def clore(user, retex):
    if retex.etat != Retex.ETAT_VALIDE or not peut_valider(user, retex):
        raise PermissionError("Vous ne pouvez pas clore ce RETEX.")
    if retex.taches.filter(statut__in=Tache.STATUTS_OUVERTS).exists():
        raise ValidationError("Des actions restent ouvertes : terminez-les avant de clore.")
    retex.etat = Retex.ETAT_CLOS
    retex.save(update_fields=["etat", "updated_at"])
    _tracer(retex, user, "clos")


def ajouter_domaine(user, nom, coma, organisme):
    ship = chaine(user)[0]
    if ship is None or user_role_level(user) < niveau_requis_pour(user, "retex_validation") or equipage_a_terre_lecture_seule(user):
        raise PermissionError("Vous ne pouvez pas configurer les domaines.")
    if not nom.strip():
        raise ValidationError("Indiquez le nom du domaine.")
    domaines_du_navire(ship)
    DomaineRetex.objects.update_or_create(
        ship_id=ship, nom=nom.strip(), defaults={"coma": coma.strip(), "organisme": organisme.strip(), "actif": True})


def source_de(modele, pk):
    from demandes.services import trouver_objet
    return trouver_objet(modele, pk, OBJETS_RETEX)
