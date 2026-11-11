# Inventaire mesuré de l'état B (généré)

Généré par `outils/inventaire.py` sur la copie du code `etatB`. Ne pas éditer à la main.

## Synthèse par paquet

| Paquet | Modèles | Relations | Relations génériques | Routes | Migrations | Tests (fonctions) | Services |
|---|---|---|---|---|---|---|---|
| `absences` | 1 | 5 | 0 | 1 | 1 | 21 | services.py |
| `accounts` | 10 | 10 | 0 | 29 | 23 | 159 | services.py |
| `annonces` | 4 | 11 | 0 | 4 | 3 | 46 | services.py |
| `assets` | 29 | 106 | 0 | 90 | 46 | 493 | — |
| `calendar_app` | 1 | 1 | 0 | 9 | 2 | 124 | — |
| `core` | 1 | 1 | 0 | 0 | 0 | 0 | — |
| `dashboard` | 2 | 7 | 1 | 17 | 2 | 261 | — |
| `demandes` | 1 | 10 | 1 | 5 | 2 | 41 | services.py |
| `documentation` | 3 | 11 | 1 | 5 | 2 | 9 | services.py |
| `logistics` | 8 | 36 | 0 | 32 | 15 | 228 | — |
| `maintenance` | 6 | 30 | 0 | 30 | 9 | 178 | — |
| `notifications` | 2 | 3 | 1 | 16 | 5 | 165 | services.py |
| `org` | 15 | 19 | 0 | 20 | 18 | 163 | structure_services.py |
| `postes` | 2 | 10 | 0 | 3 | 2 | 7 | services.py |
| `programme` | 3 | 13 | 0 | 5 | 2 | 10 | services.py |
| `quarts` | 22 | 83 | 0 | 15 | 26 | 609 | services.py |
| `retex` | 2 | 10 | 1 | 5 | 3 | 5 | services.py |
| `rondes` | 4 | 20 | 0 | 0 | 2 | 0 | — |
| `taches` | 5 | 13 | 0 | 5 | 8 | 94 | services.py |
| `threads` | 3 | 9 | 1 | 12 | 3 | 30 | — |
| `training` | 11 | 40 | 0 | 25 | 16 | 310 | services.py |
| **Total** | **135** | **448** | **6** | **721** | **190** | **3002** | |

Paquets sans modèle : reports.

## Tâches planifiées (Celery beat)

| Nom | Tâche | Planification |
|---|---|---|
| `purger_sessions_daily` | `matrix.core.tasks.purger_sessions` | 86400 |
| `appliquer_releves_echues_minute` | `matrix.core.tasks.appliquer_releves_echues` | 60 |
| `signaler_divergences_feuilles_15min` | `quarts.tasks.signaler_divergences_feuilles` | 900 |
| `traiter_echeances_activation_minute` | `quarts.tasks.traiter_echeances_activation` | 60 |
| `purger_brouillons_daily` | `matrix.core.tasks.purger_brouillons` | 86400 |
| `generate_occurrences_daily` | `maintenance.tasks.generate_occurrences` | 86400 |
| `compute_overdue_hourly` | `maintenance.tasks.compute_overdue` | 3600 |
| `notify_expiring_training_daily` | `notifications.tasks.notify_expiring_training` | 86400 |
| `notify_overdue_occurrences_hourly` | `notifications.tasks.notify_overdue_occurrences` | 3600 |
| `notify_maintenance_echeance_proche_daily` | `notifications.tasks.notify_maintenance_echeance_proche` | 86400 |
| `notify_low_stock_daily` | `notifications.tasks.notify_low_stock` | 86400 |
| `generate_installation_occurrences_daily` | `maintenance.tasks.generate_installation_occurrences` | 86400 |
| `generate_installation_notifications_daily` | `notifications.tasks.generate_installation_notifications` | <crontab: * * * * * (m/h/dM/MY/d)> |
| `generate_installation_maintenance_notifications_daily` | `notifications.tasks.generate_installation_maintenance_notifications` | <crontab: * * * * * (m/h/dM/MY/d)> |
| `detect_installation_drift_daily` | `notifications.tasks.detect_installation_drift` | <crontab: 30 8 * * * (m/h/dM/MY/d)> |
| `diffuser_annonces_hourly` | `annonces.tasks.diffuser_annonces` | 3600 |
| `rappeler_accuses_annonces_daily` | `annonces.tasks.rappeler_accuses_annonces` | <crontab: 15 7 * * * (m/h/dM/MY/d)> |
| `notify_taches_en_retard_daily` | `notifications.tasks.notify_taches_en_retard` | <crontab: 0 7 * * * (m/h/dM/MY/d)> |
| `notify_ma_journee_minute` | `notifications.tasks.notify_ma_journee` | <crontab: * * * * * (m/h/dM/MY/d)> |
| `notify_ma_journee_demain_minute` | `notifications.tasks.notify_ma_journee_demain` | <crontab: * * * * * (m/h/dM/MY/d)> |

