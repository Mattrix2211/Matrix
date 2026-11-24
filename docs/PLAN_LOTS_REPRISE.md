# Plan des lots de reprise du développement (après les arbitrages du 24/11/2026)

> **DOCUMENT PROVISOIRE — DIFFUSION RESTREINTE.** Plan **proposé**, non validé : aucun développement ne commence sans l'accord explicite du PO. Il réutilise le découpage L01 à L28 du registre (`registre.json`, section `lots`) et n'ajoute que les lots que les arbitrages rendent nécessaires. Décisions : `docs/DECISIONS_PO.md`.

## 1. Point de départ

- **Livrés sur l'état B** : L01 (verrou démo), L05 (configuration de production), L02 (archivage), L03 (suppression sûre) ; correctif administrateur `44e7129` (branche `claude/securite-admin-identifiants-v11`, non fusionné). Tests : suites complètes SQLite et PostgreSQL vertes sur `6d6d0be` ; ciblés sur `44e7129`.
- **Non lancés et touchés par les arbitrages** : L06, L07, L08, L09, L10, L24, L27 (voir §4).
- **Inchangés** : L11 à L23, L25 à L28, restent dans le backlog sans modification.
- Ne pas attribuer à un commit les résultats d'un autre : chaque lot est qualifié sur son propre candidat.

## 2. Principe directeur : un seul contrôle d'habilitation

