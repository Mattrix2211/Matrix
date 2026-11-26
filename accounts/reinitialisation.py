"""Réinitialisation du mot de passe par code à usage unique (AC-16), sans messagerie ni Internet.

Parcours : une autorité habilitée demande la réinitialisation ; Matrix génère un code temporaire (seule son empreinte salée est
conservée) que l'autorité remet au titulaire après vérification de son identité ; le titulaire définit lui-même son nouveau mot
de passe sur la page publique de réinitialisation ; le code est alors invalidé et les sessions anciennes tombent. Le code
n'authentifie jamais, ne vaut que pour sa demande et son compte, expire (30 minutes par défaut) ; les essais erronés bloquent
progressivement la seule source qui les commet.

Pour un compte porteur d'une autorité, la vérification d'identité est indépendante et imposée par le mécanisme : deux codes
sont nécessaires, l'un remis à l'initiateur, l'autre généré seulement quand un second responsable distinct, compétent pour ce
compte, a lui-même validé la demande depuis sa propre session. L'initiateur seul ne peut donc pas terminer le parcours.
"""
import secrets
from datetime import timedelta
from functools import lru_cache

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import check_password, make_password
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone

from matrix.core.roles import ROLE_TO_LEVEL, RoleLevel
from matrix.core.scopes import is_master_admin, ship_id_for_user

from . import securite
from .models import AuditLog, DemandeReinitialisation, UserProfile
from .services import (
    PROTECTION_GENERALE, niveau_de_competence, niveaux_de_protection,
)

ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # sans caractères ambigus (0/O, 1/I)
Statut = DemandeReinitialisation.Statut


def generer_code():
    """Code de 16 caractères (environ 80 bits) présenté en quatre groupes."""
    brut = "".join(secrets.choice(ALPHABET) for _ in range(16))
    return "-".join(brut[i:i + 4] for i in range(0, 16, 4))


def _normaliser(code):
    return "".join(c for c in (code or "").upper() if c.isalnum())


def _empreinte(demande_id, utilisateur_id, role, code):
    """Le code est lié à sa demande, à son compte et à son rôle (initiateur ou vérificateur) : inutilisable ailleurs."""
    return make_password(f"{demande_id}:{utilisateur_id}:{role}:{_normaliser(code)}")


def _verifier_empreinte(demande, role, code, empreinte):
    return check_password(f"{demande.pk}:{demande.user_id}:{role}:{_normaliser(code)}", empreinte)


def exige_verification_independante(cible, niveau_protection=None):
    """Tout compte porteur d'une autorité (grade de commandement, fonction, désignation, droits d'administration) : au-delà
    de l'équipier ordinaire, l'identité doit être vérifiée par un second responsable distinct de l'initiateur."""
    niveau = niveau_protection if niveau_protection is not None else niveaux_de_protection([cible])[cible.pk]
    profil = getattr(cible, "profile", None)
    grade = ROLE_TO_LEVEL.get(profil.role if profil else "", RoleLevel.EQUIPIER)
    return niveau >= PROTECTION_GENERALE or grade >= RoleLevel.CHEF_SECTION


def _validite():
    return timedelta(minutes=settings.CODE_REINITIALISATION_VALIDITE_MINUTES)


def _annuler_ouvertes(cible):
    DemandeReinitialisation.objects.filter(user=cible, statut__in=DemandeReinitialisation.OUVERTES).update(statut=Statut.ANNULEE)


def _verrouiller_compte(cible):
    """Sérialise les ouvertures de demande d'un même compte (PostgreSQL) ; la contrainte d'unicité garde l'invariant."""
    get_user_model().objects.select_for_update().filter(pk=cible.pk).first()


def _ouvrir_exclusivement(cible, creer, *, preserver_recuperation=False):
    """Annule la demande ouverte du compte puis crée la nouvelle, sans erreur 500 si deux ouvertures se croisent."""
    def ouvrir():
        with transaction.atomic():
            _verrouiller_compte(cible)
            if preserver_recuperation and DemandeReinitialisation.objects.filter(
                    user=cible, statut__in=DemandeReinitialisation.OUVERTES, nature=DemandeReinitialisation.Nature.RECUPERATION).exists():
                raise ValidationError("Une récupération d'accès est en cours pour ce compte : elle doit aboutir ou expirer.")
            _annuler_ouvertes(cible)
            return creer()

    try:
        return securite.avec_reprises(ouvrir)  # SQLite sérialise les écritures : un verrou momentané se rejoue
    except IntegrityError:
        raise ValidationError("Une autre demande vient d'être ouverte pour ce compte : réessayez.")


