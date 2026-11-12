# Annexe F — Sources, décisions citées, branches et éléments non vérifiés (généré)

> Diffusion restreinte. Généré par `outils/generer_annexe_f.py` ; état B (`6d6d0be`), non fusionné dans `main`. Les sections F.1 et F.2 consignent ce qui a été **lu** et **non lu**, à la date de rédaction.

## F.1 Sources lues

| Source | Utilisation |
|---|---|
| Code de l'état B (`6d6d0be`), 21 applications et le noyau | Tous les chapitres ; références `fichier:ligne` vérifiées par script |
| Dossier V1.2 (`docs/dossier-technique-v12/`, branche `claude/eager-hopper-2cbcqh`) : registre des 125 décisions, plan en 28 lots, comptes rendus L01, L05, L02, L03 | Décisions citées par `DEC-…`, jamais rouvertes ni recopiées |
| Notion : Cahier des charges ; Organigramme et rôles ; pages 02, 06, 07, 11, 12 (glossaire), 13 (lues avant l'ensemble 1) ; page 04 (lue pour le chapitre 11) | Chapitres 4 à 16, 22, 25 (voir les citations « Notion » dans chaque chapitre) |
| Notion : Feuille de route (10/10/2026) ; Cap UX/UI « Naval Premium » (29/10/2026) ; Recette UX V1.1 (31/10/2026) | Chapitres 17, 20, 25, 26 |
| Notion : « 03 — Formation, stages, CFPES, FPS et qualification opérationnelle » (29/09/2026) | Chapitre 14, chapitre 21 |
| Notion : « 04 — Maintenance, installations, SSF, SLM, ERDT… » (21/10/2026) | Chapitre 11 (configuration réelle, états techniques, interlocuteurs SSF/ERO/ERDT) |
| Notion : « 07 — SIC, cyber, protection-défense et conformité » (30/09/2026) | Chapitre 23 (aucune exigence technique chiffrée trouvée) |
| Documents du dépôt : `README.md`, `CLAUDE.md`, `docs/UX.md`, `docs/REFERENCE.md`, `docs/DEMO.md`, `docs/COMPATIBILITE_CHECKLIST.md`, `docs/recette/` | Chapitres 17, 23, 24 |

## F.2 Sources non lues ou lues seulement par résultat de recherche ⚪

- Notion : « Vision et Objectifs », « Audit métier Matrix × Guide du marin 2023 (31/10/2026) », « Ordre de travail Claude — Correctifs métier et UX V1.1 (01/11/2026) », « [CADRAGE UX] Corrections UX ciblées », « Tranche 1 — Prototype Naval Premium » : **vues dans les résultats de recherche, non lues en entier**.
- Notion : pages 01, 05, 08, 09, 10 de l'organigramme (contexte) ; tâche « Recette V1 — F4 et F7 » ; **« [CADRAGE UX] Corrections UX ciblées »** (vue seulement dans les résultats de recherche).
- Notion : tâches « Recette V1 — … » et autres tâches de la base « Tâches en cours » : non relues une à une.
- Sous-module `design/` (charte graphique) : **vide** dans l'environnement de rédaction.
- `docs/propositions/`, `docs/prototypes/`, `docs/archive/` du dépôt : exploités ponctuellement (par exemple les propositions mer/quai), non lus en entier ; l'archive n'est jamais une consigne.
- *Guide du marin 2023* : **jamais disponible, non utilisé**.
- Aucune exigence SIC opposable, aucune procédure de sauvegarde ou de supervision n'a été fournie.

## F.3 Décisions du PO citées dans le dossier

**70 identifiants `DEC-…`** distincts sont cités dans les chapitres ; **70** existent dans le registre V1.2 (125 décisions au total). Aucun identifiant inventé.

`DEC-ANO-01`, `DEC-APP-01`, `DEC-APP-02`, `DEC-APP-03`, `DEC-APP-09`, `DEC-APP-10`, `DEC-APP-11`, `DEC-APP-12`, `DEC-APP-13`, `DEC-APP-14`, `DEC-BLQ-01`, `DEC-BLQ-03`, `DEC-BLQ-05`, `DEC-CLO-01`, `DEC-CLO-04`, `DEC-CLO-05`, `DEC-COL-01`, `DEC-COL-02`, `DEC-COL-05`, `DEC-DRT-01`, `DEC-DRT-02`, `DEC-DRT-05`, `DEC-DRT-06`, `DEC-DUR-01`, `DEC-FDS-01`, `DEC-FDS-02`, `DEC-FDS-04`, `DEC-FDS-05`, `DEC-FDS-06`, `DEC-FDS-07`, `DEC-FDS-08`, `DEC-FDS-13`, `DEC-FDS-14`, `DEC-MAT-01`, `DEC-MAT-04`, `DEC-MUT-01`, `DEC-MUT-06`, `DEC-MUT-07`, `DEC-ORG-02`, `DEC-ORG-04`, `DEC-ORG-05`, `DEC-OUT-01`, `DEC-OUT-03`, `DEC-OUT-05`, `DEC-PER-01`, `DEC-PER-04`, `DEC-PRE-01`, `DEC-PRE-02`, `DEC-PRE-03`, `DEC-PRE-04`, `DEC-PRE-06`, `DEC-QUA-01`, `DEC-QUA-03`, `DEC-QUA-04`, `DEC-RTX-01`, `DEC-RTX-02`, `DEC-RTX-03`, `DEC-RTX-04`, `DEC-SUP-01`, `DEC-TAC-01`, `DEC-TAC-04`, `DEC-TAC-05`, `DEC-TAC-06`, `DEC-UX-01`, `DEC-UX-04`, `DEC-UX-05`, `DEC-UX-06`, `DEC-UX-08`, `DEC-UX-09`, `DEC-UX-11`

## F.4 Branches distantes

**53 branches distantes** à la date de l'inventaire. « Analysée » = expliquée au chapitre 26 ; « non analysée » = listée seulement.

| Branche | Date | Commit | Dans A (`main`) | Dans B | Statut |
|---|---|---|---|---|---|
| `chatgpt/relecture-g0-corrections-20261112` | 2026-11-12 | `1aac419` | non | non | non analysée ⚪ |
| `claude/fervent-wright-kl6gtx` | 2026-11-12 | `1173aef` | non | non | analysée |
| `claude/eager-hopper-2cbcqh` | 2026-11-11 | `6cc1557` | non | non | analysée |
| `claude/l03-suppression-sure-v11` | 2026-11-11 | `6d6d0be` | non | oui | analysée |
| `claude/l02-archivage-effectif-v11` | 2026-11-11 | `6e14a65` | non | oui | analysée |
| `claude/l05-config-production-v11` | 2026-11-10 | `517a2ce` | non | oui | analysée |
| `claude/l01-verrou-demo-v11` | 2026-11-10 | `8e60fee` | non | oui | analysée |
| `claude/matrix-audit-general-9oohvw` | 2026-11-05 | `4aa4dcf` | non | non | analysée |
| `claude/matrix-audit-general-rg0ddz` | 2026-11-05 | `1ef7047` | non | non | analysée |
| `claude/iteration-ux-v11-20261102` | 2026-11-05 | `1c37f22` | non | oui | analysée |
| `claude/recette-metier-ux-v11-20261101` | 2026-11-01 | `284430d` | non | oui | analysée |
| `claude/ux-naval-premium-v11` | 2026-10-31 | `a1503ac` | non | oui | analysée |
| `claude/maquette-carte-a-faire` | 2026-10-30 | `0fb5e17` | non | non | analysée |
| `main` | 2026-10-28 | `6ef16ad` | oui | oui | analysée |
| `claude/ux9-role-creation-sans-defaut` | 2026-10-27 | `994a530` | oui | oui | analysée |
| `integration/v1-fanlab-20261021` | 2026-10-27 | `994a530` | oui | oui | analysée |
| `claude/ux9-corrections-recette` | 2026-10-27 | `5e80fae` | oui | oui | analysée |
| `claude/ux9-fiche-tache-remontee` | 2026-10-27 | `fa8eaae` | oui | oui | analysée |
| `claude/ux9-interlocuteur-terre` | 2026-10-27 | `09b12ed` | oui | oui | analysée |
| `claude/ux9-retours-libelles` | 2026-10-26 | `c529d02` | oui | oui | analysée |
| `claude/quarts-regler-echanges-atomique` | 2026-10-22 | `c9c3b28` | oui | oui | analysée |
| `claude/securite-cache-permissions` | 2026-10-21 | `7628e8c` | oui | oui | analysée |
| `claude/feuille-service-suivi` | 2026-10-21 | `50ae6a1` | oui | oui | analysée |
| `claude/releve-date-effet` | 2026-10-21 | `01215cc` | oui | oui | non analysée ⚪ |
| `claude/feuille-service-rectificatif` | 2026-10-20 | `386aa2c` | oui | oui | analysée |
| `claude/feuille-service-historisation` | 2026-10-20 | `5159564` | oui | oui | analysée |
| `claude/matrix-v1-recette-audit-4olae7` | 2026-10-20 | `b2dfacb` | non | non | analysée |
| `claude/fiabilite-annonces-concurrence` | 2026-10-20 | `355217d` | oui | oui | analysée |
| `claude/fiabilite-quarts-trace` | 2026-10-20 | `cc4ebff` | oui | oui | analysée |
| `claude/fiabilite-stock-push` | 2026-10-20 | `545d0ad` | oui | oui | analysée |
| `claude/validations-critiques-confirmation` | 2026-10-20 | `1a726a0` | oui | oui | analysée |
| `claude/feuille-service-escalade` | 2026-10-17 | `d8ed862` | oui | oui | analysée |
| `claude/ergonomie-p2` | 2026-10-17 | `5f57d96` | oui | oui | analysée |
| `claude/securite-terre-second` | 2026-10-17 | `1a7f212` | oui | oui | analysée |
| `claude/compat-postgresql` | 2026-10-16 | `4ade094` | oui | oui | analysée |
| `claude/securite-calendrier-fichiers` | 2026-10-13 | `7a57264` | oui | oui | analysée |
| `claude/securite-perimetres-api` | 2026-10-13 | `0ca4e2f` | oui | oui | analysée |
| `claude/recette-v1-passage-b` | 2026-10-13 | `0f9f799` | non | non | analysée |
| `claude/fix-ano-001-equipage-postgres` | 2026-10-13 | `06131ca` | oui | oui | analysée |
| `claude/gracious-planck-g0pwzh` | 2026-10-13 | `7b722a4` | oui | oui | non analysée ⚪ |
| `claude/taches-lot1` | 2026-10-10 | `0de7ff9` | non | non | non analysée ⚪ |
| `claude/verif-socle-accounts` | 2026-10-10 | `36b32f8` | non | non | non analysée ⚪ |
| `integration/pr6-et-travail-local` | 2026-10-10 | `50df154` | oui | oui | analysée |
| `claude/ux-fondations` | 2026-10-09 | `9691fbf` | non | non | non analysée ⚪ |
| `claude/ux-3-10` | 2026-10-08 | `a074f42` | non | non | non analysée ⚪ |
| `claude/economie-tokens` | 2026-10-02 | `2905228` | non | non | non analysée ⚪ |
| `docs/cahier-ux` | 2026-10-02 | `4258568` | oui | oui | analysée |
| `claude/paquet-bordops-review-69huab` | 2026-10-01 | `f69a8cb` | oui | oui | analysée |
| `claude/versionnage-listes-en-cours` | 2026-09-23 | `f03ad71` | oui | oui | non analysée ⚪ |
| `claude/adoring-einstein-71zc3z` | 2026-09-23 | `e0f7514` | oui | oui | non analysée ⚪ |
| `sauvegarde/sonnet-2026-09-23` | 2026-09-23 | `0ee6947` | non | non | non analysée ⚪ |
| `claude/matrix-project-tasks-d2c1x6` | 2026-08-21 | `fe5e1a3` | non | non | non analysée ⚪ |
| `claude/quizzical-curran` | 2026-04-03 | `11515b8` | non | non | non analysée ⚪ |

## F.5 Registre des éléments non vérifiés (⚪), par chapitre (généré)

**173 passages** répartis sur 41 fichiers.
Chaque ligne reprend, à l'identique, un passage marqué ⚪ dans un chapitre. Aucune ligne n'a été ajoutée ni retirée à la main.

### 01_vision.md
- - ⚪ Les formulations du cahier des charges (édition du 10/10/2026) ont été relues contre le code ; celles qui décrivent des fonctions non développées sont en 🔵. La génération automatique des tours de quart, décrite aux sections 8, 10 et 11 du cahier, **a été abandonnée** par décision métier : la planification est manuelle, avec …
- - ⚪ La page Notion « Cahier des charges » porte l'état « non vérifié » ; elle n'est pas une recette.
- - ⚪ Le *Guide du marin 2023* n'a jamais été disponible : le dossier ne s'appuie sur lui pour aucune règle.

### 02_vue_ensemble.md
- > ⚪ Ces parcours sont reconstitués d'après le code et les écrans décrits ; ils n'ont **pas été rejoués dans un navigateur** pour cette édition. Les captures viendront avec la recette navigateur (chapitre 17). Les données de l'exemple sont fictives.
- 4. Il consulte son **calendrier** : un quart demain à 06 h. Un collègue lui propose un **échange de tour** : il accepte, puis la demande est validée par la personne qui gère la liste. 🔵 Règle cible validée par le PO : le chef de liste ou le BSC instruit, et le COMAEQ (ou son suppléant) décide ; elle n'est pas encore en place (ch…
- - ⚪ Les parcours du §2.4 n'ont pas été rejoués dans un navigateur.
- - ⚪ La correspondance « responsable de classe ≈ IRB » et « responsable de spécialité ≈ ALFAN Exploitation » vient de la page Notion « 13 — Décisions » ; elle n'est pas modélisée dans le code au-delà des deux désignations `ResponsableClasseNavire` et `ResponsableSpecialite`.

### 03_lire_ce_dossier.md
- | ⚪ **Non vérifié** | Information issue d'une seule source (Notion, mémoire) ou point non rejoué | La limite est dite en clair ; recensée en annexe F |
- - ⚪ Le dossier décrit un **état du code**, pas un état déployé ; il ne vaut ni recette ni homologation.
- - ⚪ Les vérifications portent sur le code et ses tests (suite complète sur SQLite). **PostgreSQL, Windows et un navigateur réel n'ont pas été rejoués** pour cette édition.
- - ⚪ Les pages Notion consultées portent l'état « non vérifié » ; ce qui n'en est reconnu que par elles est étiqueté en conséquence.
- - ⚪ Quelques pages Notion n'ont été vues que dans les résultats de recherche, sans lecture complète, et le sous-module de charte graphique est vide dans l'environnement de rédaction : la liste exacte des sources lues et non lues est dans la partie restreinte (annexe F).

### 04_organisation.md
- 4. **Effets.** L'équipage à bord change ; l'historique des périodes d'équipage est enregistré (jamais reconstitué rétroactivement) ; la **synthèse de passation** est générée ; les feuilles de service et visas historiques restent inchangés (décision du PO, ⚪ non rejouée ici).
- - 🟢 Le comportement décrit pour la relève, l'archivage et la suppression est couvert par des tests de l'état B ; la suite complète (3 963 tests, SQLite) passe. ⚪ **Non vérifié** : PostgreSQL (20 tests propres à ce moteur sont ignorés sur SQLite), Windows, navigateur réel.
- - ⚪ Relations génériques (fils de discussion, notifications) attachées à une unité : non vérifiées lors de L03 (à contrôler avant production, chapitre 23).
- - ⚪ En l'absence de circuit de transfert de matériel (lot L13), un secteur équipé ne peut pas encore être archivé ; le matériel se réaffecte entre-temps par l'affectation en masse.
- - ⚪ L'archivage d'un **bâtiment** passe par l'API ou l'administration, pas par l'écran Réglages.
- - ⚪ Les pages Notion « 02 — RH, postes… » et « 11 — Modèle de données cible » décrivent un vocabulaire cible (poste, qualification, capacité, mission) plus riche que ce qui existe ; il n'est pas présenté ici comme du fonctionnement actuel.

### 05_comptes_roles_autorisations.md
- - 🟢 Les contrôles décrits sont couverts par des tests de l'état B (`accounts/tests/`, dont la matrice des droits, les fuites de périmètre et la réinitialisation de mot de passe). La suite complète passe sur SQLite ; ⚪ PostgreSQL, Windows et navigateur n'ont pas été rejoués.
- - ⚪ Les pages Notion « 02 — RH, postes, qualifications » et « 03 — Formation, stages » décrivent des objets cibles (poste, aptitudes, profondeur de relève, couverture de fonctions) qui **ne sont pas des fonctions actuelles**.
- - ⚪ L'ordre exact des grades et la liste des brevets ne sont pas dans le code ; ils sont à fournir par le PO (informations manquantes IM-01 et IM-02 du dossier V1.2).
- - ⚪ Le détail action par action de ce que peut faire un administrateur d'unité est établi dans les chapitres qui traitent chaque circuit.

### 06_accueil_pilotage.md
- - 🟢 Couverture de tests de l'état B : 261 fonctions de test dans `dashboard`. ⚪ Les écrans n'ont pas été rejoués dans un navigateur ; leur description vient du code et des gabarits.
- - ⚪ Le contenu exact de chaque vue de pilotage évolue avec les modules sources ; ce chapitre en décrit la **logique d'assemblage**, pas chaque indicateur.
- - ⚪ Le PDF exige des bibliothèques natives non installées dans l'environnement de rédaction : l'export PDF n'a pas été rejoué.
- - ⚪ La page Notion « Recette UX V1.1 » a été consultée lors de la rédaction du chapitre 17 ; les observations de recette n'ont toutefois pas été rapprochées une à une du comportement du code ni rejouées sur un poste réel.

### 07_calendrier.md
- - 🟢 Couverture de tests de l'état B : 124 fonctions de test dans `calendar_app`. ⚪ L'affichage (FullCalendar) n'a pas été rejoué dans un navigateur.
- - ⚪ Les événements du calendrier ne portent pas tous la même règle de déplacement : ce chapitre en donne la liste exhaustive ; une évolution la modifierait.
- - ⚪ Le flux iCal n'inclut pas les tâches ni le programme : constat issu de la lecture du code, non confronté à un usage réel.

### 08_quarts_services_feuille.md
- - 🟢 Les circuits décrits sont couverts par des tests de l'état B (`quarts/tests/`, 609 fonctions de test dans le paquet) ; ⚪ PostgreSQL, Windows et navigateur n'ont pas été rejoués ; les parcours du §8.2 sont reconstitués d'après le code.
- - ⚪ Le rendu imprimable d'une **liste** existe ; celui de la **feuille de service** n'a pas été trouvé dans le code (§8.8, cible).
- - ⚪ L'autorité de déclaration d'un accostage ou d'un appareillage (COMAEQ ou commandant de l'équipage à bord) est décrite par les propositions `mer_quai_*` validées par le PO ; elle ne figure pas dans le registre des 125 décisions (B4 du registre des écarts).
- - ⚪ Le détail de l'écran d'entrée (vue « quotidienne » et vue « responsable ») est décrit d'après la documentation ; non rejoué.

