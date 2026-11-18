# Lire ce registre

> **Public :** PO, responsables, mainteneurs · **Accès restreint** · Source unique : `registre.json` (généré).

Ce registre rassemble les **écarts** entre ce que le PO a décidé et ce que fait le logiciel, les **points à confirmer**, les **propositions** non arbitrées, les **anomalies du dossier** et l'**état des {{fait:n_decisions_v12}} décisions**. Un écart est **documenté, pas autorisé à corriger** : il ne modifie ni le logiciel ni une décision du PO.

| Niveau de preuve | Signification |
|---|---|
| [C] | lu dans le code de l'état B |
| [N] | vérifié dans le navigateur (instance de démonstration, données fictives) |
| [T] | vérifié par un test exécuté |
| [V] | vérifié visuellement |
| [A] | mesure automatique |
| [R] | rapporté par une source antérieure, non revérifié |
| [?] | non vérifié |

**Répartition :** 26 écarts, 8 points à confirmer, 7 propositions, 7 nouveaux écarts du logiciel, 38 anomalies documentaires (36 ouvertes), 125 décisions.

# Écarts du logiciel (A1 à A26)

## A1 — Administrateur technique et actes métier

| Rubrique | Contenu |
|---|---|
| **Règle validée** | Un administrateur technique ne devient pas automatiquement autorité de validation métier : il désigne les titulaires, sans viser à leur place. Application mécanique d'un transfert approuvé autorisée. (`DEC-DRT-02`, source S1 §4, DP-09, cahier §5, Notion « 13 — Décisions ») |
| **Constat dans l'état B** | Le niveau numérique de l'administrateur d'unité (8) est supérieur ou égal à tous les seuils par défaut des actions métier du registre (annexe B, colonne « Admin. unité »). Dans les circuits des quarts, il franchit la **supervision du commandement** (`NIVEAU_SUPERVISION_GLOBALE_LISTE = COMMANDANT`, `quarts/models.py:147`) : il peut gérer et **publier** les listes de son bâtiment (`peut_publier_liste`, `quarts/models.py:355`), **valider ou refuser** un échange de tours (`peut_valider_echange`, `quarts/echanges.py:205`) et viser aux paliers « secteur » et « service » de la feuille de service (`_supervision_sur_navire`, `quarts/models.py:1977`). Le visa du COMAEQ et la rédaction de la feuille de service lui restent fermés (`peut_viser_comaeq` `:2215` ; `peut_rediger_feuille_service` `:2065`). |
| **Conséquences** | *Fonctionnelles* : un administrateur technique peut trancher des échanges et publier des listes alors que la règle le lui interdit. *Sécurité / traçabilité* : l'acte est tracé au nom de l'administrateur, mais il brouille la séparation des pouvoirs voulue entre administration de la plateforme et autorité métier. Pas de contournement d'authentification : l'écart est dans la **répartition** des droits. |
| **Sources et preuves** | `matrix/core/roles.py:4` (niveaux) ; `matrix/core/role_thresholds.py:45` (seuils) ; `quarts/models.py:147,355,1977,2065,2215` ; `quarts/echanges.py:205` ; annexe B ; dossier V1.2 `A_REGISTRE_DECISIONS.md` (`DEC-DRT-02`), `M_PLAN_DEVELOPPEMENT.md` (L06) |
| **Profils concernés** | administrateur d'unité ; commandement |
| **Lot de correction prévu** | L06 — Exclusion de l'administrateur technique des actes métier (non lancé) |
| **Niveau de preuve** | [C] |
| **Statut** | documenté, non arbitré (pas une autorisation de modifier le logiciel) |

## A2 — Échanges de tours

| Rubrique | Contenu |
|---|---|
| **Règle validée** | La décision finale revient au COMAEQ ou à son suppléant officiellement habilité. Le BSC ou le chef de liste peut **instruire** la demande, mais n'a pas automatiquement l'autorité de décision finale. Cette décision **remplace** la note Notion du 28/10 (« le chef de liste habilité valide »). (`DEC-FDS-07`, `DEC-FDS-13` ; sources S1 §7, S3 ; `J_TRIAGE_ET_ARBITRAGES.md` §2) |
| **Constat dans l'état B** | Un échange accepté par le marin sollicité attend « le chef de liste » (`STATUT_ACCEPTE` : « En attente du chef de liste »). La validation et le refus sont ouverts à qui **gère la liste** (`peut_valider_echange`, `quarts/echanges.py:205`, qui s'appuie sur `peut_gerer_liste`, `quarts/models.py:297`) : le chef de liste désigné pour le périmètre exact de la liste, ou le commandement du bâtiment (niveau commandant et au-dessus). Aucune règle ne désigne le COMAEQ ni un suppléant. À défaut de chef de liste désigné, la notification va au créateur de la liste (`chefs_de_liste_a_notifier`, `quarts/echanges.py:176`). |
| **Conséquences** | *Fonctionnelles* : l'autorité qui tranche n'est pas celle décidée ; un chef de liste (qui peut être un chef de section) valide seul un échange de service à quai. Le COMAEQ n'est ni notifié ni habilité. *Sécurité* : sans suppléance officielle, la règle cible ne peut pas être appliquée telle quelle (voir B3). |
| **Sources et preuves** | `quarts/echanges.py:176,205,342` ; `quarts/models.py:297,855` ; dossier V1.2 (J_TRIAGE_ET_ARBITRAGES) (CT-01) ; `B_CARTOGRAPHIE.md` (circuit « Échange de tours ») |
| **Profils concernés** | marins ; chefs de liste ; COMAEQ |
| **Lot de correction prévu** | L10 — Échanges de tours décidés par le COMAEQ (non lancé) ; dépend de la suppléance explicite (L08) |
| **Niveau de preuve** | [C] |
| **Statut** | documenté, non arbitré (pas une autorisation de modifier le logiciel) |

## A3 — Publication des listes de quarts et de gardes

| Rubrique | Contenu |
|---|---|
| **Règle validée** | Le chef de liste **prépare et propose** ; le COMAEQ ou son suppléant officiellement habilité **approuve et publie**. Toute modification après publication est tracée et donne lieu à une nouvelle version officielle si nécessaire. (`DEC-FDS-14`, S4 arbitrage C-1) |
| **Constat dans l'état B** | Le chef de liste propose (`proposer`, `quarts/models.py` : statut `PROPOSEE`) ; la publication (`publier`) est ouverte à `peut_publier_liste` (`quarts/models.py:355`) : (a) le commandement du bâtiment (commandant, administrateur d'unité, administrateur général sur son périmètre) ; (b) tout rôle atteignant le seuil configurable `liste_service_publication` (**chef de service** par défaut) **et** dont le périmètre personnel est **exactement** celui de la liste ; le commandant en second est explicitement exclu (`_perimetre_dans_scope_utilisateur`, `:308`). La **fonction COMAEQ n'intervient pas** : un COMAEQ ne publie que si sa propre portée est celle de la liste ou s'il est commandement. |
| **Conséquences** | *Fonctionnelles* : la publication relève d'un chef de service du périmètre ou du commandement ; l'autorité fonctionnelle « vie à bord » n'est pas mobilisée. *Sécurité* : le seuil est réglable par bâtiment : un bâtiment peut l'abaisser et élargir qui publie. |
| **Sources et preuves** | `quarts/models.py:297,308,355,373,423` ; `matrix/core/role_thresholds.py` (clé `liste_service_publication`) ; `A1_DECISIONS_S1_S2.md` (`DEC-FDS-14`), `J_TRIAGE_ET_ARBITRAGES.md` (CT-04, C-1) |
| **Profils concernés** | chefs de liste ; chefs de service ; COMAEQ ; commandement |
| **Lot de correction prévu** | L09 — Visas par fonction et listes publiées (non lancé ; découpé en trois) |
| **Niveau de preuve** | [C] |
| **Statut** | documenté, non arbitré (pas une autorisation de modifier le logiciel) |

## A4 — Droits du commandant en second

| Rubrique | Contenu |
|---|---|
| **Règle validée** | Le commandant en second est le remplaçant désigné du commandant et a une **vision globale**. Ses droits d'écriture **découlent de ses responsabilités métier réelles**, et non d'un simple seuil « commandant ou plus ». Il publie des annonces sur son bâtiment, garde la suppléance du commandant pour la validation de la relève, n'a pas le visa COMA. (Notion « 13 — Décisions » 10/10 et recette V1 ; dossier V1.2 `DEC-DRT-01`) |
| **Constat dans l'état B** | Deux familles de comparaison coexistent. Pour l'**API** et les vues qui utilisent `niveau_ecriture`, son écriture héritée du grade est **retirée** (il retombe au niveau équipier, `ROLES_SANS_ECRITURE_HERITEE`, `matrix/core/roles.py:50`), sauf action explicitement ouverte (`annonce_publication`). Pour de **nombreuses vues web**, le seuil est comparé à son **grade** (`user_role_level`) : il peut alors gérer les modules (`matrix/views.py:289`), saisir le programme (`programme/services.py:47`), proposer des fiches (`assets/fiche_validation.py:130`), voir l'annuaire (`matrix/core/navigation.py`). Dans les circuits des quarts, il est exclu de la désignation, du visa et de la publication (`quarts/models.py:308`). |
| **Conséquences** | *Fonctionnelles* : ce que le second peut faire dépend de la page utilisée, non d'une liste de responsabilités qui lui sont attribuées. *Sécurité* : un même acte peut être refusé par l'API et accepté par l'écran correspondant. |
| **Sources et preuves** | `matrix/core/roles.py:50,53` ; `niveau_pour_action` (`matrix/core/role_thresholds.py:273`) ; gestion des modules (`matrix/views.py:289`) ; `programme/services.py:47` ; `assets/fiche_validation.py:130` ; annexe B (colonne ✱) ; Notion « 13 — Décisions » |
| **Profils concernés** | commandant en second |
| **Lot de correction prévu** | Aucun lot identifié ne traite spécifiquement l'harmonisation (voir B2). Liens : L07 (rattachement et validation des rôles), L09 (visas par fonction). |
| **Niveau de preuve** | [C] |
| **Statut** | documenté, non arbitré (pas une autorisation de modifier le logiciel) |

## A5 — Identifiants stables pour de futures interfaces

| Rubrique | Contenu |
|---|---|
| **Règle validée** | Règles du projet : « garder des identifiants stables (UUID, NNO) pour de futures API » (`CLAUDE.md`) |
| **Constat dans l'état B** | UUID et NNO existent côté matériel, catalogue, ticket, objets de la feuille de service ; ni compte, ni unité, ni tâche, ni liste |
| **Conséquences** | Un futur interfaçage devra s'appuyer sur d'autres identifiants pour les personnes et les unités ; pas d'effet sur le fonctionnement actuel |
| **Sources et preuves** | `couverture/etat_B/MODELES.md` ; `assets/models.py:259,496,736,798` |
| **Profils concernés** | développeurs ; intégrateurs |
| **Lot de correction prévu** | Aucun (périmètre à décider) |
| **Niveau de preuve** | [C] |
| **Statut** | documenté, non arbitré (pas une autorisation de modifier le logiciel) |

## A6 — Documentation du dépôt en retard sur le nombre d'applications

| Rubrique | Contenu |
|---|---|
| **Règle validée** | `docs/REFERENCE.md` §4 « Les 14 apps Django » |
| **Constat dans l'état B** | L'état B contient 21 applications et le noyau (paquet `matrix/core`) |
| **Conséquences** | Documentation du dépôt en retard ; pas d'effet fonctionnel |
| **Sources et preuves** | `docs/REFERENCE.md:74` (section) ; `INSTALLED_APPS` |
| **Profils concernés** | développeurs |
| **Lot de correction prévu** | L28 (dette documentaire) |
| **Niveau de preuve** | [C] |
| **Statut** | documenté, non arbitré (pas une autorisation de modifier le logiciel) |

## A7 — Modèle de droits sans moteur d'attributs général

| Rubrique | Contenu |
|---|---|
| **Règle validée** | Cahier §35 : « RBAC + ABAC + périmètre + responsabilité » |
| **Constat dans l'état B** | Rôle + périmètre + attributs ciblés (équipage, fonction de commandant adjoint) + désignations ; pas de moteur d'attributs général |
| **Conséquences** | Les règles à attributs sont codées au cas par cas (« configuration plutôt que code » partielle) |
| **Sources et preuves** | chapitre 5 |
| **Profils concernés** | responsables ; développeurs |
| **Lot de correction prévu** | — |
| **Niveau de preuve** | [C] |
| **Statut** | documenté, non arbitré (pas une autorisation de modifier le logiciel) |

## A8 — Cahier des charges partiellement obsolète

| Rubrique | Contenu |
|---|---|
| **Règle validée** | Cahier §8, §10, §11 (génération automatique des tours) ; §20 (rondes) ; organisation « miroir » |
| **Constat dans l'état B** | Génération abandonnée (décision du 09/10) ; rondes retirées ; organisation miroir retirée |
| **Conséquences** | Documentation du cahier partiellement obsolète ; **le dossier décrit le code** |
| **Sources et preuves** | chapitres 1, 4, 18 |
| **Profils concernés** | PO |
| **Lot de correction prévu** | Alignement Notion par le PO |
| **Niveau de preuve** | [C] |
| **Statut** | documenté, non arbitré (pas une autorisation de modifier le logiciel) |

