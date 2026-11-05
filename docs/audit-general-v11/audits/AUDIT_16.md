# Audit 16 — Qualité des tests et non-régression (rapport partiel)

**Statut : partiel, non terminé.** Mesures de volume et lacunes constatées pendant les autres audits ; la pertinence de chaque test n'a pas été évaluée.

## 1. Volume et exécution (rejoués)

- 3 829 tests Django : **OK sous SQLite** (792 s, 20 ignorés) et **OK sous PostgreSQL 16** (899 s, 0 ignoré).
- 4 scripts de test JavaScript purs (`matrix/tests/*.test.js`) lancés depuis des tests Django ; rejoués seuls avec `node` : 4 OK.
- Répartition des tests (comptage textuel `def test_`, approximatif) : cœur `matrix` 881, `quarts` 609, `assets` 493, `training` 310, `dashboard` 261, `logistics` 228, `maintenance` 178, `notifications` 165, `accounts` 159, `calendar_app` 124, `org` 95, `taches` 94, `reports` 49, `annonces` 46, `demandes` 41, `threads` 30, `absences` 21, `programme` 10, `documentation` 9, `postes` 7, `retex` 5, `rondes` 0 (module retiré).

## 2. Lacunes constatées (preuves : autres rapports)

| Lacune | Constat |
|---|---|
| Aucun test de navigateur versionné dans le dépôt | recherche de `playwright`/`selenium` hors audit : aucun (AUD-003) |
| Aucune intégration continue | AUD-002 |
| Le test `test_administrateurs_ne_redigent_ni_ne_visent_par_le_seul_role` ne couvre que la feuille de l'équipage B à terre | l'administrateur d'unité vise les paliers secteur et service de la feuille de l'équipage à bord (AUD-014) |
| Liens affichés mais refusés : aucun test ne parcourt les pages par profil | 5 liens morts sur 42 comptes (AUD-016), déjà « corrigés » une fois dans les données seulement (ANO-001) |
| Aucun test d'un secteur sans section | DP-03 |
| Aucun test du mode production derrière un proxy TLS | AUD-011 |
| Aucun test d'import ou de suppression d'organisation avec conséquences | AUD-020, AUD-021 |
| Les tests de recette sont des déclarations tant qu'ils ne sont pas rejoués | audit 01 |

## 3. Principe de lecture

Une suite verte ne prouve pas la conformité métier : sur ce commit, elle est verte alors que les constats AUD-008, AUD-014, AUD-016, AUD-020 et AUD-021 sont reproductibles.

## 4. Non audité

Qualité des assertions, tests flous ou redondants, tests qui encodent un comportement erroné, couverture mesurée (aucun outil de couverture lancé), temps d'exécution par app, isolation entre tests.