### 09_communication.md
- - 🟢 Couverture de tests de l'état B : `notifications` 165 fonctions de test, `annonces` 46, `threads` 30. ⚪ Les écrans n'ont pas été rejoués dans un navigateur ; le Web Push n'a pas été éprouvé sur un appareil réel.
- - ⚪ **Relations génériques** (discussions, notifications) : elles désignent leur objet sans clé étrangère protégée ; leur comportement face à la suppression de l'objet visé, notamment une unité, n'est pas vérifié (chapitre 19, §19.6).
- - ⚪ Le détail de chaque catégorie de notification et de chaque icône n'est pas inventorié ici (propositions `notifications_par_regime.md`, état B).
- - ⚪ L'API REST des fils expose seulement les fils de **tickets** et d'**occurrences de maintenance** ; les fils des autres objets passent par les vues web de leurs modules.

### 10_taches_demandes_programme_postes.md
- - 🟢 Les circuits décrits sont couverts par des tests de l'état B (`taches/tests/`, `demandes/tests/`, `programme/tests/`, `postes/tests/`). ⚪ Les modules `programme` et `postes` n'ont que très peu de tests propres (10 et 7 fonctions de test) : leur description repose surtout sur la lecture du code.
- - ⚪ Les parcours du §10.1 sont reconstitués d'après le code ; non rejoués dans un navigateur.
- - ⚪ La décision « Tâches périodiques générées à partir des fiches de maintenance » relève du chapitre 12.

