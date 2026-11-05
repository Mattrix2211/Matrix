# Audit 13 — Architecture et dette technique

**Statut : partiel.** Mesures objectives (taille, complexité, imports inutilisés, couplage par recherche textuelle) ; pas de revue de conception module par module.

## Mesures

| Indicateur | Valeur | Commande |
|---|---|---|
| Code applicatif (hors tests, migrations, docs) | ≈ 48 100 lignes Python | `find … \| xargs wc -l` |
| Code de test | ≈ 53 700 lignes (ratio tests/applicatif ≈ 1,1) | idem |
| Paquets applicatifs | 22 (dont `rondes` résiduel) ; `docs/REFERENCE.md` §4 en annonce 14 (AUD-005) | `ls` |
| Plus gros fichiers | `quarts/models.py` 2 381 l., `training/web_views.py` 2 103, `quarts/listes_views.py` 1 134, `dashboard/web_views.py` 1 064, `matrix/views.py` 1 016 | `wc -l` |
| Fonctions de complexité cyclomatique > 25 | **8**, dont `matrix/views.py: post` (101), `assets/asset_views.py: post` (70), `accounts/web_views.py: post` (66), `training/web_views.py: post` (44), `quarts/feuille_service_views.py: _traiter` (38) | `ruff --select C901` |
| Imports/variables inutilisés | 86 corrigeables automatiquement | `ruff --select F401,F841` |
| Appels de périmètre (`scope_filters_for_user`, `build_scope_q`, `perimetre_*_q`) | 260 appels dans 48 fichiers | `grep` |
| Droits en dur | 55 comparaisons de niveau (P05) | `grep` |
| Dépendances externes déclarées | 19 dont `boto3`, `django-storages` apparemment inutilisés | `requirements.txt` |
| Serveur d'application de production | aucun déclaré | `requirements.txt` |

## Constats

- Les « vues géantes à `post` unique » (un `if action == …` de 40 à 100 branches) concentrent la logique de droits et d'écriture de plusieurs modules : difficiles à relire, risque de régression élevé, et site probable des défauts d'organisation (AUD-019 à AUD-021 sont dans `matrix/views.py`).
- Dette d'hygiène : 86 imports ou variables inutiles contraires à la règle « pas de code mort » de `CLAUDE.md`.
- Bonne séparation par applications Django ; le couplage par les helpers de périmètre est assumé mais massif (260 appels).
- Couche asynchrone : Celery + Redis ; panne silencieuse documentée (README) ; non supervisée (AUD-017 d'exploitation).

## Recommandations (non lancées)

Découper les `post` en vues ou services par action, en priorité `matrix/views.py` ; supprimer les imports inutiles ; retirer `boto3` et `django-storages` si inutilisés ; choisir et déclarer un serveur d'application ; documenter le périmètre comme dépendance centrale.

## Non vérifié

Performances avec un volume réel, requêtes N+1 systématiques, cycles d'import, duplication de code entre applications (aucun outil de duplication lancé), évolutivité multi-bâtiments (décision d'architecture de déploiement ouverte dans Notion).
