# Audit 17 — Déploiement et exploitation (rapport partiel, 2ᵉ passe)

**Statut : Clôturé avec réserves** (voir « Clôture » en bas du rapport). Aucun déploiement ; exécutions sur bases temporaires.

## 1. Constats exécutés

| Sujet | Résultat |
|---|---|
| Installation sur Python 3.13 / Ubuntu 24.04 | `pip install -r requirements.txt` réussit (Django 5.2.17) |
| Base vierge SQLite | `migrate` ≈ 35 s, `seed_demo` ≈ 11 s |
| **Base vierge PostgreSQL 16** (cluster jetable local) | `migrate` ≈ 30 s sans erreur ; `seed_demo` ≈ 10 s ; 42 comptes comme sous SQLite |
| Suite de tests sous PostgreSQL | voir `08_LIMITES_ET_PREUVES.md` §3 ter |
| Production derrière un reverse proxy TLS | **ne fonctionne pas tel que livré** (`AUDIT_15.md` §4) |
| Serveur d'application | aucun dans `requirements.txt` (ni gunicorn, ni waitress, ni uvicorn) : seul `runserver` est présenté |
| Sauvegarde / restauration | aucune procédure écrite dans `README.md`, `docs/` |
| Supervision | aucune (journaux de Celery redirigés vers `celery.log` par `start.bat`, selon le README) ; une panne de Celery ou de Redis est **silencieuse** (README) |
| `storages` dans `INSTALLED_APPS` | `boto3` et `django-storages` installés ; **aucune configuration de stockage distant trouvée** : probable dépendance inutile (principe « aucun service cloud obligatoire ») |
| Intégration continue | absente (AUD-002) |

## 2. Fonctionnalité manquante (pas un bug)

Procédure de mise en service d'un bâtiment (ordre : unité, services, secteurs, sections, rôles, comptes, installations) et import en masse du personnel : voir AUD-012, `AUDIT_03.md`.

## 3. Non audité

Fichiers `*.bat` sous Windows, rotation des journaux, reprise après redémarrage de Celery/Redis, retour arrière après migration, mise à jour d'un bord sans accès Internet (transfert des dépendances).

## Clôture (4ᵉ passe)

**Statut : Clôturé avec réserves.** « Avec réserves » signifie que l'analyse technique est achevée sur le périmètre décrit ; **les éléments listés ci-dessous restent non vérifiés et ne doivent pas être lus comme conformes**.

### Contrôles ajoutés à la 4ᵉ passe

Sondes **reproductibles** : `sondes/rejouer_tout.sh` recrée une base de démonstration et rejoue les sondes avec contrôle des résultats attendus (voir `sondes/README.md`). Montée de version vérifiée.

### Non vérifié ou dépendant d'une validation externe

Vrai proxy TLS et serveur d'application, Windows, supervision, reprise après redémarrage, sauvegarde.