## Commandes de gestion

- `assets/management/commands/catalogue_reprise.py`
- `maintenance/management/commands/generate_installation_occurrences.py`
- `matrix/core/management/commands/marquer_instance_demo.py`
- `matrix/core/management/commands/purger_brouillons.py`
- `matrix/core/management/commands/seed_demo.py`
- `matrix/core/management/commands/seed_demo_dense.py`
- `matrix/core/management/commands/seed_demo_mer_quai.py`
- `matrix/core/management/commands/seed_demo_metier.py`
- `matrix/core/management/commands/verifier_instance.py`
- `notifications/management/commands/generate_installation_maintenance_notifications.py`
- `notifications/management/commands/generate_installation_notifications.py`
- `notifications/management/commands/generate_vapid_keys.py`
- `org/management/commands/importer_referentiel_batiments.py`
- `quarts/management/commands/analyser_chevauchements_mer_quai.py`
- `quarts/management/commands/analyser_designations_chef_de_liste.py`
- `quarts/management/commands/initialiser_mode_batiment.py`
- `quarts/management/commands/signaler_divergences_feuilles.py`
- `training/management/commands/fusionner_formations.py`

## Actions à seuil de rôle configurable

| Clé | Catégorie | Portée | Seuil par défaut | Second |
|---|---|---|---|---|
| `structure_navire_ecriture` | Organisation de l'unité | SHIP | ADMIN_NAVIRE |  |
| `unite_administration` | Organisation de l'unité | SHIP | ADMIN_NAVIRE |  |
| `asset_ecriture_simple` | Matériel mobile | SHIP | CHEF_SECTION |  |
| `asset_gestion_avancee` | Matériel mobile | SHIP | CHEF_SERVICE |  |
| `installation_ecriture_simple` | Installations | SHIP | CHEF_SECTION |  |
| `installation_gestion_avancee` | Installations | SHIP | CHEF_SERVICE |  |
| `installation_entretien_gestion` | Installations | SHIP | CHEF_SERVICE |  |
| `fiche_bord_redaction` | Installations | SHIP | CHEF_SECTION |  |
| `fiche_flotte_proposition` | Installations | SHIP | CHEF_SECTION |  |
| `rattachement_parent_gestion` | Installations | SHIP | CHEF_SERVICE |  |
| `plan_navire_configuration` | Installations | SHIP | CHEF_SERVICE |  |
| `stock_ecriture` | Stock | SHIP | CHEF_SECTION |  |
| `maintenance_execution_ecriture` | Maintenance | SHIP | EQUIPIER |  |
| `maintenance_occurrence_gestion_tiers` | Maintenance | SHIP | CHEF_SECTION |  |
| `maintenance_compte_rendu_correction` | Maintenance | SHIP | CHEF_SECTEUR |  |
| `maintenance_plan_ecriture` | Maintenance | SHIP | CHEF_SECTION |  |
| `supervision_aujourdhui` | Tableau de bord | SHIP | CHEF_SECTEUR |  |
| `thread_ecriture` | Discussions | SHIP | CHEF_SECTION |  |
| `liste_service_publication` | Quarts / Services de garde | SHIP | CHEF_SERVICE |  |
| `feuille_service_configuration` | Feuille de service | SHIP | CHEF_SERVICE |  |
| `feuille_service_visa_secteur` | Feuille de service | SHIP | CHEF_SECTEUR |  |
| `feuille_service_visa_service` | Feuille de service | SHIP | CHEF_SERVICE |  |
| `alerte_organisation_validation` | Feuille de service | SHIP | COMMANDANT |  |
| `module_gestion` | Modules | SHIP | COMMANDANT_EN_SECOND |  |
| `mot_de_passe_reinitialisation` | Comptes | SHIP | ADMIN_NAVIRE |  |
| `tache_attribution` | Tâches | GLOBALE | CHEF_SECTION |  |
| `annonce_publication` | Annonces | SHIP | CHEF_SERVICE | oui |
| `programme_saisie` | Programme du bâtiment | SHIP | ETAT_MAJOR |  |
| `programme_types` | Programme du bâtiment | SHIP | ADMIN_NAVIRE |  |
| `poste_gestion` | Postes du bord | SHIP | CHEF_SERVICE |  |
| `documentation_redaction` | Documentation | SHIP | CHEF_SECTION |  |
| `documentation_validation` | Documentation | SHIP | CHEF_SERVICE |  |
| `retex_validation` | RETEX | SHIP | CHEF_SERVICE |  |
| `referentiel_global_ecriture` | Référentiels globaux | GLOBALE | MASTER_ADMIN |  |
| `responsabilite_transverse_gestion` | Référentiels globaux | GLOBALE | MASTER_ADMIN |  |