### 11_materiel_installations.md
- - On y consigne des **événements** et des **modifications techniques** (⚪ la page Notion « 04 » décrit l'orientation selon laquelle une modification technique devrait entraîner la mise à jour de la configuration, de la documentation, de la maintenance, des rechanges et de la formation ; **cette propagation n'existe pas** dans l'…
- - 🟢 Couverture de tests de l'état B : `assets` 493 fonctions de test. ⚪ Les écrans (plan du navire, grille, assistants de fiche) n'ont pas été rejoués dans un navigateur.
- - ⚪ Le détail de chacun des 29 modèles est dans le dictionnaire généré ; ce chapitre explique les mécanismes, pas chaque champ.
- - ⚪ La signification de **NNO** (« numéro de nomenclature OTAN ») est donnée par le libellé du champ du stock ; le champ du matériel porte seulement « NNO ».
- - ⚪ Le circuit de transfert n'existe pas : le comportement au moment d'une réaffectation en masse n'est pas décrit comme un circuit.
- - ⚪ Les pages Notion « 04 — Maintenance… » décrivent des objets cibles (composants, potentiels, configuration) **non développés** ; ils ne sont pas présentés comme existants.

### 12_maintenance_anomalies_tickets.md
- 2. **L'API « démarrer »** : elle écrit « En cours » **sans contrôler l'état de départ**, et un marin assigné peut l'appeler. L'occurrence quitte alors « En validation » sans que personne ne l'ait validée, alors que son compte rendu terminé reste « non conforme » : état **incohérent**, qui apparaît ensuite en retard. Une correcti…
- | Tâches (ch. 10) | Une tâche peut être rattachée à un objet ; création depuis une anomalie ⚪ non vérifiée |
- - ⚪ Les écrans (exécution, tournée, ticket) n'ont pas été rejoués dans un navigateur.
- - ⚪ Les envois de notifications (web push, e-mail) n'ont pas été rejoués ; seules leurs conditions de déclenchement sont décrites.

### 13_logistique.md
- ⚪ Dans l'état B, **la demande de pièces n'a pas de circuit d'approbation ni de commande réelle** : les états décrivent le suivi par le bord ; rien n'est transmis à un système d'approvisionnement.
- **Demandes de pièces** : demande par ticket (**Ouverte / Fermée**), lignes avec fournisseur, numéro de commande, coûts estimé et réel, dates de commande et de réception ; six états de ligne ; interface programmable (API) pour les tickets, les demandes et les lignes ; **le stock n'a pas de route API propre** ⚪.
- **Non trouvé dans le code examiné** (constat, pas une cible ; ⚪ absence déduite de la lecture des modèles et des routes) : approbation d'une demande, commande transmise à un fournisseur, réception comptable, valorisation du stock, inventaire planifié, réservation de pièces, transfert entre bâtiments, rattachement automatique d'u…
- - ⚪ Absence de circuit d'approbation pour les demandes de pièces : constatée au code, non confirmée comme voulue.
- - ⚪ Les envois de notifications n'ont pas été rejoués.
- - ⚪ Pas de page de détail rejouée dans un navigateur.

### 14_formations.md
- 🟢 **Qui est « l'organisme » ?** Dans Matrix, un organisme de formation est **une unité de type École ou Centre de formation**, avec sa propre hiérarchie et ses propres marins. La **réponse** (attribuer ou refuser des places, choisir ou créer une session) est donnée par **un référent de cette formation dans l'unité de l'organisme…
- ⚪ Aujourd'hui, la transition automatique « session effectuée → validation → qualification » n'existe pas : **c'est le référent qui enregistre la validation** (cible Notion, §14.10).
- - ⚪ Les envois de notifications (expiration, place libérée) n'ont pas été rejoués ; seules leurs conditions sont décrites.
- - ⚪ Le détail de la visibilité des dossiers de formation par rôle est dans le code (`dossiers_formation_visibles_q`) ; il n'est pas reproduit ici cas par cas.
- - ⚪ Le fonctionnement avec un organisme **réel hors Matrix** (sans unité créée) reste à préciser par le PO.

### 15_documentation_retex.md
- ⚪ **À confirmer avec les procédures métier applicables** : les **destinataires, les canaux et les responsabilités exacts** de la transmission. Aucune règle n'est inventée ici.
- | Annonces (ch. 9) | ⚪ Pas de lien automatique |
- - ⚪ **Couverture de tests faible** : `documentation` 9 fonctions de test, `retex` 5 fonctions (contre 493 pour `assets`). Les règles décrites viennent surtout de la lecture du code ; la suite des 7 paquets de l'ensemble 3 passe (1 491 tests), mais elle ne protège presque pas ces deux modules.
- - ⚪ Le modèle documentaire **cible** (bibliothèque unifiée, droits de lecture fins par document) n'est pas décrit : aucune décision correspondante n'a été lue.
- - ⚪ Les écrans n'ont pas été rejoués dans un navigateur.

### 16_preparation_appareillage.md
- **Matrix ne délivre pas l'autorisation opérationnelle d'appareiller** (`DEC-APP-13`, décision du PO). La session d'appareillage **atteste qu'une préparation a été menée et clôturée**, pas que le bâtiment est apte à appareiller. Le code le précise : la signature **atteste la clôture de la session**, pas l'aptitude du bâtiment (⚪ …
- - `DEC-APP-14` (**principe validé par le PO, conservé comme fonctionnement cible**) : le **chef de secteur propose** les contrôles et leur classification (**obligatoire**, **critique**) ; le **chef de service examine** la proposition ; le **COMANAV approuve le référentiel**, y compris les contrôles obligatoires et critiques. ⚪ L…
- ⚪ **À confirmer.** Qui, concrètement, valide la **classification** « critique » et comment elle s'accorde aux procédures du bord (`DEC-APP-14`) — aucune règle n'est inventée ici.
- | Quarts (ch. 8) | ⚪ Le mode du bâtiment (mer/quai) n'intervient pas dans l'ouverture d'une session |
- - ⚪ Les écrans n'ont pas été rejoués dans un navigateur.
- - ⚪ Aucune fiche de référence d'appareillage n'existe dans le code ; le cahier des charges et les pages Notion de procédures opérationnelles ne sont pas décrits comme existants.
- - ⚪ Le lien entre le mode MER/QUAI et la préparation n'est pas établi.

### 17_ergonomie_navigation.md
- ⚪ Le PO a relevé en recette un menu de **24 entrées** pour un équipier à 1366 × 768 (parfois coupé). Le regroupement en sept groupes répond à cette observation ; la recette sur poste réel n'a pas été rejouée ici.
- 🟢 **Ce qui existe.** Pages à mise en page fluide (Bootstrap) ; le cahier UX demande des zones d'action d'au moins 44 px sur les écrans opérationnels (⚪ non mesuré) ; QR code imprimable sur les fiches d'équipement qui ouvre le contrôle du jour, **manifeste d'application web** (nom, icônes, affichage « application ») et **service …
- ⚪ **Ce qui n'a pas été vérifié.** L'affichage sur téléphone et tablette réels, Safari sur iPhone, Firefox, lecteurs d'écran (VoiceOver, NVDA), Windows et l'impression physique : la checklist `docs/COMPATIBILITE_CHECKLIST.md` demande de noter ces contrôles « non effectué » quand ils ne sont pas rejoués ; **ils ne le sont pas dans…
- ⚪ Le **design system** (logo, charte graphique) vit dans le sous-module `design/`, **vide dans l'environnement de rédaction** : sa description vient des documents du dépôt, pas du sous-module.
- **Statut :** ce sont des **constats qualifiés « à décider »**, pas des règles. Le dossier ne les présente ni comme corrigés ni comme non corrigés dans l'état B ⚪ : seuls ceux qui ont un écart au registre sont suivis (A11 : libellé « Mes tours de services »). Le défaut de droits PO-17 (un matelot pouvait créer une feuille de serv…
- - ⚪ Aucune recette navigateur n'a été rejouée pour ce dossier (Chrome, Firefox, Safari, mobile, clavier, impression, lecteur d'écran).
- - ⚪ Sous-module `design/` non initialisé.
- - ⚪ Les observations PO-xx sont des constats d'un seul passage, non reproduits.

