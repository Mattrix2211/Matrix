"""Point de contrôle commun des habilitations : lire ou écrire par n'importe quel point d'entrée.

Il compose compte actif, module activé et niveau d'écriture sur le service, et rend une décision explicable ; il n'ajoute
aucune règle. La lecture d'une liste reste bornée par les requêtes de périmètre : lui passer un objet à lire est refusé.
L'équipage à terre reste du seul ressort du middleware. Les lots suivants ajoutent un facteur à `FACTEURS`.
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
