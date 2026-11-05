# Audit 03 — Première mise en service d'un bâtiment (rapport partiel)

**Statut : partiel, non terminé.** Simulation limitée à l'installation technique sur SQLite ; la création d'un bâtiment par l'interface n'a pas été parcourue.

## 1. Ce qui a été mesuré

| Étape | Constat | Preuve |
|---|---|---|
| Dépendances | `pip install -r requirements.txt` réussit sur Python 3.13 (Django 5.2.17). | Exécution du 2026-11-05 |
| Base vierge | `migrate` : environ 35 s, sans erreur, sur SQLite. | Exécution |
| Données de démonstration | `seed_demo` : environ 11 s ; 5 bâtiments dont un à double équipage. | Exécution |
| Sous-module `design` | Non initialisé dans l'environnement d'audit : charte non relue. | `git submodule status` |

## 2. Étapes que le README impose à l'exploitant

Python et venv, `pip`, sous-module `design`, `.env`, `migrate`, `createsuperuser`, puis — pour les alertes automatiques — Redis, un worker Celery et Celery Beat (sans eux, aucune notification automatique, sans message d'erreur visible). Il n'existe pas de procédure de mise en service d'un bâtiment (ordre : unité, services, secteurs, sections, rôles, utilisateurs, installations) dans le README.

## 2 bis. Autonomie de configuration constatée (2ᵉ passe)

Une fois l'application installée, **seul le compte technique de la flotte** (superutilisateur) peut créer les bâtiments, services, secteurs et sections, ni renommer (AUD-019). L'administrateur d'unité règle les modules et les seuils de rôle de son bâtiment. Création de l'effectif : un compte à la fois (annuaire, formulaire), puis mise à jour groupée (rôle, bâtiment, service, secteur, section, fonction) sur les comptes existants ; pas d'import de personnel (AUD-012). Mesures sur la démonstration : `migrate` 30 à 35 s, `seed_demo` 10 s (SQLite et PostgreSQL 16).

## 2 ter. Import de personnel : fonctionnalité de mise en service à planifier (DP-11)

Besoin confirmé par le PO : import en masse **avec prévisualisation, détection des doublons, validation des rattachements et rapport d'import**. Classement : fonctionnalité de mise en service, **pas une anomalie bloquante de V1.1**. Exigences à reprendre : mêmes validations de rattachement que P01 (V1 à V12), aucune création de rôle supérieur sans validation, mots de passe initiaux à usage unique, rapport conservé, annulation de l'import. Le modèle existant d'import de matériel (`assets/import_materiel.py`, avec fichier modèle) montre la forme du parcours.

## 3. Constats

- **AUD-011 (P1)** : le mode production exige HTTPS sans documentation.
- **AUD-012 (P2)** : pas d'import en masse des marins trouvé.
- **AUD-009 (P1)** : risque de lancer `seed_demo` sur une vraie instance.
- Dépendance aux processus de fond (Celery, Redis) : une panne est silencieuse (README) ; non testée ici.

## 4. Non audité

Parcours complet « nouveau bâtiment » dans l'interface (création d'unité, organigramme, installations, rôles), sections facultatives (DP-03), formation des utilisateurs, PostgreSQL, Windows (`setup.bat`, `start.bat` non exécutés).
