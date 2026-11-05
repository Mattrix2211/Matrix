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
| 1. Référentiel historique | 01 | **Clôturé avec réserves** (voir ci-dessous l'état 3ᵉ passe) : les 13 sous-pages Notion « Organigramme et rôles » sont lues ; le backlog (380 tâches) n'est lu qu'en statuts ; les PR #1 à #16 non lues |
| 2. Cohérence Marine nationale | 19 | **Partiel** |
| 3. Fonctionnel, organisation, UX | 02 à 12 | **Partiel** : rapports partiels pour les 11 audits |
| 4. Fondations techniques | 13 à 17 | **Partiel** : rapports partiels pour les 5 audits |
| 5. Données de démonstration | 20 | **Clos avec réserves** |
| 6. Synthèse | 18 | **Partiel** (synthèse intermédiaire) |

Aucun audit n'est déclaré terminé. Existent (tous partiels) : `AUDIT_01`, `02`, `03`, `04`, `05`, `06`, `09`, `14`, `15`, `16`, `17`, plus `AUDIT_DP03_SECTIONS`. Les autres fichiers n'existent pas encore : ils seront créés au fur et à mesure, pas en coquilles vides.

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

| 2026-11-05 (2ᵉ passe, consignes du PO) | DP-01 tranché (main intacte). Lecture des 13 sous-pages Notion. Matrice de droits des quarts (21 profils, 1 407 requêtes) et effets réels du circuit de la feuille ; 42 comptes × 3 778 requêtes de navigation ; navigateur réel (Chromium) sur 7 profils ; PostgreSQL 16 jetable (migrate, démo, suite complète lancée) ; simulation production (proxy TLS, clé « change-me »). Analyse DP-03. Anomalies AUD-014 à AUD-018 ; AUD-008 à AUD-013 requalifiées. |

## Reprise : ce qu'il reste à faire en priorité

1. Audit 19 (conformité Marine) : croiser les pages Notion (lues) avec libellés, rôles et circuits du code ; lire les PR #1 à #16 et les tâches « Terminé » clés (audit 01).
2. Audit 06 complet : droits des autres modules (tâches, maintenance, stock, formation, annonces), API DRF, délégations, double équipage hors quarts.
3. Navigateur : parcours métier restants (signalement d'anomalie jusqu'à l'envoi, tâche bloquée, échange de service, maintenance, mobile, impression, mode sombre) ; comparaison aux maquettes UX V1.1 (sous-module `design` à initialiser).
4. Audits 07 à 12 (calendrier, maintenance, logistique, communication, autres modules), 13 (architecture), compléments 14 et 16, 20, enfin 18. Attendre les décisions DP-03, DP-09, DP-10, DP-13 avant de figer les recommandations correspondantes.
| 2026-11-05 (3ᵉ passe, autonomie jusqu'à la clôture) | Propositions P01 à P05 (DP-03, DP-09, DP-10, DP-13, DP-14). Rapports 07, 08, 10, 11, 12, 13, 18, 19, 20. Pipeline complet de démonstration (61 comptes) : liens (8 468 requêtes), droits, circuit, structure rejoués. Maquettes et charte comparées (dépôt design-system récupéré, `78060c5`). Registre trié (32 anomalies : 2 P0, 6 P1, 14 P2, 10 P3). Bilan : `09_BILAN_DES_AUDITS.md`. |


| 2026-11-05 (4ᵉ passe, autonomie jusqu'à la fin des vérifications réalisables) | 11 parcours navigateur de bout en bout ; revue de qualité des tests (métriques, 13 mutations en 18 exécutions) ; cas limites (listes publiées, délégations, suppressions, archivage, suppression de compte) ; comparaison `main` / V1.1 (worktree de `main`, matrice de droits, diffs) ; montée de version d'une base peuplée (SQLite et PostgreSQL) ; effet réel des seuils ; simulation d'un nouveau bâtiment ; connexions répétées ; sondes versionnées et rejouables (22 conformes sur base neuve). Propositions P06 (AUD-009) et P07 (AUD-020, 021, 028, 034). Registre : 42 anomalies. Les 20 audits sont classés **clôturés avec réserves** (`09_BILAN_DES_AUDITS.md`). |

**État final : 20 audits clôturés avec réserves, 0 clôturé sans réserve, 0 bloqué.** Reprise possible : voir la section « Travaux réalisables qui n'ont pas été faits » de `09_BILAN_DES_AUDITS.md`.
| 2026-11-05 (contrôle de conformité à l'addendum « 20 audits en 6 phases ») | Livrables renommés (`AUDIT_19_COHERENCE_MARINE.md`, `AUDIT_20_DONNEES_DEMONSTRATION.md`) ; audit 19 refait avec 46 règles métier (source, nature, implémentation, conformité, preuve, décision) et la souplesse des organisations ; audit 20 refait avec matrice module × profil, couverture des états et scénarios manquants ; audit 18 refait comme consolidation des 20 audits ; registre unique (42, anomalies des audits 10 et 11 ajoutées) ; matrice unique (A exigences, B règles Marine, C couverture) ; `11_CONFORMITE_ADDENDUM.md`. |
