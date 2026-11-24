"""Inventaire automatique des points d'entrée de Matrix : pages, API, administration, tâches planifiées et appelées.

Lecture seule : rien n'est créé ni exécuté. Sert à la vérification de couverture (`registre_acces.py`) et à la cartographie
(`manage.py cartographier_points_entree`).
"""
import re
from dataclasses import dataclass, field

from django.conf import settings
from django.contrib import admin
from django.urls import URLResolver, get_resolver

WEB, API, ADMIN, TACHE = "web", "api", "admin", "tache"
METHODES_ECRITURE = {"POST", "PUT", "PATCH", "DELETE"}
_ECHANTILLONS = {"int": "1", "uuid": "00000000-0000-0000-0000-000000000001"}


@dataclass(frozen=True)
class PointEntree:
    nature: str
    cle: str  # identifiant stable : route normalisée, « admin:app.modele » ou chemin de la tâche
    nom: str = ""
    vue: str = ""
    methodes: tuple = None  # None : fonction dont les méthodes ne se déduisent pas du code
    declare: tuple = field(default_factory=tuple)  # protections lisibles dans le code (mixins, permissions)
    url_exemple: str = None
    variante_format: bool = False  # doublon d'une route d'API avec suffixe « .json »
    planifiee: bool = False

    @property
    def ecriture_possible(self):
        return self.methodes is None or bool(METHODES_ECRITURE & set(self.methodes))


def _motif(pattern):
    return pattern._route if hasattr(pattern, "_route") else pattern._regex


def _parcourir(patterns, prefixe=""):
    for p in patterns:
        if isinstance(p, URLResolver):
            yield from _parcourir(p.url_patterns, prefixe + _motif(p.pattern))
        else:
            yield prefixe + _motif(p.pattern), p


def _normaliser(route):
    return route.replace("^", "").replace("$", "").replace("/?", "/").replace("\\.", ".").lstrip("/")


def _est_format(route):
    return "(?P<format>" in route or "drf_format_suffix" in route


def _url_exemple(route):
    """Adresse d'essai : les paramètres reçoivent une valeur fictive ; None si la route ne se construit pas."""
    if _est_format(route):
        return None
    adresse = re.sub(r"\(\?P<\w+>[^)]*\)", "1", route)
    adresse = re.sub(r"<(\w+):\w+>", lambda m: _ECHANTILLONS.get(m.group(1), "x"), adresse)
    return "/" + _normaliser(adresse)


def _methodes_et_declarations(callback):
    cls = getattr(callback, "view_class", None) or getattr(callback, "cls", None)
    actions = getattr(callback, "actions", None)
    if cls is None:
        return None, (f"fonction:{getattr(callback, '__name__', '?')}",)
    if actions:
        methodes = tuple(sorted(m.upper() for m in actions))
    else:
        methodes = tuple(sorted(m.upper() for m in cls.http_method_names if m not in ("options", "head") and hasattr(cls, m)))
    declare = [f"permission:{c.__name__}" for c in getattr(cls, "permission_classes", ())]
    declare += [f"mixin:{c.__name__}" for c in cls.__mro__ if c.__name__.endswith("Mixin") and c.__module__.startswith(("django.contrib.auth", "matrix.core"))]
    return methodes, tuple(declare)


def routes():
    """Pages et API (hors administration, inventoriée par ModelAdmin)."""
    resultat = []
    for route, pattern in _parcourir(get_resolver().url_patterns):
        cle = _normaliser(route)
        if cle.startswith("admin/"):
            continue
        callback = pattern.callback
        methodes, declare = _methodes_et_declarations(callback)
        cls = getattr(callback, "view_class", None) or getattr(callback, "cls", None) or callback
        resultat.append(PointEntree(
            nature=API if cle.startswith("api/") else WEB, cle=cle, nom=pattern.name or "",
            vue=f"{cls.__module__}.{cls.__name__}",
            methodes=methodes, declare=declare, url_exemple=_url_exemple(route),
            variante_format=_est_format(route),
        ))
    return resultat


def nombre_routes_admin():
    return sum(1 for route, _ in _parcourir(get_resolver().url_patterns) if _normaliser(route).startswith("admin/"))


def modeles_admin():
    resultat = []
    for modele, model_admin in admin.site._registry.items():
        surcharges = tuple(sorted(
            nom for nom in ("has_view_permission", "has_add_permission", "has_change_permission", "has_delete_permission",
                            "has_module_permission", "get_queryset", "get_actions")
            if getattr(type(model_admin), nom) is not getattr(admin.ModelAdmin, nom)
        ))
        resultat.append(PointEntree(
            nature=ADMIN, cle=f"admin:{modele._meta.label_lower}", nom=type(model_admin).__name__,
            vue=f"{type(model_admin).__module__}.{type(model_admin).__name__}", declare=tuple(f"surcharge:{n}" for n in surcharges),
            url_exemple=f"/admin/{modele._meta.app_label}/{modele._meta.model_name}/",
        ))
    return sorted(resultat, key=lambda p: p.cle)


def taches():
    """Toutes les tâches Celery du projet (hors tâches internes de Celery et tâches définies par des tests) ; `planifiee` si elles figurent au calendrier."""
    from matrix.celery import app

    app.loader.import_default_modules()
    planifiees = {entree["task"] for entree in settings.CELERY_BEAT_SCHEDULE.values()}
    noms = sorted(nom for nom in app.tasks if not nom.startswith("celery.") and ".tests." not in nom)
    return [PointEntree(nature=TACHE, cle=nom, nom=nom, vue=nom, planifiee=nom in planifiees) for nom in noms]


def inventaire():
    return routes() + modeles_admin() + taches()
