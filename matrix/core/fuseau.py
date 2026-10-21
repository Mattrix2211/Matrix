"""Fuseau horaire de référence d'un bâtiment : saisie et affichage ; les instants restent stockés en UTC."""
from datetime import datetime, timezone as dt_timezone
from zoneinfo import ZoneInfo, available_timezones

from django.conf import settings

MESSAGE_FUSEAU_INVALIDE = "Fuseau horaire inconnu : choisissez un fuseau de la liste (ex. Europe/Paris)."
MESSAGE_FUSEAU_OBLIGATOIRE = "Choisissez explicitement le fuseau horaire de l'unité (ex. Europe/Paris)."


def fuseaux_disponibles():
    return sorted(available_timezones())


def fuseau_valide(nom):
    return bool(nom) and nom in available_timezones()


def fuseau_herite(navire):
    """Vrai si le bâtiment n'a pas choisi de fuseau : le paramétrage du serveur s'applique."""
    return not navire.fuseau_horaire


def nom_fuseau(navire):
    return navire.fuseau_horaire or settings.TIME_ZONE


def libelle_fuseau(navire):
    """Fuseau affiché à l'écran ; un fuseau hérité est clairement distingué d'un choix du bord."""
    if fuseau_herite(navire):
        return f"Fuseau par défaut hérité : {settings.TIME_ZONE}"
    return f"Fuseau du bâtiment : {navire.fuseau_horaire}"


def local_vers_utc(navire, naif):
    """Heure saisie (sans fuseau) dans le fuseau du bâtiment -> (instant UTC, erreur).

    Une heure inexistante ou répétée par un changement d'heure est refusée plutôt que devinée.
    """
    zone = ZoneInfo(nom_fuseau(navire))
    premiere = naif.replace(tzinfo=zone, fold=0)
    seconde = naif.replace(tzinfo=zone, fold=1)
    decalage = premiere.utcoffset()
    if decalage != seconde.utcoffset():
        return None, "Cette heure est ambiguë (changement d'heure) : choisissez une autre heure."
    utc = premiere.astimezone(dt_timezone.utc)
    if utc.astimezone(zone).replace(tzinfo=None) != naif:
        return None, "Cette heure n'existe pas (changement d'heure) : choisissez une autre heure."
    return utc, ""


def utc_vers_local(navire, instant):
    return instant.astimezone(ZoneInfo(nom_fuseau(navire)))


def formater(navire, instant):
    """« 21/10/2026 14:30 (Europe/Paris) » ; tiret si l'instant est inconnu."""
    if instant is None:
        return "—"
    return f"{utc_vers_local(navire, instant):%d/%m/%Y %H:%M} ({nom_fuseau(navire)})"


def champ_local(navire, instant):
    """Valeur d'un champ `datetime-local` (heure du bâtiment, à la minute)."""
    return f"{utc_vers_local(navire, instant):%Y-%m-%dT%H:%M}"


def lire_champ_local(navire, texte):
    """Valeur d'un champ `datetime-local` -> (instant UTC, erreur)."""
    try:
        naif = datetime.strptime((texte or "").strip(), "%Y-%m-%dT%H:%M")
    except ValueError:
        return None, "Indiquez la date et l'heure d'effet de la relève."
    return local_vers_utc(navire, naif)


def minute_courante(maintenant):
    """Début de la minute en cours : la saisie est à la minute, « maintenant » reste proposable."""
    return maintenant.replace(second=0, microsecond=0)

