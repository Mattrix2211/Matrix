# L. Vérification des sources

Objet : dire précisément ce qui a été lu, ce qui ne l'a pas été, et ce qui pourrait modifier une décision importante. Je n'ai pas cherché à lire tout Notion.

## L.1 Pages Notion lues (cumul)

| Page | Usage |
|---|---|
| Cahier des charges (Matrix 2.0) | Principes, modules, phases |
| Organigramme et rôles | Hiérarchie, fiches, circuits, organismes à terre |
| 13 — Décisions Matrix et gouvernance fonctionnelle | Décisions validées, recette V1, double équipage |
| 06 — Service courant, BSC, feuille de service | BSC, COMAEQ, fraction, quarts, tableaux |
| Feuille de Route | État et phases |
| Cap UX/UI « Naval Premium » | Cap UX, aide progressive |
| Ordre de travail du 01/11 (+ compte rendu) | A1, A2, B1, B2, C, relecture |
| Audit métier Matrix × Guide du marin 2023 | M-01 à M-11 (synthèse Notion du guide) |
| Tâches (base) : liste complète des tâches ouvertes | Statuts et titres |
| **Lues pour cette mise à jour** : Échanges de garde (28/10) ; Mutation (02/10) ; Prêt à appareiller (06/10) ; Veille d'appareillage (20/10) ; Rattachement obligatoire (28/10) ; Priorité sécurité `seed_demo` (28/10) ; Dette « accounts » (27/10) ; commandants en second (commentaires) | Remplacent ou confirment des décisions (voir `J_TRIAGE_ET_ARBITRAGES.md`) |

## L.2 Pages non consultées pouvant modifier une décision importante

| Page | Pourquoi elle pourrait compter | Décisions concernées | Impact potentiel | Faut-il la lire avant le développement ? |
|---|---|---|---|---|
| Organigramme 02 — RH, postes, qualifications et disponibilité | Définit probablement postes, qualifications, grades/brevets et disponibilité | DEC-ORG-04, DEC-ORG-05, DEC-QUA-*, DEC-COL-02, IM-01, IM-02 | **Élevé** pour la distinction brevets / grades / fonctions et l'ordre des grades | **Oui, avant L16 et L18** |
| Organigramme 03 — Formation, stages, CFPES, FPS | Liste des formations et brevets (FEM, BE, BAT, BS, BST, BHT, C-CDM) | DEC-ORG-05, IM-01 | Moyen : alimente le référentiel, pas le code | Oui, avant L18 |
| Organigramme 07 — SIC, cyber, protection-défense, conformité | Exigences de sécurité des systèmes d'information | AUD-011, 031, 035 ; DEC-PRE-06 | Moyen : peut imposer des contraintes de déploiement et de journalisation | Oui, avant L21 (avec les SIC) |
| Organigramme 11 — Modèle de données cible | Cible de modélisation de l'organisation, des postes, des qualifications | DEC-ORG-02, DEC-ORG-03, F-03, F-10, L12 | Moyen : peut orienter les migrations de structure | Oui, avant L12 |
| Tâche « Recette V1 — F4 et F7 » | Détail des droits du commandement à terre et du commandant en second | DEC-DRT-01, NOT-08, NOT-09 | Faible pour les premiers lots | Avant L06/L09 |
| Page « Recette UX V1.1 » | Retours du PO et des marins sur l'accueil et les tours de service | DEC-UX-*, CT-06 | Faible, ergonomie | Avant L24 |
| Tâche « [CADRAGE UX] Corrections UX ciblées » | Corrections UX à valider | DEC-UX-* | Faible | Avant L24 |
| Organigramme 01, 04, 05, 08, 09, 10, 12 ; Vision et Objectifs ; Tranche 1 | Contexte général | — | Faible pour ce dossier | Non |

**Aucune de ces pages ne devrait remettre en cause L01 à L05** (sécurité et intégrité). Les lots dépendants sont signalés ci-dessus.

## L.3 Guide du marin 2023

**Source non disponible.** Je n'ai jamais eu le document. Je ne cite que les références de pages que reprend la page Notion « Audit métier », sans les avoir vérifiées. Le dossier ne s'appuie sur le guide pour aucune décision.

## L.4 Brevets, grades, fonctions : trois notions distinctes

Les décisions restent séparées dans le registre :

| Notion | Décisions | Remarque |
|---|---|---|
| **Grade** | DEC-ORG-04 (distinction), DEC-COL-02 à 04 (grade le plus élevé pour proposer le coordinateur ; **seul usage du grade** dans le dossier) | Aucun droit métier ne découle du grade seul (DEC-DRT-01) |
| **Fonction exercée** | DEC-DRT-01, DEC-FDS-02, DEC-SUP-01, DEC-FDS-01 (BSC), NOT-01, NOT-21 | Les droits viennent de la fonction et du périmètre |
| **Brevets, formations, habilitations** | DEC-ORG-05, DEC-QUA-01 à 04, DEC-SUP-06 | Jamais bloquants pour une tâche ordinaire ; exigences réglementaires respectées pour visas, fonctions de service, signatures officielles |

## L.5 Limites restantes

- Les pages Notion portent l'état « non vérifié » : leur contenu est celui que vous avez saisi ou validé, mais aucune vérification ne l'atteste.
- Les comptes rendus de développement et « relectures indépendantes » dans Notion ne sont pas des recettes du PO ; ils ne sont pas traités comme des décisions.
- Les affirmations sur le code restent celles de `H_ANOMALIES_47.md` : `[V]` relu, `[A]` audit.
