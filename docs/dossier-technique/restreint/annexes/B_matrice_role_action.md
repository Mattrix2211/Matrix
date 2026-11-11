# Annexe B — Matrice rôle × action (généré, état B)

> Diffusion restreinte. Généré par `outils/generer_annexe_b.py` depuis `matrix/core/role_thresholds.py`, `matrix/core/roles.py` et `matrix/core/permissions.py` de l'état B (`6d6d0be`, non fusionné dans `main`). Ne pas éditer à la main.

## B.1 Actions à seuil de rôle configurable (valeurs par défaut)

Lecture : ✔ = le rôle atteint le seuil par défaut ; ✔† = idem, mais un état-major n'écrit que dans les services rattachés à sa fonction de commandant adjoint ; ✱ = commandant en second : son grade atteint le seuil mais l'écriture héritée du grade lui est retirée, l'accès dépend de la vue (certaines vues comparent le seuil au grade, par exemple la gestion des modules, d'autres au niveau d'écriture) ; — = seuil non atteint. L'administrateur d'unité peut modifier chaque seuil de son bâtiment (Réglages, onglet Sécurité) ; ceux de portée « flotte » ne le sont que par l'administrateur général. Le niveau n'est qu'une condition : le périmètre de l'objet doit aussi être respecté (chapitre 5).