def initier(acteur, cible):
    """Ouvre une demande ; renvoie (demande, code_initiateur). Le code n'est jamais ré-affichable."""
    from .services import peut_reinitialiser_cible

    if not peut_reinitialiser_cible(acteur, cible):
        raise PermissionDenied
    niveaux = niveaux_de_protection([cible])
    verification = exige_verification_independante(cible, niveaux[cible.pk])
    code = generer_code()

    def creer():
        demande = DemandeReinitialisation.objects.create(
            user=cible, initiateur=acteur, verification_requise=verification, code_initiateur="",
            statut=Statut.EN_ATTENTE_VERIFICATION if verification else Statut.ACTIVE, expire_le=timezone.now() + _validite())
        demande.code_initiateur = _empreinte(demande.pk, cible.pk, "initiateur", code)
        demande.save(update_fields=["code_initiateur"])
        AuditLog.objects.create(
            actor=acteur, action="reinitialisation_demandee", target_user=cible,
            details=f"demande={demande.pk}; verification_independante={'oui' if verification else 'non'}; "
                    f"valide jusqu'au {demande.expire_le:%d/%m/%Y %H:%M}")
        return demande

    demande = _ouvrir_exclusivement(cible, creer, preserver_recuperation=True)
    from notifications.models import Notification, NotificationLevel
    Notification.objects.create(
        user=cible, level=NotificationLevel.WARNING, categorie="securite",
        verb="Une réinitialisation de votre mot de passe a été demandée. Si vous n'en êtes pas à l'origine, prévenez un responsable.")
    return demande, code


def verificateurs_eligibles_pour(demande):
    """Comptes habilités à valider l'identité du titulaire : distincts de l'initiateur et du titulaire, compétents pour son
    niveau de protection, dans son bâtiment (l'administrateur général : partout)."""
    niveau = niveaux_de_protection([demande.user])[demande.user_id]
    exclus = {demande.user_id, demande.initiateur_id}
    return [
        u for u in get_user_model().objects.filter(is_active=True).exclude(pk__in=exclus).select_related("profile")
        if niveau_de_competence(u) >= niveau and (is_master_admin(u) or ship_id_for_user(u) == ship_id_for_user(demande.user))
    ]


def demandes_a_verifier_par(verificateur):
    """Demandes en attente que `verificateur` est habilité à valider (jamais les siennes, jamais pour lui-même)."""
    en_attente = DemandeReinitialisation.objects.filter(
        statut=Statut.EN_ATTENTE_VERIFICATION, nature=DemandeReinitialisation.Nature.REINITIALISATION, expire_le__gt=timezone.now(),
    ).exclude(initiateur=verificateur).exclude(user=verificateur).select_related("user", "initiateur")
    competence = niveau_de_competence(verificateur)
    if competence == 0:
        return []
    comptes = [d.user for d in en_attente]
    niveaux = niveaux_de_protection(comptes) if comptes else {}
    return [
        d for d in en_attente
        if niveaux[d.user_id] <= competence and (is_master_admin(verificateur) or ship_id_for_user(verificateur) == ship_id_for_user(d.user))
    ]


def verifier_identite(verificateur, demande_id):
    """Validation indépendante : génère le second code, remis au seul vérificateur. Renvoie (demande, code_verificateur)."""
    code = generer_code()
    with transaction.atomic():
        try:
            demande = DemandeReinitialisation.objects.select_for_update().select_related("user").get(
                pk=demande_id, statut=Statut.EN_ATTENTE_VERIFICATION, nature=DemandeReinitialisation.Nature.REINITIALISATION)
        except DemandeReinitialisation.DoesNotExist:
            raise ValidationError("Cette demande n'existe plus ou a déjà été traitée.")
        if demande.expire_le <= timezone.now():
            DemandeReinitialisation.objects.filter(pk=demande.pk).update(statut=Statut.EXPIREE)
            raise ValidationError("Cette demande a expiré.")
        if verificateur.pk in (demande.initiateur_id, demande.user_id) or demande not in demandes_a_verifier_par(verificateur):
            raise PermissionDenied
        demande.code_verificateur = _empreinte(demande.pk, demande.user_id, "verificateur", code)
        demande.verificateur, demande.statut = verificateur, Statut.ACTIVE
        demande.save(update_fields=["code_verificateur", "verificateur", "statut", "updated_at"])
        AuditLog.objects.create(
            actor=verificateur, action="reinitialisation_identite_verifiee", target_user=demande.user,
            details=f"demande={demande.pk}; initiateur={demande.initiateur.username if demande.initiateur_id else '—'}")
    return demande, code


