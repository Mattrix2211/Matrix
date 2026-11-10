# Dossier technique Matrix V1.2

Dossier d'analyse et de préparation de la phase de correction et d'implémentation. **Aucun code applicatif n'est modifié par ce dossier.**

- **Base de référence** : V1.1, commit `1c37f22` (branche `claude/iteration-ux-v11-20261102`), validée par le PO.
- **Audit repris** : branche `claude/matrix-audit-general-9oohvw`, commit `4aa4dcf`, dossier `docs/audit-general-v11/` (47 anomalies, dont 2 P0).
- **Rédigé le** : 2026-11-10 (mise à jour le même jour après le message S3), sur la branche `claude/eager-hopper-2cbcqh` (issue de `main`, sans la V1.1 : les chemins de code cités se lisent sur `1c37f22`).
- **Sources** : dépôt, audit, Notion (cahier, organigramme, décisions, feuille de route, tâches, ordre de travail du 01/11, service courant, audit métier), messages du PO.

## Lecture conseillée

1. `00_SYNTHESE.md` — résultat et suite.
2. `J_TRIAGE_ET_ARBITRAGES.md` — contradictions et questions triées ; les 2 qui restent.
3. `K_PRIORITES_JUSTIFIEES.md` — priorités P0 à P3 justifiées.
4. `M_PLAN_DEVELOPPEMENT.md` — 28 lots et premier lot recommandé.
5. `L_SOURCES_NON_CONSULTEES.md` — sources lues et non lues.
6. En référence : `A_REGISTRE_DECISIONS.md`, `A1_DECISIONS_S1_S2.md`, `B_CARTOGRAPHIE.md`, `C_MATRICE_TRACABILITE.md`, `E_STRATEGIE_TESTS.md`, `E2_CATALOGUE_TESTS.md`, `G_ECARTS_DOCUMENTAIRES.md`, `H_ANOMALIES_47.md`, et le détail d'origine `I_CONTRADICTIONS_ET_MANQUES.md`, `F_QUESTIONS_RESIDUELLES.md`, `D_PLAN_CORRECTION.md`.

## Conventions

- **Une décision PO** a un identifiant `DEC-…`, une source, un statut. Une **proposition technique** est `PT-…`, une **règle technique évidente** `RT-…`, une **contradiction** `CT-…`, une **information manquante** `IM-…`, une **question** `F-…`, un **test** `T-…`.
- Preuve de code : `fichier:ligne` sur `1c37f22`. `[V]` relu pour ce dossier ; `[A]` constat de l'audit, non rejoué ; `[N]` Notion.
- « Absent » = non trouvé par recherche dans `1c37f22`, pas preuve d'absence.
- Rien dans ce dossier ne modifie Notion, `main` ni le code.
