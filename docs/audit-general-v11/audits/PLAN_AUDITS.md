# Plan des 20 audits

Pour chaque audit : questions, sources historiques, code à inspecter, vérifications possibles. État au 2026-11-05 : **aucun audit terminé**.

| N° | Phase | Sujet | Questions centrales | Code et preuves à examiner en priorité | Sources historiques | État |
|---|---|---|---|---|---|---|
| 01 | 1 | Besoin et historique | Matrix est-il toujours l'application imaginée ? Quoi de promis, reporté, abandonné, oublié ? | Notion (cahier, feuille de route, tâches), `docs/archive`, git, PR | Cahier §1 à §42 | **Partiel** |
| 19 | 2 | Conformité Marine | Terminologie, hiérarchie, quarts, visas : règle confirmée, usage variable ou hypothèse ? | `org/`, `accounts/`, `quarts/`, libellés des gabarits | Notion « Organigramme et rôles » et pages 01 à 13 | Non commencé |
| 02 | 3 | Configurabilité | Un bord se règle-t-il seul : services, secteurs, sections facultatives, rattachements, seuils ? | `org/`, `matrix/core/role_thresholds.py`, `VersionConfiguration`, écrans de paramètres | Cahier §4, §5, §33 | Non commencé |
| 03 | 3 | Première mise en service | Installer, initialiser, importer, former : combien d'étapes techniques ? | `scripts/`, `README.md`, commandes de gestion, `setup.bat` | Cahier §25 à §28 | Non commencé |
| 04 | 3 | Usage quotidien | Parcours matin, exécution, signalement, validation, fin de journée | `dashboard/`, `taches/`, `maintenance/`, parcours navigateur | Cahier §2, §6, §40 | Non commencé |
| 05 | 3 | UX et accessibilité | Écart aux maquettes, clavier, responsive, postes partagés | `matrix/templates`, `matrix/static`, `docs/UX.md`, `docs/prototypes` | UX.md, décisions UX V1.1 | Non commencé |
| 06 | 3 | Rôles et permissions | Droits par fonction, périmètre, double équipage, séparation des bâtiments | `matrix/core/permissions*`, `scopes`, `role_thresholds`, tests d'étanchéité | Notion décisions (relève, COMA, terre) | Non commencé |
| 07 | 3 | Calendrier | Alimentation unique, conflits, vues perso/collectives | `calendar_app/`, `programme/` | Cahier §15 | Non commencé |
| 08 | 3 | Maintenance et installations | Fiches, gammes, périodicité, anomalies, circuits de validation | `maintenance/`, `assets/`, `rondes/` | Cahier §20, circuits fiche flotte | Non commencé |
| 09 | 3 | Quarts, services MER/QUAI | Listes, validation, échanges, changements de mode, feuille de service | `quarts/` | Cahier §8 à §14, Notion 06 | Non commencé |
| 10 | 3 | Logistique | Stocks, mouvements, demandes, inventaires | `logistics/`, `demandes/` | Cahier §21 | Non commencé |
| 11 | 3 | Communication | Fils contextuels, annonces, notifications | `threads/`, `annonces/`, `notifications/` | Cahier §16 à §19, §38 | Non commencé |
| 12 | 3 | Autres modules | Formations, documentation, RETEX, absences, rondes, postes | `training/`, `documentation/`, `retex/`, `absences/`, `postes/` | Cahier §22 | Non commencé |
| 13 | 4 | Architecture | Découpage, couplage, duplication, performance | tout le dépôt | Cahier §32 | Non commencé |
| 14 | 4 | Données | Contraintes, transactions, concurrence, SQLite et PostgreSQL | `*/models.py`, migrations | Cahier §30, §31 | Non commencé |
| 15 | 4 | Sécurité et résilience | Authentification, secrets, journalisation, sauvegarde | `matrix/settings.py`, middleware, `AuditLog` | Cahier §29 | Non commencé |
| 16 | 4 | Tests | Pertinence, trous, absence de tests navigateur versionnés | tous les `tests/` | — | Non commencé |
| 17 | 4 | Déploiement et exploitation | Installation, mise à jour, sauvegarde, supervision | `README.md`, `docker-compose.yml`, `*.bat` | Cahier §25, §27 | Non commencé |
| 20 | 5 | Données de démonstration | Crédibilité, couverture rôles et cas limites | `seed_demo_*`, `docs/demo`, `docs/recette` | — | Non commencé |
| 18 | 6 | Synthèse | Croisement des 19 autres audits, feuille de route | tous les rapports | — | Non commencé |
