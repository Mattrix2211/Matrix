# Décisions du PO du 24/11/2026 (ARB-01 à ARB-09) — consolidation et traçabilité

> **DOCUMENT PROVISOIRE — DIFFUSION RESTREINTE.** Précaution documentaire, non une classification officielle.

Ce document consolide les neuf arbitrages validés le 24/11/2026. Il est la **référence métier pour la reprise du développement** et **prévaut sur les décisions antérieures contradictoires**, qui restent consultables (§3). Il complète, sans le remplacer, le registre `docs/dossier-technique/refonte/5_registre/registre.json` de la branche documentaire (source des PDF validés, **non modifiée**) dont il réutilise les identifiants (`DEC-*`, `A*`, `NE-*`, `B*`, `D*`, `L*`). Les lots sont décrits dans `docs/PLAN_LOTS_REPRISE.md`.

Aucune règle n'est modifiée ici : ce texte consigne des décisions et mesure l'écart avec le code de l'état B (`6d6d0be`) augmenté du correctif administrateur (`44e7129`). Les pages Notion (cahier des charges, tâches, feuille de route) ne sont pas touchées : voir §7.

## 1. Identifiants

Les identifiants officiels sont proposés au format du registre (`DEC-<domaine>-NN`, numéros libres à ce jour). Ils deviennent définitifs à l'intégration au registre, lors d'une révision documentaire autorisée ; d'ici là, **ARB-nn** est l'alias de travail.

| Alias | Identifiant officiel proposé | Sujet | Écarts, points et propositions du registre rattachés |
|---|---|---|---|
| ARB-01 | `DEC-DRT-07` | Autorité, administration et organisation | A1, A3, A4, A7, B2 ; précise `DEC-DRT-01`, `DEC-DRT-02`, `DEC-ORG-04`, `DEC-ORG-06` |
| ARB-02 | `DEC-DRT-08` | Confidentialité des passations | A14, NE-06 ; `DEC-PRE-02` |
| ARB-03 | `DEC-MOD-01` (domaine nouveau : modules) | Désactivation complète des modules | A25 |
| ARB-04 | `DEC-FDS-15` | Échanges de garde | A2, B3, B5 ; tranche `DEC-FDS-07` et `DEC-FDS-13` |
| ARB-05 | `DEC-FDS-16` | BSC et feuilles de service | B1 ; précise `DEC-FDS-01`, `-02`, `-11`, `-12` |
| ARB-06 | `DEC-DRT-09` | Périmètres des commandants adjoints et délégations | R1 de `docs/propositions/matrice_modules_sans_service.md`, B1 ; précise `DEC-DRT-03`, `DEC-DRT-04`, `DEC-SUP-01` à `-07` |
| ARB-07 | `DEC-NOT-01` (domaine nouveau : notifications) | Notifications et régimes MER/QUAI | Principe `D7-NOT` de `docs/propositions/mer_quai_consolidation.md` §8 ; D6 (observations de recette) |
| ARB-08 | `DEC-UX-12` | Ergonomie des quarts et tours | ANO-007 à ANO-010 de `docs/recette/04_REGISTRE_ANOMALIES.md` ; D6 ; `DEC-UX-*` |
| ARB-09 | `DEC-ORG-07` | Suppression définitive du module Rondes | A8 ; `docs/propositions/audit_reprise_v11.md` §4 |

**Deux « D7 » distincts — notations définitives.** Le registre (`registre.json`, section `propositions`) désigne par `D7` la sauvegarde, la restauration, la supervision et la conservation des journaux (sans source, toujours ouvert, A24). Les documents mer/quai et la décision ARB-07 désignent par « D7 » le principe de priorisation des notifications par régime. Dans toutes les références nouvelles, on écrit :

- **`D7-NOT`** : priorisation des notifications par régime MER/QUAI (ARB-07, `DEC-NOT-01`) ;
- **`D7-EXP`** : exploitation (sauvegarde, restauration, supervision, conservation des journaux ; registre `D7`, A24), qui reste un **blocage avant déploiement** (voir `docs/PLAN_LOTS_REPRISE.md` §9).

Le sigle nu « D7 » ne doit plus être employé dans les nouveaux documents. Les anciens textes ne sont pas réécrits ; la correspondance est ici.

## 2. Décisions consolidées

Chaque décision reprend le texte validé. « État » mesure le code actuel (analyse du dépôt, aucun test nouveau, lecture seule).

### ARB-01 — Autorité, administration et organisation (`DEC-DRT-07`)

**Règles validées.**
1. Le rôle d'administrateur technique ne confère aucune autorité métier.
2. Les droits métier découlent des fonctions exercées, des désignations et des habilitations.
3. Rôles techniques et métier sont indépendants et cumulables.
4. Un administrateur ne peut pas s'attribuer lui-même une autorité métier.
5. Le commandant en second dispose de ses prérogatives propres, des délégations explicites et des prérogatives d'une suppléance officielle ; pas automatiquement de toutes celles du commandant.
6. Organisation, désignations et circuits de validation sont configurables sans code.
7. Les seuils minimaux d'autorité ne sont pas contournables par configuration.
8. Les modifications d'organisation et d'habilitation sont tracées.
9. Ces règles valent pour tous les points d'entrée.

**État : non implémentée, avec des briques partielles.**
- L'administrateur d'unité est le plus haut niveau numérique de l'échelle (`ADMIN_NAVIRE` = 8, `accounts/models.py`, `matrix/core/roles.py`) : il franchit tous les seuils par défaut (écart A1, lot L06 non lancé). Le test d'audit A1 reproduit l'écart ; sa réussite ne le corrige pas.
- Les rôles technique et métier sont **un seul champ ordonné** (`UserProfile.role`) : l'indépendance et le cumul exigés (règle 3) imposent de séparer le caractère « administrateur technique » de l'échelle métier. 46 références à `ADMIN_NAVIRE` hors tests et migrations.
- Le second ne désigne, ne vise ni ne publie plus (lecture de commandement seulement, `quarts/models.py`), mais l'écart A4 (écran/API) n'est pas levé pour tous les actes.
- Configuration sans code : existante (`RolePermission`, `role_thresholds`) ; plancher non contournable : absent.
- Traçabilité des changements d'organisation : partielle (`AuditLog` utilisé par endroits).
- Points d'entrée : seule une partie des écritures passe par un contrôle commun (`matrix/core/ecriture_service.py`) ; API, administration Django et tâches automatiques à cartographier.

