<!-- couvre: restreint/annexes/B_matrice_role_action.md | Annexe B — Matrice rôle × action (généré, état B) -->
<!-- couvre: restreint/annexes/B_matrice_role_action.md | B.1 Actions à seuil de rôle configurable (valeurs par défaut) -->
<!-- couvre: restreint/annexes/B_matrice_role_action.md | B.2 Qui peut attribuer ou gérer quel rôle (comptes) -->
<!-- partie: Organisation et rôles -->
# Qui peut quoi : matrice des actions à seuil

<div class="ligne-public"><b>Public :</b> responsables, commandement · <b>Ce que vous y trouverez :</b> pour chaque action réglable, le niveau minimal par défaut, en libellés · <b>Version avec clés de code :</b> annexes consultables (accès restreint)</div>

Matrix tient un registre de {{fait:n_actions_seuil}} actions dont le niveau minimal est réglable par bâtiment. Le tableau donne les **valeurs par défaut**. Un niveau suffisant n'est qu'une condition : le **périmètre** s'y ajoute toujours, et un état-major n'écrit que dans les services rattachés à sa fonction.

## Organisation de l'unité

| Action | Niveau minimal par défaut |
|---|---|
| Modifier ou supprimer la structure de l'unité : services, secteurs, sections, configuration des secteurs, lieux | Administrateur d'unité |
| Archiver l'unité, activer/désactiver son double équipage ou changer son fuseau horaire de référence | Administrateur d'unité |

## Matériel mobile

| Action | Niveau minimal par défaut |
|---|---|
| Créer ou modifier un matériel, un dossier | Chef de section |
| Supprimer un matériel, un dossier, un document, ou lancer une action groupée | Chef de service |

## Installations

| Action | Niveau minimal par défaut |
|---|---|
| Créer ou modifier une installation, ajouter un document | Chef de section |
| Supprimer une installation ou un de ses documents, ou lancer une action groupée | Chef de service |
| Gérer les tâches d'entretien d'une installation (ajout, modification, suppression, pièce jointe) | Chef de service |
| Rédiger ou proposer une nouvelle version d'une fiche de maintenance d'installation (chef de section ou de secteur) | Chef de section |
| Proposer une fiche de maintenance flotte (matériel ou installation) ou son adaptation (chef de section ou de secteur) | Chef de section |
| Modifier le rattachement parent/enfant d'un matériel ou d'une installation | Chef de service |
| Configurer les ponts et le positionnement du matériel sur le plan visuel du navire | Chef de service |

## Stock

| Action | Niveau minimal par défaut |
|---|---|
| Gérer le stock de pièces : créer ou modifier une pièce, prélever, saisir un mouvement ou un inventaire | Chef de section |

## Maintenance

| Action | Niveau minimal par défaut |
|---|---|
| Créer ou modifier une occurrence ou une exécution de maintenance | Équipier |
| Exécuter ou commenter une maintenance qui n'est pas la sienne | Chef de section |
| Corriger un compte rendu de maintenance terminé (motif obligatoire, saisie d'origine conservée) | Chef de secteur |
| Créer ou modifier un plan de maintenance préventive | Chef de section |

## Tableau de bord

| Action | Niveau minimal par défaut |
|---|---|
| Voir le bloc Supervision (retards, validations, indicateurs du secteur ou du service) de la page Aujourd'hui | Chef de secteur |

## Discussions

| Action | Niveau minimal par défaut |
|---|---|
| Créer ou modifier une discussion | Chef de section |

## Quarts / Services de garde

| Action | Niveau minimal par défaut |
|---|---|
| Publier (valider) une liste de quarts ou de services de garde proposée par un chef de liste | Chef de service |

## Feuille de service

| Action | Niveau minimal par défaut |
|---|---|
| Configurer les rubriques d'en-tête et les fonctions de service de la feuille de service quotidienne | Chef de service |
| Viser une feuille de service en tant que chef du secteur rédacteur | Chef de secteur |
| Viser une feuille de service en tant que chef du service rédacteur (ex. Pont) | Chef de service |
| Valider une modification de l'organisation sécurité / protection-défense (scénarios d'alerte et postes) | Commandant |

## Modules

| Action | Niveau minimal par défaut |
|---|---|
| Activer ou désactiver un module applicatif pour cette unité (onglet Modules des Réglages) | Commandant en second |

## Comptes

| Action | Niveau minimal par défaut |
|---|---|
| Réinitialiser le mot de passe d'un marin du bâtiment (mot de passe provisoire à changer à la connexion) | Administrateur d'unité |

## Tâches

| Action | Niveau minimal par défaut |
|---|---|
| Attribuer une tâche à un marin de son secteur ou de son service et suivre l'avancement de l'équipe | Chef de section |

## Annonces

| Action | Niveau minimal par défaut |
|---|---|
| Publier une annonce à son niveau (bâtiment, service, secteur, section, équipage) | Chef de service (ouverte au commandant en second) |

## Programme du bâtiment

| Action | Niveau minimal par défaut |
|---|---|
| Saisir le programme du bâtiment (escales, arrêts techniques, exercices, réunions) et déléguer ce droit | État-major |
| Configurer les types d'événements du programme du bâtiment | Administrateur d'unité |

## Postes du bord

| Action | Niveau minimal par défaut |
|---|---|
| Créer les postes du bord, définir leurs formations exigées et y affecter des marins | Chef de service |

## Documentation

| Action | Niveau minimal par défaut |
|---|---|
| Rédiger et soumettre à validation un document ou une nouvelle version | Chef de section |
| Valider et publier un document ou une nouvelle version, archiver un document | Chef de service |

## RETEX

| Action | Niveau minimal par défaut |
|---|---|
| Valider, refuser ou clore un RETEX et en décider les actions | Chef de service |

## Référentiels globaux

| Action | Niveau minimal par défaut |
|---|---|
| Modifier les grades, spécialités ou la disponibilité des rôles (référentiel commun à toute la flotte) | Administrateur général |
| Désigner ou retirer un responsable de spécialité ou de classe de navire (dashboards transverses flotte) | Administrateur général |

## Qui peut attribuer ou gérer quel rôle

On ne gère que des rôles **inférieurs ou égaux au sien**, selon une table unique appliquée à l'écran comme à l'interface de programmation. Le commandant en second ne gère aucun compte ; hors administrateur général, on n'agit que sur les comptes de son propre bâtiment. La table complète est dans les annexes consultables (table B2) ; le schéma de la section [[RF:05_roles_et_autorisations]] la résume.
