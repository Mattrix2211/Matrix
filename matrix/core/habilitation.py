"""Point de contrôle commun des habilitations : lire ou écrire par n'importe quel point d'entrée.

Il compose les mécanismes existants (compte actif, module activé, niveau d'écriture sur le service) et rend une décision
explicable. Il n'ajoute aucune règle.

- Lecture : seuls le compte et le module sont contrôlés ici. Borner ce qu'un marin lit reste le travail de la requête de
  périmètre (`scope_filters_for_user`) ; passer un objet à une lecture est refusé pour qu'aucun appelant ne croie le contraire.
- Écriture : s'ajoute le niveau d'écriture sur le service de l'objet. Une validation est une écriture avec `niveau_requis`.
- L'équipage à terre et le soutien à terre ne sont pas redits ici : `EquipageATerreMiddleware` refuse toute écriture par défaut
  et reste la seule source de ses exemptions de chemins.

Les lots suivants ajoutent un facteur à `FACTEURS` (plancher non contournable, délégation, suppléance) sans toucher aux appelants.
"""
from dataclasses import dataclass
from enum import Enum

from .ecriture_service import niveau_ecriture_sur
from .modules import module_actif_pour_user
from .roles import RoleLevel


class Action(str, Enum):
    LIRE = "lire"
    ECRIRE = "ecrire"


@dataclass(frozen=True)
class Demande:
    user: object
    action: Action
    objet: object = None
    module: str = None
    niveau_requis: RoleLevel = RoleLevel.EQUIPIER


@dataclass(frozen=True)
class Decision:
    autorise: bool
    facteur: str = ""
    motif: str = ""

    def __bool__(self):
        return self.autorise


AUTORISE = Decision(True)


def _authentifie(demande):
    user = demande.user
    if not getattr(user, "is_authenticated", False) or not user.is_active:
        return "Compte non authentifié ou désactivé."


def _module(demande):
    if demande.module and not module_actif_pour_user(demande.module, demande.user):
        return f"Le module « {demande.module} » est désactivé pour ce bâtiment."


def _niveau_sur_service(demande):
    if demande.action is Action.LIRE:
        return None
    if niveau_ecriture_sur(demande.user, demande.objet) < demande.niveau_requis:
        return "Niveau d'écriture insuffisant sur le service concerné."


FACTEURS = (
    ("authentifie", _authentifie),
    ("module_actif", _module),
    ("niveau_sur_service", _niveau_sur_service),
)
NOMS_FACTEURS = tuple(nom for nom, _ in FACTEURS)


def evaluer(user, action, **contexte):
    """Décision pour `user` sur `action` ; premier facteur refusant. Un visiteur non connecté est toujours refusé."""
    demande = Demande(user=user, action=Action(action), **contexte)
    if demande.action is Action.LIRE and demande.objet is not None:
        raise ValueError("La lecture d'un objet se borne par la requête de périmètre, pas par evaluer().")
    for nom, facteur in FACTEURS:
        motif = facteur(demande)
        if motif:
            return Decision(False, nom, motif)
    return AUTORISE
