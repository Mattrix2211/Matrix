"""Cohérence multi-processus des réglages mis en cache (seuils de rôle, modules).

Chaque réglage garde un cache local au processus, validé par une version stockée
en base (`org.VersionConfiguration`) : toute modification incrémente la version,
et chaque processus recharge dès qu'il constate une version différente. Une
révocation est donc vue dès la requête suivante, quel que soit le processus.

Toutes les versions sont lues en UNE requête, mémorisée pour la durée d'une
requête web ou d'une tâche Celery (`ouvrir_contexte`). Hors de ces contextes,
la validation a lieu à chaque lecture.
"""
import uuid
from contextvars import ContextVar

from django.db import IntegrityError, transaction
from django.db.models import F

VERSION_ABSENTE = (0, None)

# Mémo des versions pour la requête ou la tâche en cours ; None = hors contexte.
_contexte = ContextVar("config_version_contexte", default=None)
# Cache local au processus : clé -> (version, valeurs).
_cache = {}


def cle_seuils(ship_id):
    return f"seuils:{ship_id if ship_id is not None else 'global'}"


def cle_modules(ship_id):
    return f"modules:{ship_id}"


def ouvrir_contexte():
    return _contexte.set({"versions": None})


def fermer_contexte(jeton=None):
    if jeton is None:
        _contexte.set(None)
    else:
        _contexte.reset(jeton)


def _versions():
    from org.models import VersionConfiguration

    contexte = _contexte.get()
    if contexte is not None and contexte["versions"] is not None:
        return contexte["versions"]
    versions = {
        cle: (valeur, jeton)
        for cle, valeur, jeton in VersionConfiguration.objects.values_list("cle", "valeur", "jeton")
    }
    if contexte is not None:
        contexte["versions"] = versions
    return versions


def valeurs_validees(cle, charger):
    """Valeurs en cache pour `cle` si la version en base n'a pas changé, sinon `charger()`.

    La version est lue AVANT les données : une écriture concurrente laisse une
    version périmée en cache, donc un rechargement au prochain contrôle."""
    version = _versions().get(cle, VERSION_ABSENTE)
    entree = _cache.get(cle)
    if entree is not None and entree[0] == version:
        return entree[1]
    valeurs = charger()
    _cache[cle] = (version, valeurs)
    return valeurs


def incrementer(cle):
    """Incrémente atomiquement la version de `cle` (à appeler APRÈS l'écriture des données).

    Le jeton aléatoire empêche qu'une base restaurée ou annulée retombe sur une
    version déjà vue par un processus."""
    from org.models import VersionConfiguration

    def maj():
        return VersionConfiguration.objects.filter(cle=cle).update(valeur=F("valeur") + 1, jeton=uuid.uuid4())

    with transaction.atomic():
        if not maj():
            try:
                with transaction.atomic():
                    VersionConfiguration.objects.create(cle=cle, valeur=1)
            except IntegrityError:
                maj()  # créée entre-temps par un autre processus
    contexte = _contexte.get()
    if contexte is not None:
        contexte["versions"] = None
