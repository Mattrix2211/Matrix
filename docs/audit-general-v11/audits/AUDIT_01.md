# Audit 01 — Expression de besoin et historique (rapport partiel)

**Statut : partiel, non terminé.** Commit audité : `1c37f22`.

## 1. Questions

1. Matrix correspond-il toujours à l'application imaginée au départ ?
2. Quelles fonctions ont été promises, reportées, abandonnées ? Lesquelles ont pu être oubliées ?
3. Les sources de vérité sont-elles cohérentes entre elles ?

## 2. Sources effectivement consultées

| Source | Lue | Remarque |
|---|---|---|
| Notion « Cahier des charges » (v. du 10/10/2026) | Entière | 42 sections ; bandeaux du 09 et 10/10 |
| Notion « Organigramme et rôles » | Entière | Hub ; les 13 sous-pages ne sont pas toutes lues |
| Notion sous-page 13 « Décisions… » | Entière | Source principale des décisions |
| Notion sous-page 06 « Service courant… » | Entière | Quarts, fraction de service, hommes morts |
| Notion « Feuille de route » | Entière | État du 10/10 |
| Notion « Ordre de travail V1.1 » (40b6e7f2…) | **Partielle** : 58 000 caractères, seulement les titres et le passage Rondes | À relire en entier |
| Notion base « Tâches en cours » | Schéma et décompte seulement | 380 tâches : 343 Terminé, 14 À faire, 21 À faire plus tard, 1 En cours, 1 En vérification |
| `CLAUDE.md`, `docs/REFERENCE.md`, `docs/RECETTE.md`, `docs/DEMO.md`, `docs/recette/00_SYNTHESE.md` et `03_*`, titres de `docs/propositions/*` | Oui, avec lecture partielle des propositions | — |
| Historique Git | Statistiques et jalons | 317 commits sur `main`, 434 environ sur la V1.1 ; première date 2026-04-03 |
| PR #1 à #16 | Titres de fusion seulement | Descriptions non lues |
| Conversations ChatGPT | **Non disponibles** | Le brief mentionne des « avis ChatGPT » repris dans Notion : seule la copie Notion est consultable |

## 3. Chronologie reconstituée (à compléter)

| Période | Jalon | Source |
|---|---|---|
| 2026-04 | Première livraison (PR #1) : 7 commits | `git log` |
| 2026-08 | BordOps, paquet de revue (PR #2) | `git log` |
| 2026-09-03 | Anciennes phases 1 à 6, statuts fondés sur le code | Notion FDR |
| 2026-09-06 | Cahier Matrix 2.0 : 7 principes, 8 phases | Notion CDC |
| 2026-09-23 | Réétiquetage Phase 0 à 7 ; archive `VISION_MATRIX_2_0.md` | FDR |
| 2026-10-09 | Cap de démonstration : calendrier colonne vertébrale ; génération automatique abandonnée | CDC, FDR |
| 2026-10-10 | PR #6 (refonte UX) et #7 fusionnées ; double équipage A/B ; passation et organisation miroir retirées | FDR |
| 2026-10-13 à 22 | Vague de sécurité (périmètres, cache des permissions, concurrence des quarts, PostgreSQL) ; PR #8 à #16 | `git log` |
| 2026-10-21 | Décisions organismes à terre, PÉPIN/CRAT | Page 13 |
| 2026-10-28 | PR #16 : V1 FANLAB dans `main` | `git log` |
| 2026-10-29 | Décision UX/UI progressive | Page 13 |
| 2026-10-31 | Directive « logique de marin militaire » ; quarts, fractions, hommes morts | Pages 06 et 13 |
| 2026-11-01 à 05 | Itération V1.1 (117 commits) : recette métier, retrait de Rondes (02/11), mer/quai, démonstration, dossier de recette | Ordre de travail Notion, `git log` |

## 4. Réponses provisoires

1. *Fidélité à la vision.* Les principes du cahier (configuration, traçabilité, dialogue contextuel, hors-ligne) sont repris dans `CLAUDE.md` et dans de nombreux tests. Pas de verdict : le référentiel v0 compte 54 exigences, presque toutes NV.
2. *Promis/reporté/abandonné.* **Abandonnés par décision explicite et datée** : génération automatique des tours (09/10), Rondes (02/11), QR codes en V1, ancien modèle `org.Equipage` et organisation miroir (10/10). **Différés** : synchronisation bord–terre (Phase 7), organismes à terre, circuits PÉPIN/CRAT, fonctions OSS et adjudant de compagnie, contrôle de qualification à quai. Aucune fonction **oubliée** n'est encore établie : l'audit n'a pas confronté les 380 tâches au cahier. Le cahier cite pourtant des fonctions dont rien ne prouve l'état (par exemple « prêts » et « retours » du §21, recherche universelle du §37, versionnement du §31).
3. *Cohérence des sources.* Plusieurs écarts : voir AUD-004, AUD-005, AUD-006 et `01_REFERENTIEL_EXIGENCES.md`.

## 5. Contradictions de décisions (à arbitrer)

- Passation : DP-02.
- Baseline et cible de fusion : DP-01.

## 6. Premières vérifications techniques exécutées (base temporaire, aucune base existante touchée)

| Vérification | Résultat |
|---|---|
| `manage.py check` | 0 erreur ; 1 avertissement de configuration (`matrix.W002`, sans valeur : l'audit tourne avec `DJANGO_DEBUG=1`) |
| `manage.py makemigrations --check --dry-run` | « No changes detected » : modèles et migrations concordent |
| `manage.py check --deploy` | 7 avertissements, tous liés à `DEBUG=1` ou à la clé factice de l'audit ; **non exploitable** : à rejouer sans DEBUG (audit 15) |
| Suite complète `manage.py test --parallel` (SQLite) | 3 829 tests OK, 20 ignorés, 792 s (détail : `08_LIMITES_ET_PREUVES.md` §3) |

## 7. Ce qu'il reste à faire pour clore l'audit 01

- Lire les 380 tâches (commentaires des agents) et les rattacher à des exigences.
- Lire intégralement l'Ordre de travail V1.1 et les pages Notion 01 à 05 et 07 à 12.
- Lire les descriptions des PR #1 à #16.
- Retrouver la source écrite du caractère facultatif des sections (DP-03).
- Confronter le cahier §1 à §42 au code pour établir la liste des oublis.