### 25_fonctionnement_cible.md
- ## 25.9 Orientations du cahier des charges, non décidées en lots 🔵⚪
- - ⚪ Le plan en 28 lots **est une proposition** ; ni l'ordre ni la taille ne sont engagés. Seules les décisions `DEC-…` citées sont validées par le PO.
- - ⚪ Les décisions et lots ont été relevés dans le dossier V1.2 (125 décisions) et dans les comptes rendus L01, L05, L02, L03 ; l'état des autres lots est « non lancé ».

### 26_historique_versions_lots.md
- - ⚪ Le dépôt compte **52 branches distantes** (à la date de l'inventaire) ; seules celles qui expliquent l'évolution sont analysées (annexe F, restreint). Les autres sont **listées sans analyse**.
- - ⚪ Les versions antérieures à septembre 2026 (premier code, anciennes phases) ne sont **pas reconstituées** : le dossier ne s'appuie que sur la feuille de route Notion pour cette période.
- - ⚪ Aucune **balise de version** (tag) n'existe : la V1 « non publiée » est repérée par son commit.
- - ⚪ Aucun **déploiement** n'est consigné : aucune version n'a été mise en production réelle (NO GO du PO).

### 04_organisation_technique.md
- - ⚪ PostgreSQL non exécuté (20 tests réservés à ce moteur ignorés) ; les unicités partielles et `select_for_update` ont leur comportement de référence sur PostgreSQL.
- - ⚪ Relations génériques vers une unité (discussions, notifications) non vérifiées lors de L03.
- - ⚪ L'archivage d'un bâtiment n'a pas d'écran Réglages.

### 05_comptes_autorisations_technique.md
- - ⚪ Les deux familles de comparaison (§5T.2) ne sont pas harmonisées : le comportement du commandant en second varie selon la vue. Le détail par vue est établi chapitre par chapitre.
- - ⚪ `BasicAuthentication` est acceptée par l'API en plus de la session : utile pour des scripts, à considérer pour l'exploitation (chapitre 23).
- - ⚪ Aucune limitation du nombre de tentatives de connexion n'a été trouvée dans le code ; « absent » signifie « non trouvé par recherche », pas preuve d'absence.
- - ⚪ PostgreSQL, Windows, navigateur : non rejoués.

### 06_accueil_pilotage_technique.md
- - ⚪ `a_faire` effectue plusieurs requêtes par type d'objet ; aucune mesure de performance n'a été faite.
- - ⚪ Le PDF n'a pas été rejoué (bibliothèques natives absentes de l'environnement).
- - ⚪ Chaque indicateur de la Vue flotte, de la Vue COMANAV et des dashboards transverses n'est pas détaillé ici.