## A9 — Principe « Internet n'existe pas » et dépendances déclarées

| Rubrique | Contenu |
|---|---|
| **Règle validée** | Principe « Internet n'existe pas » |
| **Constat dans l'état B** | Tenu par le code ; `boto3` et `requests` déclarés sans usage constaté |
| **Conséquences** | Aucune ; observation d'exploitation |
| **Sources et preuves** | chapitre 18 |
| **Profils concernés** | exploitants |
| **Lot de correction prévu** | — |
| **Niveau de preuve** | [C] |
| **Statut** | documenté, non arbitré (pas une autorisation de modifier le logiciel) |

## A10 — Vocabulaire cible sans équivalent dans le code

| Rubrique | Contenu |
|---|---|
| **Règle validée** | Vocabulaire cible de Notion 11 (mission, capacité, dérogation…) |
| **Constat dans l'état B** | Sans équivalent dans le code |
| **Conséquences** | Cible non développée |
| **Sources et preuves** | chapitre 19 |
| **Profils concernés** | PO |
| **Lot de correction prévu** | — |
| **Niveau de preuve** | [C] |
| **Statut** | documenté, non arbitré (pas une autorisation de modifier le logiciel) |

## A11 — Libellé « Mes tours de service »

| Rubrique | Contenu |
|---|---|
| **Règle validée** | « Mes tours de **services** » (`DEC-UX-08`, S1 §12 ; `CT-06`) |
| **Constat dans l'état B** | L'accueil affiche « Mes tours de **service** » |
| **Conséquences** | Libellé : purement visuel |
| **Sources et preuves** | `matrix/templates/dashboard/aujourdhui.html:57` |
| **Profils concernés** | marins |
| **Lot de correction prévu** | Lot UX (L24) |
| **Niveau de preuve** | [C] |
| **Statut** | documenté, non arbitré (pas une autorisation de modifier le logiciel) |

## A12 — Impression de la feuille de service

| Rubrique | Contenu |
|---|---|
| **Règle validée** | **Fonctionnement cible** : impression A4 de la feuille de service par le BSC, signalement de la nécessité de réimprimer une feuille déjà affichée, et **réimpression avec versionnement** (`DEC-FDS-04`, `DEC-FDS-05`, `DEC-FDS-06`) |
| **Constat dans l'état B** | Les versions de la feuille sont conservées (VersionFeuilleService). **Une impression par le navigateur existe** (bouton « Imprimer » de la fiche de la feuille, constat AUD-002, vérifié dans le navigateur le 12/11/2026) ; il n'existe ni mise en page A4 dédiée à l'affichage, ni alerte de réimpression, ni réimpression versionnée. |
| **Conséquences** | Le BSC imprime avec les moyens du navigateur ; pas d'alerte de remplacement d'un affichage |
| **Sources et preuves** | `matrix/templates/quarts/liste_detail.html` (impression) ; absence dans `feuille_service_detail.html` |
| **Profils concernés** | BSC ; COMAEQ |
| **Lot de correction prévu** | L27 |
| **Niveau de preuve** | [C][N] |
| **Révision** | Texte révisé : l'ancien énoncé « aucune page imprimable » était inexact (AUD-002). |
| **Statut** | documenté, non arbitré (pas une autorisation de modifier le logiciel) |

## A13 — Priorités de tâche : deux niveaux au lieu de trois

| Rubrique | Contenu |
|---|---|
| **Règle validée** | Trois priorités : normale, haute, urgente ; priorité du chef de secteur non abaissable par le chef de section (`DEC-TAC-04`, `DEC-TAC-05`) |
| **Constat dans l'état B** | Deux priorités : normale, urgente ; pas de règle d'abaissement |
| **Conséquences** | Perte d'un niveau de nuance ; pas de règle de hiérarchie des priorités |
| **Sources et preuves** | `taches/models.py:38-43` |
| **Profils concernés** | chefs de secteur ; chefs de section |
| **Lot de correction prévu** | L14 |
| **Niveau de preuve** | [C] |
| **Statut** | documenté, non arbitré (pas une autorisation de modifier le logiciel) |

## A14 — Confidentialité de la synthèse de passation

| Rubrique | Contenu |
|---|---|
| **Règle validée** | Synthèse de passation : un chef de section ne consulte que **sa propre section** (Notion « 13 — Décisions », recette V1) |
| **Constat dans l'état B** | `syntheses_visibles` (`dashboard/passation.py:53`) filtre par bâtiment et équipage, **sans borne par section** ; le contenu figé couvre tout le bâtiment (`contenu_passation`, `dashboard/passation.py:220`) ; le code assume « l'équipage montant lit tout ». **Test du 12/11/2026 (état B, comptes fictifs, deux sections)** : un chef de section lit les tâches, blocages et anomalies de l'autre section ; équipier, chef d'un autre bâtiment, chef sans équipage et chef d'un troisième équipage refusés |
| **Conséquences** | Un chef de section peut lire la synthèse de tout le bâtiment (qualifications, annonces, listes, tâches). Écart confirmé ; **aucune fuite réelle alléguée** ; la règle du PO n'est pas modifiée |
| **Sources et preuves** | `dashboard/passation.py:53,220` ; `PassationView` (`dashboard/passation.py:306`) ; Notion « 13 » |
| **Profils concernés** | chefs de section ; commandement ; équipage sortant |
| **Lot de correction prévu** | Non identifié |
| **Vérifications** | test 12/11/2026 (8 tests, comptes fictifs) ; navigateur 12/11/2026 : chef de section de l'équipage sortant lit 28 tâches dont 12 hors de sa section ; équipier et chef d'un autre bâtiment : 404 |
| **Niveau de preuve** | [T][N] |
| **Statut** | documenté, non arbitré (pas une autorisation de modifier le logiciel) |

## A15 — Circuit de validation des RETEX

| Rubrique | Contenu |
|---|---|
| **Règle validée** | Circuit RETEX : auteur → chef de section → chef de secteur → chef de service (`DEC-RTX-01`) ; correction motivée, nouvelle version (`DEC-RTX-02`, `DEC-RTX-03`) |
| **Constat dans l'état B** | Une seule étape : tout habilité du bâtiment (seuil `retex_validation`, chef de service) valide ou refuse ; les fonctions citant le COMA référent passent en premier dans la notification ; pas de demande de correction |
| **Conséquences** | Un RETEX peut être validé sans visa de la hiérarchie directe de l'auteur ; pas de boucle de correction |
| **Sources et preuves** | `retex/services.py:54` (`valideurs`), `peut_valider` ; seuil dans `matrix/core/role_thresholds.py` |
| **Profils concernés** | auteurs de RETEX ; chefs de section, de secteur et de service |
| **Lot de correction prévu** | L11 |
| **Niveau de preuve** | [C] |
| **Statut** | documenté, non arbitré (pas une autorisation de modifier le logiciel) |

## A16 — Diffusion « flotte » d'un RETEX

| Rubrique | Contenu |
|---|---|
| **Règle validée** | Diffusion « flotte » : proposé à l'organisme destinataire |
| **Constat dans l'état B** | La diffusion « flotte » **marque** le RETEX ; aucune transmission n'existe |
| **Conséquences** | L'organisme n'est jamais saisi ni notifié par Matrix ; qui transmet est **à confirmer** |
| **Sources et preuves** | `retex/models.py` (`diffusion`, `organisme`) |
| **Profils concernés** | auteurs de RETEX ; organismes destinataires |
| **Lot de correction prévu** | L11 |
| **Niveau de preuve** | [C] |
| **Statut** | documenté, non arbitré (pas une autorisation de modifier le logiciel) |

## A17 — Préparation à l'appareillage : fiche de référence et circuit

| Rubrique | Contenu |
|---|---|
| **Règle validée** | Préparation à l'appareillage : contrôles issus de fiches de référence approuvées ; circuit section/secteur → service → COMANAV ; contrôles obligatoires, critiques non dérogeables, réserves (`DEC-APP-01`, `DEC-APP-02`, DEC-APP-10, DEC-APP-11, DEC-APP-12, `DEC-APP-14`) |
| **Constat dans l'état B** | Les points sont calculés à l'ouverture depuis l'état des installations critiques ; une seule signature (chef de secteur ou plus) ; ni classification, ni réserve, ni fiche de référence |
| **Conséquences** | Aucun circuit COMANAV ; la signature atteste la clôture de la session, pas l'aptitude. Compatibilité avec les procédures du bord **à confirmer avant implémentation** |
| **Sources et preuves** | `_points_de_vigilance_navire` (`dashboard/web_views.py:367`) ; `SessionAppareillageSignerView` (`dashboard/web_views.py:664`) |
| **Profils concernés** | chefs de secteur ; chefs de service ; COMANAV |
| **Lot de correction prévu** | L23 |
| **Niveau de preuve** | [C] |
| **Statut** | documenté, non arbitré (pas une autorisation de modifier le logiciel) |

## A18 — Transfert de matériel entre secteurs et services

| Rubrique | Contenu |
|---|---|
| **Règle validée** | Transfert de matériel entre secteurs et entre services avec approbations (DEC-MAT-01, DEC-MAT-02, DEC-MAT-03, DEC-MAT-04) |
| **Constat dans l'état B** | Aucun circuit ; réaffectation par l'affectation en masse |
| **Conséquences** | Pas de trace d'approbation du transfert ni de suivi des tâches ouvertes |
| **Sources et preuves** | `assets/` (aucune vue de transfert) |
| **Profils concernés** | chefs de service ; gestionnaires de matériel |
| **Lot de correction prévu** | L13 |
| **Niveau de preuve** | [C] |
| **Statut** | documenté, non arbitré (pas une autorisation de modifier le logiciel) |

## A19 — Demande de places de formation

| Rubrique | Contenu |
|---|---|
| **Règle validée** | Demande de places : l'organisme de formation répond dans un **dossier vivant** (timeline, fil, transmission, prise en compte) — cible Notion « 03 » |
| **Constat dans l'état B** | L'organisme est une **unité de type École ou Centre de formation** ; un référent de la formation dans cette unité attribue ou refuse (`_attribuer_places`) ; le demandeur est notifié. Pas de timeline, pas de fil systématique, pas d'étape « transmise à l'organisme » pour la demande de places |
| **Conséquences** | Cible non développée ; correction par rapport au rapport E3 (qui disait que l'organisme n'était pas un acteur) |
| **Sources et preuves** | `_attribuer_places` (`training/web_views.py:1311`) ; `org/models.py` |
| **Profils concernés** | référents de formation ; demandeurs ; organismes de formation |
| **Lot de correction prévu** | Cible Notion « 03 » |
| **Niveau de preuve** | [C] |
| **Statut** | documenté, non arbitré (pas une autorisation de modifier le logiciel) |

## A20 — Échéance « En validation » : règle de sortie

| Rubrique | Contenu |
|---|---|
| **Règle validée** | Occurrence non conforme : état « En validation » (pas de règle de sortie décidée par le PO) |
| **Constat dans l'état B** | **Vérifié par test (12/11/2026)** : aucune action de validation dédiée ; sorties : (1) correction du compte rendu par un chef de secteur ou plus (conformité finale conforme) ; (2) API `start` sans contrôle de l'état (appelable par un assigné), qui laisse « En cours » avec un compte rendu terminé non conforme ; (3) administration Django. Exclue du calcul des retards (choix explicite) ; aucune notification ; visible en « À faire » et en supervision ; clôture du ticket sans effet sur l'occurrence ; pour une **installation**, pas de ticket automatique et **échéance suivante non générée** tant que l'état dure |
| **Conséquences** | **Risque de blocage** : « En validation » sans échéance ni relance, entretien récurrent d'installation suspendu ; sortie par l'API `start` non voulue. Règle de sortie **à décider par le PO** (D2) ; aucune règle inventée |
| **Sources et preuves** | `maintenance/web_views.py:283` ; `maintenance/views.py:108` ; `maintenance/perimetre.py:18` ; `maintenance/management/commands/generate_installation_occurrences.py:79` |
| **Profils concernés** | exécutants ; chefs de secteur ; responsables des installations |
| **Lot de correction prévu** | Non identifié (à décider par le PO) |
| **Vérifications** | test 12/11/2026 (18 tests) ; navigateur 12/11/2026 : bouton « Enregistrer la correction » visible du seul chef de secteur et au-delà |
| **Niveau de preuve** | [T][N] |
| **Statut** | documenté, non arbitré (pas une autorisation de modifier le logiciel) |

## A21 — Périodicités nommées, remarques d'outillage, durée indicative

