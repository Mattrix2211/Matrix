"""Relevés d'une fiche reportés dans les mesures de l'installation (heures de marche, isolement, vibrations).

Un relevé de fiche marqué `releve` alimente, à la clôture du compte rendu, le modèle de mesure existant : une
mesure par compte rendu et par type, mise à jour (jamais doublée) quand le compte rendu est corrigé.
"""
from decimal import Decimal

from django.utils import timezone

from assets.models import InstallationHourReading, InstallationIsolationReading, InstallationVibrationReading, TypeReleve

from .compte_rendu import valeur_de

# Type de relevé : (modèle de mesure, champ de la valeur, borne exclusive imposée par la colonne décimale).
MESURES = {
    TypeReleve.HEURES: (InstallationHourReading, "hours", Decimal("100000000")),
    TypeReleve.ISOLEMENT: (InstallationIsolationReading, "ohms", Decimal("10000000000")),
    TypeReleve.VIBRATIONS: (InstallationVibrationReading, "state", None),
}
ETATS_VIBRATION = {code for code, _ in InstallationVibrationReading.STATE_CHOICES}


def _lignes(items):
    """Première ligne de la fiche pour chaque type de relevé."""
    lignes = {}
    for it in items:
        if it.releve in MESURES:
            lignes.setdefault(it.releve, it)
    return lignes


def _valeur(type_releve, it, results, mesures):
    """Valeur à reporter (Decimal ou lettre), ou None si la ligne n'est pas renseignée."""
    if type_releve == TypeReleve.VIBRATIONS:
        texte = valeur_de(results, it)
        return texte.strip().upper() if isinstance(texte, str) and texte.strip() else None
    nombre = valeur_de(mesures, it)
    return None if nombre is None else Decimal(str(round(nombre, 2)))


def verifier(items, results, mesures):
    """Erreurs des relevés qui alimentent une mesure d'installation (jamais d'erreur serveur sur une valeur forgée)."""
    erreurs = []
    for type_releve, it in _lignes(items).items():
        valeur = _valeur(type_releve, it, results, mesures)
        if valeur is None:
            continue
        borne = MESURES[type_releve][2]
        if type_releve == TypeReleve.VIBRATIONS:
            if valeur not in ETATS_VIBRATION:
                erreurs.append(f"« {it.label} » : saisissez A, B ou C.")
        elif valeur < 0 or valeur >= borne:
            erreurs.append(f"« {it.label} » : valeur hors des limites acceptées.")
    return erreurs


def reporter(execution, installation, items, results, mesures, auteur):
    """Crée, met à jour ou retire la mesure de chaque relevé de la fiche pour ce compte rendu."""
    jour = timezone.localdate(execution.completed_at)
    for type_releve, it in _lignes(items).items():
        modele, champ, _ = MESURES[type_releve]
        existante = modele.objects.filter(execution=execution, installation=installation).first()
        valeur = _valeur(type_releve, it, results, mesures)
        if valeur is None:
            if existante:
                existante.delete()
            continue
        if existante is None:
            existante = modele(execution=execution, installation=installation, created_by=auteur)
        existante.date, existante.updated_by = jour, auteur
        setattr(existante, champ, valeur)
        if type_releve != TypeReleve.HEURES:
            existante.note = "Relevé du compte rendu de maintenance"
        existante.save()
