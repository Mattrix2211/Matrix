"""Génère l'annexe B (matrice rôle × action, valeurs par défaut) depuis le code de l'état B.

Usage : python generer_annexe_b.py <racine_du_code> <fichier_de_sortie>
"""
import os
import sys
from pathlib import Path

RACINE, SORTIE = Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve()
os.chdir(RACINE)
sys.path.insert(0, str(RACINE))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "matrix.settings")
os.environ["DJANGO_DEBUG"] = "1"

import django  # noqa: E402

django.setup()

from accounts.models import Roles  # noqa: E402
from matrix.core.permissions import ManageUsersPermission  # noqa: E402
from matrix.core.role_thresholds import REGISTRE_ACTIONS  # noqa: E402
from matrix.core.roles import ROLE_TO_LEVEL, ROLES_SANS_ECRITURE_HERITEE, RoleLevel  # noqa: E402

ORDRE = [Roles.MASTER_ADMIN, Roles.ADMIN_NAVIRE, Roles.COMMANDANT, Roles.COMMANDANT_EN_SECOND, Roles.ETAT_MAJOR,
         Roles.CHEF_SERVICE, Roles.CHEF_SECTEUR, Roles.CHEF_SECTION, Roles.EQUIPIER]
COURT = {Roles.MASTER_ADMIN: "Admin. général", Roles.ADMIN_NAVIRE: "Admin. unité", Roles.COMMANDANT: "Commandant",
         Roles.COMMANDANT_EN_SECOND: "Second", Roles.ETAT_MAJOR: "État-major", Roles.CHEF_SERVICE: "Chef service",
         Roles.CHEF_SECTEUR: "Chef secteur", Roles.CHEF_SECTION: "Chef section", Roles.EQUIPIER: "Équipier"}


def niveau(role, action):
    """Niveau comparé au seuil : le second retombe au niveau équipier sauf action qui lui est ouverte."""
    n = ROLE_TO_LEVEL[role.value]
    if role.value in ROLES_SANS_ECRITURE_HERITEE and not action.ouverte_au_second:
        return RoleLevel.EQUIPIER
    return n


L = ["# Annexe B — Matrice rôle × action (généré, état B)", "",
     "> Diffusion restreinte. Généré par `outils/generer_annexe_b.py` depuis `matrix/core/role_thresholds.py`, "
     "`matrix/core/roles.py` et `matrix/core/permissions.py` de l'état B (`6d6d0be`, non fusionné dans `main`). Ne pas éditer à la main.", "",
     "## B.1 Actions à seuil de rôle configurable (valeurs par défaut)", "",
     "Lecture : ✔ = le rôle atteint le seuil par défaut ; ✔† = idem, mais un état-major n'écrit que dans les services "
     "rattachés à sa fonction de commandant adjoint ; ✱ = commandant en second : son grade atteint le seuil mais l'écriture héritée du grade lui est retirée, l'accès dépend de la vue (certaines vues comparent le seuil au grade, par exemple la gestion des modules, d'autres au niveau d'écriture) ; — = seuil non atteint. L'administrateur d'unité peut modifier chaque "
     "seuil de son bâtiment (Réglages, onglet Sécurité) ; ceux de portée « flotte » ne le sont que par l'administrateur général. "
     "Le niveau n'est qu'une condition : le périmètre de l'objet doit aussi être respecté (chapitre 5).", "",
     "| Catégorie | Action | Seuil | " + " | ".join(COURT[r] for r in ORDRE) + " |",
     "|---|---|---|" + "---|" * len(ORDRE)]
for a in REGISTRE_ACTIONS:
    cases = []
    for r in ORDRE:
        ok = niveau(r, a) >= a.defaut
        if r == Roles.MASTER_ADMIN:
            ok = True
        if r == Roles.COMMANDANT_EN_SECOND and not ok and ROLE_TO_LEVEL[r.value] >= a.defaut:
            cases.append("✱")  # grade suffisant, écriture héritée retirée : dépend de la vue
            continue
        cases.append(("✔†" if r == Roles.ETAT_MAJOR else "✔") if ok else "—")
    portee = "flotte" if a.portee == "GLOBALE" else "bâtiment"
    L.append(f"| {a.categorie} | {a.libelle} | {a.defaut.name} ({portee}) | " + " | ".join(cases) + " |")

L += ["", f"Total : **{len(REGISTRE_ACTIONS)} actions** configurables. Le commandant en second n'hérite pas de son grade pour "
      "l'écriture ; seules les actions marquées « ouverte au second » dans le registre lui restent accessibles selon son grade.", "",
      "Actions ouvertes au commandant en second : " +
      (", ".join(f"`{a.cle}`" for a in REGISTRE_ACTIONS if a.ouverte_au_second) or "aucune") + ".", "",
      "## B.2 Qui peut attribuer ou gérer quel rôle (comptes)", "",
      "| Rôle de l'acteur | Rôles qu'il peut attribuer ou gérer |", "|---|---|",
      "| Administrateur général | Tous |"]
for r in ORDRE[1:]:
    cibles = ManageUsersPermission.MANAGE_MAP.get(r.value)
    L.append(f"| {r.label} | " + (", ".join(Roles(c).label for c in sorted(cibles, key=lambda c: -ROLE_TO_LEVEL[c.value])) if cibles else "Aucun") + " |")
L += ["", "La même table sert à l'API et aux écrans web. Un administrateur d'unité ne gère jamais l'administrateur général ; "
      "hors administrateur général, un acteur n'agit que sur les comptes de son propre bâtiment et peut toujours modifier son propre compte.", ""]
SORTIE.parent.mkdir(parents=True, exist_ok=True)
SORTIE.write_text("\n".join(L), encoding="utf-8")
print(len(REGISTRE_ACTIONS), "actions")
