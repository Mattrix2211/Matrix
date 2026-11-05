# Audit 16 — Qualité des tests et non-régression (rapport partiel)

**Statut : Clôturé avec réserves** (voir « Clôture » en bas du rapport). Mesures de volume et lacunes constatées pendant les autres audits ; la pertinence de chaque test n'a pas été évaluée.

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

## 5. Revue de qualité des tests (4ᵉ passe)

Outils : `sondes/qualite_tests.py` (analyse statique des tests par AST) et `sondes/mutations/` (mutations de la logique de droits dans une **copie jetable** du dépôt, hors du dépôt de travail ; aucune ligne de l'application n'a été modifiée).

### 5.1 Métriques statiques (3 815 tests dans 356 fichiers)

| Indicateur | Valeur | Lecture |
|---|---|---|
| Assertions par test | moyenne 2,3 ; médiane 2 | niveau correct |
| Tests avec une seule assertion | 1 213 (32 %) | acceptable pour des tests de refus ; risque de test trop mince ailleurs |
| Tests sans assertion directe | 20, dont `test_fuites_sans_rattachement` (délégation à une fonction d'aide) et `test_contrastes` | à vérifier un par un : certains délèguent l'assertion, d'autres peuvent être vides |
| Tolérances « 403 ou 404 » interchangeables | 19 occurrences | un refus pour une mauvaise raison passe : faux positif possible |
| `mock.patch` | 170 | usage modéré |
| Tests avec `try/except` | 14 | risque d'avaler une erreur : à relire |
| `skip` | 14 déclarations ; 20 tests ignorés sous SQLite (propres à PostgreSQL, **exécutés et verts sous PostgreSQL**) | acceptable |
| Clés du registre de seuils jamais citées dans un test | **16 sur 35** (`installation_gestion_avancee`, `maintenance_execution_ecriture`, `thread_ecriture`, `programme_saisie`, `poste_gestion`, `documentation_redaction`, `documentation_validation`, `retex_validation`…) ; 12 autres citées 1 à 2 fois | **couverture de permissions insuffisante par action** : ces clés ne sont éprouvées qu'indirectement par leur valeur par défaut |

### 5.2 Mutations de la logique de droits (13 mutations distinctes, 18 exécutions)

Une mutation est **tuée** si au moins un test échoue. Certaines ont été rejouées sans arrêt au premier échec pour mesurer la force de détection (lignes « 19 échecs », « 7 échecs »…).

| Mutation | Résultat | Détail |
|---|---|---|
| Rédaction de la feuille ouverte à tous | tuée | 3 tests lancés avant arrêt |
| Visa COMAEQ ouvert à tous | tuée | **19 échecs** sur 124 tests de la feuille |
| Visa chef de secteur ouvert à tous | tuée | 7 échecs sur 124 |
| Visa chef de service ouvert à tous | tuée | arrêt au 21ᵉ test |
| Désignation des rédacteurs ouverte à tous | tuée | idem |
| Publication d'une liste ouverte à tous | tuée | **8 échecs** sur 78 |
| Gestion d'une liste ouverte à tous | tuée | 9 tests |
| Validation d'une qualification ouverte à tous | tuée | 27 tests |
| Périmètre supprimé (`build_scope_q` → tout) | tuée | 2 tests |
| Périmètre des tickets sans étanchéité | tuée | 2 tests |
| Stock négatif accepté | tuée | 2 tests |
| Suppression de compte hors périmètre (`_utilisateurs_gerables_par` → tous) | tuée, **par un seul test** sur 200 | couverture fragile : un seul test protège cette frontière |
| Seuils de rôle désactivés, 4 modules de droits (103 tests) | **SURVIVANTE** | les modules nommés « permissions » et « sécurité des écritures » **ne détectent pas** la neutralisation des seuils |
| Seuils de rôle désactivés, suite complète | tuée par **161 tests sur 3 829** (157 échecs, 4 erreurs) | la sémantique des seuils est protégée, mais dans les modules fonctionnels, pas dans un test central |

Lecture : **les tests de permissions sont efficaces sur les circuits les plus travaillés (feuille de service, listes, formation, périmètres)**, mais : (1) la protection de la suppression de compte tient à un test unique ; (2) 16 clés du registre n'ont pas de test nommé ; (3) aucune mutation ne vérifie l'**absence** d'accès d'un **administrateur technique** (c'est pourquoi AUD-014 n'est pas détecté par la suite) ; (4) une suite verte coexiste avec 42 anomalies enregistrées.

### 5.3 Risques de faux positifs identifiés

1. Les 19 tolérances « 403 ou 404 ».
2. Le test central `test_administrateurs_ne_redigent_ni_ne_visent_par_le_seul_role` ne couvre que la feuille de l'équipage B à terre : il donne l'impression d'une garantie plus large que celle prouvée.
3. Des tests de refus sans vérification de l'absence d'effet en base (à échantillonner).

### 5.4 Scénarios manquants (à créer avec les corrections)

Administrateur technique sans droit de visa ; suppression d'unité ou de compte avec historique ; secteur sans section ; marin transversal ; liens affichés ↔ droits serveur ; double envoi d'ajout de créneau ; message de confirmation de maintenance non conforme sur installation ; proxy TLS ; verrouillage de connexions.

## Clôture (4ᵉ passe)

**Statut : Clôturé avec réserves.** « Avec réserves » : l'analyse est terminée sur le périmètre décrit ; les éléments listés ci-dessous restent non vérifiés et ne doivent pas être lus comme conformes.

### Non vérifié

Qualité de chacune des 3 815 assertions (échantillonnage et métriques seulement), mesure de couverture de lignes (aucun outil de couverture lancé), mutation d'autres modules (maintenance, annonces, documents).
