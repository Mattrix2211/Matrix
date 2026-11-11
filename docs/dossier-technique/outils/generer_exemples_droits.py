"""Génère le tableau « sept profils × actions » du chapitre 5 depuis le code de l'état B.

Usage : python generer_exemples_droits.py <racine_du_code> <fichier_de_sortie>
Les profils sont de simples objets de test (aucune base de données) : on applique les mêmes fonctions de niveau que le code réel.
"""
import os
import sys
from pathlib import Path
from types import SimpleNamespace

RACINE, SORTIE = Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve()
os.chdir(RACINE)
sys.path.insert(0, str(RACINE))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "matrix.settings")
os.environ["DJANGO_DEBUG"] = "1"

import django  # noqa: E402

django.setup()

from matrix.core.role_thresholds import REGISTRE_PAR_CLE, niveau_pour_action  # noqa: E402

PROFILS = [  # libellé, rôle, fonction de commandant adjoint
    ("Matelot (équipier)", "EQUIPIER", ""), ("Chef de section", "CHEF_SECTION", ""),
    ("Chef de secteur", "CHEF_SECTEUR", ""), ("Chef de service", "CHEF_SERVICE", ""),
    ("COMAEQ (état-major)", "ETAT_MAJOR", "COMAEQ"), ("Commandant", "COMMANDANT", ""),
    ("Administrateur technique (unité)", "ADMIN_NAVIRE", ""),
]
ACTIONS = [
    ("maintenance_execution_ecriture", "Exécuter une maintenance"),
    ("tache_attribution", "Attribuer une tâche à un marin"),
    ("asset_ecriture_simple", "Créer ou modifier un matériel"),
    ("asset_gestion_avancee", "Supprimer un matériel, action groupée"),
    ("maintenance_compte_rendu_correction", "Corriger un compte rendu de maintenance terminé"),
    ("supervision_aujourdhui", "Voir le bloc Supervision de la page Aujourd'hui"),
    ("liste_service_publication", "Publier une liste de quarts ou de gardes (seuil)"),
    ("feuille_service_visa_service", "Viser une feuille de service au palier du chef de service (seuil)"),
    ("annonce_publication", "Publier une annonce"),
    ("module_gestion", "Activer ou désactiver un module du bâtiment"),
    ("mot_de_passe_reinitialisation", "Réinitialiser un mot de passe"),
    ("structure_navire_ecriture", "Modifier la structure du bâtiment"),
]


def utilisateur(role, coma):
    profil = SimpleNamespace(role=role, fonction_coma=coma, navire_id_effectif=1, ship_id=1)
    return SimpleNamespace(is_superuser=False, is_authenticated=True, profile=profil, pk=1)


L = ["| Action (valeur par défaut du seuil) | " + " | ".join(p[0] for p in PROFILS) + " |", "|---|" + "---|" * len(PROFILS)]
for cle, libelle in ACTIONS:
    action = REGISTRE_PAR_CLE[cle]
    cases = []
    for _, role, coma in PROFILS:
        u = utilisateur(role, coma)
        ok = niveau_pour_action(u, cle) >= action.defaut
        cases.append("oui" if ok else "non")
    L.append(f"| {libelle} ({action.defaut.name}) | " + " | ".join(cases) + " |")
SORTIE.write_text("\n".join(L) + "\n", encoding="utf-8")
print("\n".join(L))
