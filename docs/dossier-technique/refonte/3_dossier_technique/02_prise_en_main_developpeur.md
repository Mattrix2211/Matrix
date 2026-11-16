<!-- partie: Prise en main -->
# Prise en main développeur

<div class="ligne-public"><b>Public :</b> développeurs, mainteneurs · <b>Accès restreint</b> · <b>Ce que vous y trouverez :</b> installer, lancer, tester, puis ajouter une action de seuil, un module activable et une tâche planifiée · <b>Preuve :</b> chaque pas a été exécuté le 16/11/2026 dans une copie isolée de l'état B ; le journal est archivé dans <code>audit_preuves/prise_en_main_developpeur_journal.txt</code></div>

## Principe

Tous les pas ci-dessous ont été **exécutés** sur une copie isolée de l'état B (extraite par `git archive`), avec une base SQLite jetable. Le journal brut des commandes et de leurs sorties est dans `audit_preuves/prise_en_main_developpeur_journal.txt`. Ce qui n'a pas pu être rejoué est dit en fin de section (⚪). Environnement du rejeu : Python 3.13 sous Linux ; le projet suppose Python 3.12 ou plus (écart A22 : le script d'installation annonce 3.8). Les commandes d'activation d'un environnement virtuel diffèrent sous Windows (`venv\Scripts\activate`) : non rejoué ⚪.

## Installer et lancer

| Pas | Commande | Résultat constaté |
|---|---|---|
| 1. Dépendances | `pip install -r requirements.txt` | Rejouée en simulation (`--dry-run`) : les dépendances sont satisfaites, à une exception près : `pywebpush` est installé en 2.5.0 alors que `requirements.txt` demande 2.4.0 |
| 2. Réglages locaux | Variables `DJANGO_DEBUG=1`, `DJANGO_SECRET_KEY`, `MATRIX_SQLITE_PATH` (ou fichier `.env` créé depuis `.env.example`) | Sans `DJANGO_DEBUG`, l'application démarre en mode production et exige `DJANGO_SECRET_KEY` (écart sans suite : garde-fou voulu) |
| 3. Contrôle de configuration | `python manage.py check` | « 1 issue » : avertissement `matrix.W002` (DEBUG actif hors serveur de développement), attendu en local |
| 4. Base de données | `python manage.py migrate` | Les {{fait:n_migrations}} migrations s'appliquent sur une base vide |
| 5. Compte administrateur | `python manage.py createsuperuser --noinput --username … --email …` avec `DJANGO_SUPERUSER_PASSWORD` | « Superuser created successfully » ; ne jamais réutiliser un mot de passe réel |
| 6. Serveur | `python manage.py runserver 127.0.0.1:8811` | La page `/accounts/login/` répond **200** |

Sans worker ni planificateur, **aucune tâche planifiée ne s'exécute** : pour les rejouer, lancer `celery -A matrix worker -l info --pool=solo` (sous Windows) et `celery -A matrix beat -l info` avec Redis (non rejoué ⚪ : voir la recette de déploiement, [[DT:23_configuration_deploiement_exploitation]]).

## Tester

| Commande | Résultat constaté |
|---|---|
| `python manage.py test retex postes` | 12 tests, OK (10,9 s) |
| `python manage.py test matrix.tests.test_coherence_configuration` | 24 tests, OK (43,8 s) |
| `python manage.py test matrix.tests.test_modules_activables` | 16 tests, OK (5,9 s) |

Règle du projet : pendant le travail, ne lancer que les tests de l'application touchée ; la suite complète (`python manage.py test --parallel`) une seule fois en fin de chantier. La suite complète n'a **pas** été rejouée pour ce dossier ⚪ (3 963 tests rapportés par les comptes rendus de lots, non rejoués).

## Ajouter une action de seuil

Un seuil est une entrée du registre central `REGISTRE_ACTIONS` (`matrix/core/role_thresholds.py`) : clé, libellé, catégorie, portée et niveau par défaut. Les seuils sont ensuite réglables par bâtiment.

1. Ajouter une entrée `ActionSeuil(clé, libellé, catégorie, PORTEE_NAVIRE, RoleLevel.…)` au registre.
2. Lire la valeur : `seuil_role("<clé>")` renvoie le niveau par défaut (constaté : `2` pour le niveau chef de section).
3. Contrôler la cohérence : le registre passe de 35 à 36 actions ; la suite `matrix.tests.test_coherence_configuration` reste verte.
4. Protéger l'écriture côté serveur avec `niveau_requis_pour(user, clé)` : le menu masque, c'est le serveur qui décide.

## Ajouter un module activable

Un module activable est une entrée de `REGISTRE_MODULES` (`matrix/core/modules.py`) : clé (nom de l'application Django), libellé, description. Constaté : une entrée ajoutée fait passer le registre de 14 à 15 modules, `python manage.py check` reste inchangé et la suite `matrix.tests.test_modules_activables` passe (16 tests). Rattacher ensuite les entrées de menu et de recherche à la clé du module (`module=` dans `matrix/core/navigation.py` et `matrix/core/recherche.py`) ; **cette dernière étape n'a pas été rejouée** ⚪.

## Ajouter une tâche planifiée

1. Écrire la tâche avec `@shared_task` dans le fichier `tasks.py` de l'application (exemple : `matrix/core/tasks.py`).
2. La déclarer dans `CELERY_BEAT_SCHEDULE` (`matrix/settings.py`) avec son chemin et sa fréquence en secondes.
3. Contrôle constaté : la tâche d'exemple s'exécute en direct (`apply()`) et renvoie `ok` ; le planificateur compte 21 entrées au lieu de 20.
4. Le déclenchement réel par le planificateur n'a **pas** été rejoué (Redis et Celery absents de la copie) ⚪.

## Ce qui n'a pas été rejoué ⚪

- Installation réelle des dépendances (simulation seulement) et environnement virtuel Windows.
- Démarrage de Celery, du planificateur et de Redis.
- Suite complète de tests ; PostgreSQL.