Cinq arbitrages (01, 02, 03, 06, 04) reposent sur la même question : « cette personne peut-elle lire ou écrire cet objet, maintenant, par ce point d'entrée ? ». Aujourd'hui les contrôles sont dispersés (`matrix/core/ecriture_service.py` pour une partie des écritures, `scopes.py` pour la lecture, des tests de niveau dans les vues, le middleware pour les pages, rien pour l'API et les tâches). Plutôt que d'ajouter des contrôles spécifiques par module :

1. **Étendre l'existant** (`ecriture_service`, `scope_filters_for_user`, `RolePermission`, `role_thresholds`) sans créer de système parallèle ; une seule fonction d'entrée par question (lire / écrire / valider) qui tient compte de la fonction, du périmètre, de la suppléance ou délégation active, de l'équipage, de l'état du module et d'un plancher non contournable.
2. **Prouver l'application par l'exécution** (lot L29) : un inventaire automatique des routes (pages, API, administration) et des tâches échoue si une entrée n'est pas déclarée, **et** une matrice exécutée appelle réellement les accès sensibles (lectures, écritures, API, administration, traitements internes) avec des profils types et compare le résultat obtenu au résultat attendu. Une classification des routes seule ne prouverait pas que les autorisations s'appliquent ; c'est la matrice exécutée qui garantit le « même résultat quel que soit le point d'entrée ».
3. **Journaliser au même endroit** : un refus, une attribution, une délégation, un changement de désignation passent par la même trace (`AuditLog`).

## 3. Ordre de réalisation proposé

| Vague | Lot | Nature | Complexité | Migration | Dépend de | Recette intermédiaire possible |
|---|---|---|---|---|---|---|
| 0 | **L24-Q** Ergonomie quarts et tours (ARB-08) | Ergonomie | S | non | rien ; parallèle à L29 sous condition (§3 bis) | oui (poste et iPhone) |
| 0 | **L36-a** Rondes : inventaire et retrait du code résiduel (ARB-09) | Nettoyage | S | non | rien | non-régression |
| 1 | **L29** Socle d'habilitation et preuve d'application des autorisations (ARB-01) | Bloquant | M à L | non | rien | non-régression et preuve par exécution (pas de changement fonctionnel voulu) |
| 1 | **L06** Administrateur technique sans autorité métier, seuils planchers, second (ARB-01) | Bloquant | L | **oui** | L29 | oui (comptes et droits) |
| 1 | **L30** Confidentialité des passations (ARB-02) | Bloquant | M | probable (partage ciblé) | L29 | oui (passation par profil) |
| 1 | **L34** Désactivation complète des modules (ARB-03) — remontée après L30, voir §3 bis | Bloquant | M à L | probable (dépendances) | L29 (techniquement ni L06 ni L30) | oui |
| 2 | **L08** Délégations et suppléance explicites (ARB-06, `DEC-SUP-*`) | Fonctionnel | L | **oui** | L29, L06 | oui |
| 2 | **L32** Écriture bornée au périmètre dans tous les modules et par l'API (ARB-06) | Bloquant | L | non | L29 (L08 pour les délégations) | oui |
| 2 | **L10** Échanges de garde décidés par le COMAEQ (ARB-04) | Fonctionnel | M | possible | L08, L29 | oui |
| 2 | **L33** BSC : suppléant habilité et recours (ARB-05) | Fonctionnel | S | non | L08 | oui |
| 3 | **L35** Notifications : classification configurable et règles « jamais repliées » (`D7-NOT`, ARB-07) | Fonctionnel | M | **oui** (configuration) | L34 recommandé | oui |
| 4 | **L36-b** Rondes : suppression des données et des tables (ARB-09) | Nettoyage | M | **oui, destructive** | L36-a, sauvegarde, **autorisation distincte** | non-régression |

**Justification de l'ordre.**
- Sécurité et confidentialité d'abord (vague 1) : A1 et A14 sont les deux écarts les plus exposés ; ils bloquent tout déploiement avec des données réelles.
- Le socle L29 précède tout : sinon chaque lot réinvente un contrôle et les divergences que le PO veut éviter reviennent.
- L06 avant L08 : on sépare administrateur et autorité métier avant d'introduire des délégations, sinon une délégation pourrait être attribuée par un administrateur.
- L10 après L08 : le circuit COMAEQ exige suppléant et délégation.
- La vague 0 ne dépend de rien : elle peut précéder ou accompagner L29 et donne rapidement une recette utilisateur (ergonomie) et un nettoyage sans risque.
- L36-b en dernier : seul lot destructif ; sauvegarde et **autorisation distincte** préalables, jamais déduite de l'accord sur le plan.
- Chaque vague se clôt par une recette intermédiaire (§6) avant la suivante.

Les corrections **bloquantes** (L29, L06, L30, L32, L34) conditionnent tout usage opérationnel ; les **fonctionnelles** (L08, L10, L33, L35) alignent le comportement sur les arbitrages ; l'**ergonomie** (L24-Q) et le **nettoyage** (L36) n'ont pas d'incidence sur la sécurité.

## 3 bis. Études demandées par le PO (24/11/2026)

### L34 remonté immédiatement après L06 et L30
- **Dépendances techniques réelles.** L34 s'appuie sur le contrôle commun de L29 (l'état du module devient une dimension du contrôle, au même titre que le périmètre). Il **ne dépend techniquement ni de L06 ni de L30** : l'état d'un module est indépendant de la séparation administrateur/autorité métier et de la confidentialité des passations. Le placer après L06 et L30 est donc possible, et le placer plus tôt aussi ; la contrainte est L29 seulement.
- **Recouvrements.** (a) L30 et L34 touchent tous deux `dashboard/` (passation d'un côté, blocs d'accueil de l'autre) : séquencer plutôt que paralléliser. (b) L34 ferme l'API ; L32 borne aussi l'API : L32 doit **réutiliser** le point de contrôle de L34/L29 et non en ajouter un second. (c) La table de dépendances entre modules (livrable de L34) alimente L35.
- **Conséquences du déplacement.** L08, L32, L10 et L33 sont décalés après L34 ; l'exposition A25 est traitée avant les délégations. Le coût est un décalage des lots fonctionnels, sans conflit de dépendance. L35 gagne à suivre L34.
- **Ordre retenu dans ce plan** : L29 → L06 → L30 → **L34** → L08 → L32 → L10 → L33 → L35 → L36-b ; **ajustable** si le PO préfère placer L34 avant L06 ou L30.
- **Point de vigilance.** L34 est large (web, API, accueil, calendrier, notifications, Celery) : il se découpe en deux tranches recettables (a : lecture et navigation, accueil, calendrier, recherche ; b : API, notifications, tâches automatiques, dépendances), si une seule livraison s'avère trop risquée.

### L24-Q en parallèle de L29 : indépendance à démontrer
Fichiers prévus pour L24-Q : `matrix/core/navigation.py` (libellé du menu), `matrix/templates/quarts/*` et `quarts/web_views.py` (vues journalière et mensuelle), `calendar_app` (vue mensuelle), l'assistant de signalement d'anomalie (bandeau, `matrix/static/js/brouillon.js`), `accounts/preferences.py` et la vue d'enregistrement des préférences (`accounts/web_views.py`). Fichiers de L29 : `matrix/core/` (contrôle commun), un registre déclaratif des routes, des tests.
- **Indépendance démontrée au niveau des fichiers** : aucun fichier commun, à une condition. **Condition :** L29 déclare le contrôle dans un registre central et ne modifie pas les vues (pas de décorateur ajouté dans `quarts/web_views.py` ni `calendar_app`). Si L29 devait intervenir dans ces vues, les deux lots sont **séquencés** (L24-Q avant ou après).
- **Autres conflits possibles** : `accounts/` (L06 modifie `UserProfile`, donc après L24-Q si la préférence passe par le même fichier) ; `quarts/web_views.py` (L10 plus tard). L24-Q ne comporte pas de migration, donc aucune collision de numérotation.
- **Garde-fous** : branches distinctes, test de non-régression des routes de L29 rejoué sur la branche de L24-Q avant intégration, une préférence d'affichage n'est jamais un contrôle d'accès.

## 4. Fiches de lots

Conditions de clôture communes : tests positifs et négatifs du lot verts sur SQLite **et** PostgreSQL ; tests des apps touchées verts ; relecture indépendante ; mise à jour de `docs/DECISIONS_PO.md`, de `docs/REFERENCE.md` et du registre d'anomalies ; recette intermédiaire du PO ; suite complète exécutée **une fois**, sur le candidat final à l'intégration, pas à chaque lot. Aucun résultat d'un commit n'est reporté sur un autre.

### L29 — Socle d'habilitation et preuve d'application des autorisations
- **Statut (24/11/2026) : réalisé sur la branche `claude/l29-socle-habilitation-v11`, en attente de la validation du PO.** Preuves : `docs/recette/L29_CARTOGRAPHIE_ET_PREUVES.md`.
- **Objectif et périmètre.** Un contrôle commun lecture / écriture / validation par fonction, désignation, périmètre, équipage, état du module et plancher ; un registre déclaratif des points d'entrée ; une **preuve par exécution** que les autorisations s'appliquent réellement. Aucun changement fonctionnel voulu : c'est une réorganisation de contrôles de sécurité, donc **pas un lot à risque faible**.
- **Décisions.** ARB-01 (règles 2, 7, 9), préalable de ARB-02, 03, 04, 06.
- **Composants.** `matrix/core/ecriture_service.py`, `scopes.py`, `roles.py`, `role_thresholds.py`, `matrix/core/middleware.py`, routes web, API et administration, tâches Celery et services internes ; inventaire des routes (annexes C1 à C3 du dossier de reprise).
- **Complexité.** M à L. **Migration.** Aucune.
- **Risques réels.** (1) Une réorganisation peut **élargir** un droit (faille silencieuse) ou le **restreindre** (régression bloquante) sans qu'aucun test existant ne le voie ; (2) les contrôles actuels sont dispersés et parfois incohérents entre web et API : les unifier révèle des divergences à arbitrer, pas à trancher en silence ; (3) coût en requêtes (services rattachés recalculés) ; (4) faux sentiment de sécurité si le test ne vérifie que des étiquettes ; (5) liste d'exemptions qui grossit sans justification.
- **La classification ne prouve rien.** Classer une route « contrôlée » n'établit pas que le contrôle s'applique. Le test doit **exécuter** les accès.
- **Critères.** CA-L29-1 : toute route (web, API, administration) est inventoriée ; toute route d'écriture ou de lecture sensible est contrôlée ou exemptée avec justification écrite. CA-L29-2 : une route ajoutée sans inventaire fait échouer la suite. CA-L29-3 : pour chaque route sensible, le résultat par profil est celui attendu **à l'exécution**. CA-L29-4 : les divergences web/API trouvées sont listées, non corrigées en silence. CA-L29-5 : suites existantes inchangées.
- **Preuve par exécution (conception du test).** Trois niveaux, chacun exigible :
  1. *Inventaire* : énumération automatique des routes web, API, administration et des tâches planifiées ; échec si une entrée n'est pas déclarée.
  2. *Matrice exécutée* : pour chaque route sensible (**lectures sensibles** — passations, absences et motifs, dossiers, tableaux de bord, exports, recherche —, **écritures**, **API**, **administration Django**), appel réel avec des profils types : anonyme ; marin ; chef du périmètre ; chef hors périmètre ; autre bâtiment ; équipage à terre ; administrateur technique seul ; module désactivé ; délégation expirée. Résultat attendu déclaré pour chaque couple, comparé au résultat réel (code de retour et absence de fuite dans le contenu).
  3. *Traitements internes pertinents* : tâches Celery, signaux et services appelés sans requête (génération de notifications, d'occurrences, de listes) : vérifier qu'ils respectent périmètre, équipage et état du module, et qu'ils ne créent pas de donnée hors périmètre ; les appels inter-modules légitimes sont listés explicitement.
  Jeu de données minimal : deux bâtiments, deux équipages, deux services voisins, un module désactivé.
- **Tests.** T-L29-1 inventaire web ; T-L29-2 inventaire API et administration ; T-L29-3 inventaire des tâches et traitements internes ; T-L29-4 matrice exécutée sur les lectures sensibles ; T-L29-5 matrice exécutée sur les écritures web et API ; T-L29-6 administration Django (droits de modèle, actions groupées) ; T-L29-7 traitements internes ; T-L29-8 test négatif de contrôle du test (une route volontairement non protégée dans le jeu d'essai doit être détectée) ; T-L29-9 non-régression des apps touchées, SQLite et PostgreSQL.
- **Clôture.** Rapport des divergences découvertes, soumis au PO avant L06 : chacune est classée corrigée par L29, reportée vers un lot nommé, ou exemptée avec justification.

### L06 — Administrateur technique sans autorité métier
- **Objectif et périmètre.** Séparer l'administration technique de l'échelle métier ; interdire l'auto-attribution ; planchers non abaissables ; prérogatives du commandant en second ; traces.
- **Décisions.** ARB-01 ; A1, A3, A4, B2.
- **Composants.** `accounts.UserProfile` et rôles, seuils, `quarts/models.py` (supervision, publication), API, administration Django, `org/admin.py`, création d'administrateur (`create_admin.bat`).
- **Preuve de recette héritée de L29.** Règles du registre d'accès (`matrix/core/registre_acces.py`) dont l'exécution reste à prouver ici : `ADMIN-ORGANISATION`, `WEB-QUARTS`.
- **Complexité.** L. **Migration.** Oui : indicateur technique distinct, reprise des comptes `ADMIN_NAVIRE` existants (sort à confirmer, `docs/DECISIONS_PO.md` §8).
- **Risques.** 46 références à `ADMIN_NAVIRE` ; perte d'accès légitime à la configuration ; rupture des démonstrations et seeds ; incompatibilité PostgreSQL non vue en SQLite.
- **Critères.** CA-L06-1 : un administrateur seul ne valide, ne publie ni ne vise aucun acte. CA-L06-2 : un administrateur ne s'attribue pas de fonction métier. CA-L06-3 : cumul administrateur + fonction métier possible. CA-L06-4 : seuil inférieur au plancher refusé à la configuration. CA-L06-5 : le second n'a que ses prérogatives, délégations et suppléance. CA-L06-6 : tout changement d'habilitation tracé.
- **Tests.** T-L06-1 admin seul refusé sur échange, publication, visa (négatif, web et API) ; T-L06-2 admin + fonction métier autorisé (positif) ; T-L06-3 auto-attribution refusée ; T-L06-4 plancher refusé ; T-L06-5 second : actes propres autorisés, actes du commandant refusés ; T-L06-6 trace d'audit ; T-L06-7 migration : comptes existants conservés, sur SQLite et PostgreSQL, avec sauvegarde restaurable.

### L30 — Confidentialité des passations
- **Objectif et périmètre.** Visibilité par périmètre de responsabilité, partage ciblé, équipage à terre sans limite de durée.
- **Décisions.** ARB-02 ; A14, NE-06.
- **Composants.** `dashboard/passation.py` (`syntheses_visibles`, `contenu_passation`), `org.SynthesePassation`, `scopes.py`, gabarits de passation.
- **Preuve de recette héritée de L29.** Règles du registre d'accès (`matrix/core/registre_acces.py`) dont l'exécution reste à prouver ici : `API-TABLEAUX`, `WEB-MEDIA`, `WEB-TABLEAUX`.
- **Complexité.** M. **Migration.** Probable (partage ciblé).
- **Risques.** Contenu figé à l'échelle du bâtiment : filtrage à la lecture ligne par ligne, coût en requêtes ; fuite par un export ou une notification ; ne pas régresser les passations déjà générées.
- **Critères.** CA-L30-1 : chaque échelon ne lit que son périmètre (marin, section, secteur, service, adjoint, second et commandant). CA-L30-2 : administrateur sans droit supplémentaire. CA-L30-3 : partage ciblé sans ouvrir la passation entière. CA-L30-4 : équipage à terre : lecture dans son périmètre, aucune écriture sur l'équipage embarqué, sans limite de durée. CA-L30-5 : autre bâtiment toujours invisible.
- **Tests.** T-L30-1 matrice échelon × contenu (positif et négatif) ; T-L30-2 les tests d'audit A14 sont **inversés** (ils prouvaient l'écart) ; T-L30-3 partage ciblé ; T-L30-4 équipage à terre ; T-L30-5 administrateur ; T-L30-6 PostgreSQL et volumétrie.

### L08 — Délégations et suppléance explicites
- **Objectif et périmètre.** Un mécanisme unique de suppléance officielle et de délégation : bénéficiaire, délégant habilité, périmètre, actions, modules, dates ; expiration automatique ; traces ; récapitulatif pour le titulaire.
- **Décisions.** ARB-06 ; `DEC-SUP-01` à `-07`, `DEC-FDS-02` ; B1.
- **Composants.** Nouveau modèle de délégation (généralise `DelegationProgramme`), contrôle commun L29, tâche d'expiration, notifications.
- **Complexité.** L. **Migration.** Oui.
- **Risques.** Une délégation est une porte dérobée si l'expiration ou la révocation échoue ; une seule personne exerce un périmètre à la fois (`DEC-SUP-02`) ; qualifications réglementaires du suppléant (`DEC-SUP-06`).
- **Critères.** CA-L08-1 : sans délégation active, droits inchangés. CA-L08-2 : délégation valable seulement dans ses bornes. CA-L08-3 : expiration automatique effective. CA-L08-4 : révocation immédiate. CA-L08-5 : actes attribués à leur auteur et tracés. CA-L08-6 : configuration sans code.
- **Tests.** T-L08-1 acte dans le périmètre délégué (positif) ; T-L08-2 hors périmètre, hors module, hors dates (négatifs) ; T-L08-3 expiration sans intervention ; T-L08-4 révocation ; T-L08-5 qui peut déléguer ; T-L08-6 trace et récapitulatif ; T-L08-7 PostgreSQL (fuseaux, transactions).

### L32 — Écriture bornée au périmètre dans tous les modules
- **Objectif et périmètre.** Étendre le bornage déjà en place (matériel, logistique, maintenance, calendrier) aux tâches, formations, absences, documents, RETEX, à l'API et aux traitements internes ; protéger les motifs d'absence.
- **Décisions.** ARB-06 ; R1 étendu, `DEC-DRT-03`, `DEC-DRT-04`.
- **Composants.** `taches`, `training`, `absences`, `assets` (documents), `retex`, API REST, `calendar_app`, `matrix/core/ecriture_service.py`.
- **Preuve de recette héritée de L29.** Règles du registre d'accès (`matrix/core/registre_acces.py`) dont l'exécution reste à prouver ici : `API-DISCUSSIONS`, `API-FORMATIONS`, `API-MAINTENANCE`, `API-MATERIEL`, `WEB-ABSENCES`, `WEB-DOCUMENTATION`, `WEB-FORMATIONS`, `WEB-LOGISTIQUE`, `WEB-MAINTENANCE`, `WEB-MATERIEL`, `WEB-RAPPORTS`, `WEB-RETEX`.
- **Complexité.** L. **Migration.** Non.
- **Risques.** Casser des enchaînements légitimes entre modules (création automatique d'un ticket depuis une exécution) ; domaines sans service rattaché (formation, dialogue : règle `strict`) ; performance (services rattachés recalculés).
- **Critères.** CA-L32-1 : hors périmètre → refus identique par interface, calendrier, API et traitement. CA-L32-2 : motif d'absence masqué hors périmètre ; disponibilité visible selon les droits. CA-L32-3 à 6 : un critère par module (tâches, formations, absences, documents, RETEX).
- **Tests.** T-L32-1 à T-L32-5 par module (écriture dans/hors périmètre, web et API) ; T-L32-6 motif d'absence ; T-L32-7 enchaînements internes conservés ; T-L32-8 non-régression des adjoints existants.

### L10 — Échanges de garde décidés par le COMAEQ
- **Objectif et périmètre.** Circuit à six étapes, instruction distincte, validation finale COMAEQ ou délégué, effet seulement après validation.
- **Décisions.** ARB-04 ; A2, `DEC-FDS-07`, `-13`.
- **Composants.** `quarts/echanges.py`, `EchangeService` (statuts, vues, notifications), contrôles de qualifications et de disponibilité.
- **Preuve de recette héritée de L29.** Règles du registre d'accès (`matrix/core/registre_acces.py`) dont l'exécution reste à prouver ici : `WEB-ECHANGES`.
- **Complexité.** M. **Migration.** Possible (statut d'instruction).
- **Risques.** Échanges déjà en cours au changement de règle ; COMAEQ absent sans suppléant ; périmètre à la mer (B3) non décidé.
- **Critères.** CA-L10-1 : aucun effet avant validation finale. CA-L10-2 : le chef de liste instruit sans valider seul. CA-L10-3 : le COMAEQ ou son suppléant valide. CA-L10-4 : le chef de liste délégué valide. CA-L10-5 : contrôles automatiques bloquants rendus lisibles. CA-L10-6 : circuit tracé.
- **Tests.** T-L10-1 circuit complet (positif) ; T-L10-2 chef de liste seul refusé (négatif, web et API) ; T-L10-3 suppléant ; T-L10-4 délégation expirée refusée ; T-L10-5 contrôles automatiques ; T-L10-6 notifications et trace ; T-L10-7 reprise des échanges en cours.

### L33 — BSC : suppléant habilité et recours
- **Objectif et périmètre.** Suppléant habilité du COMAEQ pour désigner et relever le BSC ; recours du commandant ; absence de visa supplémentaire.
- **Décisions.** ARB-05. **Composants.** `quarts/models.py` (`peut_designer_redacteurs`), `feuille_service_views.py`.
- **Preuve de recette héritée de L29.** Règles du registre d'accès (`matrix/core/registre_acces.py`) dont l'exécution reste à prouver ici : `WEB-FEUILLE-SERVICE`.
- **Complexité.** S. **Migration.** Non. **Prérequis.** L08.
- **Risques.** Étendre involontairement les droits de rédaction (grade ou fonction ne suffit jamais).
- **Critères.** CA-L33-1 suppléant habilité désigne et relève ; CA-L33-2 commandant recours sans visa ; CA-L33-3 droits de rédaction inchangés.
- **Tests.** T-L33-1 suppléant (positif) ; T-L33-2 non-suppléant refusé ; T-L33-3 double équipage étanche ; T-L33-4 exception à terre conservée.

### L34 — Désactivation complète des modules
- **Objectif et périmètre.** Navigation, recherche, tableau de bord, calendrier, API, notifications, tâches automatiques, création et modification : tous fermés pour un module désactivé ; données conservées ; dépendances contrôlées ; configuration et état visibles pour l'administration ; consultation exceptionnelle des archives ; traces.
- **Décisions.** ARB-03 ; A25.
- **Composants.** `matrix/core/modules.py`, `middleware.py`, API, `dashboard/`, `calendar_app/`, `notifications/`, tâches Celery, `org.ModuleActivation`, administration.
- **Preuve de recette héritée de L29.** Règles du registre d'accès (`matrix/core/registre_acces.py`) dont l'exécution reste à prouver ici : `ADMIN-AUTRES`, `WEB-PERSONNEL`.
- **Complexité.** M à L. **Migration.** Probable (table des dépendances si stockée en base).
- **Risques.** Enchaînements métier entre modules (maintenance ↔ logistique) ; notifications orphelines ; Celery qui continue de créer des données ; réactivation avec incohérences.
- **Critères.** CA-L34-1 : module fermé sur tous les points d'entrée. CA-L34-2 : données conservées. CA-L34-3 : réactivation sans perte. CA-L34-4 : désactivation refusée si un module actif en dépend. CA-L34-5 : l'administrateur voit l'état, sans droit métier. CA-L34-6 : changement tracé.
- **Tests.** T-L34-1 web, API, accueil, calendrier, recherche (négatifs) ; T-L34-2 tâches Celery ; T-L34-3 notifications ; T-L34-4 réactivation ; T-L34-5 dépendances ; T-L34-6 administrateur ; T-L34-7 les tests d'audit A25 sont **inversés**.

### L35 — Notifications : classification et règles « jamais repliées »
- **Objectif et périmètre.** Table de classification configurable ; feuilles de service en COMMUN ; règles de non-repli (urgence, sécurité, action, échéance imminente, prochain quart ou tour, transition imminente) ; seuils d'imminence configurables ; notifications lues retirées du tableau de bord mais conservées dans le centre.
- **Décisions.** ARB-07. **Composants.** `notifications/regimes.py`, `notifications/models.py`, émetteurs dans `quarts/` (une vingtaine de `regime="..."`), tableau de bord, centre de notifications.
- **Complexité.** M. **Migration.** Oui (configuration).
- **Risques.** Reclassement qui masque une alerte ; valeur `COMMUNES` contre « COMMUN » ; règles de sécurité non contournables par la configuration.
- **Critères.** CA-L35-1 table conforme à ARB-07 ; CA-L35-2 feuilles de service en COMMUN ; CA-L35-3 règles de non-repli respectées ; CA-L35-4 seuils configurables ; CA-L35-5 lues : absentes du tableau de bord, présentes dans le centre ; CA-L35-6 aucune notification supprimée.
- **Tests.** T-L35-1 chaque ligne de la table ; T-L35-2 chaque cas de non-repli (négatif : la configuration ne peut pas replier une alerte de sécurité) ; T-L35-3 modes MER, QUAI, transition ; T-L35-4 seuils ; T-L35-5 lues ; T-L35-6 PostgreSQL.

### L24-Q — Ergonomie des quarts et tours
- **Objectif et périmètre.** ANO-007 à ANO-010 ; préférences d'affichage individuelles ; vue personnelle proposée à la première utilisation ; vue collective soumise aux habilitations.
- **Décisions.** ARB-08. **Composants.** vues et gabarits `quarts`, `calendar_app`, `accounts/preferences.py` (`preferences_interface`), assistant de signalement des anomalies.
- **Complexité.** S. **Migration.** Non (champ JSON existant).
- **Risques.** Préférence interprétée comme droit d'accès (la vue collective reste soumise aux habilitations) ; régression mobile.
- **Critères.** CA-L24Q-1 menu « Quarts et tours » ; CA-L24Q-2 défaut personnel en vue journalière et mensuelle avec bascule ; CA-L24Q-3 préférence mémorisée par personne ; CA-L24Q-4 bandeau de brouillon supprimé quand redondant.
- **Tests.** T-L24Q-1 libellé ; T-L24Q-2 défauts et bascule ; T-L24Q-3 persistance par personne (et non partagée) ; T-L24Q-4 vue collective refusée sans habilitation ; T-L24Q-5 bandeau.

### L36 — Suppression définitive du module Rondes
- **Objectif et périmètre.** **a** : inventaire, retrait du code et des références résiduelles (hors données). **b** : sauvegarde, export, puis migration de suppression des tables, retrait de l'application.
- **Décisions.** ARB-09 ; A8.
- **Composants.** `rondes/` (4 modèles, 2 migrations), `matrix/settings.py`, `matrix/core/scopes.py`, `icones.py`, `dashboard/comanav.py`, seeds, documentation, cahier des charges.
- **Complexité.** a : S ; b : M. **Migration.** b : oui, destructive : **autorisation distincte obligatoire**.
- **Risques.** Perte irréversible de données ; références restantes (icône utilisée par deux écrans d'appareillage) ; anomalies liées par clé étrangère à `SET_NULL` ; l'historique des migrations n'est pas réécrit.
- **Critères.** CA-L36-1 plus aucune référence hors historique ; CA-L36-2 sauvegarde restaurable avant b ; CA-L36-3 migration de suppression applicable sur SQLite et PostgreSQL ; CA-L36-4 aucune autre application affectée ; CA-L36-5 documentation et backlog alignés.
- **Tests.** T-L36-1 les tests `test_module_rondes_retire` adaptés ; T-L36-2 non-régression de l'accueil, du calendrier et de la recherche ; T-L36-3 migration sur base avec données ; T-L36-4 restauration depuis sauvegarde ; T-L36-5 suite des apps voisines.

### Lots du registre touchés sans changement de périmètre
- **L07** (rattachement incomplet) : à traiter avec L29/L06, dont il partage les points d'entrée.
- **L09** (visas par fonction) : prolonge L08 ; non commencé avant lui.
- **L21** (sécurité d'accès avec les SIC) et A24/`D7-EXP` (sauvegarde, supervision, conservation) : indépendants, **toujours ouverts**, condition d'un déploiement opérationnel.

## 5. Ce qui n'est pas dans ce plan

Aucune fonctionnalité non validée (par exemple extension des échanges aux quarts à la mer, B3) ; pas de reconstruction des PDF ; pas de nouvelle règle métier. Les points à confirmer sont listés dans `docs/DECISIONS_PO.md` §8.

## 6. Stratégie de recette

Principe : **seuls les contrôles réellement exécutés sont déclarés réalisés** ; les autres sont marqués « non exécuté ».

| Axe | Méthode | Où |
|---|---|---|
| SQLite et PostgreSQL | Chaque lot : tests ciblés sur les deux moteurs ; suite complète une fois sur le candidat final ; migrations appliquées depuis un état équivalent à `main`, avec comparaison avant/après et restauration de sauvegarde | automatique |
| Autorisations positives et négatives | Pour chaque lot, une matrice rôle × acte × périmètre avec le résultat attendu, des cas de refus aussi nombreux que des cas d'autorisation | automatique |
| Accès directs et API | Tests écrits pour la même règle sur la page, l'API et l'administration ; preuve par exécution (L29) | automatique |
| Cloisonnement services, bâtiments, équipages | Cas croisés (service voisin, autre bâtiment, équipage à terre) | automatique + navigateur |
| Délégations | Début, fin, expiration sans intervention, révocation, hors périmètre, hors module | automatique |
| Modules | Désactivation puis réactivation : données intactes, tous les points d'entrée | automatique |
| Passations et absences | Lecture par échelon et par profil ; motif d'absence hors périmètre | automatique + navigateur |
| Feuilles de service, échanges | Circuit complet, double équipage, effet seulement après validation | automatique + navigateur |
| Notifications MER/QUAI | Chaque ligne de la table, chaque règle de non-repli | automatique + navigateur |
| Rondes | Non-régression de l'accueil, du calendrier, de la recherche ; restauration après sauvegarde | automatique |
| Ergonomie ordinateur et iPhone | Parcours `docs/recette/PARCOURS_RECETTE_PO_V11.md` ; iPhone par la méthode `docs/recette/RECETTE_IPHONE_WIFI_PRIVE.md` si le PO l'autorise | manuel |
| Accessibilité, persistance des préférences | Navigation au clavier, contraste, lecteur d'écran, préférences par personne sur deux comptes | manuel |

**Non exécutés à ce jour** : Windows réel, Safari, Firefox, iPhone, lecteur d'écran. **Les tests d'audit A14, A20 et A25 reproduisent un écart connu** : tant qu'ils réussissent, l'écart subsiste ; ils sont inversés au moment de la correction.

**Recettes intermédiaires proposées** : après L24-Q (ergonomie), après L06 et L30 (droits et passations), après L08, L32 et L10 (délégations, bornage, échanges), après L34 et L35 (modules et notifications). Aucun déploiement avec des données réelles avant la clôture des lots bloquants et le traitement de A23/A24.

## 7. Risques du plan

- L06 est le lot le plus risqué (migration du modèle de rôles, 46 références) : le prévoir avec sauvegarde, rejouer sur une base enrichie, relecture renforcée.
- L29 n'a pas de valeur visible et un risque réel de faille silencieuse : sa qualification repose sur la preuve par exécution, non sur une simple classification.
- Les délégations (L08) créent une surface d'attaque nouvelle : tests d'expiration et de révocation obligatoires.
- Le plan complet de 28 lots n'est pas validé dans son ensemble : seul le sous-ensemble ci-dessus est proposé.

## 8. Premier lot recommandé

**L29 — Socle d'habilitation et preuve d'application des autorisations.**
- C'est le préalable technique de cinq arbitrages (01, 02, 03, 04, 06) ; le faire en premier évite de multiplier des contrôles spécifiques et divergents.
- Il ne change aucun comportement voulu, mais **ce n'est pas un lot à risque faible** : réorganiser des contrôles d'autorisation peut ouvrir ou fermer des accès sans bruit ; la preuve par exécution (§4) est ce qui le qualifie.
- Il produit la cartographie réelle des points d'entrée (web, API, administration, tâches) et la liste des divergences actuelles, indispensables pour dimensionner L06, L30, L34 et L32 avec des chiffres.
- Une fois L29 clos, L06 et L30 traitent les deux écarts les plus exposés ; L34 suit (§3 bis).
- **Option** : mener L24-Q en parallèle seulement si la condition d'indépendance du §3 bis est respectée (L29 ne modifie pas les vues de `quarts` ni de `calendar_app`).

## 9. Registre des blocages avant déploiement (hors périmètre de cette reprise)

Ces risques d'exploitation et de sécurité ne sont **pas traités par les lots ci-dessus** et restent des **conditions préalables à tout déploiement avec des données réelles**. Ils sont conservés ici pour qu'aucun lot ne les fasse oublier. Aucun n'est tranché par ce document.

| Réf. | Blocage | Source | Porteur | Statut |
|---|---|---|---|---|
| `D7-EXP` / A24 | Sauvegarde, restauration, supervision, conservation des journaux : rien n'existe dans le dépôt (la restauration de la base a seulement été éprouvée en recette technique) | registre `D7`, A24, B8 | SIC / exploitant, PO | Ouvert |
| A23 / L21 | Sécurité d'accès avec les SIC (HTTPS, limitation des accès, pare-feu) ; architecture, PKI | registre A23, `DEC-PRE-06` | SIC, PO | Ouvert |
| NE-03, NE-04 | Redirection HTTPS sans réglage de proxy inverse ; QR codes liés au nom d'hôte de la requête | registre | exploitation | Ouvert |
| L05 (livré) | Configuration de production : secrets exigés, `DEBUG` désactivé ; à vérifier sur l'instance réelle, jamais sur des valeurs de démonstration | lot L05 | exploitation | Livré, condition de déploiement |
| Identifiants historiques | L'ancien identifiant administrateur codé en dur est dans l'historique Git : à tenir pour compromis ; contrôle des comptes déjà créés et décision de rotation (y compris l'ancienne note Notion) | correctif `44e7129` | PO | Ouvert |
| Création d'administrateur | `createsuperuser` permet de contourner les validateurs de mot de passe (réponse « y » ou mode non interactif) | constat du 24/11/2026 | PO | Décision attendue |
| Écarts de sécurité du registre | A1 à A4, A14, NE-06, A25 | lots L06, L30, L34, L32, L08, L10 | développement | Planifiés |
| Environnements non vérifiés | Windows réel, Safari, Firefox, iPhone, lecteur d'écran, Web Push, charge, réseau de bord | recette | PO, développement | Non exécutés |
| Données Rondes | Aucune suppression sans autorisation distincte | ARB-09 | PO | Autorisation distincte requise |
| Intégration de l'état B | Fusion dans `main` non décidée ; décision après arbitrages, recette utilisateur et suite complète sur le candidat final | PO | PO | En attente |

Ce registre est tenu à jour à chaque clôture de lot ; un blocage ne sort qu'avec une décision écrite du PO.
