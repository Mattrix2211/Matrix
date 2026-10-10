"""Signalement « fiche fausse ou incomplète » par le marin qui exécute la maintenance."""
from django.contrib.auth import get_user_model
from django.db import transaction

from accounts.models import AuditLog
from matrix.core.saisie import sans_nul

from . import fiche_validation as validation
from .models import SignalementFiche
from .proposition_article import ErreurCircuit

User = get_user_model()
MAX_TEXTE = 2000


def destinataires(fiche):
    """Fiche du bord : le chef de secteur (à défaut, le chef de service) ; fiche flotte : le responsable de spécialité."""
    if fiche.niveau == "FLOTTE":
        return list(User.objects.filter(is_active=True, specialites_dont_il_est_responsable__specialite=fiche.specialite_visee).distinct())
    return validation.responsables_bord(fiche.installation)


@transaction.atomic
def signaler(user, occurrence, texte):
    """Enregistre le signalement de la fiche suivie par cette occurrence et prévient le responsable."""
    texte = sans_nul(texte).strip()
    if not texte:
        raise ErreurCircuit("Dites en une phrase ce qui est faux ou manque dans la fiche.")
    if len(texte) > MAX_TEXTE:
        raise ErreurCircuit(f"Le signalement est limité à {MAX_TEXTE} caractères.")
    version = occurrence.version_fiche()
    if version is None or version.fiche_id is None:
        raise ErreurCircuit("Cette maintenance ne suit pas de fiche versionnée : rien à signaler.")
    fiche = version.fiche
    signalement = SignalementFiche.objects.create(fiche=fiche, version=version, auteur=user, texte=texte)
    validation.notifier_fiche(
        fiche, destinataires(fiche),
        f"Fiche « {fiche.title} » signalée fausse ou incomplète par {validation.nom(user)} : {texte[:200]}")
    AuditLog.objects.create(actor=user, action="fiche.signalement", details=f"« {fiche.title} » ({fiche.pk}) v{version.numero}; {texte[:200]}")
    return signalement


def ouverts(fiche):
    return fiche.signalements.filter(traite=False).select_related("auteur", "version")
