# Annexe G — Matrice de couverture (générée)

> Diffusion restreinte. Générée par `outils/generer_matrice_couverture.py` à partir de l'inventaire de l'état B (`couverture/etat_B/inventaire.json`) et des chapitres rédigés. Ne pas éditer à la main.

Chapitres rédigés pris en compte : 01_vision.md, 02_vue_ensemble.md, 03_lire_ce_dossier.md, 04_organisation.md, 04_organisation_technique.md, 05_comptes_autorisations_technique.md, 05_comptes_roles_autorisations.md, 06_accueil_pilotage.md, 06_accueil_pilotage_technique.md, 07_calendrier.md, 07_calendrier_technique.md, 08_quarts_services_feuille.md, 08_quarts_services_feuille_technique.md, 09_communication.md, 09_communication_technique.md, 10_taches_demandes_programme_postes.md, 10_taches_demandes_programme_postes_technique.md, 18_architecture.md, 19_modeles_donnees.md, 22_securite.md.

## G.1 Modèles de données

Statut : **Expliqué** = le nom du modèle figure dans un chapitre de domaine rédigé (hors chapitre 19) ; **Nommé** = cité seulement dans la présentation par familles du chapitre 19 ; **Dictionnaire seul** = présent uniquement dans `couverture/etat_B/MODELES.md`. Seuls les modèles « expliqués » sont couverts ; les autres le seront dans l'ensemble indiqué.

| Paquet | Modèles | Expliqués | Nommés (ch. 19) | Dictionnaire seul | Chapitres | Ensemble |
|---|---|---|---|---|---|---|
| `absences` | 1 | 1 | 0 | 0 | 8 | E2 |
| `accounts` | 10 | 10 | 0 | 0 | 5, 19, 22 | E1 |
| `annonces` | 4 | 4 | 0 | 0 | 9 | E2 |
| `assets` | 29 | 0 | 14 | 15 | 11 | E3 |
| `calendar_app` | 1 | 1 | 0 | 0 | 7 | E2 |
| `core` | 1 | 1 | 0 | 0 | 5, 18, 22 | E1 |
| `dashboard` | 2 | 0 | 2 | 0 | 6, 16 | E2/E3 |
| `demandes` | 1 | 1 | 0 | 0 | 10 | E2 |
| `documentation` | 3 | 0 | 3 | 0 | 15 | E3 |
| `logistics` | 8 | 0 | 7 | 1 | 12, 13 | E3 |
| `maintenance` | 6 | 0 | 6 | 0 | 12 | E3 |
| `notifications` | 2 | 2 | 0 | 0 | 9, 21 | E2/E4 |
| `org` | 15 | 15 | 0 | 0 | 4, 19 | E1 |
| `postes` | 2 | 2 | 0 | 0 | 10 | E2 |
| `programme` | 3 | 3 | 0 | 0 | 10 | E2 |
| `quarts` | 22 | 22 | 0 | 0 | 8 | E2 |
| `retex` | 2 | 0 | 2 | 0 | 15 | E3 |
| `rondes` | 4 | 0 | 4 | 0 | 12 | E3 |
| `taches` | 5 | 5 | 0 | 0 | 10 | E2 |
| `threads` | 3 | 3 | 0 | 0 | 9 | E2 |
| `training` | 11 | 0 | 4 | 7 | 14 | E3 |
| **Total** | **135** | **70** | **42** | **23** | | |

Modèles de l'ensemble 1 non nommés dans un chapitre rédigé : aucun.

## G.2 Routes (pages et API)

| Paquet de la vue | Routes | Chapitres | Ensemble |
|---|---|---|---|
| `absences` | 1 | 8 | E2 |
| `accounts` | 29 | 5, 19, 22 | E1 |
| `annonces` | 4 | 9 | E2 |
| `assets` | 90 | 11 | E3 |
| `calendar_app` | 9 | 7 | E2 |
| `dashboard` | 17 | 6, 16 | E2/E3 |
| `demandes` | 5 | 10 | E2 |
| `django` | 368 | 18, 20 | E1/E4 |
| `documentation` | 5 | 15 | E3 |
| `logistics` | 32 | 12, 13 | E3 |
| `maintenance` | 30 | 12 | E3 |
| `matrix` | 8 | 18, 20 | E1/E4 |
| `notifications` | 16 | 9, 21 | E2/E4 |
| `org` | 20 | 4, 19 | E1 |
| `postes` | 3 | 10 | E2 |
| `programme` | 5 | 10 | E2 |
| `quarts` | 15 | 8 | E2 |
| `reports` | 1 | 6 | E2 |
| `rest_framework` | 16 | 18, 20 | E1/E4 |
| `retex` | 5 | 15 | E3 |
| `taches` | 5 | 10 | E2 |
| `threads` | 12 | 9 | E2 |
| `training` | 25 | 14 | E3 |
| **Total** | **721** | | |

Le détail des routes est généré dans `couverture/etat_B/ROUTES.md` (annexe C, ensemble 4).

## G.3 Tâches planifiées

