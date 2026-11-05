# Audit 14 — Données et intégrité (rapport partiel)

**Statut : Clôturé avec réserves** (voir « Clôture » en bas du rapport). (cluster jetable local, port 54329, hors dépôt).

## 1. PostgreSQL : première vérification indépendante

| Contrôle | Résultat |
|---|---|
| `migrate` sur base vierge (175 migrations) | Réussi, ≈ 30 s |
| `seed_demo` | Réussi, ≈ 10 s ; 42 comptes comme sous SQLite |
| **Suite complète** `manage.py test --parallel 4` sur PostgreSQL 16.15 | **3 829 tests, OK, 0 ignoré**, 899 s. Les 20 tests ignorés sous SQLite (propres à PostgreSQL) **sont donc exécutés et passent** |

Cela confirme, par rejeu, la déclaration du dossier de recette (« 3 829 OK sur PostgreSQL ») pour ce commit. Cela ne prouve ni la concurrence réelle en production (plusieurs processus, charge), ni la migration d'une base déjà peuplée d'une version antérieure.

## 2. Intégrité référentielle et réorganisation (défauts confirmés)

Analyse des clés étrangères vers l'organisation (`sondes/fk.py`) et simulation de suppression sans exécution (`sondes/cascade.py`) :

- Vers une **section** : 9 relations en cascade, 6 en « mise à NULL » (dont le rattachement des marins).
- Vers un **secteur** : 13 en cascade (dont chefs de liste, listes de quart et de garde, annonces, programme, postes, documents, exigences de formation, types de matériel, fiches, rondes), 7 en « mise à NULL », 3 protégées (matériel, installations, stocks).
- Vers un **service** : 12 en cascade, 6 en « mise à NULL », 3 protégées.
- Vers un **bâtiment** : 33 en cascade.

Conséquences, déjà enregistrées : AUD-020 (suppression physique, rattachements remis à NULL, périmètre élargi, cascade sur des données historiques) et AUD-021 (erreur 500 lorsque le matériel protège la suppression).

## 3. Points favorables relevés (à ne pas perdre)

- Verrous de ligne (`select_for_update`) à 35 endroits hors tests ; tests de concurrence présents (`org/tests/test_releves_concurrence.py`, `logistics/tests/test_mouvements_stock.py`, `matrix/tests/test_saisie_robuste.py`) ; stock par mouvements immuables (`logistics/stock.py`) ; historique des relèves et des feuilles (versions, rectificatifs).
- `ATOMIC_REQUESTS` non activé : les écritures multiples reposent sur des blocs `transaction.atomic()` explicites (non audités un par un).

## 4. Non audité

Migration d'une base peuplée (sauvegarde puis montée de version), isolation multi-bâtiments par requête SQL, contraintes d'unicité et de cohérence au cas par cas, performances avec un historique réel, sauvegarde/restauration PostgreSQL, rétention de l'`AuditLog`, écritures hors transaction.

## 5. Anomalies liées

AUD-020, AUD-021.

## Clôture (4ᵉ passe)

**Statut : Clôturé avec réserves.** « Avec réserves » signifie que l'analyse technique est achevée sur le périmètre décrit ; **les éléments listés ci-dessous restent non vérifiés et ne doivent pas être lus comme conformes**.

### Contrôles ajoutés à la 4ᵉ passe

**Montée de version d'une base peuplée `main` → V1.1** : 21 migrations, SQLite et PostgreSQL 16, aucune ligne perdue, aucune migration manquante, connexions fonctionnelles. Cascades et protections mesurées (suppression d'unités et de comptes). Suite complète verte sur PostgreSQL.

### Non vérifié ou dépendant d'une validation externe

Sauvegarde/restauration PostgreSQL (aucune procédure), concurrence en charge, base réelle anonymisée.
