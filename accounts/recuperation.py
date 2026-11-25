"""Récupération exceptionnelle d'un administrateur général (AC-17).

Deux opérateurs habilités distincts, chacun authentifié séparément (identité système du processus et phrase secrète personnelle,
saisies sur le serveur), interviennent dans deux exécutions locales distinctes :
1. le premier ouvre la demande, avec une justification obligatoire, et reçoit le premier code ;
2. le second la valide dans le délai imparti et reçoit le second code.
Le titulaire du compte n'obtient l'accès qu'avec les deux codes, sur la page publique de réinitialisation : un seul opérateur
ne peut ni ouvrir et valider à lui seul, ni terminer le parcours. Sans administrateur général disponible, les opérateurs peuvent
désigner un compte existant qui le deviendra à l'utilisation des codes (`attribuer`). Aucun compte de secours, identifiant ou mot
de passe n'existe dans le code. Cette procédure ne protège pas contre un opérateur qui a un accès système ou base illimité.
"""
import os
from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import check_password, make_password
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone

from .models import AuditLog, DemandeReinitialisation, OperateurRecuperation, UserProfile
from .reinitialisation import Statut, _empreinte, _ouvrir_exclusivement, generer_code

OPERATEURS_MINIMUM = 2


def identite_systeme():
    """Identité du processus d'après le système (jamais une variable d'environnement modifiable par l'utilisateur)."""
    try:
        import pwd
        return pwd.getpwuid(os.getuid()).pw_name
    except (ImportError, KeyError):
        import getpass
        return getpass.getuser()


def habiliter_operateur(nom, identifiant_systeme, phrase):
    """Installation : deux opérateurs au plus peuvent être habilités par cette voie ; au-delà, c'est une intervention
    d'exploitation documentée (le contrôle ne protège pas contre qui a déjà un accès illimité au serveur)."""
    if len(phrase or "") < 12:
        raise ValidationError("La phrase secrète doit compter au moins 12 caractères.")
    if OperateurRecuperation.objects.filter(actif=True).count() >= OPERATEURS_MINIMUM:
        raise ValidationError("Les deux opérateurs sont déjà habilités : un changement relève d'une intervention d'exploitation tracée.")
    if OperateurRecuperation.objects.filter(nom=nom).exists():
        raise ValidationError("Ce nom d'opérateur est déjà utilisé.")
    if OperateurRecuperation.objects.filter(identifiant_systeme=identifiant_systeme).exists():
        raise ValidationError("Cette identité système est déjà habilitée : chaque opérateur utilise son propre compte d'exploitation.")
    operateur = OperateurRecuperation.objects.create(
        nom=nom, identifiant_systeme=identifiant_systeme, phrase=make_password(phrase))
    AuditLog.objects.create(actor=None, action="operateur_recuperation_habilite", details=f"nom={nom}; identite_systeme={identifiant_systeme}")
    return operateur


def authentifier_operateur(identifiant_systeme, phrase):
    operateur = OperateurRecuperation.objects.filter(identifiant_systeme=identifiant_systeme, actif=True).first()
    if operateur is None or not check_password(phrase or "", operateur.phrase):
        AuditLog.objects.create(actor=None, action="recuperation_authentification_refusee", details=f"identite_systeme={identifiant_systeme}")
        raise PermissionDenied
    return operateur


def _administrateur_general_disponible():
    return UserProfile.objects.filter(administrateur_general=True, user__is_active=True).exists()


def ouvrir(operateur, identifiant_compte, justification, attribuer=False):
    """Ouvre la demande ; renvoie (demande, premier code)."""
    if not (justification or "").strip():
        raise ValidationError("Une justification est obligatoire.")
    compte = get_user_model().objects.filter(username=identifiant_compte, is_active=True).first()
    if compte is None:
        raise ValidationError("Compte introuvable ou inactif.")
    profil, _ = UserProfile.objects.get_or_create(user=compte)
    if attribuer:
        if _administrateur_general_disponible():
            raise ValidationError("Un administrateur général applicatif existe : utilisez la récupération de son compte.")
    elif not profil.administrateur_general:
        raise ValidationError("Cette procédure ne concerne que les comptes d'administrateur général.")
    code = generer_code()

    def creer():
        demande = DemandeReinitialisation.objects.create(
            user=compte, nature=DemandeReinitialisation.Nature.RECUPERATION, operateur_initiateur=operateur.nom,
            justification=justification.strip(), verification_requise=True, attribuer_administrateur_general=attribuer,
            statut=Statut.EN_ATTENTE_VERIFICATION, code_initiateur="",
            expire_le=timezone.now() + timedelta(minutes=settings.RECUPERATION_VALIDITE_MINUTES))
        demande.code_initiateur = _empreinte(demande.pk, compte.pk, "initiateur", code)
        demande.save(update_fields=["code_initiateur"])
        AuditLog.objects.create(
            actor=None, action="recuperation_ouverte", target_user=compte,
            details=f"demande={demande.pk}; operateur={operateur.nom}; attribution={'oui' if attribuer else 'non'}; "
                    f"justification={justification.strip()[:300]}")
        return demande

    demande = _ouvrir_exclusivement(compte, creer)
    return demande, code


def valider(operateur, demande_id):
    """Second opérateur, distinct du premier : renvoie (demande, second code)."""
    code = generer_code()
    with transaction.atomic():
        try:
            demande = DemandeReinitialisation.objects.select_for_update().get(
                pk=demande_id, nature=DemandeReinitialisation.Nature.RECUPERATION, statut=Statut.EN_ATTENTE_VERIFICATION)
        except DemandeReinitialisation.DoesNotExist:
            raise ValidationError("Demande introuvable ou déjà traitée.")
        if demande.expire_le <= timezone.now():
            DemandeReinitialisation.objects.filter(pk=demande.pk).update(statut=Statut.EXPIREE)
            raise ValidationError("La demande a expiré.")
        premier = OperateurRecuperation.objects.filter(nom=demande.operateur_initiateur).first()  # `nom` est unique
        if premier is None or premier.pk == operateur.pk or premier.identifiant_systeme == operateur.identifiant_systeme \
                or premier.nom == operateur.nom:
            raise PermissionDenied
        demande.code_verificateur = _empreinte(demande.pk, demande.user_id, "verificateur", code)
        demande.operateur_verificateur, demande.statut = operateur.nom, Statut.ACTIVE
        demande.save(update_fields=["code_verificateur", "operateur_verificateur", "statut", "updated_at"])
        AuditLog.objects.create(
            actor=None, action="recuperation_validee", target_user=demande.user,
            details=f"demande={demande.pk}; operateur_1={demande.operateur_initiateur}; operateur_2={operateur.nom}")
    return demande, code
