"""Seuils de rôle minimal requis par action, configurables par navire.

Remplace les constantes RoleLevel codées en dur qui étaient dispersées dans
`assets/views.py`, `maintenance/views.py`, `threads/views.py`,
`accounts/views.py`, `assets/web_views.py` et `maintenance/web_views.py`
(tâche Notion « Seuils de rôle configurables par navire (remplacer les
constantes codées en dur) », Phase 1 - Socle).

Chaque action du REGISTRE ci-dessous porte une PORTEE :
- SHIP    : le seuil est propre à un navire (majorité des actions métier),
  stocké dans `org.models.RoleThresholdConfig` (ship=<navire>).
- GLOBALE : le seuil s'applique à toute la flotte, pour les actions portant
  sur un référentiel sans rattachement navire (ex. grades/spécialités
  communs à tout le bord) — stocké dans le même modèle avec ship=None.

Les valeurs DEFAUT ci-dessous REPRODUISENT EXACTEMENT les seuils codés en
dur avant ce système : tant qu'aucun ADMIN_NAVIRE (ou MASTER_ADMIN pour la
portée GLOBALE) ne reconfigure une action via l'onglet « Sécurité » des
Réglages, le comportement de l'application reste strictement identique à
avant — aucune régression.
"""
from dataclasses import dataclass

from django.core.cache import cache

from .roles import RoleLevel

PORTEE_NAVIRE = "SHIP"
PORTEE_GLOBALE = "GLOBALE"


@dataclass(frozen=True)
class ActionSeuil:
    cle: str
    libelle: str
    categorie: str
    portee: str
    defaut: RoleLevel


# Registre central : une entrée par action dont le seuil est désormais
# configurable. `cle` est la clé stockée telle quelle dans
# RoleThresholdConfig.thresholds (JSONField {cle: "NOM_ROLE"}).
REGISTRE_ACTIONS = [
    ActionSeuil(
        "asset_ecriture_simple", "Créer ou modifier un matériel, un dossier",
        "Matériel mobile", PORTEE_NAVIRE, RoleLevel.CHEF_SECTION,
    ),
    ActionSeuil(
        "asset_gestion_avancee",
        "Supprimer un matériel, un dossier, un document, ou lancer une action groupée",
        "Matériel mobile", PORTEE_NAVIRE, RoleLevel.CHEF_SERVICE,
    ),
    ActionSeuil(
        "installation_ecriture_simple", "Créer ou modifier une installation",
        "Installations", PORTEE_NAVIRE, RoleLevel.CHEF_SECTION,
    ),
    ActionSeuil(
        "installation_gestion_avancee",
        "Supprimer une installation ou lancer une action groupée",
        "Installations", PORTEE_NAVIRE, RoleLevel.CHEF_SERVICE,
    ),
    ActionSeuil(
        "installation_entretien_gestion",
        "Gérer les tâches d'entretien d'une installation (ajout, modification, suppression, pièce jointe)",
        "Installations", PORTEE_NAVIRE, RoleLevel.CHEF_SERVICE,
    ),
    ActionSeuil(
        "rattachement_parent_gestion",
        "Modifier le rattachement parent/enfant d'un matériel ou d'une installation",
        "Installations", PORTEE_NAVIRE, RoleLevel.CHEF_SERVICE,
    ),
    ActionSeuil(
        "plan_navire_configuration",
        "Configurer les ponts et zones du plan visuel du navire",
        "Installations", PORTEE_NAVIRE, RoleLevel.CHEF_SERVICE,
    ),
    ActionSeuil(
        "maintenance_execution_ecriture",
        "Créer ou modifier une occurrence ou une exécution de maintenance",
        "Maintenance", PORTEE_NAVIRE, RoleLevel.EQUIPIER,
    ),
    ActionSeuil(
        "maintenance_occurrence_gestion_tiers",
        "Exécuter ou commenter une maintenance qui n'est pas la sienne",
        "Maintenance", PORTEE_NAVIRE, RoleLevel.CHEF_SECTION,
    ),
    ActionSeuil(
        "maintenance_plan_ecriture",
        "Créer ou modifier un plan de maintenance préventive",
        "Maintenance", PORTEE_NAVIRE, RoleLevel.CHEF_SECTION,
    ),
    ActionSeuil(
        "thread_ecriture", "Créer ou modifier une discussion",
        "Discussions", PORTEE_NAVIRE, RoleLevel.CHEF_SECTION,
    ),
    ActionSeuil(
        "referentiel_global_ecriture",
        "Modifier les grades, spécialités ou la disponibilité des rôles (référentiel commun à toute la flotte)",
        "Référentiels globaux", PORTEE_GLOBALE, RoleLevel.MASTER_ADMIN,
    ),
]

REGISTRE_PAR_CLE = {a.cle: a for a in REGISTRE_ACTIONS}


def _cache_key(ship_id):
    return f"seuils_role:{ship_id if ship_id is not None else 'global'}"


def invalidate_cache(ship_id):
    """Invalide le cache des seuils d'un navire (ou de la configuration
    globale si ship_id est None) — à appeler après tout enregistrement
    d'une RoleThresholdConfig."""
    cache.delete(_cache_key(ship_id))


def _thresholds_for(ship_id):
    """Dictionnaire {cle_action: 'NOM_ROLE'} pour le navire donné (ou pour
    la configuration globale si ship_id est None), avec cache : un seuil de
    rôle change rarement, inutile de re-requêter la base à chaque contrôle
    de permission. Pas d'expiration : le cache est invalidé explicitement
    (invalidate_cache) à chaque sauvegarde de configuration."""
    cle = _cache_key(ship_id)
    valeurs = cache.get(cle)
    if valeurs is not None:
        return valeurs
    from org.models import RoleThresholdConfig
    config = RoleThresholdConfig.objects.filter(ship_id=ship_id).first()
    valeurs = dict(config.thresholds) if config else {}
    cache.set(cle, valeurs, None)
    return valeurs


def seuil_role(cle_action, ship_id=None):
    """Retourne le RoleLevel minimal requis pour l'action donnée, en tenant
    compte de la configuration du navire (ou de la configuration globale
    pour une action de portée flotte), avec repli sur le seuil par défaut
    si rien n'est configuré ou si le navire de l'appelant est inconnu."""
    action = REGISTRE_PAR_CLE.get(cle_action)
    if action is None:
        raise ValueError(f"Action de seuil de rôle inconnue : {cle_action!r}")
    if action.portee == PORTEE_GLOBALE:
        valeurs = _thresholds_for(None)
    elif ship_id is None:
        return action.defaut
    else:
        valeurs = _thresholds_for(ship_id)
    nom = valeurs.get(cle_action)
    if not nom:
        return action.defaut
    try:
        return RoleLevel[nom]
    except KeyError:
        return action.defaut


def ship_id_de(user):
    """Identifiant du navire de l'utilisateur (ou None), pour résoudre le
    seuil applicable. Import différé : évite tout cycle d'import (ce module
    est importé très tôt, par de nombreuses apps)."""
    from .scopes import ship_id_for_user
    return ship_id_for_user(user)


def niveau_requis_pour(user, cle_action):
    """Raccourci pour les vues web (pas de ViewSet DRF, pas de résolution
    via RolePermission) : résout directement le seuil de rôle requis pour
    l'utilisateur courant sur l'action donnée."""
    return seuil_role(cle_action, ship_id_de(user))
