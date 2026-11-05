# Audit 17 — Déploiement et exploitation (rapport partiel)

**Statut : partiel, non terminé.** Lecture de la configuration et de la documentation ; aucun déploiement.

## 1. Constats

- Installation documentée pour le développement (Windows en priorité) ; **aucune procédure de production** : serveur web, HTTPS, supervision des processus, journaux (AUD-011).
- **Sauvegarde et restauration** : aucune procédure trouvée dans `README.md` ni `docs/` (recherche textuelle non exhaustive) ; `django-storages` et `boto3` figurent dans `requirements.txt` et `storages` dans `INSTALLED_APPS` (`matrix/settings.py:71`), mais aucune configuration de stockage distant n'a été trouvée : dépendances probablement inutilisées, à confirmer (principe « aucun service cloud obligatoire »).
- **Mises à jour** : le hook local bloque un commit si les migrations ne sont pas appliquées à `db.sqlite3` ; aucune procédure de mise à jour d'un bord n'est écrite.
- **Intégration continue** : absente (AUD-002).
- `docker-compose.yml` ne fournit que PostgreSQL et Redis ; les ports sont limités à `127.0.0.1` (README).
- Compatibilité PostgreSQL : non vérifiée ici (aucune instance disponible) ; 20 tests sont ignorés sous SQLite.

## 2. Non audité

Fichiers `*.bat`, supervision, rotation des journaux, reprise après redémarrage de Celery/Redis, procédure de retour arrière après une migration.
