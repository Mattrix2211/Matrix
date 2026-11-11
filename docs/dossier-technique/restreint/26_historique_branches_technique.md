# Chapitre 26 (technique) — Branches, commits et état de fusion

> **Diffusion restreinte.** Complète `diffusable/26_historique_versions_lots.md`. **État décrit :** état B (`6d6d0be`), non fusionné dans `main`. Légende : 🟢 vérifié dans Git, ⚪ non analysé.
> **Pour qui :** développeurs, responsable du projet. **Ce que vous y trouverez :** les branches qui expliquent l'évolution, leurs commits de référence et leur état par rapport à `main`. La liste complète des branches distantes est l'annexe F.

---

## 26T.1 Les branches qui comptent

| Branche | Date | Commit | Dans A / B | Rôle |
|---|---|---|---|---|
| `main` | 28/10/2026 | `6ef16ad` | A | V1 FANLAB (PR n° 16) : point de comparaison |
| `integration/v1-fanlab-20261021` | 27/10 | `994a530` | A, B | Consolidation de la V1 FANLAB |
| `integration/pr6-et-travail-local` | 10/10 | `50df154` | A, B | Base des PR n° 6 et n° 7 |
| `claude/paquet-bordops-review-69huab` | 01/10 | `f69a8cb` | A, B | Retrait de la génération automatique des quarts |
| `claude/feuille-service-*` (4), `claude/quarts-regler-echanges-atomique` | 17–22/10 | — | A, B | Chaîne feuille de service et échanges |
| `claude/securite-*` (4), `claude/fiabilite-*` (3), `claude/validations-critiques-confirmation`, `claude/compat-postgresql`, `claude/fix-ano-001-equipage-postgres` | 10–21/10 | — | A, B | Sécurité, fiabilité, PostgreSQL |
| `claude/ux9-*` (5), `claude/ergonomie-p2`, `docs/cahier-ux` | 02–27/10 | — | A, B | Ergonomie et cahier UX |
| `claude/ux-naval-premium-v11` | 31/10 | `a1503ac` | B seul | Prototype UX V1.1 (kit de recette) |
| `claude/recette-metier-ux-v11-20261101` | 01/11 | `284430d` | B seul | Correctifs métier et UX V1.1 |
| `claude/iteration-ux-v11-20261102` | 05/11 | `1c37f22` | B seul | **V1.1**, base des lots |
| `claude/l01-verrou-demo-v11` | 10/11 | `8e60fee` | B (empilé) | Lot L01 |
| `claude/l05-config-production-v11` | 10/11 | `517a2ce` | B (empilé) | Lot L05 |
| `claude/l02-archivage-effectif-v11` | 11/11 | `6e14a65` | B (empilé) | Lot L02 |
| `claude/l03-suppression-sure-v11` | 11/11 | `6d6d0be` | **B** | Lot L03, **état décrit par le dossier** |
| `claude/matrix-audit-general-9oohvw`, `…-rg0ddz` | 05/11 | `4aa4dcf`, `1ef7047` | ni A ni B | Audit général V1.1 (source du dossier V1.2, non repris) |
| `claude/matrix-v1-recette-audit-4olae7`, `claude/recette-v1-passage-b` | 13–20/10 | `b2dfacb`, `0f9f799` | ni A ni B | Recette V1 |
| `claude/eager-hopper-2cbcqh` | 11/11 | `6cc1557` | ni A ni B | **Dossier V1.2** et comptes rendus de lots |
| `claude/maquette-carte-a-faire` | 30/10 | `0fb5e17` | ni A ni B | Maquette « ne pas fusionner » |
| `claude/fervent-wright-kl6gtx` | 11/11 | — | ni A ni B | **Branche documentaire** du dossier technique (aucun code) |

## 26T.2 Commits des lots (état B)

| Lot | Commits |
|---|---|
| L01 | `1b4cd5a` verrou et mots de passe non prévisibles ; `bc4fcbc` relecture (réinitialisation, mise en forme) ; `59a0606` preuve de préparation, identifiants propres à chaque base, recette Windows ; `8e60fee` un fichier voisin vide n'est jamais une preuve ; adoption explicite des anciennes bases ; migration 0022 |
| L05 | `517a2ce` refus en production d'une clé ou d'un mot de passe de base insuffisants (AUD-010, AUD-017) |
| L02 | `b6a4b99` archivage effectif (AUD-028) ; `a3832b3` relecture (matériel en masse et API, comptes désactivés, déplacement vers un parent archivé) ; `b9b66e6` fermeture des contournements restants ; `6e14a65` refus de rôle des exigences de formation |
| L03 | `6d6d0be` protection contre les suppressions destructrices des unités (AUD-020) |

🟢 `6ef16ad` est **ancêtre** de `1c37f22` (V1.1), lui-même ancêtre de `6d6d0be` : l'état B contient entièrement l'état A. **127 commits** séparent `main` de B.

## 26T.3 Fusion

🟢 **Aucune branche de lot, ni la V1.1, n'est fusionnée dans `main`.** Les lots sont **empilés** : fusionner L03 revient à fusionner L01, L05, L02 et la V1.1. Cette décision revient au PO ; ce dossier n'y touche pas.

## 26T.4 Limites : ce qui n'est pas analysé ⚪

- Les ~25 autres branches (essais de printemps et d'été, `economie-tokens`, `sauvegarde/sonnet-2026-09-23`, `quizzical-curran`, `ux-fondations`, `ux-3-10`, `taches-lot1`, `verif-socle-accounts`, `matrix-project-tasks-…`) sont **listées en annexe F sans analyse**.
- Aucune balise Git n'existe.

---

**Sources.** `git for-each-ref`, `git log`, `git merge-base --is-ancestor` (état du dépôt à la date d'inventaire) ; `G0_SOMMAIRE_DETAILLE.md` §9.
