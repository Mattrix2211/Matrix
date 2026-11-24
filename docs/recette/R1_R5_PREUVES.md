# Recette technique de l'état B — synthèse des preuves R1 à R5

Commit testé : `6d6d0be` (branche `claude/l03-suppression-sure-v11`), comparé à `main` @ `6ef16ad`. Exécution du 24/11/2026, copies isolées, comptes et données fictifs. Aucun secret ni identifiant dans ce document.
Journaux bruts : `R1_R5_journaux_bruts.tgz` (journaux de test, instantanés avant/après, outils de comparaison, script de scénarios).

## 1. Suites complètes (commit 6d6d0be)

| Moteur | Commande | Tests | Réussis | Échecs / erreurs | Ignorés |
|---|---|---|---|---|---|
| SQLite | `python manage.py test --parallel 4` | 3963 | 3943 | 0 / 0 | 20 |
| PostgreSQL 16 (UTF8) | idem, `DB_HOST` renseigné | 3963 | 3941 | 0 / 0 | 22 |

Un premier passage PostgreSQL est invalide : cluster temporaire créé en SQL_ASCII (7 échecs, 217 erreurs, 22 ignorés). Défaut de l'environnement de recette, pas du code ; conservé sous `pg_run1_invalide_SQL_ASCII.log`.

## 2. Tests ignorés et motifs

| Moteur | Nb | Motif |
|---|---|---|
| SQLite | 14 | Verrous de ligne : PostgreSQL requis |
| SQLite | 4 | Concurrence réelle testée sur PostgreSQL seulement |
| SQLite | 1 | Verrou de ligne (préférences) : PostgreSQL seulement |
| SQLite | 1 | Le caractère NUL n'est refusé que par PostgreSQL |
| PostgreSQL | 21 | Chemin de base simulé : SQLite seulement (verrou démo) |
| PostgreSQL | 1 | Moteur simulé : SQLite seulement |

Les deux moteurs se complètent : chaque test ignoré sur l'un s'exécute sur l'autre.

## 3. Tests JavaScript

Rejeu ciblé le 24/11/2026 sur le commit 6d6d0be (les journaux d'origine n'avaient pas été conservés ; trois de ces fichiers (brouillon, grille, inactivité) sont aussi appelés par des tests Django `test_logique_pure`, ignorés seulement si `node` est absent). Node v22.23.4.

| Commande | Résultat |
|---|---|
| `node matrix/tests/brouillon.test.js` | OK, code 0 |
| `node matrix/tests/compte_rendu.test.js` | OK, code 0 |
| `node matrix/tests/grille.test.js` | OK, code 0 |
| `node matrix/tests/inactivite.test.js` | OK, code 0 |

Bilan : 4 fichiers réussis, 0 échec, 0 ignoré. Ce sont des scripts à assertions (pas de lanceur de tests) : il n'existe pas de décompte par cas, seulement succès/échec par fichier. Limite : logique pure uniquement, pas de rendu navigateur.

## 4. Migrations (37 ajoutées par rapport à main)

- Application depuis un état équivalent à main, enrichi de données fictives : SQLite et PostgreSQL, 44 lignes « Applying … OK » chacune, sans erreur.
- Comparaison avant/après (`pre*.snap.json` / `post_b*.snap.json`) : comptes de lignes, relations et contraintes conservés, aucun orphelin.
- Schéma : retour arrière technique réussi sur les deux moteurs. Valeurs calculées par `quarts` 0014, 0017, 0019 non reconstituées (sens inverse `noop`), données saisies après migration perdues : démontré.
- Les migrations L03 (`on_delete`) n'ont aucun effet SQL (la règle est côté Python).
- Restauration depuis sauvegarde (`pg_dump -Fc` / copie SQLite) : état de main retrouvé sans écart. Seul chemin de retour fiable ; aucun retour arrière sans sauvegarde.

## 5. Scénarios L02 et L03 (SQLite et PostgreSQL, résultats identiques)

S1 archivage d'un service occupé refusé ; S2 archivage puis réactivation d'un service vide ; S3 suppression d'un bâtiment référencé : `ProtectedError`, objet conservé ; S4 suppression d'un service référencé refusée (2 profils) ; S5 action groupée d'administration « supprimer la sélection » : toute la sélection est refusée, trace d'audit `suppression_unite_refusee`, message HTTP 200 trompeur ; S6 le marin reste rattaché.

## 6. Tests de sécurité : trois natures à ne pas confondre

| Nature | Ce qu'ils prouvent | Éléments |
|---|---|---|
| **Conformité fonctionnelle** | Le comportement attendu est bien implémenté | L01 (verrou démo), L05 (configuration de production), L02/L03 (archivage, suppression), étanchéité équipage, écritures des adjoints, circuit BSC |
| **Non-régression** | Un comportement existant n'a pas changé | Suites complètes, `test_securite_ecritures` |
| **Audit reproduisant un écart connu** | L'écart existe encore | A14, A20, A25 : 29 tests, tous « OK » sur main **et** sur B. Leur réussite **ne signifie pas que l'écart est corrigé** ; elle confirme qu'il est toujours présent |

Rejeu des tests de protection de B sur la copie de main : modules non importables (`erreurs_secrets_production`, service d'écriture des adjoints, `InstanceDemo`, `archivage`, `structure_services`, `RedacteurFeuilleService` absents). Cela confirme l'**absence des composants** sur main, mais ne démontre ni l'existence ni l'exploitation d'une vulnérabilité à elle seule. Seule exception évaluée : `test_securite_ecritures` s'exécute sur main avec 2 échecs sur 41 (400 au lieu de 404, 204 au lieu de 409), ce qui est un écart de comportement observé.

## 7. Identifiants administrateur

Avant correctif (6d6d0be) : `scripts/create_superuser.py` créait, sans garde, un superutilisateur avec un identifiant et un mot de passe codés en dur si le compte n'existait pas. Constaté sur bases jetables main et B ; aucune authentification sur instance réelle. Correctif : commit `44e7129`, branche `claude/securite-admin-identifiants-v11` (scripts supprimés, `create_admin.bat` seule voie, 8 tests ajoutés).

Tests ciblés du commit 44e7129 (aucune suite complète sur ce commit) :

| Moteur | Découverts et exécutés | Réussis | Échoués | Ignorés |
|---|---|---|---|---|
| SQLite | 221 | 220 | 0 | 1 (verrou de ligne : PostgreSQL seulement) |
| PostgreSQL 16 | 221 | 199 | 0 | 22 (21 chemins de base simulée et 1 moteur simulé : SQLite seulement) |

Précision sur `createsuperuser` : voir le compte rendu du 24/11/2026 (mot de passe faible acceptable sur réponse « y » à l'invite, et non validé en mode non interactif).

## 8. Emplacement

- Résumé et documents préparatoires : `docs/recette/` de la branche `claude/securite-admin-identifiants-v11`.
- Journaux bruts (≈ 200 Ko) : hors dépôt Git, remis à la personne qui valide la recette.
