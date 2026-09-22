"""Registre des modules applicatifs désactivables par navire, et fonctions de
résolution de leur état (tâche Notion « Modules activables par bâtiment
(administration distribuée, configuration) », Phase 1 - Socle).

Même principe que matrix/core/role_thresholds.py : un registre central, une
configuration par navire (org.models.ModuleActivation) avec repli sur une
valeur par défaut si rien n'est configuré. Ici, la valeur par défaut est
TOUJOURS "activé" pour CHAQUE module du registre : tant qu'aucun rôle habilité
(cf. REGISTRE_ACTIONS["module_gestion"] dans role_thresholds.py) n'a
explicitement désactivé un module pour son navire, le comportement de
l'application reste strictement identique à avant ce système — aucune
régression sur les navires déjà existants.

Désactiver un module ne supprime AUCUNE donnée : il masque uniquement le menu
(matrix/templates/base.html, filtre org_extras::module_actif) et bloque
l'accès direct par URL aux VUES WEB de ce module (matrix/core/middleware.py::
ModuleActivationMiddleware). L'API REST (/api/*), les tâches Celery et les
enchaînements métier internes entre modules (ex. création automatique d'un
ticket correctif logistics depuis une exécution maintenance) continuent de
fonctionner normalement, quel que soit l'état du module côté web — voir le
commentaire de ModuleActivationMiddleware pour le détail de ce choix.

Seules les apps dont la désactivation NE CASSE PAS le socle de l'application
sont enregistrées ci-dessous. Les apps suivantes sont volontairement EXCLUES
du registre (donc jamais désactivables, quelle que soit la configuration) :

- accounts       : comptes, profils, rôles — sans ce module, plus personne
                   ne peut se connecter ni être identifié.
- org            : hiérarchie Navire/Service/Secteur/Section — le périmètre
                   (scope_filters_for_user) de TOUS les autres modules en
                   dépend, y compris la résolution de l'activation des
                   modules elle-même (ModuleActivation.ship).
- notifications  : système d'alertes in-app/Web Push utilisé EN INTERNE par
                   tous les autres modules (maintenance, logistics,
                   training...) — le désactiver casserait leurs
                   notifications sans rien supprimer du code qui les
                   déclenche encore.
- dashboard      : espace personnel (page d'accueil "/"), vue flotte,
                   dashboards spécialité/classe de navire, prêt à
                   appareillage.
- calendar_app   : calendrier central, explicitement désigné « colonne
                   vertébrale » par CLAUDE.md — agrège les événements de
                   tous les autres modules.
- threads        : discussions génériques attachées à d'autres objets par
                   relation générique — aucune page dédiée dans le menu
                   (pas de web_urls.py), embarquées directement dans les
                   fiches d'autres modules (installation, ticket...) : ce
                   n'est pas un module autonome activable/désactivable.

Si une future tâche identifie un besoin de désactiver l'une de ces apps,
cela nécessite une analyse dédiée (pas juste l'ajouter au registre) — voir
le commentaire Notion de la tâche d'origine.
"""
from dataclasses import dataclass

from django.core.cache import cache


@dataclass(frozen=True)
class ModuleInfo:
    cle: str  # app_label Django (nom du module Python de l'app)
    libelle: str
    description: str


REGISTRE_MODULES = [
    ModuleInfo(
        "assets", "Matériels & installations",
        "Matériel mobile (extincteurs, EPI, multimètres...), installations fixes "
        "(propulseurs, pompes, circuits électriques...) et plan visuel du navire.",
    ),
    ModuleInfo(
        "maintenance", "Maintenance préventive",
        "Plans de maintenance préventive, occurrences et exécutions (checklists guidées).",
    ),
    ModuleInfo(
        "logistics", "Logistique & anomalies",
        "Tickets correctifs, demandes de pièces, stock, retours d'expérience, anomalies génériques.",
    ),
    ModuleInfo(
        "training", "Formations",
        "Catalogue de formations, validations, prérequis, arbre de compétences.",
    ),
    ModuleInfo(
        "quarts", "Quarts et services de garde",
        "Listes de quart, gardes à quai, échanges de service, chefs de liste.",
    ),
    ModuleInfo(
        "rondes", "Rondes",
        "Modèles de ronde et points de contrôle configurables, exécution des rondes.",
    ),
    ModuleInfo(
        "reports", "Bilans & rapports",
        "Génération de bilans instantané/période (export PDF, CSV, Excel).",
    ),
]

REGISTRE_PAR_CLE = {m.cle: m for m in REGISTRE_MODULES}


def _cache_key(ship_id):
    return f"modules_actifs:{ship_id}"


def invalidate_cache(ship_id):
    """Invalide le cache des modules actifs d'un navire — à appeler après
    tout enregistrement d'un ModuleActivation."""
    cache.delete(_cache_key(ship_id))


def _actifs_pour(ship_id):
    """Dictionnaire {module: bool actif} configuré explicitement pour ce
    navire (les modules absents du dictionnaire sont activés par défaut,
    cf. module_actif() ci-dessous) — avec cache, mêmes principes que
    role_thresholds._thresholds_for()."""
    cle = _cache_key(ship_id)
    valeurs = cache.get(cle)
    if valeurs is not None:
        return valeurs
    from org.models import ModuleActivation
    valeurs = dict(ModuleActivation.objects.filter(ship_id=ship_id).values_list("module", "active"))
    cache.set(cle, valeurs, None)
    return valeurs


def module_actif(cle_module, ship_id):
    """Vrai si le module <cle_module> est activé pour le navire <ship_id>.

    Comportement par défaut (module inconnu du registre, navire sans
    configuration explicite, ou ship_id=None comme un administrateur général
    sans navire attribué) : TOUJOURS activé — ne rien changer pour les
    navires existants ni pour les utilisateurs sans périmètre défini."""
    if cle_module not in REGISTRE_PAR_CLE or ship_id is None:
        return True
    return _actifs_pour(ship_id).get(cle_module, True)


def module_actif_pour_user(cle_module, user):
    """Raccourci pour les vues web et les gabarits : résout le module actif
    à partir du navire de l'utilisateur courant. Import différé du même
    type que role_thresholds.ship_id_de, pour éviter tout cycle d'import."""
    from .scopes import ship_id_for_user
    return module_actif(cle_module, ship_id_for_user(user))