### ARB-02 — Confidentialité des passations (`DEC-DRT-08`)

**Règles validées.** Consultation selon le périmètre de responsabilité : marin = ce qui le concerne ; chef de section = sa section ; chef de secteur = son secteur ; chef de service = son service ; commandant adjoint = ses services de rattachement ; commandant en second et commandant = tout le bâtiment ; administrateur technique = aucun droit métier supplémentaire. Partage transversal **ciblé** possible, sans ouvrir toute la passation. L'équipage à terre conserve la consultation pendant toute sa période à terre, dans son périmètre ; il suit l'évolution du bâtiment et prépare sa prochaine embarquée, sans modifier les activités de l'équipage embarqué. **Aucune limite de durée arbitraire.**

**État initial (avant L30) : non implémentée ; L30 l'implémente (`docs/recette/L30_PASSATIONS_CLOISONNEMENT.md`).** `syntheses_visibles` (`dashboard/passation.py`) filtrait par bâtiment et équipage, sans borne par section, secteur ou service ; un chef de l'équipage sortant lit la synthèse figée du bâtiment (A14, NE-06 ; tests d'audit A14 qui reproduisent l'écart). Le partage ciblé n'existe pas. Le contenu figé couvre tout le bâtiment à la génération : le filtrage doit se faire par ligne ou par bloc à la lecture.

### ARB-03 — Désactivation des modules (`DEC-MOD-01`)

**Règles validées.** Désactivation complète, réversible, par bâtiment, sans code ni redémarrage ; elle couvre navigation et accès directs, recherche, tableau de bord, calendrier, API, notifications, tâches automatiques, création et modification. Données conservées (réactivation sans perte). L'administration garde la configuration et l'état du module sans droit métier supplémentaire. Consultation exceptionnelle des données archivées pour les habilitations nécessaires. Dépendances contrôlées avant désactivation ; toute modification tracée.

**État : partielle (A25).** Par bâtiment et sans redémarrage : oui (`org.ModuleActivation`, base de données). Menu, recherche et pages web : couverts (`ModuleActivationMiddleware`, limité aux vues web). API, administration, tâches Celery, accueil, calendrier, notifications : **non couverts, choix documenté dans le code** (`matrix/core/middleware.py`, `matrix/core/modules.py`) que cette décision remplace. Contrôle des dépendances entre modules : absent. Traçabilité : partielle.

### ARB-04 — Échanges de garde (`DEC-FDS-15`)

**Circuit validé.** (1) Demande par un marin ; (2) acceptation ou refus du marin sollicité ; (3) contrôles automatiques (qualifications, disponibilités, conflits, règles de service) ; (4) instruction par le chef de liste ; (5) validation finale par le COMAEQ ou par un chef de liste **disposant d'une délégation explicite** ; (6) application et actualisation des données. COMAEQ = autorité par défaut ; en son absence, son suppléant officiellement désigné. Aucun échange n'a d'effet avant validation finale. Circuit entièrement tracé. Tranche `DEC-FDS-07` et `DEC-FDS-13`.

**État : écart A2, non implémentée.** `peut_valider_echange` = « gère la liste » (`quarts/echanges.py`) ; statut « En attente du chef de liste » ; pas d'étape d'instruction distincte ni de validation finale par le COMAEQ ; le COMAEQ n'est pas notifié. Contrôles automatiques : absences, recouvrements (règle D-C) et services à quai déjà couverts ; qualifications à vérifier. Suppléance et délégation explicites : absentes (lot L08). **Point à confirmer** (non contradictoire) : le circuit ne concerne aujourd'hui que les services à quai d'une même liste (B3) ; la décision ne dit pas qu'il s'étend aux quarts à la mer.

### ARB-05 — BSC et feuilles de service (`DEC-FDS-16`)

**Règles validées.** Le COMAEQ désigne et relève le BSC ; son suppléant habilité exerce cette autorité en son absence ; le commandant est l'autorité de recours, notamment en cas de vacance ; aucun visa supplémentaire du commandant pour la désignation. Seuls le BSC désigné et les rédacteurs explicitement habilités rédigent ; ni grade ni fonction ne suffit. En double équipage, chaque équipage a ses rédacteurs, feuilles et circuits. L'équipage à terre prépare, rédige et fait viser ses feuilles avant sa prochaine embarquée : **exception explicite** à la lecture seule à terre.

**État : en grande partie implémentée (état B, lot BSC).** `peut_designer_redacteurs` : COMAEQ titulaire de l'équipage, commandant de l'équipage si le poste est vacant (`quarts/models.py`) ; rédaction réservée aux rédacteurs désignés ; retrait par la même autorité ; exception à terre via `ACTIONS_FEUILLE_SERVICE_A_TERRE` (`matrix/core/middleware.py`). **Manque** : suppléant officiel habilité (dépend de L08) ; formulation explicite du recours du commandant hors vacance ; vérification de l'absence de visa du commandant.

### ARB-06 — Périmètres des commandants adjoints et délégations (`DEC-DRT-09`)

**Règles validées.** Limitation de l'écriture au périmètre de responsabilité **généralisée à tout Matrix** (calendrier, maintenance, tickets correctifs, tâches, formations, absences, documents), quel que soit le point d'entrée (interface, calendrier, API, traitement interne). Motifs d'absence inaccessibles hors périmètre sauf habilitation spécifique ; disponibilité consultable selon les droits. Délégations temporaires configurables sans code : bénéficiaire, autorité délégante habilitée, périmètre, actions, modules, dates de début et de fin ; expiration automatique ; attribution et actions tracées.