| Rubrique | Contenu |
|---|---|
| **Règle validée** | Périodicités nommées, remarques d'outillage et durée indicative : décisions DEC-PER-01, DEC-PER-02, DEC-PER-03, DEC-PER-04, DEC-OUT-01, DEC-OUT-02, DEC-OUT-03, DEC-OUT-04, DEC-OUT-05, DEC-DUR-01, DEC-DUR-02, DEC-DUR-03, DEC-DUR-04, DEC-DUR-05, DEC-DUR-06, DEC-DUR-07. |
| **Constat dans l'état B** | État décision par décision (les statuts viennent du plan en lots et du code, sans promotion) : DEC-PER-01 : partielle (L19) ; DEC-PER-02 : non développée (L19) ; DEC-PER-03 : non développée (L19) ; DEC-PER-04 : réalisée (L19) ; DEC-OUT-01 : non développée (L26) ; DEC-OUT-02 : non développée (L26) ; DEC-OUT-03 : non développée (L26) ; DEC-OUT-04 : non développée (L26) ; DEC-OUT-05 : non développée (L26) ; DEC-DUR-01 : non développée (L20) ; DEC-DUR-02 : non développée (L20) ; DEC-DUR-03 : non développée (L20) ; DEC-DUR-04 : non développée (L20) ; DEC-DUR-05 : non développée (L20) ; DEC-DUR-06 : non développée (L20) ; DEC-DUR-07 : non développée (L20). **Réellement disponible** : génération des échéances depuis les plans et fiches par un intervalle en jours (90 par défaut) ; historique des états conservé, retards compris. **Reste à développer** : périodicités nommées (hebdomadaire à quinquennale), échéance calculée depuis la réalisation effective, remarques d'outillage, durée indicative actualisée. Seules DEC-PER-01 (partielle) et DEC-PER-04 (réalisée) ont une part existante. |
| **Conséquences** | Cible validée par le PO, pour l'essentiel non développée ; ne contredit pas le fonctionnement actuel. Aucune règle nouvelle. |
| **Sources et preuves** | `maintenance/models.py:18` |
| **Profils concernés** | chefs de secteur |
| **Lot de correction prévu** | L19 (périodicités), L26 (outillage), L20 (durée) : non livrés dans l'état B |
| **Niveau de preuve** | [C] |
| **Statut** | documenté, non arbitré (pas une autorisation de modifier le logiciel) |

## A22 — Version de Python annoncée par l'installation

| Rubrique | Contenu |
|---|---|
| **Règle validée** | Le projet suppose Python 3.12 ou plus (README, dépendances) |
| **Constat dans l'état B** | Le script d'installation annonce « Python 3.8 ou supérieur » |
| **Conséquences** | Une installation sur un Python ancien échouerait tard ; incohérence de documentation uniquement |
| **Sources et preuves** | `setup.bat:11` ; `README.md` |
| **Profils concernés** | développeurs ; exploitants |
| **Lot de correction prévu** | L28 |
| **Niveau de preuve** | [C] |
| **Statut** | documenté, non arbitré (pas une autorisation de modifier le logiciel) |

## A23 — Sécurité d'accès avec les SIC

| Rubrique | Contenu |
|---|---|
| **Règle validée** | Sécurité d'accès avec les SIC : HTTPS, limitation des connexions (cible) |
| **Constat dans l'état B** | En production, redirection HTTPS et cookies sécurisés actifs ; **ni limitation des tentatives de connexion, ni HSTS, ni réglage de proxy inverse** ; origines CSRF de confiance codées sur `localhost` ; aucun serveur HTTPS ni serveur d'application livré |
| **Conséquences** | Cible non développée ; l'architecture réelle de mise en service reste à définir avec les SIC |
| **Sources et preuves** | `matrix/settings.py:413` |
| **Profils concernés** | exploitants ; SIC |
| **Lot de correction prévu** | L21 |
| **Niveau de preuve** | [C] |
| **Statut** | documenté, non arbitré (pas une autorisation de modifier le logiciel) |

## A24 — Sauvegarde, restauration, supervision, journaux

| Rubrique | Contenu |
|---|---|
| **Règle validée** | Sauvegarde, restauration, supervision, conservation des journaux (à fournir, `IM-10` pour les durées) |
| **Constat dans l'état B** | **Rien n'existe** dans le dépôt : ni script, ni documentation |
| **Conséquences** | Aucun plan de reprise ; durées de conservation des notifications, journaux et estimations non définies (B8) |
| **Sources et preuves** | recherche dans tout le dépôt (termes « sauvegarde », « backup », `dumpdata`, `pg_dump`) |
| **Profils concernés** | exploitants ; SIC |
| **Lot de correction prévu** | À définir avec les SIC |
| **Niveau de preuve** | [C] |
| **Statut** | documenté, non arbitré (pas une autorisation de modifier le logiciel) |

## A25 — Modules désactivés encore actifs par certains chemins

| Rubrique | Contenu |
|---|---|
| **Règle validée** | Les modules désactivés « n'existent plus » pour le bâtiment (principe de configuration par bâtiment) |
| **Constat dans l'état B** | **Vérifié par test (12/11/2026)**, modules maintenance et logistique désactivés : toutes les routes web des modules du registre (134 au total, toutes à vue-classe) sont refusées (redirection vers l'accueil) ; menu et recherche masquent le module ; **API : lecture et écriture restent accessibles** (liste, démarrage d'une occurrence, transition d'un ticket) ; **administration Django** accessible ; **tâches planifiées** : notifications de retard et de stock créées, échéances générées ; **enchaînement interne** : ticket créé depuis une maintenance non conforme ; **accueil « À faire » et calendrier continuent d'afficher** les maintenances avec un lien vers une page refusée |
| **Conséquences** | Choix volontaire du code pour ne pas casser les enchaînements ; ni l'accueil ni le calendrier n'appliquent le filtre de module ; la **règle métier attendue** (désactiver = masquer l'interface seulement, ou bloquer aussi l'API et les tâches) **n'est pas décidée** |
| **Sources et preuves** | `matrix/core/modules.py` ; `matrix/core/middleware.py:210` ; `matrix/core/navigation.py:111` ; `matrix/core/recherche.py:202` |
| **Profils concernés** | administrateurs d'unité ; commandants ; intégrateurs |
| **Lot de correction prévu** | — |
| **Vérifications** | test 12/11/2026 (3 tests de constat) |
| **Niveau de preuve** | [T] |
| **Statut** | documenté, non arbitré (pas une autorisation de modifier le logiciel) |

## A26 — Modules sans interface de programmation

| Rubrique | Contenu |
|---|---|
| **Règle validée** | Neuf modules sans API (quarts, absences, tâches, annonces, demandes, programme, postes, documentation, RETEX) |
| **Constat dans l'état B** | Aucune route `/api/` ; pilotage par les pages seulement |
| **Conséquences** | Aucune intégration possible sur ces objets ; cohérent avec la phase 7 « différée » |
| **Sources et preuves** | `couverture/etat_B/ROUTES.md` |
| **Profils concernés** | intégrateurs |
| **Lot de correction prévu** | Phase 7 |
| **Niveau de preuve** | [C] |
| **Statut** | documenté, non arbitré (pas une autorisation de modifier le logiciel) |

# Nouveaux écarts du logiciel (NE-01 à NE-07)

## NE-01 — Bouton « Exécuter » affiché sans droit d'exécution

| Rubrique | Contenu |
|---|---|
| **Constat** | La liste de maintenance affiche « Exécuter » pour des occurrences que le serveur refuse (403) à l'utilisateur ; le bouton « M'assigner » existe aussi. |
| **Profils concernés** | marins ; chefs de section |
| **Niveau de preuve** | [N] |
| **Preuve** | audit_preuves/navigateur_droits.md |
| **Statut** | documenté, non arbitré (pas une autorisation de modifier le logiciel) |

## NE-02 — Lignes de tickets cliquables sans lien ni focus clavier

| Rubrique | Contenu |
|---|---|
| **Constat** | Les lignes de la liste des tickets s'ouvrent par un gestionnaire de clic sur la ligne seulement ; non accessible au clavier. |
| **Profils concernés** | tous profils |
| **Niveau de preuve** | [C] |
| **Preuve** | matrix/templates/logistics/ticket_list.html (accès restreint) |
| **Statut** | documenté, non arbitré (pas une autorisation de modifier le logiciel) |

## NE-03 — Redirection HTTPS sans réglage de proxy inverse

| Rubrique | Contenu |
|---|---|
| **Constat** | SECURE_SSL_REDIRECT est actif en production sans réglage de proxy TLS ; comportement derrière un proxy non testé. |
| **Profils concernés** | exploitants ; SIC |
| **Niveau de preuve** | [C][?] |
| **Preuve** | chapitre « Exploitation » du dossier technique |
| **Statut** | documenté, non arbitré (pas une autorisation de modifier le logiciel) |

## NE-04 — QR codes liés au nom d'hôte de la requête

| Rubrique | Contenu |
|---|---|
| **Constat** | Le QR d'un équipement encode l'adresse absolue de la requête ; un QR imprimé depuis un autre nom d'hôte pointe vers une adresse erronée ; non documenté avant l'audit. |
| **Profils concernés** | exploitants ; gestionnaires de matériel |
| **Niveau de preuve** | [C] |
| **Preuve** | assets/views.py (accès restreint) |
| **Statut** | documenté, non arbitré (pas une autorisation de modifier le logiciel) |

## NE-05 — Codes de refus 404 et 403 hétérogènes

| Rubrique | Contenu |
|---|---|
| **Constat** | L'équipier reçoit 404 sur certaines pages d'écriture (nouvelle documentation, passation) et 403 sur la plupart des autres ; masquage volontaire ou incohérence non documentée. |
| **Profils concernés** | marins |
| **Niveau de preuve** | [N] |
| **Preuve** | audit_preuves/navigateur_droits.md |
| **Statut** | documenté, non arbitré (pas une autorisation de modifier le logiciel) |

## NE-06 — Synthèse de passation lisible par l'équipage sortant

| Rubrique | Contenu |
|---|---|
| **Constat** | Les chefs de l'équipage sortant, passé à terre, lisent la synthèse figée ; conforme au code, mais l'écart A14 les concerne aussi. |
| **Profils concernés** | chefs de l'équipage sortant |
| **Niveau de preuve** | [N] |
| **Preuve** | audit_preuves/a14_navigateur_chef_section.png |
| **Statut** | documenté, non arbitré (pas une autorisation de modifier le logiciel) |

## NE-07 — Message de fin de compte rendu inexact pour une installation

| Rubrique | Contenu |
|---|---|
| **Constat** | À la fin d'un compte rendu non conforme, l'écran annonce « Un ticket correctif sera (ou a été) ouvert automatiquement » pour toute échéance, y compris celle d'une installation, pour laquelle le code ne crée aucun ticket (navigateur, 14/11/2026 : échéance « En validation », 0 ticket créé). Le lien « signaler une anomalie » de cet écran n'apparaît que pour un relevé chiffré hors plage, pas pour un contrôle non conforme. |
| **Profils concernés** | marins ; chefs de section ; responsables des installations |
| **Niveau de preuve** | [N][C] |
| **Preuve** | audit_preuves/maintenance_non_conforme_installation_fin_de_compte_rendu.png ; matrix/templates/maintenance/_execute_done.html:3-4 (accès restreint) |
| **Statut** | documenté, non arbitré (pas une autorisation de modifier le logiciel) |

# Points à confirmer (B1 à B8)

## B1 — Suppléance du COMAEQ

| Rubrique | Contenu |
|---|---|
| **Décision existante applicable** | `DEC-SUP-01` : la suppléance est **explicitement désignée, activée par une autorité compétente, temporaire, limitée à une fonction et à un périmètre, et tracée** ; `DEC-SUP-02`, `DEC-SUP-04`, `DEC-SUP-05`, `DEC-SUP-07` |
| **Fonctionnement actuel vérifié** | Aucun mécanisme général. Seuls secours codés : le commandant de l'équipage peut viser la feuille de service et désigner les rédacteurs quand le poste COMAEQ est **vacant** (`quarts/models.py:2210`) ; remplacement temporaire d'un chef de liste des services à quai (`quarts/remplacement.py:27`) |
| **Règle cible** | Le principe est décidé. **La procédure exacte de désignation du suppléant du COMAEQ est à confirmer** (lot L08) |
| **Profils concernés** | COMAEQ ; commandants |
| **Statut** | à confirmer par le PO |

## B2 — Commandant en second

| Rubrique | Contenu |
|---|---|
| **Décision existante applicable** | Notion « 13 — Décisions » : vision globale ; écritures limitées aux **responsabilités attribuées** ; il ne tient pas ses droits automatiquement de son grade |
| **Fonctionnement actuel vérifié** | Écriture héritée du grade retirée (API) mais seuil comparé au grade dans plusieurs vues web (A4) |
| **Règle cible** | Les responsabilités doivent être **explicites et attribuées dans un cadre autorisé** ; qui les attribue, par quel mécanisme et dans quelles limites est **à confirmer** |
| **Profils concernés** | commandant en second |
| **Statut** | à confirmer par le PO |

## B3 — Échanges et quarts à la mer

| Rubrique | Contenu |
|---|---|
| **Décision existante applicable** | `DEC-FDS-07` : « échanges de tours » sans préciser le périmètre ; `DEC-FDS-13` |
| **Fonctionnement actuel vérifié** | Échanges limités aux **services à quai** d'une même liste (`quarts/echanges.py:1`) |
| **Règle cible** | **Ne pas généraliser** aux quarts à la mer sans validation métier : à confirmer |
| **Profils concernés** | chefs de liste ; COMAEQ |
| **Statut** | à confirmer par le PO |

## B4 — Accostage et appareillage

