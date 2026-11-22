# Rapport final de recette — refonte documentaire G0 révision 2

> **DOCUMENT PROVISOIRE — DIFFUSION RESTREINTE.** Précaution documentaire, non une classification officielle.
> Jalon V2 validé par le PO sur le plan documentaire le 22/11/2026. Ce rapport ne valide ni le logiciel Matrix ni sa diffusion. Il décrit les PDF du commit `63e9be2` (empreintes dans `INVENTAIRE_LIVRABLES.md`).

Branche `claude/fervent-wright-kl6gtx` · état applicatif B `6d6d0be` · base d'audit `637de94`.

## 1. Résultat

| Document | Pages | C8 bloquants | Pages remplies à moins de 40 % |
|---|---|---|---|
| Guide utilisateur | 86 | 0 | 6, 47 (réserve V2), 59, 71, 80, 86 |
| Référentiel fonctionnel | 138 | 0 | 8, 16, 131, 138 |
| Dossier technique | 96 | 0 | 7, 9, 12, 56, 75 |
| Registre | 52 | 0 | 43 |

Aucune modification du code applicatif depuis `637de94` (C13 : différence vide). `main` n'est pas touchée.

## 2. Contrôles C1 à C14 (résultats finaux)

| Contrôle | Résultat |
|---|---|
| C1 couverture de l'ancienne édition | 507 titres du périmètre, 507 couverts ou retirés avec motif, 0 orphelin |
| C2 étiquettes (🟢 🔵 🟣 ⚪) | 0 bloquant ; relectures manuelles consignées dans `config/revue_manuelle.yaml` |
| C3 chiffres | 0 écart avec `faits.yaml` |
| C4 références de code | 0 erreur |
| C5 séparation et mention provisoire | 0 bloquant ; mention vérifiée sur chaque page des quatre PDF |
| C6 sommaires et renvois | 37 (guide), 39 (référentiel), 38 (dossier technique), 38 (registre) entrées vérifiées, 0 écart ; signets : référentiel 321, dossier technique 206, tous sur la page de leur titre |
| C7 décisions | 0 bloquant ; 125 décisions sur 125 avec leur état dans le PDF du registre |
| C8 mise en page | 0 bloquant ; contrôle renforcé : titre de chapitre coupé, encadré « Public » coupé, titre séparé de son encadré (0 sur les quatre PDF) ; rejoué sur les PDF antérieurs, il signale bien les quatre défauts corrigés |
| C9 captures | 72 captures au manifeste (2 émulées signalées), 6 assertions DOM |
| C10 inspection à taille réelle | 372 pages au journal final (voir §3) |
| C11 cohérence inter-documents | 35 actions identiques à l'inventaire ; états des décisions identiques au registre ; relations des schémas S02, S14, S22, S27, S38 : 0 écart |
| C12 reproductibilité | reconstructions temporaires de pré-vérification identiques page par page (pixel pour pixel) aux livrables |
| C13 aucun changement applicatif | 0 fichier hors documentation modifié |
| C14 données sensibles | 0 mot de passe, secret ni chemin local |

Lisibilité des schémas : 46 schémas, 46 « OK » (corps de police ≥ 8 pt à la largeur de la page, `pdf_candidats/schemas_lisibilite.csv`).

## 3. Inspection (journal final par page)

`pdf_candidats/JOURNAL_INSPECTION_FINAL.csv` : une ligne par page des quatre PDF (372). Aucune inspection nouvelle n'y est déclarée ; chaque page est rattachée à une inspection réellement effectuée.

| Méthode | Pages |
|---|---|
| Inspection directe (relecture visuelle à 100 ppp ; cinq schémas du référentiel et deux du dossier technique aussi à 140 ppp) | 31 (référentiel 22, dossier technique 9) |
| Identité graphique démontrée avec une page déjà inspectée (100 ppp, niveaux de gris, pied de page exclu, mêmes dimensions) | 203 (référentiel 116, dossier technique 87) |
| Identité binaire du document avec une version inspectée (même SHA-256) | 138 (guide 86, registre 52) |

Le script `outils/consolider_journal.py` recalcule la chaîne de preuves à partir de l'historique git. Une identité de texte seule n'est jamais retenue comme inspection.

## 4. Réserves connues et documentées

1. Seize pages peu remplies (§1), justifiées par des débuts de chapitre ou des fins de partie ; aucun défaut ouvert.
2. Cinq schémas conservés comme fichiers mais non repris dans les documents : S09, S10b, S24, S28b, S40.
3. Les écarts A1 à A26 et NE-01 à NE-07 sont des écarts **documentés**, non des autorisations de modifier le logiciel. NE-07 (message de fin de compte rendu inexact pour une installation) n'est pas corrigé.
4. Le ticket correctif est automatique pour un contrôle non conforme sur un matériel mobile ; pour une installation il n'en existe pas. La proposition D1 (ticket de suivi pour une installation) reste une proposition 🟣 non arbitrée.
5. Les résultats de tests des lots (3 963 tests OK, 20 ignorés) sont des preuves historiques tirées des comptes rendus, non rejouées pour cette révision.
6. Fonctions 🔵 (cible) et 🟣 (proposition) : jamais présentées comme disponibles.
7. Aucune recette navigateur réelle (mobile, lecteur d'écran, PostgreSQL, Windows) n'est revendiquée en dehors de ce que les documents indiquent comme rejoué.

## 5. Reconstructions

Après la première construction candidate (phase 10) et jamais remises à zéro : guide 5, référentiel 9, dossier technique 5, registre 3. Le budget initial de deux reconstructions par document a été dépassé sur autorisation expresse du PO ; les constructions temporaires de vérification (C12) ne sont pas comptées. Plus aucune reconstruction n'est demandée.

## 6. Historique des jalons

| Commit | Jalon |
|---|---|
| `046444c` | Phases 4 à 9 : sources, captures, barrière G1 (16/11/2026) |
| `cdae46e`, `25f4c0e` | Phase 10 : PDF candidats, corrections de rendu |
| `574a374` | Inspection complète de 367 pages, rapport V2 |
| `3481fce`, `5a9885e` | Passe finale : tickets, schémas de flux, index des 46 schémas |
| `636bf6b` | Règle de titres, constat A25 précisé |
| `63e9be2` | Coupures de titres et d'encadrés « Public » corrigées, C8 renforcé ; clôture V2 |
| (ce commit) | Documents de suivi, journal final par page, plan du basculement V3 |

## 7. Ce que ce rapport ne dit pas

Il ne dit pas que le logiciel est validé, ni qu'une diffusion est autorisée, ni que le basculement V3 est fait : les anciennes arborescences et les trois anciens PDF sont conservés jusqu'à l'arbitrage du PO.
