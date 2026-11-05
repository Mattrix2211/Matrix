# Audit 15 — Sécurité et résilience (rapport partiel)

**Statut : partiel, non terminé.** Aucun test intrusif ; vérifications de configuration et de comportement sur base temporaire.

## 1. Constats vérifiés

| Point | Résultat | Preuve |
|---|---|---|
| Fonctionnement sans Internet (Principe n°4) | **Conforme** pour le code statique : les seules URL `http(s)` des gabarits, scripts et feuilles de style sont des commentaires de licence des bibliothèques auto-hébergées. | Recherche `https?://` dans `matrix/templates`, `*/templates`, `matrix/static` ; `matrix/static/vendor/` |
| Contrôles Django | `check` : 1 avertissement (`matrix.W002`, normal en développement) ; `makemigrations --check` : aucun changement en attente. | Exécution du 2026-11-05 |
| `check --deploy` en production simulée | Un seul avertissement : HSTS non configuré. | Exécution avec `DJANGO_DEBUG=0` |
| Clé secrète | Démarrage refusé en production avec la clé de développement. | `matrix/settings.py:53-56` |
| Pages protégées | 227 routes sans paramètre : seules les pages de connexion et le service worker sont ouvertes à un anonyme. | Sonde du 2026-11-05 |
| Déconnexion sur poste partagé | Décrite (15 min) ; **non rejouée**. | `docs/REFERENCE.md` §5 |

## 2. Constats non conformes ou à risque

- **AUD-009 (P1)** : commandes `seed_demo*` sans garde-fou, mots de passe connus.
- **AUD-011 (P1)** : production = HTTPS imposé, sans réglage ni documentation pour un réseau de bord en HTTP.
- **AUD-010 (P2)** : mot de passe PostgreSQL par défaut `matrix`.
- `CSRF_TRUSTED_ORIGINS` est fixé en dur sur `localhost:8000` (`matrix/settings.py:399-404`) : un déploiement derrière un nom de domaine ou un proxy pourrait devoir le modifier ; **non vérifié** en conditions réelles.

## 3. Non audité

Politique de mots de passe (validateurs listés, non évalués), verrouillage après échecs, journalisation (`AuditLog` : couverture non mesurée), sauvegarde et restauration (aucune procédure trouvée dans le README ni dans `docs/` : à confirmer), téléversement de fichiers, injection et XSS (non testés), PostgreSQL.