### 07_calendrier_technique.md
- - ⚪ Le flux iCal est lié à la session : un client d'agenda externe qui ne conserve pas la session ne peut pas s'abonner sans mécanisme complémentaire (non étudié).
- - ⚪ Le détail HTMX du panneau (fil, démarrage d'une tâche) n'a pas été rejoué dans un navigateur.

### 08_quarts_services_feuille_technique.md
- - ⚪ PostgreSQL : les verrous (`select_for_update`) et les unicités partielles ont leur comportement de référence sur ce moteur ; non rejoué.
- - ⚪ `peut_publier_liste` itère sur les utilisateurs actifs pour trouver les destinataires (`publicateurs_a_notifier`) : comportement connu ; aucune mesure de performance faite.
- - ⚪ Le détail des écrans (vue quotidienne, vue responsable) n'a pas été rejoué dans un navigateur.

### 09_communication_technique.md
- - ⚪ Relations génériques (`Thread`, `Notification`) non contrôlées face à la suppression d'un objet visé (chapitre 19).
- - ⚪ La requête de `peut_publier_liste` / `publicateurs_a_notifier` (chapitre 8) boucle sur les utilisateurs actifs ; mesure de performance non faite.
- - ⚪ Web Push : **HTTPS requis** hors développement ; non éprouvé sur appareil réel ; navigateurs concernés non étudiés.
- - ⚪ Le courrier électronique n'est pas utilisé pour les notifications (configuration console par défaut).

### 10_taches_demandes_programme_postes_technique.md
- - ⚪ `programme` et `postes` sont peu couverts par des tests propres ; leur description repose sur le code.
- - ⚪ `peut_superviser` compare au **grade**, `peut_attribuer` au **niveau d'écriture** : même schéma de deux comparaisons qu'au chapitre 5 (le commandant en second y est concerné).
- - ⚪ Aucune API REST pour les tâches et les demandes : tout passe par les vues web (et HTMX).

### 11_materiel_installations_technique.md
- - ⚪ Les écrans (plan du navire, grille, assistants de fiche) n'ont pas été rejoués dans un navigateur.
- - ⚪ Aucun circuit de transfert de matériel n'existe (A18).

### 12_maintenance_anomalies_tickets_technique.md
- - ⚪ Les envois de notifications ne sont pas rejoués.

### 13_logistique_technique.md
- - ⚪ Aucun circuit d'approbation de commande dans `logistics/` ; aucune décision V1.2 sur le stock.
- - ⚪ Les envois de notifications ne sont pas rejoués.

### 14_formations_technique.md
- - ⚪ Un organisme de formation est une unité de type École ou Centre de formation (`org/models.py` `Ship.type_unite`) ; pas de dossier vivant ni de transmission formalisée (A19).
- - ⚪ Pas de transition automatique session → qualification.

### 15_documentation_retex_technique.md
- - ⚪ Couverture de tests faible pour ces deux paquets : les règles décrites viennent surtout de la lecture du code.
- - ⚪ Circuit RETEX en une étape (A15) ; pas de transmission à l'organisme (A16).

### 16_preparation_appareillage_technique.md
- - ⚪ Aucune fiche de référence d'appareillage dans le code (A17).
- - ⚪ L'affichage de la précision « la signature n'atteste pas l'aptitude » n'a pas été vérifié à l'écran.

### 17_ergonomie_navigation_technique.md
- - ⚪ Aucune recette navigateur rejouée ; sous-module `design/` vide.
- - ⚪ Les observations PO-xx de la recette V1.1 ne sont pas rapprochées une à une du code de l'état B.

### 18_architecture.md
- Bibliothèques **présentes dans les dépendances mais sans usage constaté dans le code** (recherche textuelle) : `boto3`, `requests` ; `django-storages` est déclaré parmi les applications installées, mais le stockage des fichiers est celui du système de fichiers local (`matrix/settings.py:398`). Aucune ne déclenche d'appel externe…
- Certaines tâches s'exécutent **chaque minute** et décident elles-mêmes, par marin, s'il est temps de notifier (heure du matin et du soir propre à chacun) : leur nom contient « daily » ou « minute » sans que cela reflète toujours la cadence réelle de planification. ⚪ Le détail est traité au chapitre 21.
- - ⚪ Versions : lues dans `requirements.txt` de l'état B ; non vérifiées par une installation à neuf dans cet environnement (l'installation de `pywebpush` y a demandé l'option `--use-pep517`, comme l'indique le README).
- - ⚪ PostgreSQL 16 : version de l'image `docker-compose.yml` ; le moteur n'a pas été exécuté ici.
- - ⚪ Aucun test de charge ni mesure de performance n'a été trouvé ou réalisé.