| Tâche | Nom | Citée dans un chapitre rédigé |
|---|---|---|
| `matrix.core.tasks.purger_sessions` | `purger_sessions_daily` | domaine seulement (ch. 18), détail ch. 21 |
| `matrix.core.tasks.appliquer_releves_echues` | `appliquer_releves_echues_minute` | oui |
| `quarts.tasks.signaler_divergences_feuilles` | `signaler_divergences_feuilles_15min` | oui |
| `quarts.tasks.traiter_echeances_activation` | `traiter_echeances_activation_minute` | oui |
| `matrix.core.tasks.purger_brouillons` | `purger_brouillons_daily` | domaine seulement (ch. 18), détail ch. 21 |
| `maintenance.tasks.generate_occurrences` | `generate_occurrences_daily` | domaine seulement (ch. 18), détail ch. 21 |
| `maintenance.tasks.compute_overdue` | `compute_overdue_hourly` | domaine seulement (ch. 18), détail ch. 21 |
| `notifications.tasks.notify_expiring_training` | `notify_expiring_training_daily` | oui |
| `notifications.tasks.notify_overdue_occurrences` | `notify_overdue_occurrences_hourly` | oui |
| `notifications.tasks.notify_maintenance_echeance_proche` | `notify_maintenance_echeance_proche_daily` | oui |
| `notifications.tasks.notify_low_stock` | `notify_low_stock_daily` | oui |
| `maintenance.tasks.generate_installation_occurrences` | `generate_installation_occurrences_daily` | domaine seulement (ch. 18), détail ch. 21 |
| `notifications.tasks.generate_installation_notifications` | `generate_installation_notifications_daily` | oui |
| `notifications.tasks.generate_installation_maintenance_notifications` | `generate_installation_maintenance_notifications_daily` | oui |
| `notifications.tasks.detect_installation_drift` | `detect_installation_drift_daily` | oui |
| `annonces.tasks.diffuser_annonces` | `diffuser_annonces_hourly` | oui |
| `annonces.tasks.rappeler_accuses_annonces` | `rappeler_accuses_annonces_daily` | oui |
| `notifications.tasks.notify_taches_en_retard` | `notify_taches_en_retard_daily` | oui |
| `notifications.tasks.notify_ma_journee` | `notify_ma_journee_minute` | oui |
| `notifications.tasks.notify_ma_journee_demain` | `notify_ma_journee_demain_minute` | oui |

## G.4 Commandes de gestion

| Commande | Citée dans un chapitre rédigé |
|---|---|
| `catalogue_reprise` | non (ensemble indiqué en annexe E, ensemble 4) |
| `generate_installation_occurrences` | non (ensemble indiqué en annexe E, ensemble 4) |
| `marquer_instance_demo` | non (ensemble indiqué en annexe E, ensemble 4) |
| `purger_brouillons` | non (ensemble indiqué en annexe E, ensemble 4) |
| `seed_demo` | oui |
| `seed_demo_dense` | non (ensemble indiqué en annexe E, ensemble 4) |
| `seed_demo_mer_quai` | non (ensemble indiqué en annexe E, ensemble 4) |
| `seed_demo_metier` | non (ensemble indiqué en annexe E, ensemble 4) |
| `verifier_instance` | oui |
| `generate_installation_maintenance_notifications` | oui |
| `generate_installation_notifications` | oui |
| `generate_vapid_keys` | oui |
| `importer_referentiel_batiments` | non (ensemble indiqué en annexe E, ensemble 4) |
| `analyser_chevauchements_mer_quai` | non (ensemble indiqué en annexe E, ensemble 4) |
| `analyser_designations_chef_de_liste` | non (ensemble indiqué en annexe E, ensemble 4) |
| `initialiser_mode_batiment` | non (ensemble indiqué en annexe E, ensemble 4) |
| `signaler_divergences_feuilles` | oui |
| `fusionner_formations` | non (ensemble indiqué en annexe E, ensemble 4) |

## G.5 Actions à seuil de rôle

35 actions : toutes figurent dans l'annexe B (générée depuis le registre). Exemples expliqués au chapitre 5.

## G.6 Circuits métier (liste fermée, révisée)

| Circuit | Chapitre | Ensemble | Statut |
|---|---|---|---|
| Relève d'équipage | 4 | E1 | rédigé |
| Archivage d'une unité | 4 | E1 | rédigé |
| Suppression d'une unité | 4 | E1 | rédigé |
| Création d'un compte | 5 | E1 | rédigé |
| Réinitialisation de mot de passe | 5 | E1 | rédigé |
| Suppression d'un compte (réel) et désactivation (cible L04) | 5 | E1 | rédigé |
| Proposer → valider → publier (transversal) | 22 | E1 | rédigé |
| Confirmation explicite des validations critiques | 22 | E1 | rédigé |
| Verrou des commandes de démonstration | 22 | E1 | rédigé |
| Échange de service : fonctionnement actuel | 8 | E2 | rédigé |
| Échange de service : fonctionnement cible (DEC-FDS-07/13) | 8 | E2 | rédigé |
| Activation d'une liste de services à quai | 8 | E2 | rédigé |
| Notifications et Web Push | 9 | E2 | rédigé |
| Difficulté signalée (demande) | 10 | E2 | rédigé |
| Programme du bâtiment | 10 | E2 | rédigé |
| Passation de relève | 6 | E2 | rédigé |
| Bilan et exports | 6 | E2 | rédigé |
| Recherche globale | 9 | E2 | rédigé |
| Absences | 8 | E2 | rédigé |
| Publication d'une liste de quarts ou de gardes | 8 | E2 | rédigé |
| Feuille de service, visas et rectificatif | 8 | E2 | rédigé |
| Annonce et accusé de lecture | 9 | E2 | rédigé |
| Tâche : attribution, blocage, clôture | 10 | E2 | rédigé |
| Ticket correctif et anomalie | 12 | E3 | à rédiger |
| Maintenance : exécution et clôture critique | 12 | E3 | à rédiger |
| Demande de pièce | 13 | E3 | à rédiger |
| Fiche de maintenance flotte (7 étapes) | 11 | E3 | à rédiger |
| Validation de formation par un référent | 14 | E3 | à rédiger |
| RETEX | 15 | E3 | à rédiger |
| Préparation à l'appareillage | 16 | E3 | à rédiger |

## G.7 Dépendances entre paquets

Matrice générée dans `couverture/etat_B/INVENTAIRE.md` ; synthèse expliquée au chapitre 18 (§18.6).
