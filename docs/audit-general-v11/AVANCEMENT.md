# Audit général Matrix V1.1 — journal d'avancement

Fichier de reprise : toute session doit le lire en premier et le mettre à jour en dernier.

## Cible auditée

| Élément | Valeur |
|---|---|
| Dépôt | `Mattrix2211/Matrix` |
| Commit audité | `1c37f22bdef098d3057e682ef4b4213b897eabbf` (2026-11-05, « Dossier de recette… ») |
| Branche de référence du PO | `claude/iteration-ux-v11-20261102` (même commit) |
| Branche de travail de l'audit | `claude/matrix-audit-general-rg0ddz`, posée sur 1c37f22 (aucun commit propre avant cet audit) |
| `main` à la date de l'audit | `6ef16ad` (2026-10-28) : **117 commits derrière** 1c37f22 ; la V1.1 n'est pas fusionnée |
| Sous-module `design` | `78060c5` (non initialisé dans l'environnement d'audit, voir `08_LIMITES_ET_PREUVES.md`) |

Le SHA du brief (« 1c37f22 ») était introuvable dans la copie locale initiale, qui était sur `main` : il a fallu le récupérer depuis `origin`. Tout constat ci-dessous porte sur 1c37f22, sauf mention contraire.

## Phases et audits (6 phases, 20 audits)

| Phase | Audits | État |
|---|---|---|
| 1. Référentiel historique | 01 | **En cours** : sources inventoriées, référentiel v0 posé, rapport partiel |
| 2. Cohérence Marine nationale | 19 | Non commencé (sources Notion 01 à 13 partiellement lues : voir limites) |
| 3. Fonctionnel, organisation, UX | 02 à 12 | **Partiel** : 03 et 06 en rapports partiels (reprise du 05/11) ; 02, 04, 05, 07 à 12 non commencés |
| 4. Fondations techniques | 13 à 17 | **Partiel** : 15 et 17 en rapports partiels ; 13, 14, 16 non commencés |
| 5. Données de démonstration | 20 | Non commencé |
| 6. Synthèse | 18 | Non commencé : ne peut être écrit avant les 19 autres |

Aucun audit n'est déclaré terminé. Existent : `AUDIT_01` (partiel), `03`, `06`, `15`, `17` (partiels). Les autres fichiers n'existent pas encore : ils seront créés au fur et à mesure, pas en coquilles vides.

## Prochaines étapes (ordre recommandé)

1. Terminer la phase 1 : lire les pages Notion 01 à 05 et 07 à 12, les tâches « Terminé » clés, l'historique des PR #1 à #16, puis compléter le référentiel (EX-xxx) et passer les lignes « non vérifié » à un état prouvé.
2. Phase 2 (audit 19) puis phase 3 par groupes : {02, 03, 06} organisation et droits ; {04, 05, 07} quotidien et UX ; {08, 09, 10, 11, 12} modules.
3. Phase 4 : audits 13 à 17.
4. Phases 5 et 6.

## Journal

| Date | Action |
|---|---|
| 2026-11-05 | Inventaire du dépôt, bascule sur 1c37f22, lecture de 5 pages Notion et de la documentation du dépôt, création de l'environnement d'audit isolé (hors dépôt), suite de tests complète lancée sur base temporaire, premiers documents. |
| 2026-11-05 (reprise) | Branche de travail rebasée sur l'état de `claude/matrix-audit-general-rg0ddz` (1ef7047). Vérifications dynamiques sur base temporaire : AUD-001 rejoué sur 1c37f22 (conforme), balayage de 10 profils, accès anonyme, `check --deploy`, recherche de dépendances externes. Nouvelles anomalies AUD-008 à AUD-013. Rapports partiels 03, 06, 15, 17. |

## Reprise : ce qu'il reste à faire en priorité

1. Audit 19 (conformité Marine) : lire les pages Notion de « Organigramme et rôles » (liens dans `08_LIMITES_ET_PREUVES.md`).
2. Audit 06 complet : matrice rôle × action × périmètre, API, double équipage (rejouer `marin_b` sur l'équipage A).
3. Parcours navigateur (Chromium/Playwright disponibles) pour les audits 04, 05, 09 ; qualifier AUD-008 (donnée ou code).
4. Audits 02, 07 à 12, puis 13, 14, 16 (revue des tests), 20, enfin 18.