## Dépendances entre paquets (nombre d'imports, hors tests)

| De → vers | Imports |
|---|---|
| `absences` → `accounts` (3), `notifications` (1) | |
| `accounts` → `org` (4), `quarts` (1), `training` (2) | |
| `annonces` → `accounts` (1), `notifications` (4), `org` (3), `taches` (1) | |
| `assets` → `accounts` (17), `logistics` (6), `maintenance` (7), `notifications` (2), `org` (11), `reports` (2), `threads` (3), `training` (2) | |
| `calendar_app` → `absences` (3), `accounts` (1), `logistics` (4), `maintenance` (5), `programme` (3), `quarts` (5), `taches` (7), `threads` (1), `training` (6) | |
| `dashboard` → `accounts` (4), `annonces` (4), `assets` (10), `demandes` (4), `logistics` (13), `maintenance` (12), `notifications` (5), `org` (5), `quarts` (5), `reports` (1), `taches` (4), `threads` (1), `training` (8) | |
| `demandes` → `accounts` (1), `notifications` (5), `org` (1), `taches` (3), `threads` (3) | |
| `documentation` → `accounts` (1), `annonces` (2), `demandes` (1), `notifications` (3), `org` (1) | |
| `logistics` → `accounts` (5), `assets` (3), `notifications` (3), `org` (5), `threads` (4) | |
| `maintenance` → `accounts` (6), `assets` (21), `logistics` (4), `notifications` (3), `threads` (4) | |
| `notifications` → `absences` (1), `accounts` (1), `annonces` (1), `assets` (10), `calendar_app` (1), `dashboard` (1), `demandes` (1), `documentation` (1), `logistics` (4), `maintenance` (3), `programme` (1), `quarts` (3), `retex` (2), `taches` (2), `training` (3) | |
| `org` → `accounts` (4), `assets` (1) | |
| `postes` → `accounts` (1), `annonces` (2), `org` (1), `training` (3) | |
| `programme` → `accounts` (1), `annonces` (2), `notifications` (2), `org` (1), `taches` (3) | |
| `quarts` → `absences` (1), `accounts` (14), `notifications` (9), `org` (10), `training` (2) | |
| `reports` → `assets` (1), `logistics` (2), `maintenance` (1), `org` (1), `training` (1) | |
| `retex` → `accounts` (1), `annonces` (2), `demandes` (2), `documentation` (1), `notifications` (4), `org` (1), `taches` (2) | |
| `rondes` → `accounts` (1), `assets` (1), `logistics` (1), `org` (1) | |
| `taches` → `absences` (2), `accounts` (1), `annonces` (2), `demandes` (1), `notifications` (3), `threads` (3) | |
| `threads` → `accounts` (1), `logistics` (2), `maintenance` (2), `notifications` (3) | |
| `training` → `accounts` (1), `notifications` (3), `org` (5), `threads` (1) | |

## Signaux (`@receiver`)

- `training/models.py:308 @receiver(m2m_changed, sender=TrainingCourse.prerequisites.through)`
- `training/models.py:489 @receiver(m2m_changed, sender=TrainingSession.reservations.through)`
- `training/models.py:536 @receiver(m2m_changed, sender=TrainingSession.attendees.through)`
- `org/models.py:354 @receiver(pre_save, sender=RoleThresholdConfig)`
- `org/models.py:355 @receiver(pre_save, sender=ModuleActivation)`
- `org/models.py:365 @receiver(post_save, sender=RoleThresholdConfig)`
- `org/models.py:366 @receiver(post_delete, sender=RoleThresholdConfig)`
- `org/models.py:367 @receiver(post_save, sender=ModuleActivation)`
- `org/models.py:368 @receiver(post_delete, sender=ModuleActivation)`
- `notifications/signals.py:9 @receiver(post_save, sender=Notification)`
- `maintenance/models.py:212 @receiver(post_save, sender=MaintenanceExecution)`
- `threads/mentions.py:25 @receiver(post_save, sender=Message)`
- `accounts/signals.py:9 @receiver(user_logged_in)`
- `accounts/signals.py:14 @receiver(user_logged_out)`
- `accounts/models.py:226 @receiver(post_save, sender=User)`

## Relations génériques

- `demandes.Demande` : objet
- `documentation.LienDocument` : objet
- `retex.Retex` : source
- `threads.Thread` : content_object
- `notifications.Notification` : target
- `dashboard.ItemAppareillage` : objet_source
