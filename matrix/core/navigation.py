"""Navigation latérale de Matrix (docs/UX.md §7).

Un seul registre déclaratif des entrées, regroupées par grande fonction. La
visibilité réutilise l'existant — jamais de système parallèle :
- modules activables par bâtiment : ``matrix.core.modules.module_actif_pour_user`` ;
- droits : ``RoleLevel`` / ``user_role_level`` et les mêmes règles que les vues
  (filtres ``dashboard_extras`` et ``asset_extras``).
La vue de destination revalide toujours les droits côté serveur : la barre
latérale ne fait que masquer ce que l'utilisateur ne peut pas ouvrir.
"""
from dataclasses import dataclass
from typing import Callable, Optional

from django.urls import reverse

from assets.templatetags.asset_extras import peut_configurer_plan_navire
from dashboard.templatetags.dashboard_extras import (
    peut_voir_dashboard_classe_navire,
    peut_voir_dashboard_specialite,
    peut_voir_pret_appareillage,
    peut_voir_vue_flotte,
)
from matrix.core.modules import module_actif_pour_user
from matrix.core.roles import NIVEAU_VISION_COMMANDEMENT, user_role_level


@dataclass(frozen=True)
class Entree:
    libelle: str
    icone: str  # concept de matrix/core/icones.py
    nom_url: str
    module: Optional[str] = None  # clé de REGISTRE_MODULES ; None = toujours disponible
    droit: Optional[Callable] = None  # fonction(user) -> bool ; None = tout marin connecté
    # Paramètres de requête de l'URL générée selon l'utilisateur (facultatif).
    url_utilisateur: Optional[Callable] = None


def _commandant_ou_plus(user):
    return user_role_level(user) >= NIVEAU_VISION_COMMANDEMENT


def _url_parametres(user):
    # Seul le superutilisateur voit tous les onglets ; les autres n'ont que leurs
    # réglages personnels (même règle que SettingsView).
    base = reverse("settings")
    return base if user.is_superuser else f"{base}?tab=notifications"


GROUPES = [
    ("Personnel", [
        Entree("Aujourd'hui", "aujourdhui", "home"),
        Entree("Calendrier", "calendrier", "calendar-index"),
    ]),
    ("Équipements", [
        Entree("Matériels", "materiel", "asset-list", module="assets"),
        Entree("Installations", "installation", "installation-list", module="assets"),
        Entree("Plan du navire", "plan_navire", "plan-navire-vue", module="assets"),
        Entree("Configurer le plan du navire", "configuration", "plan-navire-list",
               module="assets", droit=peut_configurer_plan_navire),
    ]),
    ("Maintenance", [
        Entree("Maintenance", "maintenance", "maintenance-occurrences", module="maintenance"),
        Entree("Tickets correctifs", "ticket", "ticket-list", module="logistics"),
        Entree("Anomalies", "anomalie", "anomalie-list", module="logistics"),
        Entree("Logistique", "logistique", "stock-piece-list", module="logistics"),
    ]),
    ("Activité", [
        Entree("Rondes", "ronde", "rondes-index", module="rondes"),
        Entree("Quarts et gardes", "quart", "quarts-index", module="quarts"),
    ]),
    ("Compétences", [
        Entree("Formations", "formation", "formation-list", module="training"),
    ]),
    ("Supervision", [
        Entree("Prêt à appareiller", "pret_appareillage", "pret-appareillage",
               droit=peut_voir_pret_appareillage),
        Entree("Flotte", "flotte", "vue-flotte", droit=peut_voir_vue_flotte),
        Entree("Spécialités", "specialite", "dashboard-specialite-choix",
               droit=peut_voir_dashboard_specialite),
        Entree("Classes de navire", "classe_navire", "dashboard-classe-navire-choix", droit=peut_voir_dashboard_classe_navire),
    ]),
    ("Administration", [
        Entree("Annuaire", "annuaire", "user-directory", droit=_commandant_ou_plus),
        Entree("Paramètres", "parametres", "settings", url_utilisateur=_url_parametres),
    ]),
]


def _visible(entree, user):
    if entree.module and not module_actif_pour_user(entree.module, user):
        return False
    return entree.droit is None or bool(entree.droit(user))


def _url(entree, user):
    if entree.url_utilisateur:
        return entree.url_utilisateur(user)
    return reverse(entree.nom_url)


def _rang_correspondance(entree, chemin):
    """None si l'entrée ne correspond pas à la page ; sinon un rang (plus grand =
    plus précis : chemin le plus long)."""
    base = reverse(entree.nom_url)
    if base == "/":
        if chemin != "/":
            return None
    elif not chemin.startswith(base):
        return None
    return len(base)


def construire_navigation(user, chemin):
    """Groupes visibles pour l'utilisateur : liste de dicts
    ``{"titre", "entrees": [{"libelle", "icone", "url", "courante"}]}``.
    Les groupes sans entrée visible sont omis ; une seule entrée est « courante »."""
    visibles = [
        (titre, [e for e in entrees if _visible(e, user)]) for titre, entrees in GROUPES
    ]
    meilleure, meilleur_rang = None, None
    for _, entrees in visibles:
        for entree in entrees:
            rang = _rang_correspondance(entree, chemin)
            if rang is not None and (meilleur_rang is None or rang > meilleur_rang):
                meilleure, meilleur_rang = entree, rang
    return [
        {
            "titre": titre,
            "entrees": [
                {
                    "libelle": e.libelle,
                    "icone": e.icone,
                    "url": _url(e, user),
                    "courante": e is meilleure,
                }
                for e in entrees
            ],
        }
        for titre, entrees in visibles
        if entrees
    ]