| Catégorie | Action | Seuil | Admin. général | Admin. unité | Commandant | Second | État-major | Chef service | Chef secteur | Chef section | Équipier |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Organisation de l'unité | Modifier ou supprimer la structure de l'unité : services, secteurs, sections, configuration des secteurs, lieux | ADMIN_NAVIRE (bâtiment) | ✔ | ✔ | — | — | — | — | — | — | — |
| Organisation de l'unité | Archiver l'unité, activer/désactiver son double équipage ou changer son fuseau horaire de référence | ADMIN_NAVIRE (bâtiment) | ✔ | ✔ | — | — | — | — | — | — | — |
| Matériel mobile | Créer ou modifier un matériel, un dossier | CHEF_SECTION (bâtiment) | ✔ | ✔ | ✔ | ✱ | ✔† | ✔ | ✔ | ✔ | — |
| Matériel mobile | Supprimer un matériel, un dossier, un document, ou lancer une action groupée | CHEF_SERVICE (bâtiment) | ✔ | ✔ | ✔ | ✱ | ✔† | ✔ | — | — | — |
| Installations | Créer ou modifier une installation, ajouter un document | CHEF_SECTION (bâtiment) | ✔ | ✔ | ✔ | ✱ | ✔† | ✔ | ✔ | ✔ | — |
| Installations | Supprimer une installation ou un de ses documents, ou lancer une action groupée | CHEF_SERVICE (bâtiment) | ✔ | ✔ | ✔ | ✱ | ✔† | ✔ | — | — | — |
| Installations | Gérer les tâches d'entretien d'une installation (ajout, modification, suppression, pièce jointe) | CHEF_SERVICE (bâtiment) | ✔ | ✔ | ✔ | ✱ | ✔† | ✔ | — | — | — |
| Installations | Rédiger ou proposer une nouvelle version d'une fiche de maintenance d'installation (chef de section ou de secteur) | CHEF_SECTION (bâtiment) | ✔ | ✔ | ✔ | ✱ | ✔† | ✔ | ✔ | ✔ | — |
| Installations | Proposer une fiche de maintenance flotte (matériel ou installation) ou son adaptation (chef de section ou de secteur) | CHEF_SECTION (bâtiment) | ✔ | ✔ | ✔ | ✱ | ✔† | ✔ | ✔ | ✔ | — |
| Installations | Modifier le rattachement parent/enfant d'un matériel ou d'une installation | CHEF_SERVICE (bâtiment) | ✔ | ✔ | ✔ | ✱ | ✔† | ✔ | — | — | — |
| Installations | Configurer les ponts et le positionnement du matériel sur le plan visuel du navire | CHEF_SERVICE (bâtiment) | ✔ | ✔ | ✔ | ✱ | ✔† | ✔ | — | — | — |
| Stock | Gérer le stock de pièces : créer ou modifier une pièce, prélever, saisir un mouvement ou un inventaire | CHEF_SECTION (bâtiment) | ✔ | ✔ | ✔ | ✱ | ✔† | ✔ | ✔ | ✔ | — |
| Maintenance | Créer ou modifier une occurrence ou une exécution de maintenance | EQUIPIER (bâtiment) | ✔ | ✔ | ✔ | ✔ | ✔† | ✔ | ✔ | ✔ | ✔ |
| Maintenance | Exécuter ou commenter une maintenance qui n'est pas la sienne | CHEF_SECTION (bâtiment) | ✔ | ✔ | ✔ | ✱ | ✔† | ✔ | ✔ | ✔ | — |
| Maintenance | Corriger un compte rendu de maintenance terminé (motif obligatoire, saisie d'origine conservée) | CHEF_SECTEUR (bâtiment) | ✔ | ✔ | ✔ | ✱ | ✔† | ✔ | ✔ | — | — |
| Maintenance | Créer ou modifier un plan de maintenance préventive | CHEF_SECTION (bâtiment) | ✔ | ✔ | ✔ | ✱ | ✔† | ✔ | ✔ | ✔ | — |
| Tableau de bord | Voir le bloc Supervision (retards, validations, indicateurs du secteur ou du service) de la page Aujourd'hui | CHEF_SECTEUR (bâtiment) | ✔ | ✔ | ✔ | ✱ | ✔† | ✔ | ✔ | — | — |
| Discussions | Créer ou modifier une discussion | CHEF_SECTION (bâtiment) | ✔ | ✔ | ✔ | ✱ | ✔† | ✔ | ✔ | ✔ | — |
| Quarts / Services de garde | Publier (valider) une liste de quarts ou de services de garde proposée par un chef de liste | CHEF_SERVICE (bâtiment) | ✔ | ✔ | ✔ | ✱ | ✔† | ✔ | — | — | — |
| Feuille de service | Configurer les rubriques d'en-tête et les fonctions de service de la feuille de service quotidienne | CHEF_SERVICE (bâtiment) | ✔ | ✔ | ✔ | ✱ | ✔† | ✔ | — | — | — |
| Feuille de service | Viser une feuille de service en tant que chef du secteur rédacteur | CHEF_SECTEUR (bâtiment) | ✔ | ✔ | ✔ | ✱ | ✔† | ✔ | ✔ | — | — |
| Feuille de service | Viser une feuille de service en tant que chef du service rédacteur (ex. Pont) | CHEF_SERVICE (bâtiment) | ✔ | ✔ | ✔ | ✱ | ✔† | ✔ | — | — | — |
| Feuille de service | Valider une modification de l'organisation sécurité / protection-défense (scénarios d'alerte et postes) | COMMANDANT (bâtiment) | ✔ | ✔ | ✔ | — | — | — | — | — | — |
| Modules | Activer ou désactiver un module applicatif pour cette unité (onglet Modules des Réglages) | COMMANDANT_EN_SECOND (bâtiment) | ✔ | ✔ | ✔ | ✱ | — | — | — | — | — |
| Comptes | Réinitialiser le mot de passe d'un marin du bâtiment (mot de passe provisoire à changer à la connexion) | ADMIN_NAVIRE (bâtiment) | ✔ | ✔ | — | — | — | — | — | — | — |
| Tâches | Attribuer une tâche à un marin de son secteur ou de son service et suivre l'avancement de l'équipe | CHEF_SECTION (flotte) | ✔ | ✔ | ✔ | ✱ | ✔† | ✔ | ✔ | ✔ | — |
| Annonces | Publier une annonce à son niveau (bâtiment, service, secteur, section, équipage) | CHEF_SERVICE (bâtiment) | ✔ | ✔ | ✔ | ✔ | ✔† | ✔ | — | — | — |
| Programme du bâtiment | Saisir le programme du bâtiment (escales, arrêts techniques, exercices, réunions) et déléguer ce droit | ETAT_MAJOR (bâtiment) | ✔ | ✔ | ✔ | ✱ | ✔† | — | — | — | — |
| Programme du bâtiment | Configurer les types d'événements du programme du bâtiment | ADMIN_NAVIRE (bâtiment) | ✔ | ✔ | — | — | — | — | — | — | — |
| Postes du bord | Créer les postes du bord, définir leurs formations exigées et y affecter des marins | CHEF_SERVICE (bâtiment) | ✔ | ✔ | ✔ | ✱ | ✔† | ✔ | — | — | — |
| Documentation | Rédiger et soumettre à validation un document ou une nouvelle version | CHEF_SECTION (bâtiment) | ✔ | ✔ | ✔ | ✱ | ✔† | ✔ | ✔ | ✔ | — |
| Documentation | Valider et publier un document ou une nouvelle version, archiver un document | CHEF_SERVICE (bâtiment) | ✔ | ✔ | ✔ | ✱ | ✔† | ✔ | — | — | — |
| RETEX | Valider, refuser ou clore un RETEX et en décider les actions | CHEF_SERVICE (bâtiment) | ✔ | ✔ | ✔ | ✱ | ✔† | ✔ | — | — | — |
| Référentiels globaux | Modifier les grades, spécialités ou la disponibilité des rôles (référentiel commun à toute la flotte) | MASTER_ADMIN (flotte) | ✔ | — | — | — | — | — | — | — | — |
| Référentiels globaux | Désigner ou retirer un responsable de spécialité ou de classe de navire (dashboards transverses flotte) | MASTER_ADMIN (flotte) | ✔ | — | — | — | — | — | — | — | — |

Total : **35 actions** configurables. Le commandant en second n'hérite pas de son grade pour l'écriture ; seules les actions marquées « ouverte au second » dans le registre lui restent accessibles selon son grade.

Actions ouvertes au commandant en second : `annonce_publication`.

## B.2 Qui peut attribuer ou gérer quel rôle (comptes)

| Rôle de l'acteur | Rôles qu'il peut attribuer ou gérer |
|---|---|
| Administrateur général | Tous |
| Administrateur d'unité | Administrateur d'unité, Commandant, Commandant en second, État-major, Chef de service, Chef de secteur, Chef de section, Équipier |
| Commandant | État-major, Chef de service, Chef de secteur, Chef de section, Équipier |
| Commandant en second | Aucun |
| État-major | Chef de service, Chef de secteur, Chef de section, Équipier |
| Chef de service | Chef de secteur, Chef de section, Équipier |
| Chef de secteur | Chef de section, Équipier |
| Chef de section | Équipier |
| Équipier | Aucun |

La même table sert à l'API et aux écrans web. Un administrateur d'unité ne gère jamais l'administrateur général ; hors administrateur général, un acteur n'agit que sur les comptes de son propre bâtiment et peut toujours modifier son propre compte.