### 19_modeles_donnees.md
- - **12 modèles portent un champ UUID** (pas devinable, stable d'une base à l'autre), le plus souvent comme clé primaire : `Asset`, `Installation`, `DocumentInstallation`, `ChecklistItemTemplate`, `CategorieCatalogue`, `ArticleCatalogue`, `PropositionArticle`, `CompteRenduCorrectif`, `CorrectiveTicket`, `RubriqueEnTeteFeuilleServ…
- ⚪ **Non vérifié.** Ces six liens n'ont pas été contrôlés vis-à-vis de la suppression ou de l'archivage d'une **unité** lors du lot L03 (compte rendu, risque résiduel 3) : un objet désignant une unité par relation générique ne serait pas compté par le contrôle de suppression. À vérifier avant une mise en production (chapitre 23).
- - ⚪ Les nombres sont ceux de l'état B ; ils changeront avec les lots suivants. Les chiffres de ce chapitre sont tous issus de l'inventaire généré et se régénèrent avec `outils/inventaire.py`.
- - ⚪ Certains modèles secondaires (`InstallationBigrameChoice`, `ChefResponsableSpecialite`, `ParametresPassation`…) ne sont décrits qu'au dictionnaire ; leur usage fonctionnel est traité dans les chapitres de domaine.
- - ⚪ PostgreSQL : l'état B contient des contraintes d'unicité partielle (relève, période d'équipage) dont la référence de comportement est PostgreSQL ; non exécuté ici.
- - ⚪ La conservation des journaux, des notifications lues et des estimations n'est pas définie (information manquante IM-10 du dossier V1.2).

### 20_api_interfaces.md
- - **Modules désactivés** : l'API **continue de répondre** même si le module est désactivé pour le bâtiment ; seules les pages web sont bloquées (vérifié par test le 12/11/2026 : lecture et écriture API, administration Django, tâches planifiées et enchaînements internes continuent ; l'accueil et le calendrier continuent aussi d'a…
- - **Pas de pagination configurée** et **pas de limitation de débit** (⚪ non trouvés dans le code) : une grosse collection est renvoyée entièrement ; un intégrateur doit filtrer.
- | Calendrier personnel dans un autre agenda | **iCal** `calendar/ical/my/` (`calendar_app/ical_views.py:13`) | 🟢 ; ⚪ sans tâches ni programme |
- | Bilan imprimable | **PDF** par WeasyPrint | 🟢 facultatif : bibliothèques natives (GTK) absentes par défaut sous Windows ; ⚪ non rejoué |
- - ⚪ Aucun appel HTTP réel n'a été rejoué sur l'API pour ce dossier ; la liste vient de l'inventaire des routes (annexe C) et de la lecture du code.
- - ⚪ Pas de test de charge, pas de mesure de performance.

### 21_interactions_modules.md
- ⚠ **Sans worker Celery et sans beat, aucune alerte automatique n'est produite**, même si la donnée qui la déclenche est visible (README). Redis doit tourner. Une panne de ces processus ne produit **aucun message d'erreur côté application** (⚪ aucune supervision livrée).
- - **Relations génériques** : une suppression d'unité ou d'objet doit rester cohérente avec elles (⚪ cas « relations génériques vs suppression d'unité » non rejoué).
- - ⚪ Les enchaînements asynchrones n'ont pas été rejoués avec Redis et Celery réels ; ils sont décrits depuis le code et les tests unitaires.
- - ⚪ Aucune mesure de performance des signaux ou des tâches.

### 22_securite.md
- - ⚪ Le journal est une table ordinaire de la base : il n'est pas scellé contre une modification par quelqu'un qui aurait un accès direct à la base. Sa durée de conservation n'est pas définie (information manquante IM-10 du dossier V1.2).
- - ⚪ La page Notion « 07 — SIC, cyber, protection-défense et conformité » a été lue : elle définit des **principes** (utilisable = fonctionne + conforme + contrôlé + autorisé ; chaîne sécurité/protection : commandant en second, COMANAV adjoint sécurité, COMAEQ adjoint protection ; à distinguer des scénarios incendie et voie d'eau…
- - ⚪ Aucune limitation du nombre de tentatives de connexion, ni en-tête de politique de sécurité de contenu, ni HSTS n'a été trouvé dans la configuration. « Absent » signifie « non trouvé par recherche ».
- - ⚪ `CSRF_TRUSTED_ORIGINS` est une liste fixe dans `matrix/settings.py:413` (localhost) ; un déploiement sous un autre nom d'hôte demande de l'adapter. À traiter au chapitre 23.
- - ⚪ Le courrier est écrit dans la console par défaut : aucune réinitialisation par e-mail ; le mot de passe provisoire est affiché à l'administrateur.
- - ⚪ PostgreSQL, Windows et navigateur n'ont pas été rejoués ; les risques résiduels déclarés par les comptes rendus L01 (Windows, acte volontaire d'un opérateur sur une base réelle) et L05 (valeurs triviales longues acceptées) restent valables.
- - ⚪ Les relations génériques (chapitre 19) ne sont pas protégées par la base.

### 23_configuration_deploiement_exploitation.md
- | **Production** | PostgreSQL recommandé | `DJANGO_DEBUG=0` : garde-fous au démarrage | ⚪ Non autorisée ; aucune instance décrite |
- | **Application** | `python manage.py runserver` (développement) | ⚪ **Aucun serveur d'application de production n'est livré** : ni `gunicorn`, ni `uvicorn` dans les dépendances ; l'interface WSGI/ASGI existe (`matrix/wsgi.py`, `matrix/asgi.py`). Le choix est à faire avec les SIC |
- - ⚪ **Non trouvés dans le code** : réglage d'un **proxy inverse** (`SECURE_PROXY_SSL_HEADER`), **HSTS**, configuration de **journalisation** (`LOGGING`), **limitation des tentatives de connexion**. Les origines CSRF de confiance sont **codées en dur sur `localhost`/`127.0.0.1:8000`** : à revoir selon l'architecture réelle (nom d…
- **Checklist avant production** (déduite du code et du README ; ⚪ pas une procédure validée) :
- 4. Serveur HTTPS et serveur d'application choisis **avec les SIC** ⚪.
- 5. `python manage.py migrate` après **sauvegarde** de la base ⚪ (procédure à fournir) ; `collectstatic`.
- 8. Worker et beat lancés et **supervisés** ⚪ ; Redis disponible.
- ⚪ **Windows** : la recette Windows (`docs/recette/L01_recette_windows.md`) existe ; le kit a été testé sous **Linux**, pas sous Windows. **Safari/iPhone** : exige un environnement mobile isolé approuvé, sinon « non effectué ».
- - ⚪ **Retour arrière** : aucune procédure fournie ; la restauration d'une sauvegarde est la seule voie sûre.
- ## 23.9 Sauvegarde et restauration ⚪
- Ce qui reste **à définir avec les SIC** : outil, fréquence, support, chiffrement, durée de conservation, essai de restauration, restauration depuis le bord vers la terre. **Aucune règle n'est inventée ici.** Redis ne porte que la file des tâches ; ⚪ la perte de Redis ne doit pas perdre de données métier, mais **l'effet d'une per…
- - **Journaux techniques** : aucune configuration de journalisation Django ; `start.bat` écrit `celery.log` et `celery-beat.log` à la racine ; ⚪ pas de rotation, pas de centralisation.
- - **Supervision** de Redis, de Celery, de la base, de l'espace disque : ⚪ **rien de livré**.
- 1. Pas de **haute disponibilité** : un serveur, une base ; ⚪ aucun plan de reprise.
- ## 23.12 Cible et à définir 🔵⚪
- - Exigences de la page Notion « 07 — SIC, cyber, protection-défense et conformité » : elle décrit l'organisation (DIRISI, CMC2, logique d'incident, conformité « utilisable = fonctionne + conforme + contrôlé + autorisé »), **sans exigence technique chiffrée** pour Matrix ; ⚪ aucune exigence SIC opposable n'a été fournie.

### 24_qualite_contribution.md
- ## 24.2 Ce qui n'est pas couvert ⚪
- - **Test utilisateur à l'aveugle** : le protocole de recette UX (4 marins) est défini dans Notion ; ⚪ ses résultats ne sont pas dans ce dossier.
- - ⚪ La suite complète n'a pas été rejouée ; les chiffres viennent des comptes rendus de lots.
- - ⚪ Le nombre de **fonctions de test** (≈ 3 950) compté par lecture ne coïncide pas exactement avec le nombre de **tests** exécutés (3 963) : les tests paramétrés ou hérités expliquent l'écart.
- - ⚪ Le fonctionnement réel des agents (PO, Développeur, Relecteur) est décrit d'après leurs fichiers de configuration, non observé dans ce dossier.

### 26_historique_branches_technique.md
- ## 26T.4 Limites : ce qui n'est pas analysé ⚪
