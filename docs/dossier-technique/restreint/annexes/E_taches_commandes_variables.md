# Annexe E — Tâches planifiées, commandes de gestion et variables (généré, état B)

> Diffusion restreinte. Généré par `outils/generer_annexes_e4.py` depuis l'inventaire de l'état B (`6d6d0be`, non fusionné dans `main`). Ne pas éditer à la main.

## E.1 Tâches planifiées (Celery beat)

20 tâches. **Sans worker ni beat, aucune n'est exécutée** (chapitres 21 et 23).

| Nom | Tâche | Rythme | Rôle (première ligne de la documentation du code) |
|---|---|---|---|
| `purger_sessions_daily` | `matrix.core.tasks.purger_sessions` | chaque jour | Supprime chaque jour les sessions expirées conservées en base. |
| `appliquer_releves_echues_minute` | `matrix.core.tasks.appliquer_releves_echues` | chaque minute | Applique chaque minute les relèves planifiées dont la date d'effet est atteinte (rattrapage compris). |
| `signaler_divergences_feuilles_15min` | `quarts.tasks.signaler_divergences_feuilles` | tous les quarts d'heure | Reprise périodique : signale les divergences que le signalement immédiat a manquées (erreur, saisie directe). |
| `traiter_echeances_activation_minute` | `quarts.tasks.traiter_echeances_activation` | chaque minute | Crée chaque minute les rappels et alertes d'activation échus (les lectures de liste le font aussi). |
| `purger_brouillons_daily` | `matrix.core.tasks.purger_brouillons` | chaque jour | Purge quotidienne des brouillons plus anciens que BROUILLONS_CONSERVATION_JOURS. |
| `generate_occurrences_daily` | `maintenance.tasks.generate_occurrences` | chaque jour | — |
| `compute_overdue_hourly` | `maintenance.tasks.compute_overdue` | chaque heure | — |
| `notify_expiring_training_daily` | `notifications.tasks.notify_expiring_training` | chaque jour | — |
| `notify_overdue_occurrences_hourly` | `notifications.tasks.notify_overdue_occurrences` | chaque heure | — |
| `notify_maintenance_echeance_proche_daily` | `notifications.tasks.notify_maintenance_echeance_proche` | chaque jour | Rappelle aux marins assignés qu'une occurrence de maintenance arrive à |
| `notify_low_stock_daily` | `notifications.tasks.notify_low_stock` | chaque jour | Alerte les chefs concernés dès qu'une pièce de stock passe sous son seuil minimal. |
| `generate_installation_occurrences_daily` | `maintenance.tasks.generate_installation_occurrences` | chaque jour | Génère les occurrences de maintenance (calendrier et/ou compteur) pour les |
| `generate_installation_notifications_daily` | `notifications.tasks.generate_installation_notifications` | chaque minute (la tâche filtre selon l'heure de chaque marin) | Alerte les marins des échéances de vibration/isolement des installations fixes. |
| `generate_installation_maintenance_notifications_daily` | `notifications.tasks.generate_installation_maintenance_notifications` | chaque minute (la tâche filtre selon l'heure de chaque marin) | Alerte les marins des échéances d'entretien (calendaire/compteur) des |
| `detect_installation_drift_daily` | `notifications.tasks.detect_installation_drift` | chaque jour à 08:30 | Détecte une dérive sur les relevés techniques des installations fixes |
| `diffuser_annonces_hourly` | `annonces.tasks.diffuser_annonces` | chaque heure | Diffuse les annonces programmées dont la date d'effet est arrivée. |
| `rappeler_accuses_annonces_daily` | `annonces.tasks.rappeler_accuses_annonces` | chaque jour à 07:15 | Relance une fois les destinataires qui n'ont pas accusé réception après le délai réglé. |
| `notify_taches_en_retard_daily` | `notifications.tasks.notify_taches_en_retard` | chaque jour à 07:00 | Relance quotidienne des tâches attribuées dont l'échéance est dépassée (logique dans taches/services.py). |
| `notify_ma_journee_minute` | `notifications.tasks.notify_ma_journee` | chaque minute (la tâche filtre selon l'heure de chaque marin) | « Ma journée » : chaque matin, résume au marin ce qui figure à son |
| `notify_ma_journee_demain_minute` | `notifications.tasks.notify_ma_journee_demain` | chaque minute (la tâche filtre selon l'heure de chaque marin) | « Ma journée de demain » : en fin de journée, anticipe ce qui figure au |

## E.2 Commandes de gestion

18 commandes (`python manage.py <nom>`).

| Commande | Paquet | Rôle (texte d'aide du code) |
|---|---|---|
| `catalogue_reprise` | `assets` | Propose (par défaut, --dry-run) ou applique (--appliquer) la reprise des dossiers de matériel en catégories du catalogue. Rien n'est supprimé. |
| `generate_installation_occurrences` | `maintenance` | Génère les occurrences de maintenance (calendrier et/ou compteur) pour les installations fixes, sur une fenêtre de 90 jours, comme generate_occurrences pour le matériel mobile (à lancer chaque jour). |
| `marquer_instance_demo` | `matrix` | Marque la base courante comme base de démonstration si elle a été préparée comme telle et ne contient que des comptes fictifs. |
| `purger_brouillons` | `matrix` | Supprime les brouillons non modifiés depuis la durée de conservation (BROUILLONS_CONSERVATION_JOURS). |
| `seed_demo` | `matrix` | Crée (ou complète) les données de démonstration de Matrix **Démonstration : refuse de s'exécuter hors d'une base de démonstration.** |
| `seed_demo_dense` | `matrix` | Enrichit la base de démonstration (volumes, liens, échanges) ; refuse toute autre base. **Démonstration : refuse de s'exécuter hors d'une base de démonstration.** |
| `seed_demo_mer_quai` | `matrix` | Ajoute les listes prévisionnelles, l'alerte en retard et la désignation historique de la démonstration mer/quai. **Démonstration : refuse de s'exécuter hors d'une base de démonstration.** |
| `seed_demo_metier` | `matrix` | Ajoute la démonstration métier approfondie (calendrier, quarts, maintenance, anomalies, logistique, notifications). **Démonstration : refuse de s'exécuter hors d'une base de démonstration.** |
| `verifier_instance` | `matrix` | Signale (sans rien modifier) une base de démonstration ou des comptes à mot de passe prévisible. |
| `generate_installation_maintenance_notifications` | `notifications` | Génère des notifications d’échéances d’entretien (calendaire et/ou compteur) pour les maintenances d’installations (à lancer chaque jour à 08:00). |
| `generate_installation_notifications` | `notifications` | Génère des notifications d’échéances vibration/isolement pour les installations (à lancer chaque jour à 08:00). |
| `generate_vapid_keys` | `notifications` | Génère une paire de clés VAPID pour les notifications Web Push. À exécuter UNE SEULE FOIS : copiez le résultat dans les variables d'environnement VAPID_PUBLIC_KEY / VAPID_PRIVATE_KEY (jamais de génération à la volée à chaque démarrage, sinon les abonnements existants deviennent invalides). |
| `importer_referentiel_batiments` | `org` | Importe le référentiel des bâtiments de la Marine nationale (idempotent, rien n'est supprimé). |
| `analyser_chevauchements_mer_quai` | `quarts` | Diagnostic en lecture seule : chevauchements entre services à quai et quarts à la mer publiés. Ne modifie rien. |
| `analyser_designations_chef_de_liste` | `quarts` | Inventaire en lecture seule des désignations de chef de liste historiques (sans type) : elles ne donnent AUCUN droit tant qu'un responsable ne les a pas qualifiées explicitement dans « Chefs de liste ». |
| `initialiser_mode_batiment` | `quarts` | Initialise explicitement le mode (MER ou QUAI) d'un bâtiment dont la situation n'est pas renseignée. Tracé, jamais déduit d'une liste. |
| `signaler_divergences_feuilles` | `quarts` | Notifie les responsables des feuilles publiées dont les affectations effectives ont changé (une fois par divergence). |
| `fusionner_formations` | `training` | Fusionne les formations dupliquées entre navires (même titre, même catégorie, même durée de validité) et convertit leur rattachement navire/référents en TrainingRequirement/ReferentFormation, avant la migration finale qui retire TrainingCourse.sector/referents. Toujours lancer avec --dry-run d'abord. |

## E.3 Variables d'environnement lues par `matrix/settings.py`

31 variables. Signification et valeurs recommandées : chapitre 23 (§23.3).

| Variable | Valeur par défaut dans le code |
|---|---|
| `BROUILLONS_CONSERVATION_JOURS` | `"30"` |
| `BROUILLONS_TAILLE_MAX` | `str(256 * 1024)` |
| `CELERY_BROKER_URL` | `"redis://localhost:6379/0"` |
| `CELERY_RESULT_BACKEND` | `"redis://localhost:6379/1"` |
| `DB_HOST` | — |
| `DB_NAME` | `"matrix"` |
| `DB_PASSWORD` | `""` |
| `DB_PORT` | `"5432"` |
| `DB_USER` | `"matrix"` |
| `DEFAULT_FROM_EMAIL` | `"no-reply@localhost"` |
| `DJANGO_ALLOWED_HOSTS` | `"localhost,127.0.0.1"` |
| `DJANGO_DEBUG` | `"0"` |
| `DJANGO_SECRET_KEY` | — |
| `DOCUMENT_TAILLE_MAX_MO` | `"20"` |
| `EMAIL_BACKEND` | `"django.core.mail.backends.console.EmailBackend"` |
| `EMAIL_HOST` | `""` |
| `EMAIL_HOST_PASSWORD` | `""` |
| `EMAIL_HOST_USER` | `""` |
| `EMAIL_PORT` | `"587"` |
| `EMAIL_USE_SSL` | `"0"` |
| `EMAIL_USE_TLS` | `"1"` |
| `INACTIVITE_AVERTISSEMENT_SECONDES` | `"60"` |
| `INACTIVITE_DELAI_SECONDES` | `"900"` |
| `MATRIX_ENV_FILE` | — |
| `MATRIX_MEDIA_ROOT` | — |
| `MATRIX_SQLITE_PATH` | — |
| `MEDIA_ACCEL_REDIRECT` | `""` |
| `VAPID_ADMIN_EMAIL` | `"no-reply@localhost"` |
| `VAPID_PRIVATE_KEY` | `""` |
| `VAPID_PUBLIC_KEY` | `""` |
| `WEBPUSH_DELAI_MAX` | `"3"` |
