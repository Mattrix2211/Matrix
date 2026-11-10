# G. Écarts documentaires

Ce qui manque pour produire ensuite un **manuel de référence professionnel** de Matrix, à trois publics : équipiers, responsables, administrateurs. Les constats viennent du dépôt (`1c37f22`), de l'inventaire de l'audit et des pages Notion lues.

## G.1 Ce qui existe

`README.md`, `CLAUDE.md`, `docs/REFERENCE.md`, `docs/UX.md` (cahier UX/UI), `docs/RECETTE.md`, `docs/DEMO.md`, `docs/TESTS_MARINS.md`, `docs/COMPATIBILITE_CHECKLIST.md`, `docs/recette/`, `docs/propositions/` (15 fichiers), `docs/archive/`, une application `documentation` (bibliothèque dans Matrix). Sources de vérité métier : Notion (cahier, organigramme, décisions, feuille de route, tâches).

## G.2 Écarts

| Public | Manque | Source à consolider |
|---|---|---|
| Tous | Glossaire unique : **rôle** (profil d'accès) ≠ **fonction** (de service, de quart) ≠ **grade** ≠ **brevet** ; BSC, COMAEQ, COMOPS, COMANAV, COMAVIA, OPN/DDI, OG, OPSC, fraction, tour, bordée, tiers, « de musique », « homme mort » | N2, N8, N9 (vigilance terminologique M-11) |
| Tous | Principes d'usage : ce que Matrix ne fait pas (n'autorise pas l'appareillage, ne bloque pas par qualification, ne remplace pas SIGLe/ODIN/SSF) | S1, N1, N2 |
| Équipier | Guide « ma journée » : tâches, bloquer, signaler une anomalie ou un outil, mes tours de service, notifications, épingler | UX, S1 §12 |
| Équipier | États d'une tâche (À faire, En cours, Bloquée, À valider, Non réalisée, Terminée) et leur signification | Décisions DEC-TAC/CLO/BLQ |
| Responsable | Attribution, priorités (3 niveaux), validation facultative, tâches collectives et coordinateur | DEC-TAC-*, DEC-COL-* |
| Responsable | Circuits de validation illustrés (feuille de service, RETEX, fiches, appareillage, transfert de matériel, mutation) | B.4 |
| Responsable | Maintenance : périodicités, calcul de l'échéance, durée indicative et sa méthode (une fois validée) | DEC-PER-*, PT-DUR-* |
| Responsable | Anomalie, intervention, clôture, décisions du chef de secteur | DEC-ANO-* |
| Responsable | Feuille de service : préparation par le BSC, approbation, version, réimpression A4, double équipage | DEC-FDS-* |
| Administrateur | Matrice de droits publiée, **par fonction et périmètre**, avec ce que l'administrateur technique ne peut pas faire | P02, DEC-DRT-02 |
| Administrateur | Structure : création, renommage, archivage, réactivation ; politique de suppression et d'archivage | P04, P07 |
| Administrateur | Comptes : rattachement obligatoire, désactivation, mutation, import (à venir) | DEC-DRT-06, DEC-MUT-* |
| Administrateur | Installation : variables d'environnement, `DJANGO_SECRET_KEY`, base, HTTPS derrière un proxy, serveur d'application | AUD-010, 011, 017 ; P03 |
| Administrateur | **Sauvegarde et restauration** (absente du dépôt) | AUD-031 |
| Administrateur | Supervision de Redis/Celery et conséquences de leur arrêt | AUD-032, 039 |
| Administrateur | Instance de démonstration isolée et verrou des commandes de démonstration | P06, N5 B |
| Développeur | Mise à jour de `CLAUDE.md` (RoleLevel/RolePermission), de `docs/REFERENCE.md` (« 14 apps » → 22), des conventions de suppression | AUD-004, 005 |
| Gouvernance | Alignement de Notion : baseline `dfd6a3c` périmée, cahier §8/§10/§11 (génération automatique abandonnée), §20 (Rondes retiré), passation | AUD-004, CT-09, CT-10 |
| Gouvernance | Registre des décisions unique, daté, avec statut (ce dossier en est la première version) | A |
| Sécurité | Politique de conservation des journaux, des notifications lues et des estimations de durée | IM-10 |

## G.3 Sources non lues pour ce dossier

Pages Notion 01 à 05, 07 à 12 de l'organigramme (RH, formation, maintenance, opérations, SIC, planification, ALFAN, CEPN, modèle de données, glossaire des organismes externes) ; « Vision et Objectifs » ; « Recette UX V1.1 » ; « Tranche 1 ». Le *Guide du marin 2023* n'a jamais été accessible : seules les références de page citées par Notion sont connues. Ces pages devront être lues avant le manuel.

## G.4 Plan proposé du manuel

1. Présentation et principes (ce que Matrix est et n'est pas).
2. Glossaire.
3. Guide de l'équipier.
4. Guide du responsable (par fonction : section, secteur, service, commandant adjoint, BSC).
5. Guide de l'administrateur (structure, comptes, droits, mutation).
6. Circuits de validation (fiches illustrées).
7. Installation, sécurité et exploitation (avec les SIC).
8. Annexes : états, matrices de droits, historique des décisions.