| Rubrique | Contenu |
|---|---|
| **Décision existante applicable** | Aucune décision du registre des 125 ; les propositions `mer_quai_*` (état B) décrivent la règle comme validée |
| **Fonctionnement actuel vérifié** | Déclaration par le **titulaire COMAEQ** ou le **commandant de l'équipage à bord** (`fonction_habilitee`, `quarts/mouvements.py:27`) ; correction par annulation motivée |
| **Règle cible** | Le fonctionnement actuel est documenté ; **l'autorité cible est à confirmer** |
| **Profils concernés** | COMAEQ ; commandants |
| **Statut** | à confirmer par le PO |

## B5 — Chef de liste des quarts

| Rubrique | Contenu |
|---|---|
| **Décision existante applicable** | Notion « 13 » : le chef de liste crée et publie les listes de service et de gardes (**décision antérieure**, remplacée par `DEC-FDS-14` pour la publication) ; `D11` (mer/quai) : chef de liste des quarts **distinct** du chef de liste des services à quai |
| **Fonctionnement actuel vérifié** | Désignation par supervision ou par un niveau chef de service dont le périmètre couvre celui visé (`quarts/listes_views.py:163`) |
| **Règle cible** | Qui désigne : **à confirmer** |
| **Profils concernés** | chefs de liste ; chefs de service |
| **Statut** | à confirmer par le PO |

## B6 — « Fin de journée » d'une tâche

| Rubrique | Contenu |
|---|---|
| **Décision existante applicable** | `DEC-BLQ-05` (état « Non réalisée — À reprogrammer ») |
| **Fonctionnement actuel vérifié** | Aucune notion de fin de journée |
| **Règle cible** | Heure par bâtiment (`IM-09`) : **à confirmer** |
| **Profils concernés** | marins ; chefs de section |
| **Statut** | à confirmer par le PO |

## B7 — Ordre des grades

| Rubrique | Contenu |
|---|---|
| **Décision existante applicable** | `DEC-COL-02` |
| **Fonctionnement actuel vérifié** | Le grade est un texte sans rang |
| **Règle cible** | Valeurs à saisir par le PO : **à confirmer** (`IM-02`) |
| **Profils concernés** | PO |
| **Statut** | à confirmer par le PO |

## B8 — Conservation

| Rubrique | Contenu |
|---|---|
| **Décision existante applicable** | Aucune décision |
| **Fonctionnement actuel vérifié** | Notifications, journaux et estimations non purgés |
| **Règle cible** | Durées **à confirmer** (`IM-10`) |
| **Profils concernés** | exploitants ; PO |
| **Statut** | à confirmer par le PO |

# Propositions non arbitrées (D1 à D7) 🟣

## D1 — Ticket de suivi pour une installation déclarée non conforme, comme pour le matériel mobile

| Rubrique | Contenu |
|---|---|
| **Origine** | Retenue comme proposition cible par le PO, « à valider » |
| **Garde-fous demandés** | Un ticket ne clôture jamais automatiquement une anomalie ; il n'autorise jamais une remise en service |
| **Chapitres concernés** | 12, 25 |
| **Statut** | 🟣 à valider par le PO — pas une décision |

## D2 — Règle de sortie de l'état « En validation » et alerte de retard associée (A20)

| Rubrique | Contenu |
|---|---|
| **Origine** | Constat du dossier |
| **Garde-fous demandés** | Aucune règle inventée |
| **Chapitres concernés** | 12, 25 |
| **Statut** | 🟣 à valider par le PO — pas une décision |

## D3 — Transmission d'un RETEX à un organisme : destinataires, canaux, responsabilités

| Rubrique | Contenu |
|---|---|
| **Origine** | Précision du PO : acte distinct de la validation et du statut |
| **Garde-fous demandés** | À confirmer avec les procédures métier ; le marquage « flotte » n'est pas une transmission |
| **Chapitres concernés** | 15, 25 |
| **Statut** | 🟣 à valider par le PO — pas une décision |

## D4 — Autorité de classification « critique » d'un contrôle d'appareillage

| Rubrique | Contenu |
|---|---|
| **Origine** | `DEC-APP-14` (principe validé) ; compatibilité avec les procédures du bord non vérifiée |
| **Garde-fous demandés** | À confirmer avant tout développement |
| **Chapitres concernés** | 16, 25 |
| **Statut** | 🟣 à valider par le PO — pas une décision |

## D5 — Favoris épinglés, recherche de personnes limitée, formulaires RH configurables

| Rubrique | Contenu |
|---|---|
| **Origine** | Observations de recette (PO-18 à PO-20) |
| **Garde-fous demandés** | « À faire plus tard » ; droits et confidentialité à spécifier |
| **Chapitres concernés** | 17, 25 |
| **Statut** | 🟣 à valider par le PO — pas une décision |

## D6 — Observations de recette PO-01 à PO-16, PO-21 (ergonomie, accueil, notifications, fiches de démonstration)

| Rubrique | Contenu |
|---|---|
| **Origine** | Notion « Recette UX V1.1 » |
| **Garde-fous demandés** | Qualification et arbitrage du PO avant toute correction |
| **Chapitres concernés** | 17 |
| **Statut** | 🟣 à valider par le PO — pas une décision |

## D7 — Sauvegarde, restauration, supervision, conservation des journaux

| Rubrique | Contenu |
|---|---|
| **Origine** | Aucune source |
| **Garde-fous demandés** | À définir avec les SIC / l'exploitant |
| **Chapitres concernés** | 23 |
| **Statut** | 🟣 à valider par le PO — pas une décision |

# Anomalies du dossier (audit)

> Une fiche par anomalie : constat, document et page, preuve, gravité, traitement prévu et statut sont séparés. Les niveaux de preuve [C] [N] [T] [V] [A] [R] [?] sont définis en début de registre.

## AUD-001 — L'en-tête de chaque page de l'ancien PDF portait une mention de large diffusion contradictoire avec la classification non validée