def _echec_generique():
    return ValidationError("Identifiant ou code invalide, expiré ou déjà utilisé.")


def _utilisateur_pour(identifiant):
    """Correspondance exacte d'abord ; insensible à la casse seulement si elle désigne un compte unique."""
    User = get_user_model()
    identifiant = (identifiant or "").strip()
    exact = User.objects.filter(username=identifiant, is_active=True).first()
    if exact is not None:
        return exact
    candidats = list(User.objects.filter(username__iexact=identifiant, is_active=True)[:2])
    return candidats[0] if len(candidats) == 1 else None


def _echec_temporise():
    """Même coût de calcul qu'une vérification de code : l'échec ne révèle ni le compte, ni la demande, ni le blocage."""
    check_password("x", _empreinte_factice())
    return _echec_generique()


@lru_cache(maxsize=1)
def _empreinte_factice():
    return make_password("empreinte-factice")


def utiliser(identifiant, code_initiateur, code_verificateur, nouveau_mot_de_passe, source="inconnue", postes=None):
    """Étape du titulaire : définit son nouveau mot de passe avec le(s) code(s). Message d'erreur volontairement unique.

    Les essais erronés sont comptés par couple (demande, source), avec blocage progressif de cette source, et au total pour la
    demande (cinq fois le seuil) : au-delà, seules les sources inconnues du titulaire sont refusées. Le titulaire qui présente
    son poste connu n'est jamais arrêté par les essais d'un tiers (AC-18)."""
    utilisateur = _utilisateur_pour(identifiant)
    if utilisateur is None:
        raise _echec_temporise()
    demande = DemandeReinitialisation.objects.filter(user=utilisateur, statut=Statut.ACTIVE).first()
    if demande is None or demande.expire_le <= timezone.now():
        if demande is not None:
            DemandeReinitialisation.objects.filter(pk=demande.pk, statut=Statut.ACTIVE).update(statut=Statut.EXPIREE)
        raise _echec_temporise()
    cle = f"code:{demande.pk}"
    poste = securite.poste_valide(postes, utilisateur.username)
    if securite.est_limite(cle, source, poste):
        raise _echec_temporise()
    valide = _verifier_empreinte(demande, "initiateur", code_initiateur, demande.code_initiateur)
    if demande.verification_requise:
        valide = _verifier_empreinte(demande, "verificateur", code_verificateur, demande.code_verificateur or "!") and valide
    if not valide:
        securite.enregistrer_echec(cle, source, seuil=settings.TENTATIVES_CODE_MAX, existe=True, poste=poste)
        raise _echec_generique()
    validate_password(nouveau_mot_de_passe, utilisateur)  # un mot de passe refusé ne consomme pas le code
    with transaction.atomic():
        # Usage unique : seule la première utilisation concurrente passe l'état ACTIVE à UTILISEE.
        if not DemandeReinitialisation.objects.filter(pk=demande.pk, statut=Statut.ACTIVE).update(statut=Statut.UTILISEE, utilisee_le=timezone.now()):
            raise _echec_generique()
        utilisateur.set_password(nouveau_mot_de_passe)  # invalide les sessions ouvertes (empreinte de session)
        utilisateur.save(update_fields=["password"])
        if demande.attribuer_administrateur_general:
            if UserProfile.objects.filter(administrateur_general=True, user__is_active=True).exists():
                raise _echec_generique()
            UserProfile.objects.filter(user=utilisateur).update(administrateur_general=True)
            AuditLog.objects.create(actor=None, action="changement_administrateur_general", target_user=utilisateur,
                                    details=f"administrateur_general: False -> True (récupération, demande={demande.pk})")
        securite.effacer_compteurs(utilisateur.username)  # les postes connus sont aussi révoqués
        securite.effacer_compteurs(cle)
        AuditLog.objects.create(
            actor=None, action="reinitialisation_effectuee", target_user=utilisateur,
            details=f"demande={demande.pk}; nature={demande.nature}; source={source}")
    from notifications.models import Notification, NotificationLevel
    Notification.objects.create(
        user=utilisateur, verb="Votre mot de passe vient d'être réinitialisé. Si ce n'est pas vous, prévenez un responsable.",
        level=NotificationLevel.WARNING, categorie="securite")
    return utilisateur
