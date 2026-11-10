# H. Les 47 anomalies de l'audit confrontées au code V1.1

Chaque fiche reprend les 10 rubriques demandées. **Vérification** : `[V]` = relu dans le code `1c37f22` pour ce dossier ; `[A]` = constat de l'audit, exécuté par lui et non rejoué ici ; `[N]` = page Notion. Aucune hypothèse n'est présentée comme une preuve : quand je n'ai pas pu vérifier, c'est écrit. **Priorité** : échelle du dossier (P0 sécurité et intégrité des données ; P1 dysfonctionnements métier et autorisations ; P2 ergonomie et amélioration des processus ; P3 évolutions non essentielles et documentation). La criticité d'origine de l'audit est rappelée quand elle diffère.

## Répartition

| Classe | Nombre |
|---|---|
| Déjà corrigée | 2 |
| Anomalie confirmée | 32 |
| Décision PO manquante | 4 |
| Écart fonctionnel non couvert par l'audit | 4 |
| À reproduire | 4 |
| Fonctionnement conforme | 1 |

| Priorité | Nombre |
|---|---|
| P0 | 8 |
| P1 | 9 |
| P2 | 14 |
| P3 | 16 |

## Vue d'ensemble

| ID | Classe | Priorité | Audit | Intitulé |
|---|---|---|---|---|
| AUD-001 | Déjà corrigée | P1 | P1 | Création de feuille de service ouverte à tout marin du bâtiment (sur `main`). |
| AUD-002 | Anomalie confirmée | P2 | P2 | Aucune intégration continue (pas de `.github`). |
| AUD-003 | Anomalie confirmée | P2 | P2 | Parcours navigateur cités comme preuve absents du dépôt. |
| AUD-004 | Anomalie confirmée | P3 | P3 | Sources de vérité non alignées (baseline Notion du 10/10 sur `dfd6a3c`, `main` à `6ef16ad`, V1.1 à `1c37f22`). |
| AUD-005 | Anomalie confirmée | P3 | P3 | `CLAUDE.md` présente `RoleLevel` / `RolePermission` comme points d'extension. |
| AUD-006 | Décision PO manquante | P3 | P2 | Décisions contradictoires sur la synthèse de passation. |
| AUD-007 | Anomalie confirmée | P3 | P3 | Résidu de Rondes : `rondes/models.py` et migrations sans test. |
| AUD-008 | Anomalie confirmée | P2 | P2 | Carte « À faire » : bouton « Ouvrir » vers une page introuvable (ticket assigné à un chef). |
| AUD-009 | Anomalie confirmée | P0 | P0 | Commandes `seed_demo*` : comptes à mots de passe connus, sans garde-fou. |
| AUD-010 | Anomalie confirmée | P0 | P2 | Mot de passe PostgreSQL par défaut faible (`matrix`). |
| AUD-011 | Anomalie confirmée | P1 | P1 | HTTPS : reverse proxy TLS non supporté tel que livré ; serveur d'application non déclaré. |
| AUD-012 | Écart fonctionnel non couvert par l'audit | P2 | P2 | Pas d'import en masse du personnel. |
| AUD-013 | À reproduire | P3 | P3 | Rapport de bilan : 1,2 à 1,3 s en médiane. |
| AUD-014 | Anomalie confirmée | P1 | P1 | Visas intermédiaires de la feuille de service attribués par niveau hiérarchique. |
| AUD-015 | Anomalie confirmée | P1 | P1 | Modification directe de listes publiées par commandant et administrateurs. |
| AUD-016 | Anomalie confirmée | P2 | P3 | Liens ou boutons affichés à des profils sans droit. |
| AUD-017 | Anomalie confirmée | P0 | P2 | Clé secrète d'exemple (`change-me`) acceptée en production. |
| AUD-018 | Anomalie confirmée | P3 | P3 | Même titre d'onglet `Matrix` partout. |
| AUD-019 | Anomalie confirmée | P1 | P1 | Structure du bord non modifiable de façon autonome (écran réservé flotte, API admin d'unité). |
| AUD-020 | Anomalie confirmée | P0 | P0 | Suppression de section, secteur, service : marins détachés, cascade destructrice. |
| AUD-021 | Anomalie confirmée | P0 | P2 | Erreur 500 (ProtectedError) à la suppression d'un secteur/service portant du matériel. |
| AUD-022 | À reproduire | P2 | P2 | 55 comparaisons de niveau en dur contre 71 appels à des seuils configurables. |
| AUD-023 | Anomalie confirmée | P2 | P2 | Maintenance non conforme sur installation : ni ticket ni alerte ; message trompeur. |
| AUD-024 | Anomalie confirmée | P2 | P2 | Noms réels de bâtiments dans la démonstration. |
| AUD-025 | À reproduire | P3 | P3 | Flux calendrier par défaut contenant les quarts d'autres marins. |
| AUD-026 | Déjà corrigée | P3 | P3 | 404 à la reprise d'un brouillon de signalement d'anomalie. |
| AUD-027 | Anomalie confirmée | P3 | P3 | Reprise d'un brouillon de compte rendu dont l'occurrence a disparu : page introuvable. |
| AUD-028 | Anomalie confirmée | P0 | P2 | L'archivage d'un bâtiment, service, secteur, section n'a aucun effet. |
| AUD-029 | Anomalie confirmée | P3 | P3 | Fonctions de complexité excessive (jusqu'à 101). |
| AUD-030 | À reproduire | P2 | P2 | Modules documentation, RETEX, postes, programme peu testés. |
| AUD-031 | Anomalie confirmée | P0 | P1 | Aucune procédure de sauvegarde et de restauration. |
| AUD-032 | Anomalie confirmée | P2 | P2 | Sans Redis/Celery, aucune alerte automatique ni signalement. |
| AUD-033 | Anomalie confirmée | P2 | P2 | Double envoi de « ajouter un créneau » : deux créneaux identiques. |
| AUD-034 | Anomalie confirmée | P0 | P1 | Suppression physique de compte : tâches, difficultés, traçabilité détruites. |
| AUD-035 | Anomalie confirmée | P1 | P2 | Aucune limitation des tentatives de connexion. |
| AUD-036 | Écart fonctionnel non couvert par l'audit | P3 | P3 | Démonstration sans de nombreux états et cas limites. |
| AUD-037 | Décision PO manquante | P2 | P3 | Installation : service ET secteur obligatoires. |
| AUD-038 | Écart fonctionnel non couvert par l'audit | P3 | P3 | Notifications à deux états seulement ; pas d'archivage. |
| AUD-039 | Anomalie confirmée | P3 | P3 | Rappels évalués à la lecture des pages, sans tâche planifiée. |
| AUD-040 | Fonctionnement conforme | P3 | P3 | Prêts, retours, inventaires de matériel absents. |
| AUD-041 | Décision PO manquante | P3 | P3 | Niveaux d'annonce « Information / Important / Urgent » au lieu de « Critique ». |
| AUD-042 | Décision PO manquante | P3 | P3 | Deux écarts d'interface des quarts, décision UX ouverte. |
| AUD-043 | Anomalie confirmée | P2 | P2 | Ticket correctif : sauts de statut libres, état du matériel inchangé. |
| AUD-044 | Anomalie confirmée | P1 | P2 | Réaffectation d'une installation sans circuit, notification, trace ni contrôle de filiation. |
| AUD-045 | Anomalie confirmée | P1 | P3 | RETEX : « COMA référent » = simple tri ; tout habilité valide. |
| AUD-046 | Écart fonctionnel non couvert par l'audit | P2 | P3 | Composition-type d'une fraction à quai absente ; poste en texte libre. |
| AUD-047 | Anomalie confirmée | P1 | P3 | Prêt à appareiller signé avec points non vérifiés. |

## AUD-001 — Création de feuille de service ouverte à tout marin du bâtiment (sur `main`).

1. **Identifiant** : AUD-001
2. **Description** : Création de feuille de service ouverte à tout marin du bâtiment (sur `main`).
3. **État vérifié dans le code actuel** : **Déjà corrigée.** [V] En V1.1, `peut_rediger_feuille_service` exige une désignation `RedacteurFeuilleService` par bâtiment et équipage (quarts/models.py:2065-2073) ; `peut_designer_redacteurs` : COMAEQ de l'équipage, à bord comme à terre (:2076-2086). Corrige aussi l'écart « équipage à terre » relevé par la relecture du 01/11. Toujours présent sur `main` (6ef16ad).
4. **Décision PO applicable** : DEC-FDS-01, DEC-FDS-11, DEC-FDS-12, DEC-DRT-02
5. **Risque** : Création de feuilles par un matelot si `main` est déployée sans la V1.1.
6. **Correction attendue** : Aucune dans la V1.1. Reste : fusion de la V1.1 (décision DP-01 du PO) ; désignation initiale d'un BSC (fail closed).
7. **Modules concernés** : quarts (models, feuille_service_views, réglages)
8. **Dépendances** : Décision de fusion V1.1 → `main`
9. **Tests d'acceptation** : T-FDS-01 T-FDS-02 T-FDS-10 T-FDS-11 T-REG-03
10. **Priorité proposée** : P1

## AUD-002 — Aucune intégration continue (pas de `.github`).

1. **Identifiant** : AUD-002
2. **Description** : Aucune intégration continue (pas de `.github`).
3. **État vérifié dans le code actuel** : **Anomalie confirmée.** [V] Aucun répertoire `.github` ni configuration CI à la racine de 1c37f22.
4. **Décision PO applicable** : DP-07 (ouverte : CI compatible hors Internet)
5. **Risque** : Régressions non détectées avant fusion.
6. **Correction attendue** : Script local obligatoire ou serveur interne ; tests SQLite + PostgreSQL sans déploiement.
7. **Modules concernés** : racine, scripts/
8. **Dépendances** : Décision DP-07 (F-14)
9. **Tests d'acceptation** : T-REG-01 T-REG-02
10. **Priorité proposée** : P2

## AUD-003 — Parcours navigateur cités comme preuve absents du dépôt.

1. **Identifiant** : AUD-003
2. **Description** : Parcours navigateur cités comme preuve absents du dépôt.
3. **État vérifié dans le code actuel** : **Anomalie confirmée.** [V] Aucun fichier de scénario navigateur versionné trouvé (recherche par nom, partielle) ; [A] constat complet.
4. **Décision PO applicable** : DP-08 (ouverte)
5. **Risque** : Preuves non rejouables.
6. **Correction attendue** : Versionner les scripts dans un dossier dédié.
7. **Modules concernés** : tests navigateur
8. **Dépendances** : DP-08 (F-14)
9. **Tests d'acceptation** : T-REG-03
10. **Priorité proposée** : P2

## AUD-004 — Sources de vérité non alignées (baseline Notion du 10/10 sur `dfd6a3c`, `main` à `6ef16ad`, V1.1 à `1c37f22`).

1. **Identifiant** : AUD-004
2. **Description** : Sources de vérité non alignées (baseline Notion du 10/10 sur `dfd6a3c`, `main` à `6ef16ad`, V1.1 à `1c37f22`).
3. **État vérifié dans le code actuel** : **Anomalie confirmée.** [N] Cahier et Feuille de route citent `dfd6a3c` ; la page « Cap UX » cite `6ef16ad`. Pages lues le 2026-11.
4. **Décision PO applicable** : DP-04 (ouverte)
5. **Risque** : Décisions prises sur une base obsolète.
6. **Correction attendue** : Mettre à jour Notion (par le PO ou après son accord) ; ne pas le faire dans ce dossier.
7. **Modules concernés** : Notion
8. **Dépendances** : —
9. **Tests d'acceptation** : —
10. **Priorité proposée** : P3

## AUD-005 — `CLAUDE.md` présente `RoleLevel` / `RolePermission` comme points d'extension.

1. **Identifiant** : AUD-005
2. **Description** : `CLAUDE.md` présente `RoleLevel` / `RolePermission` comme points d'extension.
3. **État vérifié dans le code actuel** : **Anomalie confirmée.** [V] `RolePermission` est une classe DRF `BasePermission` (matrix/core/permissions.py:9) ; `RoleLevel` est une énumération (matrix/core/roles.py).
4. **Décision PO applicable** : —
5. **Risque** : Ambiguïté pour les développeurs ; risque de créer un système parallèle.
6. **Correction attendue** : Corriger la formulation de CLAUDE.md après accord du PO.
7. **Modules concernés** : CLAUDE.md
8. **Dépendances** : —
9. **Tests d'acceptation** : —
10. **Priorité proposée** : P3

## AUD-006 — Décisions contradictoires sur la synthèse de passation.

1. **Identifiant** : AUD-006
2. **Description** : Décisions contradictoires sur la synthèse de passation.
3. **État vérifié dans le code actuel** : **Décision PO manquante.** [N] N3 (recette V1) : « maintenue en V1, configurable, activée par défaut » ; Cahier : passation automatique différée. [V] code de synthèse présent (org/models.py, matrix/core/equipage.py).
4. **Décision PO applicable** : DEC-PRE-02, DP-02
5. **Risque** : Aucun risque technique ; confusion documentaire.
6. **Correction attendue** : Pas de nouveau module ; conserver et documenter la synthèse existante ; aligner Notion.
7. **Modules concernés** : org, matrix/core/equipage
8. **Dépendances** : DP-04
9. **Tests d'acceptation** : T-REG-03
10. **Priorité proposée** : P3 (audit : P2)

## AUD-007 — Résidu de Rondes : `rondes/models.py` et migrations sans test.

1. **Identifiant** : AUD-007
2. **Description** : Résidu de Rondes : `rondes/models.py` et migrations sans test.
3. **État vérifié dans le code actuel** : **Anomalie confirmée.** [V] `rondes/` contient `models.py`, `migrations/`, `apps.py` ; aucune route dans `matrix/urls.py` ; [A] test de retrait `matrix/tests/test_module_rondes_retire.py`. [N] N5 : « supprimer Rondes ; préserver données et migrations tant qu'aucune suppression physique n'est autorisée ».
4. **Décision PO applicable** : DP-05 (levée par N5)
5. **Risque** : Code mort conservé volontairement.
6. **Correction attendue** : Conserver tant qu'aucune suppression physique n'est autorisée ; documenter.
7. **Modules concernés** : rondes
8. **Dépendances** : —
9. **Tests d'acceptation** : —
10. **Priorité proposée** : P3

## AUD-008 — Carte « À faire » : bouton « Ouvrir » vers une page introuvable (ticket assigné à un chef).

1. **Identifiant** : AUD-008
2. **Description** : Carte « À faire » : bouton « Ouvrir » vers une page introuvable (ticket assigné à un chef).
3. **État vérifié dans le code actuel** : **Anomalie confirmée.** [A] Classe de défaut confirmée ; dépend du jeu de données. Le commit 46d2dca (main) touche les cartes « À faire » à terre ; son effet sur ce défaut n'est pas vérifié.
4. **Décision PO applicable** : DEC-UX-07
5. **Risque** : Bouton inactif, perte de confiance.
6. **Correction attendue** : Dériver le masquage des liens de la règle serveur.
7. **Modules concernés** : dashboard, logistics
8. **Dépendances** : —
9. **Tests d'acceptation** : T-UX-06
10. **Priorité proposée** : P2

## AUD-009 — Commandes `seed_demo*` : comptes à mots de passe connus, sans garde-fou.

1. **Identifiant** : AUD-009
2. **Description** : Commandes `seed_demo*` : comptes à mots de passe connus, sans garde-fou.
3. **État vérifié dans le code actuel** : **Anomalie confirmée.** [V] `seed_demo.py:92-95` : `get_or_create` puis `set_password` sur des comptes existants ; aucune référence à `DEBUG` ni à une variable d'activation ; 4 commandes concernées (`seed_demo`, `_dense`, `_mer_quai`, `_metier`).
4. **Décision PO applicable** : DEC-PRE-06, DP-01 ; proposition P06
5. **Risque** : Compromission de comptes administrateurs, écrasement de mots de passe réels.
6. **Correction attendue** : Refus par défaut, variable d'activation explicite, marqueur de base de démonstration, test automatique (P06).
7. **Modules concernés** : matrix/core/management/commands/seed_demo*
8. **Dépendances** : Aucune
9. **Tests d'acceptation** : T-SEC-01 T-SEC-02 T-SEC-03 T-SEC-04
10. **Priorité proposée** : P0

## AUD-010 — Mot de passe PostgreSQL par défaut faible (`matrix`).

1. **Identifiant** : AUD-010
2. **Description** : Mot de passe PostgreSQL par défaut faible (`matrix`).
3. **État vérifié dans le code actuel** : **Anomalie confirmée.** [V] `matrix/settings.py:186` : `env.get("DB_PASSWORD", "matrix")`.
4. **Décision PO applicable** : —
5. **Risque** : Accès base si DB_HOST défini sans mot de passe.
6. **Correction attendue** : Exiger `DB_PASSWORD` dès que `DB_HOST` est défini hors DEBUG.
7. **Modules concernés** : matrix/settings.py
8. **Dépendances** : —
9. **Tests d'acceptation** : T-SEC-06
10. **Priorité proposée** : P0 (audit : P2)

## AUD-011 — HTTPS : reverse proxy TLS non supporté tel que livré ; serveur d'application non déclaré.

1. **Identifiant** : AUD-011
2. **Description** : HTTPS : reverse proxy TLS non supporté tel que livré ; serveur d'application non déclaré.
3. **État vérifié dans le code actuel** : **Anomalie confirmée.** [V] `SECURE_SSL_REDIRECT = not DEBUG` (settings.py:410) ; aucune occurrence de `SECURE_PROXY_SSL_HEADER`.
4. **Décision PO applicable** : DP-10, DEC-PRE-06, P03
5. **Risque** : Boucle de redirection ou HTTPS inopérant derrière un proxy.
6. **Correction attendue** : Réglages pilotables par variables ; installation de référence testée ; validation SIC.
7. **Modules concernés** : matrix/settings.py, docs
8. **Dépendances** : Experts SIC (C2, C3)
9. **Tests d'acceptation** : T-REG-03
10. **Priorité proposée** : P1

## AUD-012 — Pas d'import en masse du personnel.

1. **Identifiant** : AUD-012
2. **Description** : Pas d'import en masse du personnel.
3. **État vérifié dans le code actuel** : **Écart fonctionnel non couvert par l'audit.** [V] Aucune commande ni vue d'import trouvée (recherche textuelle).
4. **Décision PO applicable** : DP-11 (besoin confirmé)
5. **Risque** : Mise en service lente et risque de saisie erronée.
6. **Correction attendue** : Import avec prévisualisation, doublons, validation des rattachements, rapport.
7. **Modules concernés** : accounts, org
8. **Dépendances** : Rattachement obligatoire (DEC-DRT-06)
9. **Tests d'acceptation** : —
10. **Priorité proposée** : P2

## AUD-013 — Rapport de bilan : 1,2 à 1,3 s en médiane.

1. **Identifiant** : AUD-013
2. **Description** : Rapport de bilan : 1,2 à 1,3 s en médiane.
3. **État vérifié dans le code actuel** : **À reproduire.** [A] Mesure de l'audit ; pas un défaut établi.
4. **Décision PO applicable** : DEC-PRE-03
5. **Risque** : Risque seulement hypothétique sur gros volumes.
6. **Correction attendue** : Mesurer sur base volumineuse avant toute optimisation ; PDF en tâche de fond si nécessaire.
7. **Modules concernés** : reports
8. **Dépendances** : —
9. **Tests d'acceptation** : T-REG-05
10. **Priorité proposée** : P3

## AUD-014 — Visas intermédiaires de la feuille de service attribués par niveau hiérarchique.

1. **Identifiant** : AUD-014
2. **Description** : Visas intermédiaires de la feuille de service attribués par niveau hiérarchique.
3. **État vérifié dans le code actuel** : **Anomalie confirmée.** [V] `NIVEAU_SUPERVISION_GLOBALE_FEUILLE_SERVICE = RoleLevel.COMMANDANT` (quarts/models.py:1015, 1974) ; [A] détail des visas.
4. **Décision PO applicable** : DEC-DRT-01, DEC-DRT-02, DEC-FDS-02, DP-09
5. **Risque** : Visa donné sans la fonction réelle.
6. **Correction attendue** : Droits par fonction avec suppléances et exclusion de l'administrateur technique (P02).
7. **Modules concernés** : quarts
8. **Dépendances** : DEC-SUP-* ; F-01
9. **Tests d'acceptation** : T-DRT-01 T-FDS-03 T-FDS-04 T-FDS-11
10. **Priorité proposée** : P1

## AUD-015 — Modification directe de listes publiées par commandant et administrateurs.

1. **Identifiant** : AUD-015
2. **Description** : Modification directe de listes publiées par commandant et administrateurs.
3. **État vérifié dans le code actuel** : **Anomalie confirmée.** [V] Seuils de niveau `NIVEAU_SUPERVISION_GLOBALE_LISTE = COMMANDANT` (quarts/models.py:147, 270) ; [A] ajout de créneau rejoué.
4. **Décision PO applicable** : DEC-DRT-02, DP-09, B3 (résiduel)
5. **Risque** : Altération d'une liste publiée sans circuit.
6. **Correction attendue** : Proposition → validation → publication ; fermeture des voies directes (tâches Notion D-05 A à D).
7. **Modules concernés** : quarts (listes)
8. **Dépendances** : F-01, F-02
9. **Tests d'acceptation** : T-DRT-01 T-FDS-05
10. **Priorité proposée** : P1

## AUD-016 — Liens ou boutons affichés à des profils sans droit.

1. **Identifiant** : AUD-016
2. **Description** : Liens ou boutons affichés à des profils sans droit.
3. **État vérifié dans le code actuel** : **Anomalie confirmée.** [A] Confirmé par l'audit (navigation, brouillons).
4. **Décision PO applicable** : DEC-UX-07
5. **Risque** : Frustration, tentatives d'accès refusées.
6. **Correction attendue** : Masquage dérivé de la règle serveur.
7. **Modules concernés** : navigation, gabarits
8. **Dépendances** : —
9. **Tests d'acceptation** : T-UX-06
10. **Priorité proposée** : P2 (audit : P3)

## AUD-017 — Clé secrète d'exemple (`change-me`) acceptée en production.

1. **Identifiant** : AUD-017
2. **Description** : Clé secrète d'exemple (`change-me`) acceptée en production.
3. **État vérifié dans le code actuel** : **Anomalie confirmée.** [V] `.env.example:2` = `change-me` ; `settings.py:53` ne refuse que `_CLE_SECRETE_DEV_PAR_DEFAUT`.
4. **Décision PO applicable** : —
5. **Risque** : Sessions et jetons falsifiables.
6. **Correction attendue** : Refuser aussi les valeurs d'exemple connues et les clés trop courtes.
7. **Modules concernés** : matrix/settings.py
8. **Dépendances** : —
9. **Tests d'acceptation** : T-SEC-05
10. **Priorité proposée** : P0 (audit : P2)

## AUD-018 — Même titre d'onglet `Matrix` partout.

1. **Identifiant** : AUD-018
2. **Description** : Même titre d'onglet `Matrix` partout.
3. **État vérifié dans le code actuel** : **Anomalie confirmée.** [V] `base.html:11` : `<title>Matrix</title>` sans bloc.
4. **Décision PO applicable** : —
5. **Risque** : Accessibilité et repérage.
6. **Correction attendue** : Bloc `title` surchargeable.
7. **Modules concernés** : matrix/templates
8. **Dépendances** : —
9. **Tests d'acceptation** : T-UX-06
10. **Priorité proposée** : P3

## AUD-019 — Structure du bord non modifiable de façon autonome (écran réservé flotte, API admin d'unité).

1. **Identifiant** : AUD-019
2. **Description** : Structure du bord non modifiable de façon autonome (écran réservé flotte, API admin d'unité).
3. **État vérifié dans le code actuel** : **Anomalie confirmée.** [V] `matrix/views.py:268-290` : écran réservé à `MASTER_ADMIN` / branches `ADMIN_NAVIRE` ; [A] détail.
4. **Décision PO applicable** : DEC-ORG-02, DP-13, A2, A3
5. **Risque** : Un bord ne peut pas s'organiser seul.
6. **Correction attendue** : Écran de structure habilité (renommer, archiver, réactiver) tenu par une fonction désignée (P04).
7. **Modules concernés** : matrix/views.py, org
8. **Dépendances** : F-10 ; DEC-DRT-05
9. **Tests d'acceptation** : T-ORG-06
10. **Priorité proposée** : P1

## AUD-020 — Suppression de section, secteur, service : marins détachés, cascade destructrice.

1. **Identifiant** : AUD-020
2. **Description** : Suppression de section, secteur, service : marins détachés, cascade destructrice.
3. **État vérifié dans le code actuel** : **Anomalie confirmée.** [V] `matrix/views.py:643, 658, 673` : `.delete()` immédiat ; aucune confirmation serveur ; journalisation après coup seulement.
4. **Décision PO applicable** : DEC-DRT-05, DP-13 ; proposition P07
5. **Risque** : Perte de listes, annonces, documents ; élargissement d'accès.
6. **Correction attendue** : Plus de suppression physique avec historique ; archivage effectif ; message clair (P07).
7. **Modules concernés** : matrix/views.py, org
8. **Dépendances** : Archivage effectif (AUD-028)
9. **Tests d'acceptation** : T-ORG-01 T-ORG-02
10. **Priorité proposée** : P0

## AUD-021 — Erreur 500 (ProtectedError) à la suppression d'un secteur/service portant du matériel.

1. **Identifiant** : AUD-021
2. **Description** : Erreur 500 (ProtectedError) à la suppression d'un secteur/service portant du matériel.
3. **État vérifié dans le code actuel** : **Anomalie confirmée.** [V] `ProtectedError` n'est capturée que pour grades/spécialités (matrix/views.py:748, 760), pas pour service/secteur/section.
4. **Décision PO applicable** : DEC-DRT-05
5. **Risque** : Page d'erreur, état incertain.
6. **Correction attendue** : Traité avec AUD-020 : message explicite.
7. **Modules concernés** : matrix/views.py
8. **Dépendances** : AUD-020
9. **Tests d'acceptation** : T-ORG-03
10. **Priorité proposée** : P0 (audit : P2)

## AUD-022 — 55 comparaisons de niveau en dur contre 71 appels à des seuils configurables.

1. **Identifiant** : AUD-022
2. **Description** : 55 comparaisons de niveau en dur contre 71 appels à des seuils configurables.
3. **État vérifié dans le code actuel** : **À reproduire.** [A] Hypothèse d'audit ; classement proposé (P05) non validé par le PO.
4. **Décision PO applicable** : DEC-ORG-06, DEC-DRT-01
5. **Risque** : Droits incohérents d'un module à l'autre.
6. **Correction attendue** : Revue au cas par cas (P05) : plancher ou règle métier.
7. **Modules concernés** : droits (code)
8. **Dépendances** : F-01
9. **Tests d'acceptation** : T-DRT-04
10. **Priorité proposée** : P2

## AUD-023 — Maintenance non conforme sur installation : ni ticket ni alerte ; message trompeur.

1. **Identifiant** : AUD-023
2. **Description** : Maintenance non conforme sur installation : ni ticket ni alerte ; message trompeur.
3. **État vérifié dans le code actuel** : **Anomalie confirmée.** [V] `maintenance/_execute_done.html:4` : « Un ticket correctif sera (ou a été) ouvert automatiquement. »
4. **Décision PO applicable** : —
5. **Risque** : Défaut non suivi, fausse assurance.
6. **Correction attendue** : Corriger le message maintenant ; alerte au chef de secteur (DEC-ANO-04).
7. **Modules concernés** : maintenance
8. **Dépendances** : F-12
9. **Tests d'acceptation** : T-ANO-03
10. **Priorité proposée** : P2

## AUD-024 — Noms réels de bâtiments dans la démonstration.

1. **Identifiant** : AUD-024
2. **Description** : Noms réels de bâtiments dans la démonstration.
3. **État vérifié dans le code actuel** : **Anomalie confirmée.** [V] `seed_demo.py:157, 214` : « Bretagne », « Normandie ».
4. **Décision PO applicable** : DP-01
5. **Risque** : Confusion avec des données réelles.
6. **Correction attendue** : Noms fictifs.
7. **Modules concernés** : seed_demo*
8. **Dépendances** : AUD-009
9. **Tests d'acceptation** : T-SEC-03
10. **Priorité proposée** : P2

## AUD-025 — Flux calendrier par défaut contenant les quarts d'autres marins.

1. **Identifiant** : AUD-025
2. **Description** : Flux calendrier par défaut contenant les quarts d'autres marins.
3. **État vérifié dans le code actuel** : **À reproduire.** [A] Hypothèse non vérifiée en navigateur. [N] Tâche Notion « Mon quotidien d'abord, vue collective séparée ».
4. **Décision PO applicable** : DEC-UX-11, DEC-DRT-04
5. **Risque** : Fuite d'information entre marins.
6. **Correction attendue** : Vue personnelle par défaut ; vue collective séparée.
7. **Modules concernés** : calendar_app
8. **Dépendances** : —
9. **Tests d'acceptation** : T-UX-08 T-DRT-03
10. **Priorité proposée** : P3

## AUD-026 — 404 à la reprise d'un brouillon de signalement d'anomalie.

1. **Identifiant** : AUD-026
2. **Description** : 404 à la reprise d'un brouillon de signalement d'anomalie.
3. **État vérifié dans le code actuel** : **Déjà corrigée.** [A] Non reproduit sur 1c37f22, présent sur `main`. [N] N5 A2 : cause = lien enregistré par le jeu de démonstration.
4. **Décision PO applicable** : DEC-UX-07
5. **Risque** : Perte de confiance.
6. **Correction attendue** : Aucune ; fusion de la V1.1.
7. **Modules concernés** : brouillons
8. **Dépendances** : Fusion V1.1
9. **Tests d'acceptation** : T-UX-06
10. **Priorité proposée** : P3

## AUD-027 — Reprise d'un brouillon de compte rendu dont l'occurrence a disparu : page introuvable.

1. **Identifiant** : AUD-027
2. **Description** : Reprise d'un brouillon de compte rendu dont l'occurrence a disparu : page introuvable.
3. **État vérifié dans le code actuel** : **Anomalie confirmée.** [A] Confirmé (réponse 400).
4. **Décision PO applicable** : DEC-UX-07
5. **Risque** : Brouillon inutilisable.
6. **Correction attendue** : Message explicite et conservation du texte.
7. **Modules concernés** : brouillons
8. **Dépendances** : —
9. **Tests d'acceptation** : T-UX-06
10. **Priorité proposée** : P3

## AUD-028 — L'archivage d'un bâtiment, service, secteur, section n'a aucun effet.

1. **Identifiant** : AUD-028
2. **Description** : L'archivage d'un bâtiment, service, secteur, section n'a aucun effet.
3. **État vérifié dans le code actuel** : **Anomalie confirmée.** [V] Champs `archived` présents (org/models.py:49,168,180,191) ; 6 usages de `archived=False` ou `archived__` hors tests (recherche textuelle, non exhaustive).
4. **Décision PO applicable** : DEC-DRT-05, DP-13
5. **Risque** : L'archivage ne remplace pas la suppression.
6. **Correction attendue** : Effet réel : masquage des sélecteurs, historique conservé, réactivation.
7. **Modules concernés** : org
8. **Dépendances** : —
9. **Tests d'acceptation** : T-ORG-02
10. **Priorité proposée** : P0 (audit : P2)

## AUD-029 — Fonctions de complexité excessive (jusqu'à 101).

1. **Identifiant** : AUD-029
2. **Description** : Fonctions de complexité excessive (jusqu'à 101).
3. **État vérifié dans le code actuel** : **Anomalie confirmée.** [A] Mesure de l'audit.
4. **Décision PO applicable** : —
5. **Risque** : Risque de régression à chaque correction.
6. **Correction attendue** : Découpage progressif, lié aux chantiers de droits et de structure.
7. **Modules concernés** : matrix/views.py, assets/asset_views.py
8. **Dépendances** : —
9. **Tests d'acceptation** : T-REG-01
10. **Priorité proposée** : P3

## AUD-030 — Modules documentation, RETEX, postes, programme peu testés.

1. **Identifiant** : AUD-030
2. **Description** : Modules documentation, RETEX, postes, programme peu testés.
3. **État vérifié dans le code actuel** : **À reproduire.** [A] Inventaire de l'audit : documentation 9 tests, RETEX 5, postes 7, programme 10 (02_INVENTAIRE_FONCTIONNEL.md) ; volume seulement, aucune mesure de couverture.
4. **Décision PO applicable** : —
5. **Risque** : Régressions silencieuses.
6. **Correction attendue** : Mesurer la couverture réelle, puis écrire les tests des circuits RETEX et appareillage.
7. **Modules concernés** : documentation, retex, postes, programme
8. **Dépendances** : —
9. **Tests d'acceptation** : T-RTX-01 T-RTX-05
10. **Priorité proposée** : P2

## AUD-031 — Aucune procédure de sauvegarde et de restauration.

1. **Identifiant** : AUD-031
2. **Description** : Aucune procédure de sauvegarde et de restauration.
3. **État vérifié dans le code actuel** : **Anomalie confirmée.** [V] Aucune occurrence de « sauvegarde » dans README.md et docs/*.md.
4. **Décision PO applicable** : DEC-PRE-06
5. **Risque** : Perte de données irréversible.
6. **Correction attendue** : Procédure écrite et testée, validée par l'exploitant et les SIC.
7. **Modules concernés** : docs, exploitation
8. **Dépendances** : Experts SIC (C4)
9. **Tests d'acceptation** : T-REG-04
10. **Priorité proposée** : P0 (audit : P1)

## AUD-032 — Sans Redis/Celery, aucune alerte automatique ni signalement.

1. **Identifiant** : AUD-032
2. **Description** : Sans Redis/Celery, aucune alerte automatique ni signalement.
3. **État vérifié dans le code actuel** : **Anomalie confirmée.** [V] `CELERY_BROKER_URL` redis par défaut (settings.py:243) ; [A] absence de supervision.
4. **Décision PO applicable** : DEC-BLQ-05
5. **Risque** : Alertes et états de fin de journée non produits.
6. **Correction attendue** : Supervision visible ; évaluer à la lecture en secours (PT-TAC-01).
7. **Modules concernés** : matrix/celery.py, notifications
8. **Dépendances** : —
9. **Tests d'acceptation** : T-TAC-14
10. **Priorité proposée** : P2

## AUD-033 — Double envoi de « ajouter un créneau » : deux créneaux identiques.

1. **Identifiant** : AUD-033
2. **Description** : Double envoi de « ajouter un créneau » : deux créneaux identiques.
3. **État vérifié dans le code actuel** : **Anomalie confirmée.** [V] `_ajouter_creneau` (quarts/listes_views.py:862-885) : aucune garde contre le doublon dans la lecture effectuée ; [A] rejeu confirmé.
4. **Décision PO applicable** : DEC-FDS-05
5. **Risque** : Doublons sur liste publiée.
6. **Correction attendue** : Garde d'idempotence (clé d'unicité ou jeton) avec D-06.
7. **Modules concernés** : quarts
8. **Dépendances** : D-06 (Notion)
9. **Tests d'acceptation** : T-FDS-05
10. **Priorité proposée** : P2

## AUD-034 — Suppression physique de compte : tâches, difficultés, traçabilité détruites.

1. **Identifiant** : AUD-034
2. **Description** : Suppression physique de compte : tâches, difficultés, traçabilité détruites.
3. **État vérifié dans le code actuel** : **Anomalie confirmée.** [V] `bulk_delete_users` : `users.delete()` (accounts/web_views.py:349-357) ; `Tache.assigne` en CASCADE.
4. **Décision PO applicable** : DEC-MUT-07, DEC-MUT-06, DEC-DRT-05 ; proposition P07
5. **Risque** : Perte d'historique et de responsabilité.
6. **Correction attendue** : Désactivation par défaut ; suppression réservée aux comptes sans historique ; tâches réattribuées ou non affectées.
7. **Modules concernés** : accounts, taches
8. **Dépendances** : F-05
9. **Tests d'acceptation** : T-CPT-01 T-CPT-02 T-CPT-03 T-CPT-09
10. **Priorité proposée** : P0 (audit : P1)

## AUD-035 — Aucune limitation des tentatives de connexion.

1. **Identifiant** : AUD-035
2. **Description** : Aucune limitation des tentatives de connexion.
3. **État vérifié dans le code actuel** : **Anomalie confirmée.** [V] Aucune occurrence de verrouillage / limitation dans matrix, accounts ; [A] 25 échecs rejoués.
4. **Décision PO applicable** : C5 (ouverte)
5. **Risque** : Attaque par force brute.
6. **Correction attendue** : Délai croissant configurable et journalisé, à valider avec les SIC.
7. **Modules concernés** : accounts, settings
8. **Dépendances** : Experts SIC
9. **Tests d'acceptation** : T-SEC-07
10. **Priorité proposée** : P1 (audit : P2)

## AUD-036 — Démonstration sans de nombreux états et cas limites.

1. **Identifiant** : AUD-036
2. **Description** : Démonstration sans de nombreux états et cas limites.
3. **État vérifié dans le code actuel** : **Écart fonctionnel non couvert par l'audit.** [A] 13 scénarios manquants.
4. **Décision PO applicable** : DP-01
5. **Risque** : Recette incomplète.
6. **Correction attendue** : Compléter après les corrections qui changent les états ; GO du PO.
7. **Modules concernés** : seed_demo*
8. **Dépendances** : Après AUD-009 et lots tâches
9. **Tests d'acceptation** : T-REG-03
10. **Priorité proposée** : P3

## AUD-037 — Installation : service ET secteur obligatoires.

1. **Identifiant** : AUD-037
2. **Description** : Installation : service ET secteur obligatoires.
3. **État vérifié dans le code actuel** : **Décision PO manquante.** [V] `assets/models.py:266-267` : FK `service` et `sector` non nulles, PROTECT.
4. **Décision PO applicable** : DEC-ORG-03, DEC-ORG-02
5. **Risque** : Bâtiments à deux niveaux non représentables.
6. **Correction attendue** : Décision PO (F-03).
7. **Modules concernés** : assets
8. **Dépendances** : F-03
9. **Tests d'acceptation** : T-ORG-07
10. **Priorité proposée** : P2 (audit : P3)

## AUD-038 — Notifications à deux états seulement ; pas d'archivage.

1. **Identifiant** : AUD-038
2. **Description** : Notifications à deux états seulement ; pas d'archivage.
3. **État vérifié dans le code actuel** : **Écart fonctionnel non couvert par l'audit.** [V] `is_read` et alertes « à action » (notifications/models.py:32-38). [N] N5 C : lues retirées du flux court, conservées dans le centre.
4. **Décision PO applicable** : DEC-UX-06
5. **Risque** : Centre qui grossit sans fin.
6. **Correction attendue** : Rétention / archivage à spécifier.
7. **Modules concernés** : notifications
8. **Dépendances** : —
9. **Tests d'acceptation** : T-UX-05
10. **Priorité proposée** : P3

## AUD-039 — Rappels évalués à la lecture des pages, sans tâche planifiée.

1. **Identifiant** : AUD-039
2. **Description** : Rappels évalués à la lecture des pages, sans tâche planifiée.
3. **État vérifié dans le code actuel** : **Anomalie confirmée.** [A] Documentation (ANO-013).
4. **Décision PO applicable** : DEC-BLQ-05
5. **Risque** : Rappels manquants hors navigation.
6. **Correction attendue** : Tâche planifiée supervisée (AUD-032).
7. **Modules concernés** : notifications
8. **Dépendances** : AUD-032
9. **Tests d'acceptation** : T-TAC-14
10. **Priorité proposée** : P3

## AUD-040 — Prêts, retours, inventaires de matériel absents.

1. **Identifiant** : AUD-040
2. **Description** : Prêts, retours, inventaires de matériel absents.
3. **État vérifié dans le code actuel** : **Fonctionnement conforme.** [N] Tâche Notion « À faire plus tard » : report volontaire.
4. **Décision PO applicable** : —
5. **Risque** : Aucun.
6. **Correction attendue** : Aucune (différé).
7. **Modules concernés** : logistics
8. **Dépendances** : —
9. **Tests d'acceptation** : —
10. **Priorité proposée** : P3

## AUD-041 — Niveaux d'annonce « Information / Important / Urgent » au lieu de « Critique ».

1. **Identifiant** : AUD-041
2. **Description** : Niveaux d'annonce « Information / Important / Urgent » au lieu de « Critique ».
3. **État vérifié dans le code actuel** : **Décision PO manquante.** [V] `NotificationLevel` : INFO « Information », WARNING « Important », DANGER « Urgent » (notifications/models.py:15-17). [N] Cahier §19 : « Critique ».
4. **Décision PO applicable** : —
5. **Risque** : Vocabulaire incohérent avec le cahier.
6. **Correction attendue** : Décision écrite (F-08).
7. **Modules concernés** : annonces, notifications
8. **Dépendances** : F-08
9. **Tests d'acceptation** : T-UX-06
10. **Priorité proposée** : P3

## AUD-042 — Deux écarts d'interface des quarts, décision UX ouverte.

1. **Identifiant** : AUD-042
2. **Description** : Deux écarts d'interface des quarts, décision UX ouverte.
3. **État vérifié dans le code actuel** : **Décision PO manquante.** [A] Confirmé en navigateur.
4. **Décision PO applicable** : DEC-UX-05
5. **Risque** : Parcours indirect.
6. **Correction attendue** : Décision UX.
7. **Modules concernés** : quarts
8. **Dépendances** : —
9. **Tests d'acceptation** : T-UX-04
10. **Priorité proposée** : P3

## AUD-043 — Ticket correctif : sauts de statut libres, état du matériel inchangé.

1. **Identifiant** : AUD-043
2. **Description** : Ticket correctif : sauts de statut libres, état du matériel inchangé.
3. **État vérifié dans le code actuel** : **Anomalie confirmée.** [V] Seules les confirmations à `RETURNED_TO_SERVICE` et `CLOSED` sont contrôlées (logistics/views.py:49-105) ; statuts arbitraires acceptés selon l'audit.
4. **Décision PO applicable** : DEC-ANO-01, DEC-ANO-03
5. **Risque** : Tickets incohérents, matériel jamais remis en état.
6. **Correction attendue** : Rejeter les statuts inconnus maintenant ; transitions après décision (F-04).
7. **Modules concernés** : logistics
8. **Dépendances** : F-04
9. **Tests d'acceptation** : T-ANO-04
10. **Priorité proposée** : P2

## AUD-044 — Réaffectation d'une installation sans circuit, notification, trace ni contrôle de filiation.

1. **Identifiant** : AUD-044
2. **Description** : Réaffectation d'une installation sans circuit, notification, trace ni contrôle de filiation.
3. **État vérifié dans le code actuel** : **Anomalie confirmée.** [V] Aucune fonction ni vue de transfert trouvée (recherche textuelle dans assets).
4. **Décision PO applicable** : DEC-MAT-01, DEC-MAT-02, DEC-MAT-03, DEC-MAT-04
5. **Risque** : Matériel déplacé sans accord ni trace.
6. **Correction attendue** : Circuit de transfert (deux chefs de service), application par l'administrateur habilité, tâches suivent le matériel, trace avant/après.
7. **Modules concernés** : assets
8. **Dépendances** : DEC-DRT-02 ; F-03
9. **Tests d'acceptation** : T-MAT-01 T-MAT-02 T-MAT-03 T-MAT-04 T-MAT-05
10. **Priorité proposée** : P1 (audit : P2)

## AUD-045 — RETEX : « COMA référent » = simple tri ; tout habilité valide.

1. **Identifiant** : AUD-045
2. **Description** : RETEX : « COMA référent » = simple tri ; tout habilité valide.
3. **État vérifié dans le code actuel** : **Anomalie confirmée.** [V] `peut_valider` : niveau d'écriture ≥ seuil (retex/services.py:46-51) ; `valideurs` ne fait que classer (:54-58).
4. **Décision PO applicable** : DEC-RTX-01, DEC-RTX-03
5. **Risque** : Validation hors circuit.
6. **Correction attendue** : Circuit auteur → section → secteur → service, versions et motifs.
7. **Modules concernés** : retex
8. **Dépendances** : DEC-SUP-*
9. **Tests d'acceptation** : T-RTX-01 T-RTX-02 T-RTX-05
10. **Priorité proposée** : P1 (audit : P3)

## AUD-046 — Composition-type d'une fraction à quai absente ; poste en texte libre.

1. **Identifiant** : AUD-046
2. **Description** : Composition-type d'une fraction à quai absente ; poste en texte libre.
3. **État vérifié dans le code actuel** : **Écart fonctionnel non couvert par l'audit.** [V] `CreneauServiceGarde.poste` = `CharField` (quarts/models.py:743). [N] Exemple BRF livré sur la recette (N5).
4. **Décision PO applicable** : DEC-FDS-08, DEC-FDS-09
5. **Risque** : Vacances de poste non vues.
6. **Correction attendue** : Composition paramétrable par bâtiment, signalement à la publication.
7. **Modules concernés** : quarts, postes
8. **Dépendances** : F-13
9. **Tests d'acceptation** : T-FDS-08 T-FDS-09
10. **Priorité proposée** : P2 (audit : P3)

## AUD-047 — Prêt à appareiller signé avec points non vérifiés.

1. **Identifiant** : AUD-047
2. **Description** : Prêt à appareiller signé avec points non vérifiés.
3. **État vérifié dans le code actuel** : **Anomalie confirmée.** [V] `SessionAppareillage` : un seul `valide_par` (dashboard/models.py:18+). Aucune génération depuis les fiches de référence trouvée.
4. **Décision PO applicable** : DEC-APP-01 à DEC-APP-13
5. **Risque** : Signature d'un appareillage incomplet.
6. **Correction attendue** : Contrôles issus des fiches, circuit à trois niveaux, réserves et points non dérogeables, versions.
7. **Modules concernés** : dashboard (appareillage), assets
8. **Dépendances** : F-07 ; fiches de référence
9. **Tests d'acceptation** : T-APP-01 à T-APP-09
10. **Priorité proposée** : P1 (audit : P3)