**État : partielle.** Le bornage au service rattaché existe pour les commandants adjoints sur matériel, installations, logistique, maintenance et le déplacement du calendrier (`matrix/core/ecriture_service.py`, `calendar_app/deplacement_views.py`) : le risque R1 du calendrier est donc **déjà appliqué** (commit `ec5fa87`), ce que le dossier d'arbitrage du 24/11 présentait à tort comme restant à décider. **Non couverts** : tâches, formations, absences, documents, RETEX ; l'API et les traitements internes ; la protection des motifs d'absence hors périmètre. Délégations : absentes (seule `DelegationProgramme` existe, pour le programme) ; suppléance explicite non lancée (L08).

### ARB-07 — Notifications et régimes MER/QUAI (`DEC-NOT-01`)

**Règles validées.** Priorisation contextuelle, pas de filtrage strict. Classification : quarts à la mer → MER ; tours de service à quai, échanges de garde → QUAI ; feuilles de service, maintenance, formations et qualifications, programme, relèves d'équipage → COMMUN ; préparation d'un appareillage ou d'un retour à quai → TRANSITION. **Les feuilles de service ne sont pas classées exclusivement QUAI.** Régime actuel prioritaire. **Jamais repliées** : alertes urgentes, consignes de sécurité, demandes d'action, échéances imminentes, informations sur le prochain quart ou tour du marin, transition imminente. Les notifications lues quittent le tableau de bord mais restent dans le centre de notifications. Classification et seuils d'imminence configurables sans code, sous réserve de règles de sécurité non contournables.

**État : partielle.** Le mécanisme existe : régime porté par la notification, répartition « régime courant / autres régimes », urgence toujours prioritaire (`notifications/regimes.py`). **Écarts** : le régime est écrit en dur à une vingtaine d'endroits (`regime="QUAI"`… dans `quarts/`) donc non configurable ; les notifications de feuille de service et de rectificatif sont classées QUAI, contrairement à la décision ; le nom de valeur est `COMMUNES` (la décision écrit « COMMUN ») ; les règles « jamais repliées » ne couvrent que l'urgence et l'action à traiter ; l'imminence n'a ni seuil ni configuration ; le comportement des notifications lues sur le tableau de bord est à vérifier.

### ARB-08 — Ergonomie des quarts et tours (`DEC-UX-12`)

**Corrections validées.** ANO-007 : « Quarts et tours » dans le menu latéral seulement ; ANO-008 : créneaux personnels par défaut en vue journalière ; ANO-009 : services personnels par défaut en vue mensuelle avec bascule vers la vue collective ; ANO-010 : supprimer le bandeau de brouillon quand il est redondant. Préférences d'affichage mémorisées par personne, en réutilisant le mécanisme existant ; vue personnelle proposée à la première utilisation ; vue collective soumise aux habilitations.

**État : non implémentée.** Mécanisme de persistance disponible : `UserProfile.preferences_interface` (JSON) et `accounts/preferences.py` (préférences d'interface, « jamais un contrôle d'accès »).

### ARB-09 — Suppression définitive du module Rondes (`DEC-ORG-07`)

**Décision.** Option A : suppression définitive, ni module inactif ni évolution planifiée. Prévoir inventaire, retrait du code, des vues, API, tâches et éléments graphiques ; traitement des données existantes avec sauvegarde préalable ; migrations de suppression sans réécriture de l'historique ; mise à jour du cahier, de la documentation et du backlog ; tests de non-régression. **Toute destruction irréversible de données reste soumise à une autorisation distincte.**

**État : partielle.** La surface est retirée dans l'état B (routes, menu, recherche, tâches ; tests `test_module_rondes_retire`). Subsistent : l'application `rondes` (modèles `RondeModele`, `PointControle`, `Ronde`, `ResultatPoint`, deux migrations) enregistrée dans `matrix/settings.py` ; références résiduelles (`matrix/core/scopes.py`, `matrix/core/icones.py` : l'icône « ronde » encore utilisée par deux écrans d'appareillage, `dashboard/comanav.py`, `seed_demo*`, documentation). Aucune autre application ne référence les migrations de `rondes`, ce qui facilite la suppression.

## 3. Décisions antérieures remplacées ou précisées (historique conservé)

Aucune entrée n'est effacée : les sources antérieures restent en place ; ce tableau donne la correspondance.

