# Synthèse du dossier technique Matrix V1.2 (mise à jour du 10/11/2026)

**Statut** : phase d'analyse et de préparation. Aucun code applicatif modifié, aucune migration, aucune PR, `main` intacte, Notion non modifié. **Base** : V1.1 `1c37f22` (audit `4aa4dcf`). Sources : dépôt, audit, Notion, messages S1, S2, S3 du PO.

## 1. Pièces du dossier (17 fichiers)

| Pièce | Contenu |
|---|---|
| `README.md`, `00_SYNTHESE.md` | Entrée et synthèse |
| `A_REGISTRE_DECISIONS.md`, `A1_DECISIONS_S1_S2.md` | 125 décisions des messages du PO (S1 à S4), DP, blocs A à D, décisions Notion, propositions techniques |
| `B_CARTOGRAPHIE.md` | Modules, acteurs, périmètres, 13 circuits |
| `C_MATRICE_TRACABILITE.md` | Décision → code → anomalie → test |
| `D_PLAN_CORRECTION.md` | Premier plan par étapes (remplacé pour l'ordonnancement par M) |
| `E_STRATEGIE_TESTS.md`, `E2_CATALOGUE_TESTS.md` | Stratégie et 117 tests d'acceptation |
| `F_QUESTIONS_RESIDUELLES.md`, `I_CONTRADICTIONS_ET_MANQUES.md` | Détail d'origine des questions et contradictions |
| **`J_TRIAGE_ET_ARBITRAGES.md`** | **Triage résolu / contradiction / technique / reportable, et les 2 contradictions restantes** |
| **`K_PRIORITES_JUSTIFIEES.md`** | **Priorités P0 à P3 justifiées une par une** |
| **`L_SOURCES_NON_CONSULTEES.md`** | **Sources lues, non lues, impact** |
| **`M_PLAN_DEVELOPPEMENT.md`** | **28 lots avec anomalies, décisions, fichiers, dépendances, migrations, risques, tests, acceptation** |
| `G_ECARTS_DOCUMENTAIRES.md`, `H_ANOMALIES_47.md` | Manuel futur ; 47 fiches |

## 2. Correction d'une erreur de ma première version

J'avais écrit que `seed_demo` « réécrit des mots de passe ». **C'est faux** : `set_password` n'est appelé qu'à la création du compte (`seed_demo.py:92-95`, `if cree:`). Le risque réel est double : la commande crée 61 comptes à mot de passe connu, dont un superutilisateur `admin`/`admin`, et elle **écrase le profil** (rôle, bâtiment, service, secteur, section, équipage, fonction) d'un compte existant portant le même nom. AUD-009 reste P0, avec ce libellé corrigé dans `H_ANOMALIES_47.md`.

## 3. Résultat sur les 47 anomalies

| Classe | Nombre |
|---|---|
| Anomalie confirmée | 32 |
| Déjà corrigée en V1.1 (AUD-001, 026) | 2 |
| À reproduire (AUD-013, 022, 025, 030) | 4 |
| Fonctionnement conforme (AUD-040) | 1 |
| Écart non couvert par l'audit (AUD-012, 036, 038, 046) | 4 |
| Décision PO manquante (AUD-006, 037, 041, 042) | 4 |

## 4. Priorités (révisées)

**P0 : 3** (AUD-009, 020, 034) · **P1 : 7** (AUD-001, 011, 014, 015, 019, 028, 031) · **P2 : 18** · **P3 : 19**. Ma proposition de 8 P0 est **retirée** : AUD-010, 017, 021 retournent à P2, AUD-028 et AUD-031 à P1. Seuls 5 reclassements par rapport à l'audit subsistent (AUD-034 P1→P0, AUD-028 P2→P1, AUD-045 et AUD-047 P3→P2, AUD-006 P2→P3). Une fonctionnalité absente n'est jamais P0. Justifications : `K_PRIORITES_JUSTIFIEES.md`.

## 5. Contradictions et questions

Après triage (`J_TRIAGE_ET_ARBITRAGES.md`) : sur 12 contradictions, 15 informations manquantes et 14 questions, **2 contradictions** restaient : elles sont **tranchées par le PO** (S4, DEC-FDS-14 et DEC-APP-14). Reste une vérification de compatibilité du circuit d'appareillage avec les procédures du bord, non faisable ici, et **1 dépendance externe** (architecture bord–terre).

| ID | Sujet | Recommandation |
|---|---|---|
| **C-1** | Qui publie les listes de quarts et de gardes ? | Le chef de liste prépare ; le COMAEQ ou son suppléant approuve et publie (même logique que la feuille et les échanges) |
| **C-2** | Qui définit qu'un contrôle d'appareillage est « obligatoire » ou « critique » ? | Je ne l'invente pas : à préciser parmi les fonctions existantes. Par défaut, aucun contrôle n'est obligatoire ni critique tant qu'une fiche approuvée ne le déclare |
| Dépendance | Architecture bord–terre pour la mutation | Lot L25 reporté ; réservé aux SIC |

Résolues par vos précisions du 10/11 : échanges (COMAEQ ou suppléant décide, BSC ou chef de liste instruit), qualifications (aucun blocage pour les tâches ordinaires ; exigences réglementaires respectées pour visas, fonctions de service, signatures officielles), suppléance (question de calendrier, non annulation), sections facultatives, droits par fonction, circuit RETEX, appareillage. **Les notes Notion plus anciennes** (échanges du 28/10, « pas de délégation en V1 », « veille d'appareillage : ne pas développer ») **ne prévalent pas** (`J` §2).

## 6. Sources

Lues en plus : échanges de garde, mutation, prêt à appareiller, veille d'appareillage, rattachement obligatoire, `seed_demo`, dette accounts. **Non lues et pouvant compter** : Organigramme 02 (qualifications, grades), 03 (brevets), 07 (SIC), 11 (modèle de données). Le *Guide du marin 2023* n'était pas disponible et n'a pas été vérifié. Détail : `L_SOURCES_NON_CONSULTEES.md`.

## 7. Plan de développement

28 lots en 5 phases (`M_PLAN_DEVELOPPEMENT.md`) : risques critiques (L01 à L05), autorisations (L06 à L13, L21), circuits de tâches (L14 à L18), maintenance, appareillage et feuille de service, puis ergonomie, mutation et dette.

## 8. Premier lot recommandé : L01 — verrou des commandes de démonstration (AUD-009)

Seul risque critique sans dépendance, entièrement spécifié (P06, 10 tests), sans effet sur les équipiers. Deux confirmations à donner (valeurs par défaut proposées) : mots de passe de démonstration (P06 : conservés derrière le garde ; Notion 28/10 : « non prévisibles ou saisis »), et migration additive d'une ligne pour le marqueur de base.

## 9. Limites

Seuls les points `[V]` de `H_ANOMALIES_47.md` ont été relus dans le code ; aucun test ni sonde rejoués. « Absent » signifie « non trouvé ». Les chemins de fichiers se lisent sur `1c37f22`.
