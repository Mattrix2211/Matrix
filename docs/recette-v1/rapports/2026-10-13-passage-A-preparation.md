# Passage A : préparation et contrôles techniques exécutés

- **SHA testé** : `59dd2f2bfca412ae97f5f006406fecfc7b0fd359` (fusion de la PR #8 du 2026-10-13, `main` = branche de recette au départ).
- **Environnement** : Python 3.13, Django 5.2.17 (`requirements.txt`), Linux, Chromium présent mais **aucun serveur MCP navigateur**.
- **Bases** : SQLite jetable ; PostgreSQL 16 jetable (instance locale créée pour la recette, supprimée ensuite).
- **Qui a exécuté** : le coordinateur lui-même. Les agents `qa-securite`, `qa-integration`, `qa-ergonomie` ont été créés mais **non lancés** (ils ne sont chargés qu'au prochain démarrage de session).
- Aucun fichier de code de Matrix modifié. Aucune fusion, aucun déploiement, aucune écriture dans le backlog Notion.

## 1. Déclaré dans la PR #8 contre exécuté ici

| Contrôle | Déclaré (PR #8) | Exécuté ici | Statut |
|---|---|---|---|
| Suite complète, 2 833 tests | « tous verts au dernier passage » | `python manage.py test --parallel` sur SQLite : **2 833 tests, OK** | **Réussi** (SQLite) |
| `makemigrations --check` propre | oui | `--check --dry-run` : « No changes detected » | **Réussi** |
| `manage.py check` | non mentionné | 1 avertissement (`W002`, DEBUG activé volontairement pour la recette) | Réussi |
| Migrations sur PostgreSQL | **« non éprouvées »** | Migration complète depuis zéro, `seed_demo` puis relance sans doublon, `migrate logistics 0012` (retour arrière de 0013/0014 avec données) puis ré-application : tous OK | **Réussi** |
| Tests sur PostgreSQL | non déclarés | 8 applications (taches, logistics, org, annonces, demandes, notifications, threads, maintenance), 711 tests : **1 échec + 21 erreurs** | **Échoué** (voir §3) |
| Test intermittent `notify_overdue_occurrences` | déclaré intermittent | Passé dans la suite SQLite ; non relancé 3 fois | Non testé (intermittence) |
| Contrôles visuels 1366×768, tablette, mobile, impression | `docs/RECETTE.md` | Aucun rejoué | **Non testé** |
| `seed_demo` relançable | `docs/DEMO.md` | Deux relances consécutives sans erreur sur SQLite et sur PostgreSQL | Réussi (sortie console ; absence de doublon non vérifiée en comptant les lignes) |

Durée de la suite : la ligne « Ran 2833 tests in … » du journal affiche une valeur aberrante (horloge de la machine), non reprise.

## 2. Ce qui n'a pas pu être fait

| Élément | Statut | Raison |
|---|---|---|
| Missions des marins testeurs (M01 à M18) | **Impossible à vérifier avec les outils disponibles** | Pas de navigateur MCP (`mcp__playwright__*`) déclaré : un marin n'aurait aucun outil. Lui donner `Bash` détruirait l'isolation exigée. Aucun test utilisateur réel n'est revendiqué. |
| Audit RBAC/périmètres (SEC-01 à 07) | **Non testé** | Agent `qa-securite` non lancé. |
| Intégration fine (INT-04 à 10) | **Non testé** | Agent `qa-integration` non lancé. |
| Ergonomie experte (ERG-01 à 06) | **Non testé** | Agent `qa-ergonomie` non lancé ; captures impossibles sans navigateur piloté. |
| Mission de Julien (maintenance) | Données absentes | voir `personas-comptes.md` |

## 3. Anomalies et réserves

### ANO-001 : P1 : erreur 500 sur PostgreSQL pour tout marin rattaché à un navire sans équipage

- **Statut** : confirmé, reproduit (exécuté, échoué).
- **Cause** : `annonces/services.py:166` utilise `"\0"` comme valeur de repli quand `profile.equipage` est vide. PostgreSQL refuse un octet NUL dans une chaîne (`ValueError: A string literal cannot contain NUL (0x00) characters`). SQLite l'accepte, d'où l'absence de détection par la suite SQLite.
- **Preuve** (base de démo sur PostgreSQL, client de test Django, mêmes URL pour chaque compte) :

| Compte | équipage | `/` | `/annonces/` | `/search/rapide/` | `/search/` |
|---|---|---|---|---|---|
| `cdt_nor`, `chef_secteur_nor`, `equipier_nor` (Normandie) | vide | **500** | **500** | **500** | 200 |
| `equipier_a` (Bretagne, équipage A) | A | 200 | 200 | 200 | 200 |
| `admin`, `terre_classe`, `terre_securite` (sans navire) | vide | 200 | 200 | 200 | 200 |

- **Impact** : sur PostgreSQL (base de production prévue), la page d'accueil et les annonces sont inutilisables pour tout bâtiment sans double équipage. L'unité de démonstration Bretagne n'est pas touchée parce que tous ses comptes ont un équipage.
- **Autres occurrences** : recherche d'un motif identique (`"\0"` en valeur de requête) dans le code hors tests : aucune autre.
- **Tests** : 21 des 22 échecs PostgreSQL ont cette cause unique, ce qui montre qu'ils détectent le défaut, mais que la suite n'est exécutée que sur SQLite.
- **Qualification** : défaut fonctionnel, pas de fuite de données.

### ANO-002 : P3 : un test dépend de l'état de la base sur PostgreSQL

`notifications.tests.test_push_fallback.CreationNotificationSansPywebpushTests` lance un sous-processus qui recrée la base `test_matrix`, déjà utilisée par le test en cours : `database "test_matrix" already exists`. Défaut du test, pas du produit (passe sur SQLite).

### Réserves

- **Écarts Notion / fixtures** (R-01 à R-03) : `personas-comptes.md` : maintenance de Julien sans données, synthèse de passation à confirmer, référent formation cumulé avec chef de liste.
- **Isolation des marins** : conditionnée à l'ajout d'un serveur MCP navigateur (voir prérequis dans `README.md`).
- **Poste d'exécution des hooks** : la création d'un commit exige `python` avec Django et un fichier `.env` local avec `DJANGO_DEBUG=1` (ignoré par git). Réglage d'environnement, pas une modification du projet.

## 4. Verdict provisoire de préparation à la démonstration V1

**Non démontrable comme « qualifiée » à ce stade ; démonstrable sur le périmètre Bretagne sur SQLite sous réserve.**

- Pour : fusion effective, suite de 2 833 tests verte, migrations propres sur PostgreSQL depuis zéro, jeu de démonstration relançable.
- Contre : un défaut P1 (ANO-001) sur la base cible de production ; aucun test utilisateur réel ni audit de permissions n'a eu lieu.
- Ce qui peut être affirmé : Matrix démarre et se migre sur les deux moteurs, et la logique du périmètre Bretagne passe ses tests.
- Ce qui ne peut pas l'être : que les marins comprennent l'application, que les permissions soient étanches, ou que Matrix soit plus rapide que le papier ou Excel.

## 5. Suites proposées (en attente d'arbitrage)

1. Présenter ANO-001 au Product Owner : correction (hors passage A) via po → dev → relecteur, puis ajouter une exécution PostgreSQL au protocole de non-régression.
2. Décider de la source du navigateur pour l'équipe B (serveur MCP Playwright ou équivalent).
3. Accord pour la fixture de recette de Julien et pour un référent formation sans rôle de chef.
4. Lancer `qa-securite`, `qa-integration` et `qa-ergonomie` en début de prochaine session.
