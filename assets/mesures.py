"""Heures de marche et mesures d'une installation.

Un relevé d'heures est le COMPTEUR TOTAL de la machine à la date du relevé (jamais
une durée à additionner). Le « total » est le plus grand compteur relevé ; les
« heures depuis la dernière visite » sont ce compteur moins celui de la dernière
visite en atelier. Fonctions pures : elles travaillent sur des listes déjà chargées.
"""
from decimal import Decimal

from django.utils.formats import number_format

ZERO = Decimal("0")


def compteur_total(releves):
    """Compteur courant : le plus grand relevé (None sans relevé)."""
    return max((r.hours for r in releves), default=None)


def compteur_a_la_visite(releves, references_echeance=()):
    """Compteur à la dernière visite en atelier.

    Visite = dernière exécution terminée d'une maintenance au compteur (sa
    `derniere_echeance_heures`), ou un relevé marqué « visite ». Les compteurs ne
    faisant que croître, le plus grand des deux est le plus récent. 0 sans visite.
    """
    candidats = [r.hours for r in releves if r.is_visit]
    candidats += [h for h in references_echeance if h is not None]
    return max(candidats, default=ZERO)


def reference_visite_maintenance(maintenance, releves):
    """Compteur de départ d'une maintenance au compteur : celui de sa dernière
    exécution, à défaut celui de la dernière visite marquée sur un relevé."""
    if maintenance.derniere_echeance_heures is not None:
        return maintenance.derniere_echeance_heures
    return compteur_a_la_visite(releves)


def heures_depuis_visite_maintenance(maintenance, releves):
    """Heures de marche écoulées depuis la dernière visite de cette maintenance
    (None sans relevé)."""
    total = compteur_total(releves)
    if total is None:
        return None
    return max(ZERO, total - reference_visite_maintenance(maintenance, releves))


def heures_par_gamme(maintenances, releves):
    """Heures depuis la dernière visite de chaque fiche suivie à l'heure de marche : les gammes ne se
    cumulent pas, chacune a sa propre visite. [{fiche, gamme, depuis_visite, seuil, pourcentage}]."""
    gammes = []
    for fiche in maintenances:
        if not fiche.seuil_heures or fiche.mode_declenchement == "CALENDRIER":
            continue
        depuis = heures_depuis_visite_maintenance(fiche, releves)
        gammes.append({
            "fiche": fiche, "gamme": f"{formater_nombre(fiche.seuil_heures)}\u00a0h", "depuis_visite": depuis,
            "seuil": fiche.seuil_heures,
            "pourcentage": None if depuis is None else min(100, int(depuis * 100 / fiche.seuil_heures)),
        })
    return sorted(gammes, key=lambda g: g["seuil"])


def resume_heures(releves, references_echeance=()):
    """Compteur total, compteur à la visite et heures depuis la visite (Decimal ;
    None partout sans relevé)."""
    total = compteur_total(releves)
    if total is None:
        return {"total": None, "a_la_visite": None, "depuis_visite": None}
    a_la_visite = compteur_a_la_visite(releves, references_echeance)
    return {"total": total, "a_la_visite": a_la_visite, "depuis_visite": max(ZERO, total - a_la_visite)}


def heures_par_releve(releves):
    """Heures effectuées entre deux relevés consécutifs, rattachées à la date du
    relevé le plus récent : [(date, heures)]. Le premier relevé n'a pas de référence."""
    tries = sorted(releves, key=lambda r: (r.date, r.hours))
    return [(cur.date, max(ZERO, cur.hours - prec.hours)) for prec, cur in zip(tries, tries[1:])]


def formater_nombre(valeur, decimales=0):
    """Nombre à la française avec séparateur de milliers : 4 715 ou 12,5."""
    return number_format(valeur, decimal_pos=decimales, use_l10n=True, force_grouping=True)


def formater_heures(valeur, decimales=0):
    """« 4 715 h » (espace insécable avant l'unité)."""
    return f"{formater_nombre(valeur, decimales)} h"


def formater_ohms(valeur):
    """Résistance d'isolement lisible : 560 kΩ, 2,4 MΩ, 750 Ω."""
    valeur = Decimal(str(valeur))
    for seuil, unite in ((Decimal("1000000"), "MΩ"), (Decimal("1000"), "kΩ")):
        if abs(valeur) >= seuil:
            reduit = (valeur / seuil).quantize(Decimal("0.01"))
            decimales = 0 if reduit % 1 == 0 else 1 if (reduit * 10) % 1 == 0 else 2
            return f"{formater_nombre(reduit, decimales)}\u00a0{unite}"
    return f"{formater_nombre(valeur, 0)}\u00a0Ω"
