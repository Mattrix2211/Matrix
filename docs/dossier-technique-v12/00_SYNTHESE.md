# Synthèse du dossier technique Matrix V1.2

**Statut** : phase d'analyse et de préparation. Aucun code applicatif modifié, aucune migration, aucune PR, `main` intacte, Notion non modifié. **Base** : V1.1 `1c37f22` (audit `4aa4dcf`). **Les 47 anomalies** ont été confrontées au code, aux décisions du dépôt, à Notion et à vos deux messages.

## 1. Ce que contient le dossier

| Pièce | Contenu |
|---|---|
| `A_REGISTRE_DECISIONS.md` + `A1_DECISIONS_S1_S2.md` | 120 décisions de vos messages (une par entrée), 14 DP et blocs A à D avec leur sort, 26 décisions Notion, 14 propositions techniques, 7 règles techniques |
| `B_CARTOGRAPHIE.md` | 22 modules, acteurs, périmètres, 13 circuits de validation, dépendances |
| `C_MATRICE_TRACABILITE.md` | décision → code → anomalie → test, et inversement |
| `D_PLAN_CORRECTION.md` | 9 étapes (0 à 8), lots, dépendances, priorités P0 à P3 |
| `E_STRATEGIE_TESTS.md` + `E2_CATALOGUE_TESTS.md` | principes, scénarios par rôle, 113 tests d'acceptation |
| `F_QUESTIONS_RESIDUELLES.md` | 14 arbitrages réellement nécessaires, avec recommandation et conséquences |
| `G_ECARTS_DOCUMENTAIRES.md` | ce qui manque pour le manuel de référence |
| `H_ANOMALIES_47.md` | les 47 fiches, 10 rubriques chacune |
| `I_CONTRADICTIONS_ET_MANQUES.md` | 12 contradictions réelles, levées, 15 informations manquantes, erratum |

## 2. Résultat sur les 47 anomalies

| Classe | Nombre |
|---|---|
| Anomalie confirmée | 32 |
| Déjà corrigée (AUD-001, AUD-026, dans la V1.1) | 2 |
| À reproduire (hypothèses d'audit non établies : AUD-013, 022, 025, 030) | 4 |
| Fonctionnement conforme (AUD-040, report volontaire) | 1 |
| Écart fonctionnel non couvert (AUD-012, 036, 038, 046) | 4 |
| Décision PO manquante (AUD-006, 037, 041, 042) | 4 |

Priorités proposées : **P0 : 8** (AUD-009, 010, 017, 020, 021, 028, 031, 034) · **P1 : 9** · **P2 : 14** · **P3 : 16**. Les deux P0 de l'audit **sont toujours présents** : `seed_demo` réécrit des mots de passe (`seed_demo.py:92-95`), et les suppressions de service, secteur et section sont immédiates (`matrix/views.py:643-673`).

## 3. Vos décisions : où en est le code (120 décisions S1/S2)

| État dans la V1.1 | Décisions |
|---|---|
| Existe | 21 |
| Partiel | 34 |
| Absent | 42 |
| Non vérifié | 23 |

Les absences majeures concernent des fonctions que vous avez décidées et que le code n'a pas : trois niveaux de priorité (il n'y en a que deux), validation facultative et statut « À valider », coordinateur de tâche collective (le grade est un texte libre, sans ordre), « Non réalisée — À reprogrammer », durée actualisée, remarques d'outillage, mutation de personnel, transfert de matériel, suppléance générale, circuit RETEX hiérarchique, préparation à l'appareillage complète.

## 4. Ce que l'erratum corrige

Plusieurs points que j'avais présentés comme ouverts étaient déjà tranchés par vous (RETEX, rattachement incomplet, sections facultatives, validation sans suppléance, départ, passation, QR, appareillage). Ils sont traités comme décisions dans le registre (`I_CONTRADICTIONS_ET_MANQUES.md`, I.4). Une précision utile : **B3 n'est tranchée que pour la feuille de service**, pas pour les listes de quarts.

## 5. Les contradictions qui restent réelles

1. **Échanges de tours** : décision finale du COMAEQ (vous) ↔ chef de liste habilité (tâche Notion plus ancienne) — CT-01.
2. **Listes de quarts/gardes** : vos règles ne couvrent que la feuille de service — CT-04.
3. **Suppléance générale** ↔ « pas de nouveau système de délégation en V1 » : phasage à confirmer — CT-02.
4. **Qualifications** : pas de blocage pour les tâches, mais non tranché pour les échanges et les visas du suppléant — CT-03.
5. **Appareillage** : vos règles détaillées ↔ cadrages Notion « ne pas développer » — CT-05.

## 6. Les 14 questions qui restent (F)

Les plus importantes : **F-01** (ordre de mise en œuvre des droits par fonction), **F-02** (listes et échanges), **F-06** (suppléance et qualifications), **F-07** (qui qualifie un contrôle d'« obligatoire » ou de « critique »), **F-10** (structure du bord). Aucune ne bloque l'étape 1 (P0) du plan. Chaque question a une recommandation ; sans réponse, les lots concernés attendent.

## 7. Votre hypothèse statistique

La méthode de durée (médiane des 5 dernières réalisations valides, écart à la médiane au-delà de 3·MAD écarté, 3 mesures minimum, historique conservé, correction manuelle prioritaire) est enregistrée comme **proposition technique PT-DUR-01 à 07, non validée**. Elle ne sera vérifiée qu'avec des temps réels.

## 8. Limites

- Je n'ai pas rejoué les sondes ni les tests de l'audit : seuls les points marqués `[V]` ont été relus dans le code.
- Je n'ai pas lu toutes les pages Notion (voir `G_ECARTS_DOCUMENTAIRES.md`, G.3) ni le *Guide du marin 2023*.
- « Absent » signifie « non trouvé par recherche textuelle dans `1c37f22` ».
- Le dossier est sur ma branche, issue de `main` ; les chemins de fichiers cités se lisent sur `1c37f22`.

## 9. Proposition de suite

1. Relire et corriger ce dossier (surtout A1 et F).
2. Répondre aux questions F-01, F-02, F-06, F-07 (les autres ont une recommandation par défaut).
3. Autoriser explicitement l'étape 0 (base de développement) puis l'étape 1 (P0). **Rien ne commence sans votre accord.**