| Rubrique | Contenu |
|---|---|
| **Constat** | L'en-tête de chaque page dit [citation d'un document antérieur : « DIFFUSION GÉNÉRALE »] et le fichier s'appelle [citation du nom d'un fichier antérieur : « DIFFUSABLE »], alors que la couverture et le chapitre 3 disent que la classification n'est pas validée. La couverture annonce « Aucune référence de code » alors que le texte contient 39 chemins de fichiers `.py` (12 pages), 8 noms de branches internes `claude/…` (7 pages), 9 chemins `docs/…` |
| **Document et page concernés** | PDF [citation du nom d'un fichier antérieur : « diffusable »] |
| **Page, chapitre ou capture** | Couverture p.1 et en-tête des 108 pages |
| **Preuve** | [A][V] `pdf_controles.md` §3 ; p.1, 14, 20, 24 |
| **Conséquence pour le lecteur** | Le PDF peut être pris pour autorisé à la [ancienne mention de large diffusion] ; le critère de séparation annoncé n'est pas celui qui a été contrôlé (« fichier:ligne » seulement) |
| **Correction recommandée** | Remplacer l'en-tête par « DIFFUSION RESTREINTE PROVISOIRE — classification à valider » (comme le guide visuel) ; aligner la couverture sur la réalité ou retirer chemins et branches ; décision de l'autorité sur ce qu'est une « référence de code » |
| **Gravité** | Bloquante (diffusion) |
| **Priorité** | P0 |
| **Traitement prévu** | P0-1 |
| **Statut** | ouverte — à traiter par la refonte |

## AUD-002 — Impression de la feuille de service : le dossier la disait introuvable alors qu'un bouton « Imprimer » existe

| Rubrique | Contenu |
|---|---|
| **Constat** | « Le rendu imprimable de la feuille de service n'a pas été trouvé dans le code » ; A12 : « aucune page imprimable » — `matrix/templates/quarts/feuille_service_detail.html:18` contient un bouton « Imprimer » (`window.print()`, classe `no-print`) ; le guide visuel p.25 le montre |
| **Document et page concernés** | Chap. 8 §8.13 (l.184) ; registre A12 |
| **Preuve** | [C][N][V] |
| **Conséquence pour le lecteur** | Faux : une impression navigateur existe ; seules l'impression A4 dédiée et l'alerte de réimpression (DEC-FDS-04/06) manquent |
| **Correction recommandée** | Corriger §8.13 et A12 : « impression par le navigateur disponible ; mise en page A4 dédiée et alerte de réimpression non développées » |
| **Gravité** | Majeure |
| **Priorité** | P0 |
| **Traitement prévu** | P0-2 |
| **Statut** | ouverte — à traiter par la refonte |

## AUD-003 — Écrans décrits comme « non rejoués » alors que le guide visuel et l'audit les ont rejoués dans un navigateur

| Rubrique | Contenu |
|---|---|
| **Constat** | « Les écrans n'ont pas été rejoués dans un navigateur » (au moins 11 occurrences) — Le guide visuel (64 captures, 5 parcours) et cet audit ont rejoué ces écrans |
| **Document et page concernés** | Chap. 2, 6 (§6.11), 7, 9, 10, 11, 12, 15, 16, 17 ; annexe F ; compléments 11T, 12T, 15T… |
| **Preuve** | [?] grep ; [N] |
| **Conséquence pour le lecteur** | Contradiction entre documents : le lecteur ne sait pas si les écrans sont vérifiés. Les étiquettes ⚪ ne reflètent plus l'état de la preuve |
| **Correction recommandée** | Réviser ces phrases : « rejoué sur instance de démonstration le 12/11/2026 pour les écrans du guide visuel ; non rejoué pour … » |
| **Gravité** | Majeure |
| **Priorité** | P0 |
| **Traitement prévu** | P0-4 |
| **Statut** | ouverte — à traiter par la refonte |

## AUD-004 — Le premier chapitre promettait les rondes de contrôle, module retiré de l'interface

| Rubrique | Contenu |
|---|---|
| **Constat** | « Que dois-je faire ? → les tâches, la maintenance, les rondes de contrôle » — Le module `rondes` n'a aucune vue et a été retiré de l'interface (chap. 2, 12 ; A8 ; `rondes/models.py` seul) |
| **Document et page concernés** | Chap. 1 §1.1 (l.18) |
| **Preuve** | [C] `matrix/tests/test_module_rondes_retire.py` cité en 12T |
| **Conséquence pour le lecteur** | Le premier chapitre promet une fonction qui n'existe pas |
| **Correction recommandée** | Retirer les rondes de la réponse ou les marquer « retirées de l'interface » |
| **Gravité** | Majeure |
| **Priorité** | P0 |
| **Traitement prévu** | P0-2 |
| **Statut** | ouverte — à traiter par la refonte |

## AUD-005 — La barre de parcours du quotidien (Mon quotidien, Mon équipe, Suivi, Synthèse) n'est décrite nulle part

| Rubrique | Contenu |
|---|---|
| **Constat** | La page « Aujourd'hui » est décrite en blocs ; la barre de parcours du quotidien (« Mon quotidien · Mon équipe · Suivi · Synthèse ») n'est décrite nulle part (« Mon équipe » : 0 occurrence dans les chapitres [ancien qualificatif de large diffusion]) — `matrix/templates/components/parcours.html` ; visible sur toutes les captures d'accueil du guide |
| **Document et page concernés** | Chap. 6, 10, 17 |
| **Preuve** | [C][N][V] |
| **Conséquence pour le lecteur** | Un chef cherche « le bloc Supervision » ; il trouve des onglets qui ne portent pas ce nom. Le fil central de navigation du chef est absent |
| **Correction recommandée** | Documenter la barre (quatre vues, onglets réservés aux chefs, ce que contient chacun) au chapitre 6 et 17 |
| **Gravité** | Majeure |
| **Priorité** | P0 |
| **Traitement prévu** | P0-2 |
| **Statut** | ouverte — à traiter par la refonte |

## AUD-006 — Schémas : légende séparée de sa figure et schéma S10 illisible (5,0 pt)

| Rubrique | Contenu |
|---|---|
| **Constat** | Détection : légende dans les 6 % supérieurs de la page. S10 vu : illisible (5,0 pt), diagramme en pelote |
| **Document et page concernés** | PDF restreint p.4–5 ; PDF [ancien qualificatif de large diffusion] p.99–100 |
| **Page, chapitre ou capture** | Schéma S10 : image p.4, légende en haut de p.5 ; S40 idem |
| **Preuve** | [A][V] `schemas_lisibilite.csv` |
| **Conséquence pour le lecteur** | Légende séparée de sa figure ; S10 inutilisable à 100 % |
| **Correction recommandée** | Garder figure et légende ensemble (`break-inside: avoid`) ; relayouter S10 (deux schémas) |
| **Gravité** | Majeure |
| **Priorité** | P0 |
| **Traitement prévu** | P0-6 |
| **Statut** | ouverte — à traiter par la refonte |

## AUD-007 — Le bouton « Exécuter » est affiché sans droit d'exécution, mais c'est le serveur qui décide (refus 403)

| Rubrique | Contenu |
|---|---|
| **Constat** | « L'écran peut masquer un bouton, mais c'est toujours le serveur qui décide » — La liste de maintenance affiche « Exécuter » sur toutes les lignes pour un équipier ; `/maintenance/occurrences/4/execute/` répond 403 pour lui. Le guide p.13 montre ces boutons sans explication |
| **Document et page concernés** | Chap. 5 §5.4 ; guide visuel p.13 |
| **Preuve** | [N] `navigateur_droits.md` |
| **Conséquence pour le lecteur** | Le marin croit pouvoir exécuter des maintenances d'autrui ; le guide visuel risque de l'enseigner |
| **Correction recommandée** | Ajouter un constat au chapitre 12 ; nouvel écart candidat NE-01 (hors décision) ; annoter la capture p.13 du guide |
| **Gravité** | Majeure (précisée en phase 2 : le bouton « M'assigner » existe aussi dans la liste) |
| **Priorité** | P0 |
| **Traitement prévu** | P0-2 |
| **Statut** | ouverte — à traiter par la refonte |

## AUD-008 — « Vérifié par test » : les fichiers de test n'étaient conservés dans aucun dépôt

| Rubrique | Contenu |
|---|---|
| **Constat** | « Vérifié par test (12/11/2026) » — Les fichiers de test ne sont dans aucun dépôt (rapport de qualification : « non conservés ») ; une copie est maintenant archivée dans `audit_preuves/tests_verification/` et relancée : 29 tests OK |
| **Document et page concernés** | Registre A14, A20, A25 ; chap. 6 §6.6, 6 §6.9, 12 ; `RAPPORT_QUALIFICATION_FINALE_G0.md` |
| **Preuve** | [T] `audit_preuves/tests_verification/` |
| **Conséquence pour le lecteur** | Une preuve non rejouable n'en est pas une pour un futur mainteneur |
| **Correction recommandée** | Citer ces fichiers dans le registre ; décider avec le PO s'ils entrent dans le dépôt applicatif (hors de cette mission) |
| **Gravité** | Majeure |
| **Priorité** | P0 |
| **Traitement prévu** | P0-5 |
| **Statut** | ouverte — à traiter par la refonte |

## AUD-009 — Pages portant 1 à 5 lignes, que le rapport de clôture disait absentes (fusionnée dans AUD-034)

| Rubrique | Contenu |
|---|---|
| **Constat** | Pages portant 1 à 5 lignes (« Limites », « Sources », une ligne de tableau) — `RAPPORT_CLOTURE_G0.md` §3 : « Pages quasi vides : Aucune dans les deux PDF » |
| **Document et page concernés** | PDF restreint p.39, 41, 45 ; [ancien qualificatif de large diffusion] p.14, 82, 93, 106 |
| **Preuve** | [A][V] `pdf_controles.md` §2 |
| **Conséquence pour le lecteur** | Impression d'inachevé ; le rapport de clôture est inexact sur ce point |
| **Correction recommandée** | Ne plus forcer un saut de page avant la dernière section des chapitres courts ; corriger le rapport |
| **Gravité** | Majeure |
| **Priorité** | P0 |
| **Traitement prévu** | AUD-034 |
| **Statut** | fusionnée dans AUD-034 |

## AUD-010 — Rapport du guide visuel : « 25 captures non retenues » et lien de ligne des tickets, deux affirmations inexactes

| Rubrique | Contenu |
|---|---|
| **Constat** | §3 « 25 captures non retenues » ; §5 « la liste des tickets n'a pas de lien de ligne visible » — 29 captures non utilisées (64 − 35). Les lignes de tickets sont cliquables (`onclick`, `matrix/templates/logistics/ticket_list.html:28`) : ma capture automatique cherchait un lien `<a>` |
| **Document et page concernés** | `guide-visuel/RAPPORT_GUIDE_VISUEL_G0.md` |
| **Preuve** | [C][A] |
| **Conséquence pour le lecteur** | Erreurs de mon propre rapport |
| **Correction recommandée** | Corriger le rapport (affirmation retirée) |
| **Gravité** | Majeure |
| **Priorité** | P0 |
| **Traitement prévu** | P0-2 |
| **Statut** | ouverte — à traiter par la refonte |

## AUD-011 — Aucun document court pour un décideur

| Rubrique | Contenu |
|---|---|
| **Constat** | Aucun document court pour un décideur — Les PDF ne contiennent ni synthèse de 2 pages (valeur, maturité, limites, risques) ni lecture de la `SYNTHESE_ECARTS_PAR_CRITICITE.md` (fichier restreint hors PDF) |
| **Document et page concernés** | Ensemble |
| **Preuve** | [V] sommaires |
| **Conséquence pour le lecteur** | Le commandement doit lire 108 pages pour comprendre l'intérêt et les limites |
| **Correction recommandée** | Ajouter un « Résumé pour décideur » en tête du PDF [ancien qualificatif de large diffusion] (valeur, maturité par module, limites, décisions en attente) |
| **Gravité** | Majeure |
| **Priorité** | P1 |
| **Traitement prévu** | P1-1 |
| **Statut** | ouverte — à traiter par la refonte |

## AUD-012 — Sommaires sans numéros de page et deux parcours « marin » contradictoires dans les guides de lecture

| Rubrique | Contenu |
|---|---|
| **Constat** | Sommaires des deux PDF sans numéros de page ; `00_LISEZ-MOI.md` et `GUIDE_DE_LECTURE.md` indiquent deux parcours « marin » différents (ch. 1–2 contre ch. 1, 6, 8, 12 + annexe A) ; le guide visuel n'est cité ni dans le LISEZ-MOI, ni dans le guide de lecture, ni dans le chapitre 3 ; la numérotation saute de 17 à 25 sans explication dans le sommaire [ancien qualificatif de large diffusion] |
| **Document et page concernés** | Sommaires, guides |
| **Preuve** | [V] p.2 ; [A] grep |
| **Conséquence pour le lecteur** | Le lecteur retrouve difficilement l'information ; les trois documents ne forment pas un ensemble |
| **Correction recommandée** | Numéroter les sommaires ; un seul parcours par profil ; référencer le guide visuel ; expliquer la numérotation |
| **Gravité** | Majeure |
| **Priorité** | P1 |
| **Traitement prévu** | P0-4 / P1-2 |
| **Statut** | ouverte — à traiter par la refonte |

## AUD-013 — 35 captures sur 64 utilisées : des écrans importants manquaient

| Rubrique | Contenu |
|---|---|
| **Constat** | 35 captures sur 64 utilisées — Écrans importants absents : accusé de réception d'une annonce, fiche d'installation (relevés, entretien), échange de tour, Documentation/RETEX, bas de l'accueil (indicateurs, bloc Supervision), prêt à appareiller avec session ouverte, vue mobile (le chapitre 17 en parle) |
| **Document et page concernés** | Guide visuel |
| **Preuve** | [V] `captures_audit.csv` |
| **Conséquence pour le lecteur** | Des parcours promis (annonces à accuser, RETEX) ne sont pas illustrés ; des doublons occupent la place de ces écrans |
| **Correction recommandée** | Ajouter 6 à 8 captures et en retirer 4 doublons |
| **Gravité** | Majeure |
| **Priorité** | P1 |
| **Traitement prévu** | P1-3 |
| **Statut** | ouverte — à traiter par la refonte |

## AUD-014 — Textes anglais du navigateur dans une interface française (dates, boutons de fichier, heures)

| Rubrique | Contenu |
|---|---|
| **Constat** | Textes anglais du navigateur dans une interface française : « mm/dd/yyyy », « Choose File / No file chosen », « 08:00 AM » |
| **Document et page concernés** | Guide visuel p.15, 19, 30 |
| **Preuve** | [V] captures `p_maintenance_1_saisie`, `p_anomalie_3_description`, `parametres` |
| **Conséquence pour le lecteur** | Le lecteur croit que Matrix affiche de l'anglais |
| **Correction recommandée** | Relancer Chromium en langue française |
| **Gravité** | Mineure |
| **Priorité** | P2 |
| **Traitement prévu** | P2 |
| **Statut** | ouverte — à traiter par la refonte |

## AUD-015 — Messages de confirmation superposés et mention « Brouillon abandonné » sur des captures

| Rubrique | Contenu |
|---|---|
| **Constat** | Messages de confirmation superposés, mention « Brouillon abandonné. » |
| **Document et page concernés** | Guide visuel p.11, 12, 17, 21, 22, 23 |
| **Preuve** | [V] |
| **Conséquence pour le lecteur** | Le regard est détourné ; une capture semi-transparente (p.23) |
| **Correction recommandée** | Attendre la disparition des messages avant capture ; abandonner le brouillon avant la session |
| **Gravité** | Mineure |
| **Priorité** | P2 |
| **Traitement prévu** | P2 |
| **Statut** | ouverte — à traiter par la refonte |

## AUD-016 — Captures en doublon exact ou quasi exact dans le guide visuel

| Rubrique | Contenu |
|---|---|
| **Constat** | 4 doublons exacts (`tache_detail`=`p_tache_1_ouverte`, `occurrences`=`p_maintenance_3_liste`, `execution_saisie`=`p_maintenance_1_saisie`) et 4 quasi-doublons |
| **Document et page concernés** | Captures sources |
| **Preuve** | [A] différence de pixels 0,0 à 4,6 % |
| **Conséquence pour le lecteur** | 21 Mo d'images dont une part redondante |
| **Correction recommandée** | Supprimer ou fusionner |
| **Gravité** | Mineure |
| **Priorité** | P2 |
| **Traitement prévu** | P1-3 |
| **Statut** | ouverte — à traiter par la refonte |

## AUD-017 — Formule répétée : « dans la partie restreinte du dossier et la partie restreinte du dossier »

| Rubrique | Contenu |
|---|---|
| **Constat** | « …dans la partie restreinte du dossier et la partie restreinte du dossier » |
| **Document et page concernés** | Chap. 5, en-tête (l.3) |
| **Preuve** | [V] p.21 ; [A] grep |
| **Conséquence pour le lecteur** | Faute visible dès la première page du chapitre le plus consulté |
| **Correction recommandée** | Corriger la phrase |
| **Gravité** | Mineure |
| **Priorité** | P2 |
| **Traitement prévu** | P2 |
| **Statut** | ouverte — à traiter par la refonte |

## AUD-018 — Identifiants coupés en milieu de mot dans les cellules des tableaux

| Rubrique | Contenu |
|---|---|
| **Constat** | Identifiants coupés en milieu de mot dans les cellules (« SynthesePassati / on », « ReferenceBatime / nt »), régression de la correction de l'ensemble précédent |
| **Document et page concernés** | PDF restreint p.4 |
| **Preuve** | [V] ; étendue non mesurée [?] |
| **Conséquence pour le lecteur** | Illisibilité des noms de modèles |
| **Correction recommandée** | Largeur minimale de colonne ou césure autorisée avant les parenthèses |
| **Gravité** | Mineure |
| **Priorité** | P2 |
| **Traitement prévu** | P2 |
| **Statut** | ouverte — à traiter par la refonte |

## AUD-019 — Le symbole ⚪ se rendait en petit cercle alors que 🟢, 🔵 et 🟣 sont des pastilles

| Rubrique | Contenu |
|---|---|
| **Constat** | Le symbole ⚪ se rend en petit cercle « ◦ » alors que 🟢🔵🟣 sont des pastilles |
| **Document et page concernés** | Deux PDF du dossier |
| **Preuve** | [V] p.1, 14, 82 |
| **Conséquence pour le lecteur** | La légende n'est pas reconnaissable |
| **Correction recommandée** | Même traitement que le guide visuel (pastille dessinée) |
| **Gravité** | Mineure |
| **Priorité** | P2 |
| **Traitement prévu** | P2 |
| **Statut** | ouverte — à traiter par la refonte |

## AUD-020 — Texte de schémas trop petit (5,8 à 6,2 pt) (fusionnée dans AUD-036)

| Rubrique | Contenu |
|---|---|
| **Constat** | S04, S13, S28 : 5,8 pt ; S09, S15 : 6,0 pt ; S01, S21 : 6,2 pt (libellés minimaux) ; S09 : flèches enchevêtrées |
| **Document et page concernés** | Schémas |
| **Preuve** | [A][V] `schemas_lisibilite.csv` |
| **Conséquence pour le lecteur** | Lecture pénible à 100 % ; S09/S13 « déjà signalés » restent petits |
| **Correction recommandée** | Relayouter ou doubler le corps de police ; S10 prioritaire (AUD-006) |
| **Gravité** | Mineure |
| **Priorité** | P1 |
| **Traitement prévu** | AUD-036 |
| **Statut** | fusionnée dans AUD-036 |

## AUD-021 — Trois chiffres différents pour le nombre de tests (≈ 3 950 fonctions, 3 963 tests)

| Rubrique | Contenu |
|---|---|
| **Constat** | « ≈ 3 950 fonctions de test » ; « 3 963 tests » |
| **Document et page concernés** | Chap. 24 §24.8 ; rapports |
| **Preuve** | Recomptage `def test_` indenté : 3 912 [C] ; 3 963 exécutés non rejoués [R] |
| **Conséquence pour le lecteur** | Trois chiffres différents pour une même notion |
| **Correction recommandée** | Un seul chiffre, avec méthode |
| **Gravité** | Mineure |
| **Priorité** | P2 |
| **Traitement prévu** | P2 |
| **Statut** | ouverte — à traiter par la refonte |

## AUD-022 — Recherche de personnes classée cible alors que la catégorie « Marins » existe

| Rubrique | Contenu |
|---|---|
| **Constat** | « Recherche de personnes » classée cible (DEC-UX-09 / PO-18) alors que la catégorie « Marins » existe (`matrix/core/recherche.py:193`, chap. 9 §77, captures p.8) |
| **Document et page concernés** | Chap. 6 §6.10, 9, 17 |
| **Preuve** | [C][N][V] |
| **Conséquence pour le lecteur** | Ambiguïté : existant ou cible ? |
| **Correction recommandée** | Préciser : « recherche par nom et grade existante ; informations professionnelles étendues : cible » |
| **Gravité** | Amélioration |
| **Priorité** | P1 |
| **Traitement prévu** | P1-6 |
| **Statut** | ouverte — à traiter par la refonte |

## AUD-023 — Les chapitres techniques renvoyaient à des chapitres absents du PDF restreint

| Rubrique | Contenu |
|---|---|
| **Constat** | Les chapitres techniques renvoient aux chapitres [ancien qualificatif de large diffusion] « à lire d'abord » mais le PDF restreint ne contient pas les chapitres 1 à 17 |
| **Document et page concernés** | PDF restreint |
| **Preuve** | [A] S02… absents de la liste des schémas ; [V] |
| **Conséquence pour le lecteur** | Le développeur doit détenir deux PDF ; l'ordre n'est dit nulle part sur la couverture |
| **Correction recommandée** | Dire sur la couverture et le sommaire que le PDF restreint complète le [ancien qualificatif de large diffusion] ; ou proposer une édition « intégrale » |
| **Gravité** | Amélioration |
| **Priorité** | P1 |
| **Traitement prévu** | P1-2 |
| **Statut** | ouverte — à traiter par la refonte |

## AUD-024 — Pas de recette du premier jour pour un développeur ni de mise en garde sur la redirection HTTPS derrière un proxy

| Rubrique | Contenu |
|---|---|
| **Constat** | Pas de recette du premier jour pour un développeur (installer, lancer, tester, ajouter une action de seuil ou un module), pas de glossaire du code ; conséquence pratique de `SECURE_SSL_REDIRECT` sans `SECURE_PROXY_SSL_HEADER` non dite (risque de redirection en boucle derrière un proxy TLS [?]) |
| **Document et page concernés** | Chap. 23, 24 |
| **Preuve** | [C] `matrix/settings.py:422-424` ; plan des chapitres |
| **Conséquence pour le lecteur** | Reprise difficile sans l'auteur |
| **Correction recommandée** | Ajouter une « Prise en main développeur » d'une page et une « Recette de déploiement » |
| **Gravité** | Amélioration |
| **Priorité** | P1 |
| **Traitement prévu** | P1-4 |
| **Statut** | ouverte — à traiter par la refonte |

## AUD-025 — Écart A20 : le texte ne précisait pas que l'exécutant et le chef de section ne voient pas le bouton de correction

| Rubrique | Contenu |
|---|---|
| **Constat** | A20 : le texte dit « seul “Enregistrer la correction” est offert » sans préciser que l'exécutant et le chef de section ne voient pas ce bouton ; A14 : la raison de la non-capture (relève validée requise) est exacte mais non démontrée à l'écran |
| **Document et page concernés** | Guide visuel p.36–37 |
| **Preuve** | [N] `navigateur_droits.md` |
| **Conséquence pour le lecteur** | Lecture trop courte du circuit |
| **Correction recommandée** | Ajouter la phrase et une capture « profil équipier » |
| **Gravité** | Mineure |
| **Priorité** | P2 |
| **Traitement prévu** | P1-3 |
| **Statut** | ouverte — à traiter par la refonte |

## AUD-026 — Les décisions DEC-… renvoient à une branche et à Notion, non joignables depuis le dossier

| Rubrique | Contenu |
|---|---|
| **Constat** | Les `DEC-*` renvoient à une branche (`claude/eager-hopper-2cbcqh`) et à Notion, non joignables dans le dossier |
| **Document et page concernés** | Registre, chap. 5 |
| **Preuve** | [?] |
| **Conséquence pour le lecteur** | Un futur mainteneur ne peut pas retrouver la décision |
| **Correction recommandée** | Annexe « Décisions citées » avec texte et date, sans inventer |
| **Gravité** | Amélioration |
| **Priorité** | P1 |
| **Traitement prévu** | P1-6 |
| **Statut** | ouverte — à traiter par la refonte |

## AUD-027 — Lignes de la liste des tickets cliquables à la souris seulement, non accessibles au clavier

| Rubrique | Contenu |
|---|---|
| **Constat** | Les lignes de la liste de tickets sont cliquables par `onclick` seulement (non accessibles au clavier) |
| **Document et page concernés** | Chap. 11, 13, 15 (hors périmètre du dossier) |
| **Preuve** | [C] `matrix/templates/logistics/ticket_list.html:28` |
| **Conséquence pour le lecteur** | Accessibilité ; nouvel écart candidat NE-02 |
| **Correction recommandée** | Le noter dans les limites du chapitre 17 |
| **Gravité** | Mineure |
| **Priorité** | P2 |
| **Traitement prévu** | P2 |
| **Statut** | ouverte — à traiter par la refonte |

## AUD-028 — Rapports précédents aux chiffres d'origine contradictoires ; 11 fichiers de pilotage à la racine

| Rubrique | Contenu |
|---|---|
| **Constat** | Les rapports précédents conservent leurs chiffres d'origine (105/142 pages, 1 093 références) ; plusieurs rapports se contredisent légèrement ; 11 fichiers de pilotage à la racine du dossier pour 3 lecteurs |
| **Document et page concernés** | Annexe F, rapports E1–E4, BILAN |
| **Preuve** | [V] listing |
| **Conséquence pour le lecteur** | Bruit pour un nouveau lecteur |
| **Correction recommandée** | Ranger les rapports de livraison dans `rapports/` et ne garder à la racine que LISEZ-MOI, guide, synthèse |
| **Gravité** | Mineure |
| **Priorité** | P2 |
| **Traitement prévu** | P2 |
| **Statut** | ouverte — à traiter par la refonte |

## AUD-029 — Deux personnages différents portent le nom « Durand » dans le chapitre 6 ; noms des captures non repris

| Rubrique | Contenu |
|---|---|
| **Constat** | « Un exemple : le maître Durand » et le « matelot Durand » (chap. 6) sont des personnages différents sous le même nom ; « personnage fictif » non repris dans les captures (noms « Karim Equipier A ») |
| **Document et page concernés** | Chap. 5 |
| **Preuve** | [V] |
| **Conséquence pour le lecteur** | Deux jeux de personnages fictifs non reliés |
| **Correction recommandée** | Un seul fil rouge de personnages (ceux du guide visuel) |
| **Gravité** | Mineure |
| **Priorité** | P2 |
| **Traitement prévu** | P2 |
| **Statut** | ouverte — à traiter par la refonte |

## AUD-030 — Chemin erroné du scan web : « assets/scan/UUID/ » au lieu de « /scan/UUID/ »

| Rubrique | Contenu |
|---|---|
| **Constat** | « scan web `assets/scan/<uuid>/` » : le chemin réel est `/scan/<uuid>/` (`assets/web_urls.py:72` ; annexe C correcte) |
| **Document et page concernés** | Ch. 20 §20.5 |
| **Preuve** | [C] |
| **Conséquence pour le lecteur** | Voir le constat. |
| **Correction recommandée** | Corriger le chemin |
| **Gravité** | Mineure |
| **Priorité** | P0 (erreur factuelle) |
| **Traitement prévu** | P0-2 |
| **Statut** | ouverte — à traiter par la refonte |

## AUD-031 — Annexe générée : lignes tronquées, fragments de tableau et symboles Markdown bruts

| Rubrique | Contenu |
|---|---|
| **Constat** | Annexe générée de 4 900 mots (79 % de l'annexe F) : lignes tronquées par « … » (« Une correcti… », « L… »), fragments de tableau (« / Tâches (ch. 10) / »), les astérisques et les accents graves bruts (p.130, 131, 134, 135), « ◦ ◦ » doublés, numérotation orpheline (« 2. L'API… »), et reprise d'énoncés périmés (« n'ont pas été rejoués ») |
| **Document et page concernés** | Annexe F §F.5, PDF restreint p.127–135 |
| **Preuve** | [V] p.127, 130, 131 |
| **Conséquence pour le lecteur** | Voir le constat. |
| **Correction recommandée** | Régénérer F.5 par chapitre sans tronquer, ou le remplacer par un tableau (chapitre, point, étiquette) |
| **Gravité** | Majeure |
| **Priorité** | P0 |
| **Traitement prévu** | P0-6 |
| **Statut** | ouverte — à traiter par la refonte |

## AUD-032 — Tableaux Markdown non rendus (barres verticales brutes) dans le PDF restreint

| Rubrique | Contenu |
|---|---|
| **Constat** | Tableaux Markdown non rendus : p.37 (« Routes web », source `restreint/13_logistique_technique.md:20-22`) et p.79 (§23.9, source `restreint/23_configuration_deploiement_exploitation.md:119-123`, tableau collé au paragraphe) apparaissent en barres verticales brutes |
| **Document et page concernés** | PDF restreint p.37 et p.79 |
| **Preuve** | [V][A] |
| **Conséquence pour le lecteur** | Voir le constat. |
| **Correction recommandée** | Ligne vide avant le tableau ; compléter l'en-tête |
| **Gravité** | Mineure |
| **Priorité** | P0 |
| **Traitement prévu** | P0-6 |
| **Statut** | ouverte — à traiter par la refonte |

## AUD-033 — Des plages de décisions présentées comme « cible, non développée » alors que certaines sont réalisées

| Rubrique | Contenu |
|---|---|
| **Constat** | Des plages de décisions sont citées comme « cible, non développée » alors que certaines sont déjà réalisées : `DEC-PER-01` (tâches périodiques générées depuis les fiches) et `DEC-PER-04` (historiques conservés) vs `maintenance/tasks.py:66` et `OccurrenceStatusLog` ; `DEC-UX-01` (accueil) vs `aujourdhui.html`. Aucune phrase ne dit que 51 décisions sur 125 ne sont pas traitées |
| **Document et page concernés** | Ch. 6 §6.10, 12 (tableau cible), 17, 25 ; registre partie C |
| **Preuve** | [C] ; source v1.2 `A1_DECISIONS_S1_S2.md` |
| **Conséquence pour le lecteur** | Voir le constat. |
| **Correction recommandée** | Citer les décisions une à une avec état (réalisée, partielle, non développée) ; ne pas utiliser de plage |
| **Gravité** | Majeure |
| **Priorité** | P0 |
| **Traitement prévu** | P0-3 |
| **Statut** | ouverte — à traiter par la refonte |

## AUD-034 — Densité des pages : trop de pages remplies à moins de 70 % et compléments techniques répétitifs

| Rubrique | Contenu |
|---|---|
| **Constat** | Densité : 18 pages du [ancien qualificatif de large diffusion] et 26 du restreint sont remplies à moins de 70 % (11 et 15 à moins de 50 %) ; les compléments techniques (1 à 3 pages par chapitre) répètent chacun un cartouche de 5 lignes ; le restreint ne contient pas les chapitres de base qu'il complète ; 3 pages ≤ 5 lignes (p.39, 41, 45) |
| **Document et page concernés** | Deux PDF ; fusionne AUD-009 |
| **Preuve** | [A] `pages_remplissage.csv` ; [V] |
| **Conséquence pour le lecteur** | Voir le constat. |
| **Correction recommandée** | Voir §J (refonte de l'architecture) |
| **Gravité** | Majeure |
| **Priorité** | P1 (P0 pour les 3 pages) |
| **Traitement prévu** | P1-8 (architecture) |
| **Statut** | ouverte — à traiter par la refonte |

## AUD-035 — Les schémas de circuit cible ne se distinguent pas des schémas de fonctionnement réel

| Rubrique | Contenu |
|---|---|
| **Constat** | Les schémas de circuit cible ne se distinguent pas des schémas de fonctionnement réel : seule la légende dit « cible » ; l'image seule (cadre, couleur, mention) est identique à S16, S20, S30, S32 |
| **Document et page concernés** | S17, S21, S31, S33 ([ancien qualificatif de large diffusion] p.42, 52, 80, 86) |
| **Preuve** | [V] |
| **Conséquence pour le lecteur** | Voir le constat. |
| **Correction recommandée** | Cadre pointillé bleu + mention « 🔵 CIBLE — non développé » dans l'image |
| **Gravité** | Majeure |
| **Priorité** | P0 (règle de distinction) |
| **Traitement prévu** | P0-7 |
| **Statut** | ouverte — à traiter par la refonte |

## AUD-036 — Qualité des 42 schémas : listes de cases sans information relationnelle, un schéma difficile, un illisible

| Rubrique | Contenu |
|---|---|
| **Constat** | Sur 42 schémas : 22 bons, 7 moyens, 10 faibles (listes de cases sans information relationnelle : S02, S14, S22, S24, S27, S36, S37, S38, S40, S42), 1 difficile (S09), 1 illisible (S10) ; S02 montre 6 groupes quand le tableau juste dessous en compte 11 |
| **Document et page concernés** | Schémas ; fusionne AUD-020 |
| **Preuve** | [V][A] `schemas_verdicts.csv` |
| **Conséquence pour le lecteur** | Voir le constat. |
| **Correction recommandée** | Remplacer les listes par des tableaux ; garder les schémas à circuit (S04, S05, S06, S07, S11, S12, S15, S16, S18, S20, S23, S25, S26, S29, S30, S32) |
| **Gravité** | Mineure |
| **Priorité** | P1 |
| **Traitement prévu** | P1-5 |
| **Statut** | ouverte — à traiter par la refonte |

## AUD-037 — Rubriques « bis » : traces d'édition d'insertions tardives

| Rubrique | Contenu |
|---|---|
| **Constat** | Rubriques « bis » : traces d'édition (insertions tardives) |
| **Document et page concernés** | Ch. 5 §5.4 bis, ch. 11 T2 bis, 12 T2 bis, 13 §13.9 bis |
| **Preuve** | [V] |
| **Conséquence pour le lecteur** | Voir le constat. |
| **Correction recommandée** | Renumérotation |
| **Gravité** | Mineure |
| **Priorité** | P2 |
| **Traitement prévu** | P2 |
| **Statut** | ouverte — à traiter par la refonte |

## AUD-038 — Deux chiffres pour le même inventaire ; annexe F.4 datée de l'ensemble 4

| Rubrique | Contenu |
|---|---|
| **Constat** | Deux chiffres pour le même inventaire ; l'annexe F.4 est datée de l'ensemble 4 et n'est plus à jour (la branche compte d'autres commits) |
| **Document et page concernés** | Ch. 26 §26.4 (« 52 branches distantes ») et annexe F.4, p.125 (« 53 branches ») ; F.4 donne `f960c84` comme tête de la branche documentaire |
| **Preuve** | [V] p.125 ; [A] grep |
| **Conséquence pour le lecteur** | Voir le constat. |
| **Correction recommandée** | Un seul chiffre, avec date ; ne pas citer la tête d'une branche vivante |
| **Gravité** | Mineure |
| **Priorité** | P2 |
| **Traitement prévu** | P2 |
| **Statut** | ouverte — à traiter par la refonte |

# Décisions du PO et état dans l'état B

> Colonne « Méthode » : **code** = vérifié dans le code de l'état B ; **plan en lots** = déduit du plan en lots du dossier V1.2 (lot livré ou non dans l'état B) ; **aucune** = non rattachée à un lot. « À instruire » signifie que le dossier ne l'a pas établi : ce n'est pas un constat de non-réalisation.