| Décision ou texte antérieur | Où | Sort | Par |
|---|---|---|---|
| Notion du 28/10 : « le chef de liste habilité valide » l'échange | Notion « Décisions » (cité par A2) | **Remplacée** | ARB-04 |
| `DEC-FDS-07`, `DEC-FDS-13` (COMAEQ décide, BSC ou chef de liste instruit) | registre | **Tranchées** : confirmées, avec délégation explicite au chef de liste | ARB-04 |
| A2 et le point B3 (échanges à la mer) | registre | A2 : cible précisée ; B3 : **toujours ouvert** | ARB-04 |
| « Le commandant en second a la même vision globale » (résumé de rôles) | `docs/REFERENCE.md` §2 | **Précisée** : lecture et prérogatives propres, pas toutes celles du commandant | ARB-01 |
| `DEC-DRT-02` « il désigne les titulaires sans viser à leur place » | registre | **Confirmée et étendue** (pas d'auto-attribution, rôles cumulables) | ARB-01 |
| A4 et B2 (droits du commandant en second) | registre | **Cible fixée** | ARB-01 |
| « Un chef de section ne consulte que sa propre section » (recette V1) | Notion « Décisions » | **Confirmée** et étendue à tous les échelons | ARB-02 |
| NE-06 (équipage sortant lit la synthèse), « l'équipage montant lit tout » | registre, code | **Remplacées** : périmètre de responsabilité, sans limite de durée | ARB-02 |
| « Lecture seule à terre » | `docs/REFERENCE.md` §2, `matrice_modules_sans_service.md` | **Précisée** : exception feuille de service (ARB-05) ; consultation dans le périmètre (ARB-02) | ARB-02, ARB-05 |
| « Choix volontaire du code : API, tâches et enchaînements internes continuent » | `matrix/core/middleware.py`, `matrix/core/modules.py`, A25 | **Remplacé** | ARB-03 |
| Recommandations R1 à R5 et options de délégation 1 et 2 | `docs/propositions/matrice_modules_sans_service.md` §4 à §6 | **Remplacées** : généralisation, délégation configurable | ARB-06 |
| « Pas de nouveau système de délégation en V1 » | `DEC-SUP-07` | **Calendrier levé** (la décision fonctionnelle `DEC-SUP-01` à `-06` s'applique) | ARB-06 |
| Étiquetage des régimes (feuille de service en QUAI) | `docs/propositions/mer_quai_consolidation.md` §8 | **Remplacé** par la table validée | ARB-07 |
| B3 « échanges et quarts à la mer : ne pas généraliser sans validation » | registre | **Tranché** : mécanisme unique mer et quai | AC-05 |
| Points §8.1 à §8.8 « à confirmer » | ce document | **Tranchés** (voir §9) | AC-01 à AC-08 |
| ANO-007 à ANO-010 « ouvertes, décision UX » | `docs/recette/04_REGISTRE_ANOMALIES.*` | **Tranchées** (statut mis à jour) | ARB-08 |
| « Conserver l'application `rondes` pour les données historiques » | `docs/propositions/audit_reprise_v11.md` §4, `docs/REFERENCE.md` §4 | **Remplacée** par la suppression définitive | ARB-09 |
| Cahier des charges §20 (rondes) | Notion | **À aligner** par le PO (non modifié ici) | ARB-09 |

## 4. Matrice de traçabilité

Colonnes : décision → exigence → anomalie ou risque → composants → lot → critères d'acceptation → tests. Les lots, critères et tests sont détaillés dans `docs/PLAN_LOTS_REPRISE.md` (identifiants `T-L..-n`).

| Décision | Exigence | Anomalie / risque | Composants principaux | Lot | Critères | Tests |
|---|---|---|---|---|---|---|
| ARB-01 | Contrôle d'habilitation unique, appliqué et prouvé par exécution sur tous les points d'entrée | A1, A4, A7 | `matrix/core/ecriture_service.py`, `scopes.py`, `roles.py`, `role_thresholds.py` | L29 | CA-L29-1 à 5 | T-L29-1 à 9 |
| ARB-01 | Administrateur sans autorité métier ; rôles cumulables ; pas d'auto-attribution ; seuils planchers | A1, A3, A4 | `accounts.UserProfile`, `accounts/`, `quarts/models.py`, API, administration | L06 | CA-L06-1 à 6 | T-L06-1 à 7 |
| ARB-02 | Visibilité des passations par périmètre ; partage ciblé ; équipage à terre | A14, NE-06 | `dashboard/passation.py`, `org.SynthesePassation`, `scopes.py` | L30 | CA-L30-1 à 5 | T-L30-1 à 6 |
| ARB-03 | Désactivation de module complète, dépendances, traces | A25 | `matrix/core/modules.py`, `middleware.py`, API, `notifications/`, Celery, `calendar_app/`, `dashboard/` | L34 | CA-L34-1 à 6 | T-L34-1 à 7 |
| ARB-04 | Circuit d'échange à cinq étapes ; validation COMAEQ ou délégué | A2, B3 | `quarts/echanges.py`, `quarts/models.py` (`EchangeService`), notifications | L10 | CA-L10-1 à 6 | T-L10-1 à 7 |
| ARB-05 | Suppléant habilité et recours du commandant pour le BSC | B1 | `quarts/models.py` (désignations), `feuille_service_views.py` | L33 | CA-L33-1 à 3 | T-L33-1 à 4 |
| ARB-06 | Bornage d'écriture généralisé ; motifs d'absence protégés | R1 étendu | `taches`, `training`, `absences`, `assets` (documents), `retex`, API | L32 | CA-L32-1 à 6 | T-L32-1 à 8 |
| ARB-06 | Délégations et suppléances configurables, expirantes, tracées | B1, `DEC-SUP-01` à `-07` | nouveau modèle de délégation, `accounts/` | L08 | CA-L08-1 à 6 | T-L08-1 à 7 |
| ARB-07 | Classification configurable, règles « jamais repliées », feuilles en COMMUN | D6 | `notifications/`, `quarts/*` (émetteurs) | L35 | CA-L35-1 à 6 | T-L35-1 à 6 |
| ARB-08 | Défauts personnels, préférences mémorisées, libellé, bandeau | ANO-007 à ANO-010 | `quarts` (vues), `calendar_app`, `accounts/preferences.py`, gabarits | L24 (volet quarts) | CA-L24Q-1 à 4 | T-L24Q-1 à 5 |
| ARB-09 | Suppression définitive des Rondes, données sauvegardées d'abord | A8 | `rondes/`, `settings.py`, `scopes.py`, `icones.py`, `comanav.py`, seeds, documentation | L36 | CA-L36-1 à 5 | T-L36-1 à 5 |

Les tests d'audit A14, A20 et A25 de `docs/dossier-technique/audit_preuves/tests_verification/` **reproduisent volontairement un écart connu** : leur réussite atteste que l'écart existe. Après correction, ils devront être inversés (ou remplacés) ; une réussite avant correction ne vaut jamais résolution.

## 5. Contradictions documentaires résolues

1. Autorité de validation des échanges de garde : note Notion du 28/10 contre `DEC-FDS-07` / `-13` → ARB-04.
2. Rondes « retirées » (A8) contre données conservées (audit de reprise) → ARB-09 : suppression définitive.
3. Désactivation d'un module : « n'existe plus » (principe) contre « choix volontaire » du code (A25) → ARB-03.
4. Équipage à terre : « lecture seule » contre rédaction de sa feuille de service → exception explicite (ARB-05).
5. Classement des notifications de feuille de service (QUAI) contre COMMUN → ARB-07.
6. Délégation : « pas de nouveau système en V1 » (`DEC-SUP-07`) contre la délégation explicite validée → ARB-06.
7. Dossier d'arbitrage du 24/11 : le bornage du calendrier (R1) était présenté comme à décider ; il est déjà appliqué sur l'état B (§2 ARB-06). Le dossier est annoté, non réécrit.

## 6. Écarts à intégrer lors d'une prochaine révision documentaire autorisée

Les quatre PDF validés (372 pages, révision 2, V3) **ne sont pas reconstruits** et leurs sources Markdown ne sont pas modifiées. Sont à intégrer plus tard :

| Document | Chapitres ou entrées touchés |
|---|---|
| Registre des écarts et décisions | Nouvelles entrées `DEC-DRT-07`, `-08`, `-09`, `DEC-MOD-01`, `DEC-FDS-15`, `-16`, `DEC-NOT-01`, `DEC-UX-12`, `DEC-ORG-07` ; statuts de A1, A2, A3, A4, A8, A14, A25, NE-06, B1, B2, B3 ; `DEC-FDS-07`, `-13`, `DEC-SUP-07` ; note sur la collision « D7 » |
| Référentiel fonctionnel | Chapitres 04 (organisation), 05 (rôles et autorisations, fiches, matrice), 08 (quarts, services, feuille), 07 (calendrier), 09 (communication : notifications), 25 (cible et feuille de route), 26 (historique) |
| Dossier technique de reprise | Chapitres 05 (comptes et autorisations), 08 (quarts), 18 (architecture), 20 (API), 21 (interactions des modules), 22 (sécurité) ; la ligne citant `reset_admin.bat` (supprimé par `44e7129`) ; l'énoncé « 3 963 tests non rejoués » (rejoués le 24/11/2026) ; description de l'état B non intégré à `main` |
| Guide utilisateur | Parcours quarts et tours (05), vues mobiles (17), limites visibles (18), index |

Les décomptes du fichier `faits.yaml` (modèles, routes, commandes) changeront avec les lots L06 à L36 : à régénérer à ce moment-là.

## 7. Suites externes à ce dépôt

Les risques d'exploitation et de sécurité hors de cette reprise (dont `D7-EXP`, A23, identifiants historiques) sont conservés dans le registre des blocages avant déploiement : `docs/PLAN_LOTS_REPRISE.md` §9.

- **Notion** (cahier des charges, tâches, feuille de route) : non modifié (hors autorisation). À aligner par le PO ou sur autorisation : §20 rondes, tâches des lots (créer L29 à L36 ; mettre à jour L06, L08, L10, L24, L32), statut des ANO.
- **Registre `registre.json`** : intégration des entrées de §1 et §3 lors de la révision documentaire autorisée.

## 8. Points à confirmer (aucune décision rouverte)

Ces points découlent de l'exécution des décisions ; ils ne remettent aucune règle en cause.

1. **Planchers de sécurité (ARB-01 règle 7, ARB-07 « règles non contournables »)** : liste des actes concernés et niveau minimal de chacun. Proposition : tirer la liste de la matrice existante `B1_matrice_role_action` (annexe consultable) ; le PO valide le tableau, sans arbitrer acte par acte à l'avance.
2. **Séparation administrateur technique / échelle métier (ARB-01 règle 3)** : trancher le modèle technique (indicateur distinct de `role`, ou fonction par désignation) relève de la conception du lot L06 ; aucune décision métier supplémentaire n'est attendue, sauf sur le sort des comptes `ADMIN_NAVIRE` existants (quelle fonction métier leur donner, le cas échéant).
3. **Partage ciblé de passation (ARB-02)** : qui peut partager (auteur, chef du périmètre ?) et jusqu'où (une ligne, un bloc, une personne ?). Proposition : partage d'un bloc ou d'une ligne vers une personne ou une fonction nommée, par un responsable du périmètre d'origine, tracé.
4. **Dépendances entre modules et consultation exceptionnelle des archives (ARB-03)** : la table des dépendances est construite pendant L34 (inventaire technique) et soumise au PO ; l'habilitation de consultation exceptionnelle est à nommer.
5. **Échanges à la mer (ARB-04, point B3)** : le circuit validé reste limité aux services à quai tant que le PO n'étend pas la règle.
6. **Unité suppléance/délégation (ARB-06 et `DEC-SUP-*`)** : proposition technique d'un modèle unique « délégation » couvrant la suppléance officielle (fonction entière, durée limitée) et la délégation ciblée (actions et modules précisés) ; à confirmer par le PO comme simplification, car cela fixe l'architecture de L08.
7. **Seuils d'imminence par défaut (ARB-07)** : valeurs initiales proposées par le PO ou reprises des délais d'alerte d'activation existants (30 minutes par défaut).
8. **Données Rondes (ARB-09)** : volume et contenu réels inconnus (seules des données de démonstration existent dans les environnements vus). Exporter, puis supprimer, relève d'une autorisation distincte.

## 9. Arbitrages complémentaires du 24/11/2026 (AC-01 à AC-08)

Huit décisions du PO complètent ARB-01 à ARB-09 ; elles prévalent sur toute décision antérieure contradictoire (§3 conserve l'historique). Identifiants officiels proposés au format du registre, définitifs à son intégration.

| Alias | Identifiant proposé | Sujet | Précise ou tranche | Lot | Critères |
|---|---|---|---|---|---|
| AC-01 | `DEC-DRT-10` | Migration des comptes administrateurs | ARB-01 règles 1 à 4 ; point §8.2 | L06 | CA-L06-1 à 8 |
| AC-02 | `DEC-DRT-11` | Seuils minimaux d'autorité | ARB-01 règle 7 ; point §8.1 | L06 (planchers), L08, L10, L33, L34 | CA-L06-4, 9 ; lots suivants pour leurs actes |
| AC-03 | `DEC-DRT-12` | Partage ciblé des passations | ARB-02 ; point §8.3 | L30 | CA-L30-3 et suivants |
| AC-04 | `DEC-MOD-02` | Archives des modules désactivés | ARB-03 ; point §8.4 | L37 (nouveau, après L34 et L08) | à définir en L37 |
| AC-05 | `DEC-FDS-17` | Échanges de quarts à la mer | ARB-04 ; **tranche B3** ; point §8.5 | L10 (un seul moteur) | CA-L10-1 à 6, étendus à la mer |
| AC-06 | `DEC-DRT-13` | Délégations et suppléances | ARB-06 ; point §8.6 ; `DEC-SUP-*` | L08 | CA-L08-1 à 6 |
| AC-07 | `DEC-NOT-02` | Seuils d'imminence des notifications | ARB-07 ; point §8.7 | L35 | CA-L35-4 et suivants |
| AC-08 | `DEC-ORG-08` | Procédure de suppression des données Rondes | ARB-09 ; point §8.8 | L36 (étapes 1 à 8) | CA-L36-1 à 5 |

**AC-01 — comptes administrateurs.** Un administrateur exclusivement technique ne garde que ses droits techniques ; un administrateur qui exerce aussi une fonction métier **explicitement établie** garde deux rôles indépendants ; fonction inconnue : droits techniques seuls ; un nouvel administrateur ne reçoit aucun droit métier par défaut ; aucune fonction n'est déduite du statut d'administrateur ; une fonction non établie est confirmée par une autorité habilitée. Une procédure sécurisée d'initialisation des premières autorités métier d'un bâtiment est prévue, sans auto-attribution ni contournement permanent : **elle fera l'objet d'une proposition soumise au PO avant implémentation** (`docs/recette/L06_PROPOSITION_INITIALISATION.md`).

**AC-02 — autorités minimales** (exigences métier validées pour Matrix, non transcription certifiée de la réglementation de la Marine nationale) :

| Acte | Autorité minimale |
|---|---|
| Modification de l'organisation hiérarchique | Commandant |
| Désignation des commandants adjoints | Commandant |
| Désignation du BSC | COMAEQ |
| Validation finale d'un échange de garde | COMAEQ ou délégataire habilité |
| Attribution d'une délégation | Autorité compétente pour l'acte concerné |
| Désignation des chefs de service | Commandant |
| Désignation des chefs de secteur et de section | Autorité hiérarchique compétente |
| Activation ou désactivation d'un module | Commandant ou délégataire habilité |
| Modification des circuits de validation | Commandant ou délégataire habilité |
| Attribution des droits techniques | Autorité technique habilitée |

Le paramétrage peut renforcer ces exigences, jamais les abaisser ; suppléances officielles et délégations autorisées restent applicables.

**AC-03 — partage ciblé.** Droits de partage : marin (ses contributions), chef de section (sa section), de secteur (son secteur), de service (son service), commandant adjoint (ses services de rattachement), commandant en second et commandant (le bâtiment), administrateur technique (aucun). Partage d'une information individuelle avec un marin, une fonction, une section, un secteur ou un service ; lecture seule ; restrictions de confidentialité respectées ; auteur, destinataires et date enregistrés ; révocable par une autorité habilitée ; jamais l'ouverture implicite d'une passation entière.

**AC-04 — archives.** Espace de consultation en lecture seule des données historiques d'un module désactivé ; commandant (sous réserve de confidentialité), second selon ses habilitations, adjoint et chef de service sur habilitation dans leur périmètre, autres marins sur autorisation, administrateur technique aucun droit automatique ; habilitations limitables dans le temps ; consultations et exports tracés ; la consultation ne réactive ni module, ni notifications, ni tâches.

**AC-05 — échanges à la mer.** Un seul moteur d'échange pour les quarts à la mer et les tours à quai : demande, acceptation, contrôles (qualifications, disponibilités et conflits, temps de repos), instruction, validation finale, traçabilité. À quai : instruction par le chef de liste, validation par le COMAEQ ou son délégataire. À la mer : instruction par le responsable des quarts concernés, validation par l'autorité compétente selon la nature du quart ; circuit configurable dans le respect des seuils.

**AC-06 — délégations et suppléances.** Fondations techniques communes, distinction métier explicite : la délégation porte sur des actes et des périmètres déterminés ; la suppléance remplace temporairement un titulaire avec les prérogatives associées. Nominatives, encadrées par une autorité compétente, limitées dans le temps, traçables, révocables, à expiration automatique. Une absence au calendrier ne transfère jamais l'autorité sans désignation préalable.

**AC-07 — seuils d'imminence** (par bâtiment, configurables sans code) : alertes urgentes et de sécurité, demandes d'action : immédiat ; prochain quart ou tour : 24 h ; appareillage ou retour à quai : 48 h ; relève d'équipage : 72 h ; échéance de maintenance : 48 h ; formation programmée : 48 h ; expiration d'une qualification : 30 jours ; autres échéances : 24 h. Sécurité et demandes d'action toujours prioritaires ; échéances dépassées prioritaires tant qu'elles sont pertinentes ; aucune notification supprimée à cause du régime ; feuilles de service : COMMUN.

**AC-08 — suppression des données Rondes.** Procédure : (1) inventaire des données et dépendances ; (2) obligations de conservation ; (3) sauvegarde et restauration vérifiée ; (4) export si nécessaire ; (5) bilan présenté au PO ; (6) autorisation explicite de destruction ; (7) suppression des données, tables et composants ; (8) intégrité des autres modules sur SQLite et PostgreSQL. Sans donnée : preuve de l'absence. **La validation de la procédure n'autorise pas la destruction.**

Points du §8 désormais tranchés : 1 (AC-02), 3 (AC-03), 4 (AC-04, habilitation de consultation), 5 (AC-05), 6 (AC-06 : fondations communes, distinction métier), 7 (AC-07), 8 (AC-08, procédure). Le point 2 est tranché pour le sort des comptes (AC-01) ; le **modèle technique** retenu par L06 est décrit dans `docs/recette/L06_MIGRATION_ET_PREUVES.md`.

## 10. Arbitrages du PO sur le rapport intermédiaire L06 (AC-09 à AC-14)

Six décisions tranchent les questions soumises au rapport intermédiaire de L06 (`2fa183a`) ; elles prévalent sur tout comportement antérieur contradictoire, y compris ceux de la première version de L06.

| Alias | Identifiant proposé | Sujet | Précise ou remplace | Lot | Critères |
|---|---|---|---|---|---|
| AC-09 | `DEC-DRT-14` | Initialisation des premières autorités (option A) | AC-01 (procédure d'initialisation) ; proposition `L06_PROPOSITION_INITIALISATION.md` | L06 | CA-L06-10 |
| AC-10 | `DEC-DRT-15` | Désignation du commandant en second | AC-02 (tableau non exhaustif) | L06 | CA-L06-11 |
| AC-11 | `DEC-DRT-16` | Séparation des trois niveaux d'administration | ARB-01 ; point « administrateur général » | L06 (L37 inchangé) | CA-L06-12 |
| AC-12 | `DEC-DRT-17` | Réinitialisation des mots de passe | première version de L06 (comptes non réinitialisables) | L06 | CA-L06-13 |
| AC-13 | `DEC-DRT-18` | Modification des seuils métier | **remplace** « l'administrateur technique peut renforcer un seuil » | L06 (délégations : L08) | CA-L06-14 |
| AC-14 | `DEC-DRT-19` | Fonctions métier à confirmer | AC-01 (fonction non établie) | L06 | CA-L06-15 |

**AC-09 — initialisation des premières autorités.** Commande d'installation exécutée localement par un installateur autorisé, une seule fois par bâtiment (`manage.py initialiser_autorites_batiment`) : désignation explicite du premier commandant sur référence d'une autorisation préalable, désignation indépendante du premier administrateur technique, cumul possible mais jamais automatique (`--accepter-cumul`), traçabilité complète, verrouillage par bâtiment (unicité en base) et protection contre les exécutions simultanées. Aucun mot de passe par défaut, identifiant codé en dur ni authentification alternative permanente. La récupération des accès est une procédure exceptionnelle séparée (`manage.py recuperer_acces_administrateur`).

**AC-10 — commandant en second.** Le commandant et l'administrateur général enregistrent et révoquent la désignation ; l'administrateur technique du bâtiment ne l'a pas ; le second ne se l'attribue pas et ne désigne pas son successeur ; tout est historisé ; la fonction reste distincte de la suppléance du commandant (L08).

**AC-11 — trois niveaux d'administration.** *Administrateur général Matrix* : gouvernance globale, création et administration des bâtiments, désignation des commandants et seconds, gestion des administrateurs techniques, administration technique globale ; aucun droit métier courant automatique. *Administrateur technique du bâtiment* : administration technique de son périmètre, droits techniques autorisés, maintenance et configuration ; aucun droit métier automatique ; aucune désignation d'autorité métier. *Superutilisateur Django* : interventions techniques exceptionnelles, distinct de l'administrateur général, jamais un profil métier courant. Le cumul explicite reste possible. La frontière de confiance (un superutilisateur ou un opérateur ayant accès à la base peut contourner les contrôles applicatifs) est documentée dans `docs/recette/L06_MIGRATION_ET_PREUVES.md` §12 avec les mesures d'exploitation.

**AC-12 — réinitialisation des mots de passe.** Équipier à chef de service : administrateur technique ; commandant adjoint, second, commandant, administrateur technique : administrateur général ; administrateur général : procédure sécurisée de récupération. En cas de cumul ou de désignation effective, le niveau de protection le plus élevé s'applique. Garanties : aucun accès au mot de passe existant ; mot de passe provisoire à usage unique, d'une validité limitée ; nouveau mot de passe choisi par le titulaire ; sessions ouvertes invalidées ; titulaire notifié ; opération tracée sans secret ; essais répétés verrouillés ; fonctionnement hors Internet. La **remise** du mot de passe provisoire reste orale, par l'autorité habilitée : si le PO veut un autre moyen de remise, c'est un arbitrage supplémentaire.

**AC-13 — seuils métier.** Un administrateur technique seul ne renforce ni n'abaisse aucun seuil métier, ne modifie aucun circuit de validation métier et ne contourne aucun plancher ; il consulte les seuils et règle les paramètres techniques de son périmètre. Les modifications métier relèvent du commandant ou d'une autorité explicitement habilitée (délégations : L08, non anticipées). Les planchers ne s'abaissent jamais ; tout est historisé.

**AC-14 — fonctions à confirmer.** Espace « Fonctions à confirmer » dans l'administration du personnel : liste des comptes concernés par la migration, ancienne fonction, confirmation, correction ou refus par l'autorité compétente, droits techniques conservés indépendamment, décisions historisées, compteur des demandes en attente. Une fonction non confirmée ne confère aucun droit. Concurrence, double traitement et auto-attribution empêchés ; cohérence données migrées, journal d'audit et décisions vérifiée.

## 11. Arbitrages du PO sur la finalisation de L06 (AC-15 à AC-21)

Sept décisions du PO complètent AC-09 à AC-14 (rapport intermédiaire `14babb4`, code testé `e004ee6`). Elles prévalent sur toute disposition antérieure contradictoire ; les décisions précédentes restent consultées en §9 et §10 (historique conservé). **AC-15 remplace** la question n° 1 du rapport intermédiaire ; **AC-16 remplace** le mot de passe provisoire d'AC-12 (la matrice des autorités d'AC-12 est conservée) ; **AC-17** précise la récupération d'AC-09 ; **AC-18** fixe les paramètres que le rapport proposait à confirmer ; **AC-19 remplace** l'attribution des droits techniques par l'administrateur technique d'AC-11 et d'AC-14 ; **AC-20** tranche le catalogue de formations.

| Alias | Identifiant proposé | Sujet | Précise ou remplace | Lot | Critères |
|---|---|---|---|---|---|
| AC-15 | `DEC-DRT-20` | Prérogatives de l'administrateur général ; superutilisateur Django | AC-11 (précisé) | L06 | CA-L06-16, 17 |
| AC-16 | `DEC-DRT-21` | Réinitialisation sécurisée par code à usage unique | AC-12 (mécanisme) | L06 | CA-L06-18, 19 |
| AC-17 | `DEC-DRT-22` | Récupération d'un administrateur général | AC-09 (récupération) | L06 | CA-L06-20 |
| AC-18 | `DEC-DRT-23` | Paramètres de sécurité et limitation des connexions | AC-12 | L06 | CA-L06-21, 24, 25 |
| AC-19 | `DEC-DRT-24` | Attribution des droits techniques | AC-11, AC-14 | L06 | CA-L06-22 |
| AC-20 | `DEC-DRT-25` | Catalogue des formations commun et local | ARB-01 ; AC-11 | L06 (autorisations et cohérence des données), L38 (référentiel local, moteur d'exploitation) | CA-L06-23, 26 ; CA-L38-1 à 6 |
| AC-21 | `DEC-DRT-26` | Risques résiduels | AC-16 à AC-18 | L06 | §19 de `L06_MIGRATION_ET_PREUVES.md` ; CA-L06-27, 28 |

**AC-15 — gouvernance.** Gouvernance conservée par l'administrateur général : création et administration des bâtiments ; désignation et révocation des commandants et seconds ; gestion des administrateurs techniques ; rattachement des marins aux bâtiments ; configuration structurelle des bâtiments ; référentiels communs de la flotte ; catalogue commun de formations ; exigences communes de formation ; configuration générale de Matrix. **Non conféré automatiquement** : circuits métier propres à un bâtiment, validation des échanges de garde, visa des feuilles de service, validation des opérations de maintenance, consultation systématique des passations confidentielles, fonctions courantes du commandant, toute autre action métier. Une fonction métier ne s'exerce que si elle a été explicitement attribuée, dans le périmètre correspondant. Le statut `is_superuser` ne confère ni gouvernance ni fonction métier dans les interfaces applicatives ordinaires ; il reste réservé aux interventions techniques exceptionnelles ; les limites réelles de cette séparation (opérateurs avec accès privilégié au serveur, au code ou à la base) sont documentées (`L06_MIGRATION_ET_PREUVES.md` §12). Les 32 tests de l'expérience de retrait sont classés individuellement (§15 du même document). Hypothèse de mise en œuvre à valider : la supervision de la Vue flotte et des tableaux par spécialité ou classe, en lecture seule, est classée « gouvernance » ; la Vue COMANAV, la supervision de maintenance et les anomalies sont classées « métier ».

**AC-16 — réinitialisation.** Remplace le mot de passe provisoire : demande par une autorité habilitée ; code temporaire généré par Matrix, remis au titulaire après vérification de son identité ; le titulaire définit son mot de passe ; code invalidé définitivement ; anciennes sessions révoquées ; le code n'authentifie jamais, n'est valable que pour sa demande et son compte, n'est conservé ni en clair ni dans les journaux. Comptes porteurs d'autorité : vérification indépendante imposée par le mécanisme, par un second responsable distinct de l'initiateur (ou un facteur préalablement enregistré : non retenu à ce stade). Aucune messagerie ni Internet. La matrice des autorités d'AC-12 est conservée.

**AC-17 — récupération.** Deux opérateurs habilités distincts, chacun authentifié séparément, exécution locale, justification obligatoire, autorisation limitée dans le temps, traçabilité complète, révocation des sessions antérieures ; la double validation ne se limite pas à la saisie de deux noms ; situation sans administrateur général prévue ; aucun compte de secours ni identifiant ou mot de passe prédéfini ; procédure simplifiée de développement impossible en production ; non présentée comme une protection contre un opérateur disposant d'un accès illimité.

**AC-18 — paramètres.** Validité du code 30 minutes ; 5 tentatives de connexion avant limitation ; limitation initiale de 15 minutes, progressive ; 5 essais de code au plus ; conservation des compteurs inactifs 30 jours ; compteurs atomiques sur SQLite et PostgreSQL ; protection contre le verrouillage malveillant ; purge automatique ; échec compté une fois ; paramètres réglables hors du code dans des bornes de sécurité ; architecture justifiée (`L06_MIGRATION_ET_PREUVES.md` §18) ; compteurs techniques distincts des journaux d'audit.

**AC-19 — droits techniques.** Seul l'administrateur général attribue et révoque les droits d'administrateur technique, nominativement, avec justification, historisés. L'administrateur technique conserve la gestion des comptes ordinaires et des paramètres techniques de son périmètre ; il ne crée ni ne révoque d'administrateur technique, ne modifie pas ses propres privilèges et ne contourne pas ces règles. L'initialisation AC-09 reste applicable.

**AC-20 — catalogue des formations.** Création et modification du catalogue commun, exigences communes : administrateur général. Formations internes d'un bâtiment, programmation des sessions : responsable formation habilité. Exigences locales : commandement (elles renforcent sans jamais affaiblir les exigences communes). Validation des qualifications individuelles : autorité métier habilitée. Administration technique du module : administrateur technique. Cloisonnement des formations internes entre bâtiments. **Dans L06** : suppression de l'écriture du référentiel commun par l'administrateur technique et des droits métier automatiques ; le référentiel local complet relève du lot L38 (`PLAN_LOTS_REPRISE.md`).

**AC-21 — risques.** Refusés en l'état et traités : usurpation par l'administrateur de réinitialisation ; verrouillage durable ou répétitif par un tiers ; compteur non atomique sur SQLite ; double comptage API ; accumulation des compteurs. Accepté sous conditions : retour arrière partiel des migrations après modification des comptes (sauvegarde complète vérifiée, restauration testée, conséquences et perte documentées, aucune exécution sur données réelles sans autorisation).