| Décision | Règle | Lot(s) | État dans l'état B | Méthode |
|---|---|---|---|---|
| <span class='nb'>DEC-ANO-01</span> | Anomalie = problème technique à suivre ; intervention = action effectuée pour le traiter. | L22 non livré dans l'état B | non développée | plan en lots |
| <span class='nb'>DEC-ANO-02</span> | Une anomalie peut nécessiter plusieurs interventions. | L22 non livré dans l'état B | non développée | plan en lots |
| <span class='nb'>DEC-ANO-03</span> | La clôture d'une intervention ne clôture pas automatiquement l'anomalie. | L22 non livré dans l'état B | non développée | plan en lots |
| <span class='nb'>DEC-ANO-04</span> | Le chef de secteur décide de la suite : intervention supplémentaire, demande d'information, ouverture d'anomalie, clôture justifiée. | L22 non livré dans l'état B | non développée | plan en lots |
| <span class='nb'>DEC-ANO-05</span> | Préserver les liens tâches ↔ interventions ↔ anomalies ↔ matériels ↔ historique. | L22 non livré dans l'état B | non développée | plan en lots |
| <span class='nb'>DEC-APP-01</span> | Chaque départ génère des contrôles à partir des fiches de référence applicables. | L23 non livré dans l'état B | non développée | plan en lots |
| <span class='nb'>DEC-APP-02</span> | Circuit : section ou secteur → service → COMANAV. | L23 non livré dans l'état B | non développée | plan en lots |
| <span class='nb'>DEC-APP-03</span> | Les modifications des références suivent leur propre circuit d'approbation. | L23 non livré dans l'état B | non développée | plan en lots |
| <span class='nb'>DEC-APP-04</span> | Référence approuvée modifiée : les préparations ouvertes sont actualisées. | L23 non livré dans l'état B | non développée | plan en lots |
| <span class='nb'>DEC-APP-05</span> | Les réponses toujours valables sont conservées. | L23 non livré dans l'état B | non développée | plan en lots |
| <span class='nb'>DEC-APP-06</span> | Les contrôles modifiés ou ajoutés sont rouverts. | L23 non livré dans l'état B | non développée | plan en lots |
| <span class='nb'>DEC-APP-07</span> | Les contrôles supprimés sont archivés. | L23 non livré dans l'état B | non développée | plan en lots |
| <span class='nb'>DEC-APP-08</span> | Les signatures affectées sont invalidées. | L23 non livré dans l'état B | non développée | plan en lots |
| <span class='nb'>DEC-APP-09</span> | Les préparations clôturées conservent leur version historique. | L23 non livré dans l'état B | non développée | plan en lots |
| <span class='nb'>DEC-APP-10</span> | Les contrôles obligatoires sont traités avant validation. | L23 non livré dans l'état B | non développée | plan en lots |
| <span class='nb'>DEC-APP-11</span> | Les réserves sont explicites, justifiées et tracées, dans les limites des règles de sécurité. | L23 non livré dans l'état B | non développée | plan en lots |
| <span class='nb'>DEC-APP-12</span> | Les contrôles critiques non dérogeables ne peuvent pas être contournés. | L23 non livré dans l'état B | non développée | plan en lots |
| <span class='nb'>DEC-APP-13</span> | Matrix ne délivre pas l'autorisation opérationnelle d'appareiller. | L23 non livré dans l'état B | réalisée | code |
| <span class='nb'>DEC-APP-14</span> | Fiche de référence d'appareillage : le chef de secteur propose les contrôles et leur classification (obligatoire, critique) ; le chef de service examine et valide la … | — | non développée (A17) | code |
| <span class='nb'>DEC-BLQ-01</span> | Un équipier peut déclarer une tâche « Bloquée » avec motif. | L17 non livré dans l'état B | non développée | plan en lots |
| <span class='nb'>DEC-BLQ-02</span> | Le responsable est informé du blocage. | L17 non livré dans l'état B | non développée | plan en lots |
| <span class='nb'>DEC-BLQ-03</span> | Le chef peut débloquer et reprogrammer sans obligation de créer une anomalie. | L17 non livré dans l'état B | non développée | plan en lots |
| <span class='nb'>DEC-BLQ-04</span> | Le chef de secteur décide si un défaut technique nécessite une anomalie. | L17 non livré dans l'état B | non développée | plan en lots |
| <span class='nb'>DEC-BLQ-05</span> | Une tâche non terminée en fin de journée n'est pas reportée en silence ; état explicite « Non réalisée — À reprogrammer ». | L17 non livré dans l'état B | non développée | plan en lots |
| <span class='nb'>DEC-CLO-01</span> | À la création/planification, case « Validation du responsable requise ». | L15 non livré dans l'état B | non développée | plan en lots |
| <span class='nb'>DEC-CLO-02</span> | Sans l'option : l'équipier termine directement ; la réalisation est enregistrée. | L15 non livré dans l'état B | non développée | plan en lots |
| <span class='nb'>DEC-CLO-03</span> | Avec l'option : l'équipier déclare terminé, la tâche passe « À valider » ; le chef approuve ou demande une correction motivée. | L15 non livré dans l'état B | non développée | plan en lots |
| <span class='nb'>DEC-CLO-04</span> | Le chef de secteur valide directement, chef de section absent, sans suppléance. | L15 non livré dans l'état B | non développée | plan en lots |
| <span class='nb'>DEC-CLO-05</span> | Les visas techniques obligatoires restent distincts de la validation facultative. | L15 non livré dans l'état B | non développée | plan en lots |
| <span class='nb'>DEC-COL-01</span> | Plusieurs marins peuvent participer à une même tâche. | — | à instruire ⚪ | aucune |
| <span class='nb'>DEC-COL-02</span> | Matrix propose comme coordinateur le participant au grade le plus élevé. | L16 non livré dans l'état B | non développée | plan en lots |
| <span class='nb'>DEC-COL-03</span> | En cas d'égalité de grade, le chef choisit. | L16 non livré dans l'état B | non développée | plan en lots |
| <span class='nb'>DEC-COL-04</span> | Le chef peut désigner un autre participant comme coordinateur. | L16 non livré dans l'état B | non développée | plan en lots |
| <span class='nb'>DEC-COL-05</span> | Le coordinateur peut déclarer le travail réalisé, mais ne remplace pas une autorité de visa technique. | L16 non livré dans l'état B | non développée | plan en lots |
| <span class='nb'>DEC-DRT-01</span> | Les droits métier découlent de la fonction exercée et du périmètre de responsabilité, pas uniquement du grade ni du niveau hiérarchique. | L09 non livré dans l'état B | non développée | plan en lots |
| <span class='nb'>DEC-DRT-02</span> | Un administrateur technique ne devient pas automatiquement autorité de validation métier ; il désigne les titulaires sans viser à leur place. | L06 non livré dans l'état B | écart (A1) | code |
| <span class='nb'>DEC-DRT-03</span> | Consultation des documents de maintenance autorisés des autres sections du secteur ; pas de modification ni de clôture hors périmètre. | — | à instruire ⚪ | aucune |
| <span class='nb'>DEC-DRT-04</span> | Accès intersectoriels et documents sensibles : droits appropriés requis. | — | à instruire ⚪ | aucune |
| <span class='nb'>DEC-DRT-05</span> | Éviter les suppressions physiques qui détruisent l'historique. | L02 livré ; L03 livré ; L04 non livré dans l'état B | partielle (2 lot(s) livré(s) sur 3) | plan en lots |
| <span class='nb'>DEC-DRT-06</span> | Un compte dont le rattachement professionnel est incomplet n'accède pas aux informations opérationnelles d'un secteur sans autorisation. | L07 non livré dans l'état B | non développée | plan en lots |
| <span class='nb'>DEC-DUR-01</span> | Matrix actualise automatiquement la durée indicative des maintenances à partir des temps réellement constatés. | L20 non livré dans l'état B | non développée | plan en lots |
| <span class='nb'>DEC-DUR-02</span> | Conserver la durée initiale. | L20 non livré dans l'état B | non développée | plan en lots |
| <span class='nb'>DEC-DUR-03</span> | Conserver l'historique des estimations. | L20 non livré dans l'état B | non développée | plan en lots |
| <span class='nb'>DEC-DUR-04</span> | Distinguer temps écoulé et charge totale en heures-personnes. | L20 non livré dans l'état B | non développée | plan en lots |
| <span class='nb'>DEC-DUR-05</span> | Éviter que interventions exceptionnellement longues, attentes et interruptions faussent l'estimation. | L20 non livré dans l'état B | non développée | plan en lots |
| <span class='nb'>DEC-DUR-06</span> | Le chef de secteur peut corriger manuellement la durée. | L20 non livré dans l'état B | non développée | plan en lots |
| <span class='nb'>DEC-DUR-07</span> | Ne pas modifier automatiquement consignes techniques ou de sécurité. | L20 non livré dans l'état B | non développée | plan en lots |
| <span class='nb'>DEC-FDS-01</span> | Le BSC prépare les feuilles de service ; il n'est pas une autorité parallèle au COMAEQ. | — | à instruire ⚪ | aucune |
| <span class='nb'>DEC-FDS-02</span> | Le COMAEQ, ou un suppléant officiellement habilité, approuve la feuille. | L08 non livré dans l'état B ; L09 non livré dans l'état B | non développée | plan en lots |
| <span class='nb'>DEC-FDS-03</span> | Après approbation, publication numérique. | — | à instruire ⚪ | aucune |
| <span class='nb'>DEC-FDS-04</span> | Le BSC assure l'impression A4 pour l'affichage. | — | à instruire ⚪ | aucune |
| <span class='nb'>DEC-FDS-05</span> | Une modification après publication entraîne une nouvelle version officielle. | L09 non livré dans l'état B | non développée | plan en lots |
| <span class='nb'>DEC-FDS-06</span> | Matrix signale la nécessité de réimprimer et remplacer une feuille déjà affichée. | L27 non livré dans l'état B | non développée | plan en lots |
| <span class='nb'>DEC-FDS-07</span> | Échanges de tours : la décision finale revient au COMAEQ ou à son suppléant officiellement habilité. | — | écart (A2) | code |
| <span class='nb'>DEC-FDS-08</span> | Les fractions de service à quai sont configurables par bâtiment. | L27 non livré dans l'état B | non développée | plan en lots |
| <span class='nb'>DEC-FDS-09</span> | Écarts signalés et justifiés, sans blocage automatique injustifié. | L27 non livré dans l'état B | non développée | plan en lots |
| <span class='nb'>DEC-FDS-10</span> | Exigences opérationnelles et réglementaires restent applicables. | — | à instruire ⚪ | aucune |
| <span class='nb'>DEC-FDS-11</span> | La création d'une feuille n'est pas ouverte à n'importe quel équipier. | — | à instruire ⚪ | aucune |
| <span class='nb'>DEC-FDS-12</span> | Prendre en compte deux équipages ; chaque équipage a sa feuille, sans validation croisée par le seul grade. | — | à instruire ⚪ | aucune |
| <span class='nb'>DEC-FDS-13</span> | Le BSC ou le chef de liste peut instruire la demande d'échange ; il ne dispose pas automatiquement de l'autorité de validation finale. | — | à instruire ⚪ | aucune |
| <span class='nb'>DEC-FDS-14</span> | Listes de quarts et de gardes : le chef de liste prépare et propose ; le COMAEQ ou son suppléant officiellement habilité approuve et publie. Toute modification après … | — | écart (A3) | code |
| <span class='nb'>DEC-MAT-01</span> | Transfert entre secteurs d'un même service : approbation du chef de service. | L13 non livré dans l'état B | non développée | plan en lots |
| <span class='nb'>DEC-MAT-02</span> | Transfert entre deux services : approbation des deux chefs de service, puis application par l'administrateur habilité. | L13 non livré dans l'état B | non développée | plan en lots |
| <span class='nb'>DEC-MAT-03</span> | Les tâches ouvertes suivent le matériel et sont réattribuées si nécessaire. | L13 non livré dans l'état B | non développée | plan en lots |
| <span class='nb'>DEC-MAT-04</span> | L'historique des interventions et des tâches clôturées reste conservé. | L13 non livré dans l'état B | non développée | plan en lots |
| <span class='nb'>DEC-MUT-01</span> | Un marin conserve son compte Matrix lorsqu'il change de bâtiment. | L25 non livré dans l'état B | non développée | plan en lots |
| <span class='nb'>DEC-MUT-02</span> | Le nouveau bâtiment demande le rattachement ; l'ancien est informé et peut confirmer le départ. | L25 non livré dans l'état B | non développée | plan en lots |
| <span class='nb'>DEC-MUT-03</span> | Sans réponse, une autorité habilitée régularise avec justification et journalisation. | L25 non livré dans l'état B | non développée | plan en lots |
| <span class='nb'>DEC-MUT-04</span> | Anciens droits retirés à la date effective de mutation ; nouveaux droits attribués selon l'affectation d'accueil. | L25 non livré dans l'état B | non développée | plan en lots |
| <span class='nb'>DEC-MUT-05</span> | L'historique est conservé. | L25 non livré dans l'état B | non développée | plan en lots |
| <span class='nb'>DEC-MUT-06</span> | Les tâches ouvertes sont réattribuées ou signalées « non affectées à un responsable ». | L04 non livré dans l'état B | non développée | plan en lots |
| <span class='nb'>DEC-MUT-07</span> | Compte d'un marin quittant le bâtiment ou la Marine : désactivé ou transféré selon le cas, sans destruction d'historique. | L04 non livré dans l'état B | non développée | plan en lots |
| <span class='nb'>DEC-ORG-01</span> | Structure : Bâtiment → Service → Secteur → Section facultative → Matériels et installations. | — | à instruire ⚪ | aucune |
| <span class='nb'>DEC-ORG-02</span> | Un secteur peut n'avoir aucune section ; le secteur reste alors l'échelon responsable. | L12 non livré dans l'état B | non développée | plan en lots |
| <span class='nb'>DEC-ORG-03</span> | Les matériels sont toujours rattachés à une entité responsable. | — | à instruire ⚪ | aucune |
| <span class='nb'>DEC-ORG-04</span> | Distinguer grade, fonction occupée, périmètre de responsabilité, spécialité, brevets/formations/habilitations. Les brevets ne sont pas des grades. | — | à instruire ⚪ | aucune |
| <span class='nb'>DEC-ORG-05</span> | Prendre en compte FEM, BE, BAT, BS, BST et les évolutions récentes (BHT, C-CDM). | — | à instruire ⚪ | aucune |
| <span class='nb'>DEC-ORG-06</span> | Configuration plutôt que code : aucune règle susceptible d'évoluer n'est codée en dur. | — | à instruire ⚪ | aucune |
| <span class='nb'>DEC-OUT-01</span> | Signaler : outil manquant, inutile, inadapté, instruction ambiguë, information manquante. | L26 non livré dans l'état B | non développée | plan en lots |
| <span class='nb'>DEC-OUT-02</span> | Remarques conservées et visibles du chef de secteur. | L26 non livré dans l'état B | non développée | plan en lots |
| <span class='nb'>DEC-OUT-03</span> | La liste d'outillage n'est jamais modifiée automatiquement. | L26 non livré dans l'état B | non développée | plan en lots |
| <span class='nb'>DEC-OUT-04</span> | Le chef décide de modifier ou non la fiche de référence. | L26 non livré dans l'état B | non développée | plan en lots |
| <span class='nb'>DEC-OUT-05</span> | Procédures techniques et de sécurité : validations applicables conservées. | L26 non livré dans l'état B | non développée | plan en lots |
| <span class='nb'>DEC-PER-01</span> | Les tâches périodiques sont générées à partir des fiches de maintenance et des matériels concernés. | L19 non livré dans l'état B | partielle | code |
| <span class='nb'>DEC-PER-02</span> | Périodicités : hebdomadaire, mensuelle, trimestrielle, annuelle, biennale, quinquennale. | L19 non livré dans l'état B | non développée | plan en lots |
| <span class='nb'>DEC-PER-03</span> | Prochaine échéance calculée depuis la réalisation effective, sauf calendrier fixe réglementaire ou technique. | L19 non livré dans l'état B | non développée | plan en lots |
| <span class='nb'>DEC-PER-04</span> | Les historiques sont conservés, retards compris. | L19 non livré dans l'état B | réalisée | code |
| <span class='nb'>DEC-PRE-01</span> | Le module d'absences est limité aux corrections nécessaires (un système extérieur gère les absences). | — | à instruire ⚪ | aucune |
| <span class='nb'>DEC-PRE-02</span> | Pas de module autonome de passation ; préserver les fonctions existantes utiles. | — | réalisée | code |
| <span class='nb'>DEC-PRE-03</span> | Conserver les exports PDF, Excel et CSV de pilotage, puis en améliorer la qualité. | — | réalisée | code |
| <span class='nb'>DEC-PRE-04</span> | QR et inspections mobiles non prioritaires : reportés, sans suppression précipitée de l'existant. | — | réalisée | code |
| <span class='nb'>DEC-PRE-05</span> | Préserver le fonctionnement local sur le réseau du bord. | — | à instruire ⚪ | aucune |
| <span class='nb'>DEC-PRE-06</span> | Architecture de déploiement, PKI, sauvegarde et sécurité des SI : à soumettre aux experts compétents. | L01 livré ; L21 non livré dans l'état B | partielle (1 lot(s) livré(s) sur 2) | plan en lots |
| <span class='nb'>DEC-QUA-01</span> | Les formations et habilitations enregistrées ne bloquent pas automatiquement l'attribution ni l'exécution des tâches ordinaires ; le responsable humain choisit. | L18 non livré dans l'état B | non développée | plan en lots |
| <span class='nb'>DEC-QUA-02</span> | Les qualifications connues peuvent être affichées à titre informatif. | L18 non livré dans l'état B | non développée | plan en lots |
| <span class='nb'>DEC-QUA-03</span> | Une information manquante ou périmée ne bloque pas l'attribution. | L18 non livré dans l'état B | non développée | plan en lots |
| <span class='nb'>DEC-QUA-04</span> | Distinguer deux situations : (1) tâches ordinaires, jamais bloquées par les qualifications enregistrées ; (2) visas techniques, fonctions de service et signatures … | L18 non livré dans l'état B | non développée | plan en lots |
| <span class='nb'>DEC-RTX-01</span> | Circuit RETEX : auteur → chef de section si présent → chef de secteur → chef de service. | L11 non livré dans l'état B | écart (A15) | code |
| <span class='nb'>DEC-RTX-02</span> | Une demande de correction doit être motivée. | L11 non livré dans l'état B | non développée | plan en lots |
| <span class='nb'>DEC-RTX-03</span> | La correction entraîne une nouvelle version et les validations nécessaires. | L11 non livré dans l'état B | non développée | plan en lots |
| <span class='nb'>DEC-RTX-04</span> | Traçabilité de qui a proposé, modifié, validé ou rejeté. | L11 non livré dans l'état B | non développée | plan en lots |
| <span class='nb'>DEC-SUP-01</span> | La suppléance est explicite, temporaire, limitée à une fonction et un périmètre, activée par une autorité compétente, traçable. | L08 non livré dans l'état B | non développée | plan en lots |
| <span class='nb'>DEC-SUP-02</span> | Une seule personne exerce la responsabilité active d'un même périmètre à un instant donné. | L08 non livré dans l'état B | non développée | plan en lots |
| <span class='nb'>DEC-SUP-03</span> | Le retour anticipé ou la fin de suppléance suit les règles de validation retenues. | L08 non livré dans l'état B | non développée | plan en lots |
| <span class='nb'>DEC-SUP-04</span> | Les actes du suppléant restent attribués à leur auteur. | L08 non livré dans l'état B | non développée | plan en lots |
| <span class='nb'>DEC-SUP-05</span> | Le titulaire retrouve un récapitulatif des actions réalisées pendant son absence. | L08 non livré dans l'état B | non développée | plan en lots |
| <span class='nb'>DEC-SUP-06</span> | Les qualifications réglementaires nécessaires à certains visas restent obligatoires pour le suppléant (voir DEC-QUA-04). | L08 non livré dans l'état B | non développée | plan en lots |
| <span class='nb'>DEC-SUP-07</span> | La note Notion « pas de nouveau système de délégation en V1 » est une question de périmètre et de calendrier de développement, non une annulation de la décision … | L08 non livré dans l'état B | non développée | plan en lots |
| <span class='nb'>DEC-TAC-01</span> | Le chef de section attribue les tâches de sa section. | — | à instruire ⚪ | aucune |
| <span class='nb'>DEC-TAC-02</span> | Le chef de secteur supervise, attribue directement et réaffecte. | — | à instruire ⚪ | aucune |
| <span class='nb'>DEC-TAC-03</span> | Le chef de service dispose de la supervision correspondant à sa fonction. | — | à instruire ⚪ | aucune |
| <span class='nb'>DEC-TAC-04</span> | Trois priorités : normale, haute, urgente. | L14 non livré dans l'état B | écart (A13) | code |
| <span class='nb'>DEC-TAC-05</span> | Une priorité imposée par le chef de secteur ne peut pas être abaissée par le chef de section. | L14 non livré dans l'état B | écart (A13) | code |
| <span class='nb'>DEC-TAC-06</span> | Les changements d'attribution et de priorité sont tracés et notifiés aux personnes concernées. | L14 non livré dans l'état B | non développée | plan en lots |
| <span class='nb'>DEC-UX-01</span> | À l'ouverture : tâches du jour, tours de service, actions en attente, urgences, informations utiles. | L24 non livré dans l'état B | partielle | code |
| <span class='nb'>DEC-UX-02</span> | Éviter grands espaces vides et défilement inutile ; réduire les textes explicatifs permanents ; cartes cliquables. | L24 non livré dans l'état B | non développée | plan en lots |
| <span class='nb'>DEC-UX-03</span> | Recherche globale centrée et utile. | L24 non livré dans l'état B | non développée | plan en lots |
| <span class='nb'>DEC-UX-04</span> | Permettre d'épingler des entrées du menu. | L24 non livré dans l'état B | non développée | plan en lots |
| <span class='nb'>DEC-UX-05</span> | Afficher clairement les tours de service à venir, à valider et effectués. | L24 non livré dans l'état B | non développée | plan en lots |
| <span class='nb'>DEC-UX-06</span> | Notifications lues conservées dans le centre mais retirées de la liste principale. | L24 non livré dans l'état B | non développée | plan en lots |
| <span class='nb'>DEC-UX-07</span> | Corriger les boutons inactifs et les parcours de navigation défaillants. | L24 non livré dans l'état B | non développée | plan en lots |
| <span class='nb'>DEC-UX-08</span> | Terminologie « Mes tours de services ». | L24 non livré dans l'état B | écart (A11) | code |
| <span class='nb'>DEC-UX-09</span> | Recherche de personnes : informations professionnelles pertinentes, sous réserve des droits. | L24 non livré dans l'état B | non développée | plan en lots |
| <span class='nb'>DEC-UX-10</span> | Interface adaptée aux utilisateurs expérimentés, sans aides envahissantes ; aide progressive réactivable. | L24 non livré dans l'état B | non développée | plan en lots |
| <span class='nb'>DEC-UX-11</span> | Le calendrier reste un élément central. | L24 non livré dans l'état B | non développée | plan en lots |

## Précisions sur les décisions partielles

- **DEC-DRT-05** — Partielle : l'archivage effectif (L02) et la suppression sûre des unités (L03) sont livrés dans l'état B ; le volet « comptes : désactiver au lieu de supprimer » (L04) n'est pas lancé. Statut global conservé : partielle. Les lots L02 et L03 attendent encore la validation du PO selon le plan.
- **DEC-PER-01** — Les échéances sont générées depuis les plans et fiches (constat sur le code) ; les périodicités nommées ne le sont pas (L19).
- **DEC-PRE-06** — Partielle : le verrou des commandes de démonstration (L01) est livré ; la sécurité d'accès avec les SIC (L21) n'est pas lancée.
- **DEC-UX-01** — Accueil « Aujourd'hui » existant ; cartes et aide progressive non développées (L24).
