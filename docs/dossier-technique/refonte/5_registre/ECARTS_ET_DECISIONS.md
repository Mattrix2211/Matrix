# Lire ce registre

> **Public :** PO, responsables, mainteneurs · **Accès restreint** · Source unique : `registre.json` (généré).

Ce registre rassemble les **écarts** entre ce que le PO a décidé et ce que fait le logiciel, les **points à confirmer**, les **propositions** non arbitrées, les **anomalies du dossier** et l'**état des 125 décisions**. Un écart est **documenté, pas autorisé à corriger** : il ne modifie ni le logiciel ni une décision du PO.

| Niveau de preuve | Signification |
|---|---|
| [C] | lu dans le code de l'état B |
| [N] | vérifié dans le navigateur (instance de démonstration, données fictives) |
| [T] | vérifié par un test exécuté |
| [V] | vérifié visuellement |
| [A] | mesure automatique |
| [R] | rapporté par une source antérieure, non revérifié |
| [?] | non vérifié |

**Répartition :** 26 écarts, 8 points à confirmer, 7 propositions, 6 nouveaux écarts du logiciel, 38 anomalies documentaires (36 ouvertes), 125 décisions.

# Écarts du logiciel (A1 à A26)

### A1 — Administrateur technique et actes métier

| Rubrique | Contenu |
|---|---|
| **Règle validée** | Un administrateur technique ne devient pas automatiquement autorité de validation métier : il désigne les titulaires, sans viser à leur place. Application mécanique d'un transfert approuvé autorisée. (`DEC-DRT-02`, source S1 §4, DP-09, cahier §5, Notion « 13 — Décisions ») |
| **Constat dans l'état B** | Le niveau numérique de l'administrateur d'unité (8) est supérieur ou égal à tous les seuils par défaut des actions métier du registre (annexe B, colonne « Admin. unité »). Dans les circuits des quarts, il franchit la **supervision du commandement** (`NIVEAU_SUPERVISION_GLOBALE_LISTE = COMMANDANT`, `quarts/models.py:147`) : il peut gérer et **publier** les listes de son bâtiment (`peut_publier_liste`, `quarts/models.py:355`), **valider ou refuser** un échange de tours (`peut_valider_echange`, `quarts/echanges.py:205`) et viser aux paliers « secteur » et « service » de la feuille de service (`_supervision_sur_navire`, `quarts/models.py:1977`). Le visa du COMAEQ et la rédaction de la feuille de service lui restent fermés (`peut_viser_comaeq` `:2215` ; `peut_rediger_feuille_service` `:2065`). |
| **Conséquences** | *Fonctionnelles* : un administrateur technique peut trancher des échanges et publier des listes alors que la règle le lui interdit. *Sécurité / traçabilité* : l'acte est tracé au nom de l'administrateur, mais il brouille la séparation des pouvoirs voulue entre administration de la plateforme et autorité métier. Pas de contournement d'authentification : l'écart est dans la **répartition** des droits. |
| **Profils concernés** | administrateur d'unité ; commandement |
| **Lot de correction prévu** | L06 — Exclusion de l'administrateur technique des actes métier (non lancé) |
| **Niveau de preuve** | [C] |
| **Statut** | documenté, non arbitré (pas une autorisation de modifier le logiciel) |

### A2 — Échanges de tours

| Rubrique | Contenu |
|---|---|
| **Règle validée** | La décision finale revient au COMAEQ ou à son suppléant officiellement habilité. Le BSC ou le chef de liste peut **instruire** la demande, mais n'a pas automatiquement l'autorité de décision finale. Cette décision **remplace** la note Notion du 28/10 (« le chef de liste habilité valide »). (`DEC-FDS-07`, `DEC-FDS-13` ; sources S1 §7, S3 ; `J_TRIAGE_ET_ARBITRAGES.md` §2) |
| **Constat dans l'état B** | Un échange accepté par le marin sollicité attend « le chef de liste » (`STATUT_ACCEPTE` : « En attente du chef de liste »). La validation et le refus sont ouverts à qui **gère la liste** (`peut_valider_echange`, `quarts/echanges.py:205`, qui s'appuie sur `peut_gerer_liste`, `quarts/models.py:297`) : le chef de liste désigné pour le périmètre exact de la liste, ou le commandement du bâtiment (niveau commandant et au-dessus). Aucune règle ne désigne le COMAEQ ni un suppléant. À défaut de chef de liste désigné, la notification va au créateur de la liste (`chefs_de_liste_a_notifier`, `quarts/echanges.py:176`). |
| **Conséquences** | *Fonctionnelles* : l'autorité qui tranche n'est pas celle décidée ; un chef de liste (qui peut être un chef de section) valide seul un échange de service à quai. Le COMAEQ n'est ni notifié ni habilité. *Sécurité* : sans suppléance officielle, la règle cible ne peut pas être appliquée telle quelle (voir B3). |
| **Profils concernés** | marins ; chefs de liste ; COMAEQ |
| **Lot de correction prévu** | L10 — Échanges de tours décidés par le COMAEQ (non lancé) ; dépend de la suppléance explicite (L08) |
| **Niveau de preuve** | [C] |
| **Statut** | documenté, non arbitré (pas une autorisation de modifier le logiciel) |

### A3 — Publication des listes de quarts et de gardes

| Rubrique | Contenu |
|---|---|
| **Règle validée** | Le chef de liste **prépare et propose** ; le COMAEQ ou son suppléant officiellement habilité **approuve et publie**. Toute modification après publication est tracée et donne lieu à une nouvelle version officielle si nécessaire. (`DEC-FDS-14`, S4 arbitrage C-1) |
| **Constat dans l'état B** | Le chef de liste propose (`proposer`, `quarts/models.py` : statut `PROPOSEE`) ; la publication (`publier`) est ouverte à `peut_publier_liste` (`quarts/models.py:355`) : (a) le commandement du bâtiment (commandant, administrateur d'unité, administrateur général sur son périmètre) ; (b) tout rôle atteignant le seuil configurable `liste_service_publication` (**chef de service** par défaut) **et** dont le périmètre personnel est **exactement** celui de la liste ; le commandant en second est explicitement exclu (`_perimetre_dans_scope_utilisateur`, `:308`). La **fonction COMAEQ n'intervient pas** : un COMAEQ ne publie que si sa propre portée est celle de la liste ou s'il est commandement. |
| **Conséquences** | *Fonctionnelles* : la publication relève d'un chef de service du périmètre ou du commandement ; l'autorité fonctionnelle « vie à bord » n'est pas mobilisée. *Sécurité* : le seuil est réglable par bâtiment : un bâtiment peut l'abaisser et élargir qui publie. |
| **Profils concernés** | chefs de liste ; chefs de service ; COMAEQ ; commandement |
| **Lot de correction prévu** | L09 — Visas par fonction et listes publiées (non lancé ; découpé en trois) |
| **Niveau de preuve** | [C] |
| **Statut** | documenté, non arbitré (pas une autorisation de modifier le logiciel) |

### A4 — Droits du commandant en second

| Rubrique | Contenu |
|---|---|
| **Règle validée** | Le commandant en second est le remplaçant désigné du commandant et a une **vision globale**. Ses droits d'écriture **découlent de ses responsabilités métier réelles**, et non d'un simple seuil « commandant ou plus ». Il publie des annonces sur son bâtiment, garde la suppléance du commandant pour la validation de la relève, n'a pas le visa COMA. (Notion « 13 — Décisions » 10/10 et recette V1 ; dossier V1.2 `DEC-DRT-01`) |
| **Constat dans l'état B** | Deux familles de comparaison coexistent. Pour l'**API** et les vues qui utilisent `niveau_ecriture`, son écriture héritée du grade est **retirée** (il retombe au niveau équipier, `ROLES_SANS_ECRITURE_HERITEE`, `matrix/core/roles.py:50`), sauf action explicitement ouverte (`annonce_publication`). Pour de **nombreuses vues web**, le seuil est comparé à son **grade** (`user_role_level`) : il peut alors gérer les modules (`matrix/views.py:289`), saisir le programme (`programme/services.py:47`), proposer des fiches (`assets/fiche_validation.py:130`), voir l'annuaire (`matrix/core/navigation.py`). Dans les circuits des quarts, il est exclu de la désignation, du visa et de la publication (`quarts/models.py:308`). |
| **Conséquences** | *Fonctionnelles* : ce que le second peut faire dépend de la page utilisée, non d'une liste de responsabilités qui lui sont attribuées. *Sécurité* : un même acte peut être refusé par l'API et accepté par l'écran correspondant. |
| **Profils concernés** | commandant en second |
| **Lot de correction prévu** | Aucun lot identifié ne traite spécifiquement l'harmonisation (voir B2). Liens : L07 (rattachement et validation des rôles), L09 (visas par fonction). |
| **Niveau de preuve** | [C] |
| **Statut** | documenté, non arbitré (pas une autorisation de modifier le logiciel) |

### A5 — Règles du projet : « garder des identifiants stables (UUID, NNO) pour de futures API » (`CLAUDE.md`)

| Rubrique | Contenu |
|---|---|
| **Règle validée** | Règles du projet : « garder des identifiants stables (UUID, NNO) pour de futures API » (`CLAUDE.md`) |
| **Constat dans l'état B** | UUID et NNO existent côté matériel, catalogue, ticket, objets de la feuille de service ; ni compte, ni unité, ni tâche, ni liste |
| **Conséquences** | Un futur interfaçage devra s'appuyer sur d'autres identifiants pour les personnes et les unités ; pas d'effet sur le fonctionnement actuel |
| **Profils concernés** | développeurs ; intégrateurs |
| **Lot de correction prévu** | Aucun (périmètre à décider) |
| **Niveau de preuve** | [C] |
| **Statut** | documenté, non arbitré (pas une autorisation de modifier le logiciel) |

### A6 — `docs/REFERENCE.md` §4 « Les 14 apps Django »

| Rubrique | Contenu |
|---|---|
| **Règle validée** | `docs/REFERENCE.md` §4 « Les 14 apps Django » |
| **Constat dans l'état B** | L'état B contient 21 applications et le noyau (paquet `matrix/core`) |
| **Conséquences** | Documentation du dépôt en retard ; pas d'effet fonctionnel |
| **Profils concernés** | développeurs |
| **Lot de correction prévu** | L28 (dette documentaire) |
| **Niveau de preuve** | [C] |
| **Statut** | documenté, non arbitré (pas une autorisation de modifier le logiciel) |

### A7 — Cahier §35 : « RBAC + ABAC + périmètre + responsabilité »

| Rubrique | Contenu |
|---|---|
| **Règle validée** | Cahier §35 : « RBAC + ABAC + périmètre + responsabilité » |
| **Constat dans l'état B** | Rôle + périmètre + attributs ciblés (équipage, fonction de commandant adjoint) + désignations ; pas de moteur d'attributs général |
| **Conséquences** | Les règles à attributs sont codées au cas par cas (« configuration plutôt que code » partielle) |
| **Profils concernés** | responsables ; développeurs |
| **Lot de correction prévu** | — |
| **Niveau de preuve** | [C] |
| **Statut** | documenté, non arbitré (pas une autorisation de modifier le logiciel) |

### A8 — Cahier §8, §10, §11 (génération automatique des tours) ; §20 (rondes) ; organisation « miroir »

| Rubrique | Contenu |
|---|---|
| **Règle validée** | Cahier §8, §10, §11 (génération automatique des tours) ; §20 (rondes) ; organisation « miroir » |
| **Constat dans l'état B** | Génération abandonnée (décision du 09/10) ; rondes retirées ; organisation miroir retirée |
| **Conséquences** | Documentation du cahier partiellement obsolète ; **le dossier décrit le code** |
| **Profils concernés** | PO |
| **Lot de correction prévu** | Alignement Notion par le PO |
| **Niveau de preuve** | [C] |
| **Statut** | documenté, non arbitré (pas une autorisation de modifier le logiciel) |

### A9 — Principe « Internet n'existe pas »

| Rubrique | Contenu |
|---|---|
| **Règle validée** | Principe « Internet n'existe pas » |
| **Constat dans l'état B** | Tenu par le code ; `boto3` et `requests` déclarés sans usage constaté |
| **Conséquences** | Aucune ; observation d'exploitation |
| **Profils concernés** | exploitants |
| **Lot de correction prévu** | — |
| **Niveau de preuve** | [C] |
| **Statut** | documenté, non arbitré (pas une autorisation de modifier le logiciel) |

### A10 — Vocabulaire cible de Notion 11 (mission, capacité, dérogation…)

| Rubrique | Contenu |
|---|---|
| **Règle validée** | Vocabulaire cible de Notion 11 (mission, capacité, dérogation…) |
| **Constat dans l'état B** | Sans équivalent dans le code |
| **Conséquences** | Cible non développée |
| **Profils concernés** | PO |
| **Lot de correction prévu** | — |
| **Niveau de preuve** | [C] |
| **Statut** | documenté, non arbitré (pas une autorisation de modifier le logiciel) |

### A11 — « Mes tours de services » (`DEC-UX-08`, S1 §12 ; `CT-06`)

| Rubrique | Contenu |
|---|---|
| **Règle validée** | « Mes tours de **services** » (`DEC-UX-08`, S1 §12 ; `CT-06`) |
| **Constat dans l'état B** | L'accueil affiche « Mes tours de **service** » |
| **Conséquences** | Libellé : purement visuel |
| **Profils concernés** | marins |
| **Lot de correction prévu** | Lot UX (L24) |
| **Niveau de preuve** | [C] |
| **Statut** | documenté, non arbitré (pas une autorisation de modifier le logiciel) |

### A12 — Fonctionnement cible : impression A4 de la feuille de service par le BSC, signalement de la nécessit

| Rubrique | Contenu |
|---|---|
| **Règle validée** | **Fonctionnement cible** : impression A4 de la feuille de service par le BSC, signalement de la nécessité de réimprimer une feuille déjà affichée, et **réimpression avec versionnement** (`DEC-FDS-04`, `DEC-FDS-05`, `DEC-FDS-06`) |
| **Constat dans l'état B** | Les versions de la feuille sont conservées (VersionFeuilleService). **Une impression par le navigateur existe** (bouton « Imprimer » de la fiche de la feuille, constat AUD-002, vérifié dans le navigateur le 12/11/2026) ; il n'existe ni mise en page A4 dédiée à l'affichage, ni alerte de réimpression, ni réimpression versionnée. |
| **Conséquences** | Le BSC imprime avec les moyens du navigateur ; pas d'alerte de remplacement d'un affichage |
| **Profils concernés** | BSC ; COMAEQ |
| **Lot de correction prévu** | L27 |
| **Niveau de preuve** | [C][N] |
| **Révision** | Texte révisé : l'ancien énoncé « aucune page imprimable » était inexact (AUD-002). |
| **Statut** | documenté, non arbitré (pas une autorisation de modifier le logiciel) |

### A13 — Trois priorités : normale, haute, urgente ; priorité du chef de secteur non abaissable par le chef d

| Rubrique | Contenu |
|---|---|
| **Règle validée** | Trois priorités : normale, haute, urgente ; priorité du chef de secteur non abaissable par le chef de section (`DEC-TAC-04`, `DEC-TAC-05`) |
| **Constat dans l'état B** | Deux priorités : normale, urgente ; pas de règle d'abaissement |
| **Conséquences** | Perte d'un niveau de nuance ; pas de règle de hiérarchie des priorités |
| **Profils concernés** | chefs de secteur ; chefs de section |
| **Lot de correction prévu** | L14 |
| **Niveau de preuve** | [C] |
| **Statut** | documenté, non arbitré (pas une autorisation de modifier le logiciel) |

### A14 — Synthèse de passation : un chef de section ne consulte que sa propre section (Notion « 13 — Décision

| Rubrique | Contenu |
|---|---|
| **Règle validée** | Synthèse de passation : un chef de section ne consulte que **sa propre section** (Notion « 13 — Décisions », recette V1) |
| **Constat dans l'état B** | `syntheses_visibles` (`dashboard/passation.py:53`) filtre par bâtiment et équipage, **sans borne par section** ; le contenu figé couvre tout le bâtiment (`contenu_passation`, `dashboard/passation.py:220`) ; le code assume « l'équipage montant lit tout ». **Test du 12/11/2026 (état B, comptes fictifs, deux sections)** : un chef de section lit les tâches, blocages et anomalies de l'autre section ; équipier, chef d'un autre bâtiment, chef sans équipage et chef d'un troisième équipage refusés |
| **Conséquences** | Un chef de section peut lire la synthèse de tout le bâtiment (qualifications, annonces, listes, tâches). Écart confirmé ; **aucune fuite réelle alléguée** ; la règle du PO n'est pas modifiée |
| **Profils concernés** | chefs de section ; commandement ; équipage sortant |
| **Lot de correction prévu** | Non identifié |
| **Vérifications** | test 12/11/2026 (8 tests, comptes fictifs) ; navigateur 12/11/2026 : chef de section de l'équipage sortant lit 28 tâches dont 12 hors de sa section ; équipier et chef d'un autre bâtiment : 404 |
| **Niveau de preuve** | [T][N] |
| **Statut** | documenté, non arbitré (pas une autorisation de modifier le logiciel) |

### A15 — Circuit RETEX : auteur → chef de section → chef de secteur → chef de service (`DEC-RTX-01`) ; correc

| Rubrique | Contenu |
|---|---|
| **Règle validée** | Circuit RETEX : auteur → chef de section → chef de secteur → chef de service (`DEC-RTX-01`) ; correction motivée, nouvelle version (`DEC-RTX-02`, `DEC-RTX-03`) |
| **Constat dans l'état B** | Une seule étape : tout habilité du bâtiment (seuil `retex_validation`, chef de service) valide ou refuse ; les fonctions citant le COMA référent passent en premier dans la notification ; pas de demande de correction |
| **Conséquences** | Un RETEX peut être validé sans visa de la hiérarchie directe de l'auteur ; pas de boucle de correction |
| **Profils concernés** | auteurs de RETEX ; chefs de section, de secteur et de service |
| **Lot de correction prévu** | L11 |
| **Niveau de preuve** | [C] |
| **Statut** | documenté, non arbitré (pas une autorisation de modifier le logiciel) |

### A16 — Diffusion « flotte » : proposé à l'organisme destinataire

| Rubrique | Contenu |
|---|---|
| **Règle validée** | Diffusion « flotte » : proposé à l'organisme destinataire |
| **Constat dans l'état B** | La diffusion « flotte » **marque** le RETEX ; aucune transmission n'existe |
| **Conséquences** | L'organisme n'est jamais saisi ni notifié par Matrix ; qui transmet est **à confirmer** |
| **Profils concernés** | auteurs de RETEX ; organismes destinataires |
| **Lot de correction prévu** | L11 |
| **Niveau de preuve** | [C] |
| **Statut** | documenté, non arbitré (pas une autorisation de modifier le logiciel) |

### A17 — Préparation à l'appareillage : contrôles issus de fiches de référence approuvées ; circuit section/s

| Rubrique | Contenu |
|---|---|
| **Règle validée** | Préparation à l'appareillage : contrôles issus de fiches de référence approuvées ; circuit section/secteur → service → COMANAV ; contrôles obligatoires, critiques non dérogeables, réserves (`DEC-APP-01`, `DEC-APP-02`, `DEC-APP-10` à `DEC-APP-12`, `DEC-APP-14`) |
| **Constat dans l'état B** | Les points sont calculés à l'ouverture depuis l'état des installations critiques ; une seule signature (chef de secteur ou plus) ; ni classification, ni réserve, ni fiche de référence |
| **Conséquences** | Aucun circuit COMANAV ; la signature atteste la clôture de la session, pas l'aptitude. Compatibilité avec les procédures du bord **à confirmer avant implémentation** |
| **Profils concernés** | chefs de secteur ; chefs de service ; COMANAV |
| **Lot de correction prévu** | L23 |
| **Niveau de preuve** | [C] |
| **Statut** | documenté, non arbitré (pas une autorisation de modifier le logiciel) |

### A18 — Transfert de matériel entre secteurs et entre services avec approbations (`DEC-MAT-01` à `DEC-MAT-04

| Rubrique | Contenu |
|---|---|
| **Règle validée** | Transfert de matériel entre secteurs et entre services avec approbations (`DEC-MAT-01` à `DEC-MAT-04`) |
| **Constat dans l'état B** | Aucun circuit ; réaffectation par l'affectation en masse |
| **Conséquences** | Pas de trace d'approbation du transfert ni de suivi des tâches ouvertes |
| **Profils concernés** | chefs de service ; gestionnaires de matériel |
| **Lot de correction prévu** | L13 |
| **Niveau de preuve** | [C] |
| **Statut** | documenté, non arbitré (pas une autorisation de modifier le logiciel) |

### A19 — Demande de places : l'organisme de formation répond dans un dossier vivant (timeline, fil, transmiss

| Rubrique | Contenu |
|---|---|
| **Règle validée** | Demande de places : l'organisme de formation répond dans un **dossier vivant** (timeline, fil, transmission, prise en compte) — cible Notion « 03 » |
| **Constat dans l'état B** | L'organisme est une **unité de type École ou Centre de formation** ; un référent de la formation dans cette unité attribue ou refuse (`_attribuer_places`) ; le demandeur est notifié. Pas de timeline, pas de fil systématique, pas d'étape « transmise à l'organisme » pour la demande de places |
| **Conséquences** | Cible non développée ; correction par rapport au rapport E3 (qui disait que l'organisme n'était pas un acteur) |
| **Profils concernés** | référents de formation ; demandeurs ; organismes de formation |
| **Lot de correction prévu** | Cible Notion « 03 » |
| **Niveau de preuve** | [C] |
| **Statut** | documenté, non arbitré (pas une autorisation de modifier le logiciel) |

### A20 — Occurrence non conforme : état « En validation » (pas de règle de sortie décidée par le PO)

| Rubrique | Contenu |
|---|---|
| **Règle validée** | Occurrence non conforme : état « En validation » (pas de règle de sortie décidée par le PO) |
| **Constat dans l'état B** | **Vérifié par test (12/11/2026)** : aucune action de validation dédiée ; sorties : (1) correction du compte rendu par un chef de secteur ou plus (conformité finale conforme) ; (2) API `start` sans contrôle de l'état (appelable par un assigné), qui laisse « En cours » avec un compte rendu terminé non conforme ; (3) administration Django. Exclue du calcul des retards (choix explicite) ; aucune notification ; visible en « À faire » et en supervision ; clôture du ticket sans effet sur l'occurrence ; pour une **installation**, pas de ticket automatique et **échéance suivante non générée** tant que l'état dure |
| **Conséquences** | **Risque de blocage** : « En validation » sans échéance ni relance, entretien récurrent d'installation suspendu ; sortie par l'API `start` non voulue. Règle de sortie **à décider par le PO** (D2) ; aucune règle inventée |
| **Profils concernés** | exécutants ; chefs de secteur ; responsables des installations |
| **Lot de correction prévu** | Non identifié (à décider par le PO) |
| **Vérifications** | test 12/11/2026 (18 tests) ; navigateur 12/11/2026 : bouton « Enregistrer la correction » visible du seul chef de secteur et au-delà |
| **Niveau de preuve** | [T][N] |
| **Statut** | documenté, non arbitré (pas une autorisation de modifier le logiciel) |

### A21 — Périodicités nommées, remarques d'outillage, durée indicative (`DEC-PER-01` à `04`, `DEC-OUT-01` à `

| Rubrique | Contenu |
|---|---|
| **Règle validée** | Périodicités nommées, remarques d'outillage, durée indicative (`DEC-PER-01` à `04`, `DEC-OUT-01` à `05`, `DEC-DUR-*`) |
| **Constat dans l'état B** | Non développé |
| **Conséquences** | Cible, non contradictoire |
| **Profils concernés** | chefs de secteur |
| **Lot de correction prévu** | Plan V1.2 |
| **Niveau de preuve** | [C] |
| **Statut** | documenté, non arbitré (pas une autorisation de modifier le logiciel) |

### A22 — Le projet suppose Python 3.12 ou plus (README, dépendances)

| Rubrique | Contenu |
|---|---|
| **Règle validée** | Le projet suppose Python 3.12 ou plus (README, dépendances) |
| **Constat dans l'état B** | Le script d'installation annonce « Python 3.8 ou supérieur » |
| **Conséquences** | Une installation sur un Python ancien échouerait tard ; incohérence de documentation uniquement |
| **Profils concernés** | développeurs ; exploitants |
| **Lot de correction prévu** | L28 |
| **Niveau de preuve** | [C] |
| **Statut** | documenté, non arbitré (pas une autorisation de modifier le logiciel) |

### A23 — Sécurité d'accès avec les SIC : HTTPS, limitation des connexions (cible)

| Rubrique | Contenu |
|---|---|
| **Règle validée** | Sécurité d'accès avec les SIC : HTTPS, limitation des connexions (cible) |
| **Constat dans l'état B** | En production, redirection HTTPS et cookies sécurisés actifs ; **ni limitation des tentatives de connexion, ni HSTS, ni réglage de proxy inverse** ; origines CSRF de confiance codées sur `localhost` ; aucun serveur HTTPS ni serveur d'application livré |
| **Conséquences** | Cible non développée ; l'architecture réelle de mise en service reste à définir avec les SIC |
| **Profils concernés** | exploitants ; SIC |
| **Lot de correction prévu** | L21 |
| **Niveau de preuve** | [C] |
| **Statut** | documenté, non arbitré (pas une autorisation de modifier le logiciel) |

### A24 — Sauvegarde, restauration, supervision, conservation des journaux (à fournir, `IM-10` pour les durées

| Rubrique | Contenu |
|---|---|
| **Règle validée** | Sauvegarde, restauration, supervision, conservation des journaux (à fournir, `IM-10` pour les durées) |
| **Constat dans l'état B** | **Rien n'existe** dans le dépôt : ni script, ni documentation |
| **Conséquences** | Aucun plan de reprise ; durées de conservation des notifications, journaux et estimations non définies (B8) |
| **Profils concernés** | exploitants ; SIC |
| **Lot de correction prévu** | À définir avec les SIC |
| **Niveau de preuve** | [C] |
| **Statut** | documenté, non arbitré (pas une autorisation de modifier le logiciel) |

### A25 — Les modules désactivés « n'existent plus » pour le bâtiment (principe de configuration par bâtiment)

| Rubrique | Contenu |
|---|---|
| **Règle validée** | Les modules désactivés « n'existent plus » pour le bâtiment (principe de configuration par bâtiment) |
| **Constat dans l'état B** | **Vérifié par test (12/11/2026)**, modules maintenance et logistique désactivés : toutes les routes web des modules du registre (134 au total, toutes à vue-classe) sont refusées (redirection vers l'accueil) ; menu et recherche masquent le module ; **API : lecture et écriture restent accessibles** (liste, démarrage d'une occurrence, transition d'un ticket) ; **administration Django** accessible ; **tâches planifiées** : notifications de retard et de stock créées, échéances générées ; **enchaînement interne** : ticket créé depuis une maintenance non conforme ; **accueil « À faire » et calendrier continuent d'afficher** les maintenances avec un lien vers une page refusée |
| **Conséquences** | Choix volontaire du code pour ne pas casser les enchaînements ; ni l'accueil ni le calendrier n'appliquent le filtre de module ; la **règle métier attendue** (désactiver = masquer l'interface seulement, ou bloquer aussi l'API et les tâches) **n'est pas décidée** |
| **Profils concernés** | administrateurs d'unité ; commandants ; intégrateurs |
| **Lot de correction prévu** | — |
| **Vérifications** | test 12/11/2026 (3 tests de constat) |
| **Niveau de preuve** | [T] |
| **Statut** | documenté, non arbitré (pas une autorisation de modifier le logiciel) |

### A26 — Neuf modules sans API (quarts, absences, tâches, annonces, demandes, programme, postes, documentatio

| Rubrique | Contenu |
|---|---|
| **Règle validée** | Neuf modules sans API (quarts, absences, tâches, annonces, demandes, programme, postes, documentation, RETEX) |
| **Constat dans l'état B** | Aucune route `/api/` ; pilotage par les pages seulement |
| **Conséquences** | Aucune intégration possible sur ces objets ; cohérent avec la phase 7 « différée » |
| **Profils concernés** | intégrateurs |
| **Lot de correction prévu** | Phase 7 |
| **Niveau de preuve** | [C] |
| **Statut** | documenté, non arbitré (pas une autorisation de modifier le logiciel) |

# Nouveaux écarts du logiciel (NE-01 à NE-06)

### NE-01 — Bouton « Exécuter » affiché sans droit d'exécution

| Rubrique | Contenu |
|---|---|
| **Constat** | La liste de maintenance affiche « Exécuter » pour des occurrences que le serveur refuse (403) à l'utilisateur ; le bouton « M'assigner » existe aussi. |
| **Profils concernés** | marins ; chefs de section |
| **Niveau de preuve** | [N] |
| **Preuve** | audit_preuves/navigateur_droits.md |
| **Statut** | documenté, non arbitré (pas une autorisation de modifier le logiciel) |

### NE-02 — Lignes de tickets cliquables sans lien ni focus clavier

| Rubrique | Contenu |
|---|---|
| **Constat** | Les lignes de la liste des tickets s'ouvrent par un gestionnaire de clic sur la ligne seulement ; non accessible au clavier. |
| **Profils concernés** | tous profils |
| **Niveau de preuve** | [C] |
| **Preuve** | matrix/templates/logistics/ticket_list.html (accès restreint) |
| **Statut** | documenté, non arbitré (pas une autorisation de modifier le logiciel) |

### NE-03 — Redirection HTTPS sans réglage de proxy inverse

| Rubrique | Contenu |
|---|---|
| **Constat** | SECURE_SSL_REDIRECT est actif en production sans réglage de proxy TLS ; comportement derrière un proxy non testé. |
| **Profils concernés** | exploitants ; SIC |
| **Niveau de preuve** | [C][?] |
| **Preuve** | chapitre « Exploitation » du dossier technique |
| **Statut** | documenté, non arbitré (pas une autorisation de modifier le logiciel) |

### NE-04 — QR codes liés au nom d'hôte de la requête

| Rubrique | Contenu |
|---|---|
| **Constat** | Le QR d'un équipement encode l'adresse absolue de la requête ; un QR imprimé depuis un autre nom d'hôte pointe vers une adresse erronée ; non documenté avant l'audit. |
| **Profils concernés** | exploitants ; gestionnaires de matériel |
| **Niveau de preuve** | [C] |
| **Preuve** | assets/views.py (accès restreint) |
| **Statut** | documenté, non arbitré (pas une autorisation de modifier le logiciel) |

### NE-05 — Codes de refus 404 et 403 hétérogènes

| Rubrique | Contenu |
|---|---|
| **Constat** | L'équipier reçoit 404 sur certaines pages d'écriture (nouvelle documentation, passation) et 403 sur la plupart des autres ; masquage volontaire ou incohérence non documentée. |
| **Profils concernés** | marins |
| **Niveau de preuve** | [N] |
| **Preuve** | audit_preuves/navigateur_droits.md |
| **Statut** | documenté, non arbitré (pas une autorisation de modifier le logiciel) |

### NE-06 — Synthèse de passation lisible par l'équipage sortant

| Rubrique | Contenu |
|---|---|
| **Constat** | Les chefs de l'équipage sortant, passé à terre, lisent la synthèse figée ; conforme au code, mais l'écart A14 les concerne aussi. |
| **Profils concernés** | chefs de l'équipage sortant |
| **Niveau de preuve** | [N] |
| **Preuve** | audit_preuves/a14_navigateur_chef_section.png |
| **Statut** | documenté, non arbitré (pas une autorisation de modifier le logiciel) |

# Points à confirmer (B1 à B8)

### B1 — Suppléance du COMAEQ

| Rubrique | Contenu |
|---|---|
| **Décision existante applicable** | `DEC-SUP-01` : la suppléance est **explicitement désignée, activée par une autorité compétente, temporaire, limitée à une fonction et à un périmètre, et tracée** ; `DEC-SUP-02`, `DEC-SUP-04`, `DEC-SUP-05`, `DEC-SUP-07` |
| **Fonctionnement actuel vérifié** | Aucun mécanisme général. Seuls secours codés : le commandant de l'équipage peut viser la feuille de service et désigner les rédacteurs quand le poste COMAEQ est **vacant** (`quarts/models.py:2210`) ; remplacement temporaire d'un chef de liste des services à quai (`quarts/remplacement.py:27`) |
| **Règle cible** | Le principe est décidé. **La procédure exacte de désignation du suppléant du COMAEQ est à confirmer** (lot L08) |
| **Profils concernés** | COMAEQ ; commandants |
| **Statut** | à confirmer par le PO |

### B2 — Commandant en second

| Rubrique | Contenu |
|---|---|
| **Décision existante applicable** | Notion « 13 — Décisions » : vision globale ; écritures limitées aux **responsabilités attribuées** ; il ne tient pas ses droits automatiquement de son grade |
| **Fonctionnement actuel vérifié** | Écriture héritée du grade retirée (API) mais seuil comparé au grade dans plusieurs vues web (A4) |
| **Règle cible** | Les responsabilités doivent être **explicites et attribuées dans un cadre autorisé** ; qui les attribue, par quel mécanisme et dans quelles limites est **à confirmer** |
| **Profils concernés** | commandant en second |
| **Statut** | à confirmer par le PO |

### B3 — Échanges et quarts à la mer

| Rubrique | Contenu |
|---|---|
| **Décision existante applicable** | `DEC-FDS-07` : « échanges de tours » sans préciser le périmètre ; `DEC-FDS-13` |
| **Fonctionnement actuel vérifié** | Échanges limités aux **services à quai** d'une même liste (`quarts/echanges.py:1`) |
| **Règle cible** | **Ne pas généraliser** aux quarts à la mer sans validation métier : à confirmer |
| **Profils concernés** | chefs de liste ; COMAEQ |
| **Statut** | à confirmer par le PO |

### B4 — Accostage et appareillage

| Rubrique | Contenu |
|---|---|
| **Décision existante applicable** | Aucune décision du registre des 125 ; les propositions `mer_quai_*` (état B) décrivent la règle comme validée |
| **Fonctionnement actuel vérifié** | Déclaration par le **titulaire COMAEQ** ou le **commandant de l'équipage à bord** (`fonction_habilitee`, `quarts/mouvements.py:27`) ; correction par annulation motivée |
| **Règle cible** | Le fonctionnement actuel est documenté ; **l'autorité cible est à confirmer** |
| **Profils concernés** | COMAEQ ; commandants |
| **Statut** | à confirmer par le PO |

### B5 — Chef de liste des quarts

| Rubrique | Contenu |
|---|---|
| **Décision existante applicable** | Notion « 13 » : le chef de liste crée et publie les listes de service et de gardes (**décision antérieure**, remplacée par `DEC-FDS-14` pour la publication) ; `D11` (mer/quai) : chef de liste des quarts **distinct** du chef de liste des services à quai |
| **Fonctionnement actuel vérifié** | Désignation par supervision ou par un niveau chef de service dont le périmètre couvre celui visé (`quarts/listes_views.py:163`) |
| **Règle cible** | Qui désigne : **à confirmer** |
| **Profils concernés** | chefs de liste ; chefs de service |
| **Statut** | à confirmer par le PO |

### B6 — « Fin de journée » d'une tâche

| Rubrique | Contenu |
|---|---|
| **Décision existante applicable** | `DEC-BLQ-05` (état « Non réalisée — À reprogrammer ») |
| **Fonctionnement actuel vérifié** | Aucune notion de fin de journée |
| **Règle cible** | Heure par bâtiment (`IM-09`) : **à confirmer** |
| **Profils concernés** | marins ; chefs de section |
| **Statut** | à confirmer par le PO |

### B7 — Ordre des grades

| Rubrique | Contenu |
|---|---|
| **Décision existante applicable** | `DEC-COL-02` |
| **Fonctionnement actuel vérifié** | Le grade est un texte sans rang |
| **Règle cible** | Valeurs à saisir par le PO : **à confirmer** (`IM-02`) |
| **Profils concernés** | PO |
| **Statut** | à confirmer par le PO |

### B8 — Conservation

| Rubrique | Contenu |
|---|---|
| **Décision existante applicable** | Aucune décision |
| **Fonctionnement actuel vérifié** | Notifications, journaux et estimations non purgés |
| **Règle cible** | Durées **à confirmer** (`IM-10`) |
| **Profils concernés** | exploitants ; PO |
| **Statut** | à confirmer par le PO |

# Propositions non arbitrées (D1 à D7) 🟣

### D1 — Ticket de suivi pour une installation déclarée non conforme, comme pour le matériel mobile

| Rubrique | Contenu |
|---|---|
| **Origine** | Retenue comme proposition cible par le PO, « à valider » |
| **Garde-fous demandés** | Un ticket ne clôture jamais automatiquement une anomalie ; il n'autorise jamais une remise en service |
| **Chapitres concernés** | 12, 25 |
| **Statut** | 🟣 à valider par le PO — pas une décision |

### D2 — Règle de sortie de l'état « En validation » et alerte de retard associée (A20)

| Rubrique | Contenu |
|---|---|
| **Origine** | Constat du dossier |
| **Garde-fous demandés** | Aucune règle inventée |
| **Chapitres concernés** | 12, 25 |
| **Statut** | 🟣 à valider par le PO — pas une décision |

### D3 — Transmission d'un RETEX à un organisme : destinataires, canaux, responsabilités

| Rubrique | Contenu |
|---|---|
| **Origine** | Précision du PO : acte distinct de la validation et du statut |
| **Garde-fous demandés** | À confirmer avec les procédures métier ; le marquage « flotte » n'est pas une transmission |
| **Chapitres concernés** | 15, 25 |
| **Statut** | 🟣 à valider par le PO — pas une décision |

### D4 — Autorité de classification « critique » d'un contrôle d'appareillage

| Rubrique | Contenu |
|---|---|
| **Origine** | `DEC-APP-14` (principe validé) ; compatibilité avec les procédures du bord non vérifiée |
| **Garde-fous demandés** | À confirmer avant tout développement |
| **Chapitres concernés** | 16, 25 |
| **Statut** | 🟣 à valider par le PO — pas une décision |

### D5 — Favoris épinglés, recherche de personnes limitée, formulaires RH configurables

| Rubrique | Contenu |
|---|---|
| **Origine** | Observations de recette (PO-18 à PO-20) |
| **Garde-fous demandés** | « À faire plus tard » ; droits et confidentialité à spécifier |
| **Chapitres concernés** | 17, 25 |
| **Statut** | 🟣 à valider par le PO — pas une décision |

### D6 — Observations de recette PO-01 à PO-16, PO-21 (ergonomie, accueil, notifications, fiches de démonstra

| Rubrique | Contenu |
|---|---|
| **Origine** | Notion « Recette UX V1.1 » |
| **Garde-fous demandés** | Qualification et arbitrage du PO avant toute correction |
| **Chapitres concernés** | 17 |
| **Statut** | 🟣 à valider par le PO — pas une décision |

### D7 — Sauvegarde, restauration, supervision, conservation des journaux

| Rubrique | Contenu |
|---|---|
| **Origine** | Aucune source |
| **Garde-fous demandés** | À définir avec les SIC / l'exploitant |
| **Chapitres concernés** | 23 |
| **Statut** | 🟣 à valider par le PO — pas une décision |

# Anomalies du dossier (audit)

| Id | Gravité | Constat | Traitement prévu | Statut |
|---|---|---|---|---|
| AUD-001 | Bloquante (diffusion) | L'en-tête de chaque page dit « DIFFUSION GÉNÉRALE » et le fichier s'appelle « DIFFUSABLE », alors que la couverture et le chapitre 3 disent que la classification n'est pas validée. La couverture annonce « Aucune référence de code » alors que le texte contient  | P0-1 | ouverte — à traiter par la refonte |
| AUD-002 | Majeure | `matrix/templates/quarts/feuille_service_detail.html:18` contient un bouton « Imprimer » (`window.print()`, classe `no-print`) ; le guide visuel p.25 le montre | P0-2 | ouverte — à traiter par la refonte |
| AUD-003 | Majeure | Le guide visuel (64 captures, 5 parcours) et cet audit ont rejoué ces écrans | P0-4 | ouverte — à traiter par la refonte |
| AUD-004 | Majeure | Le module `rondes` n'a aucune vue et a été retiré de l'interface (chap. 2, 12 ; A8 ; `rondes/models.py` seul) | P0-2 | ouverte — à traiter par la refonte |
| AUD-005 | Majeure | `matrix/templates/components/parcours.html` ; visible sur toutes les captures d'accueil du guide | P0-2 | ouverte — à traiter par la refonte |
| AUD-006 | Majeure | Détection : légende dans les 6 % supérieurs de la page. S10 vu : illisible (5,0 pt), diagramme en pelote | P0-6 | ouverte — à traiter par la refonte |
| AUD-007 | Majeure (précisée en phase 2 : le bouton « M'assigner » existe aussi dans la liste) | La liste de maintenance affiche « Exécuter » sur toutes les lignes pour un équipier ; `/maintenance/occurrences/4/execute/` répond 403 pour lui. Le guide p.13 montre ces boutons sans explication | P0-2 | ouverte — à traiter par la refonte |
| AUD-008 | Majeure | Les fichiers de test ne sont dans aucun dépôt (rapport de qualification : « non conservés ») ; une copie est maintenant archivée dans `audit_preuves/tests_verification/` et relancée : 29 tests OK | P0-5 | ouverte — à traiter par la refonte |
| AUD-009 | Majeure | `RAPPORT_CLOTURE_G0.md` §3 : « Pages quasi vides : Aucune dans les deux PDF » | AUD-034 | fusionnée dans AUD-034 |
| AUD-010 | Majeure | 29 captures non utilisées (64 − 35). Les lignes de tickets sont cliquables (`onclick`, `ticket_list.html:28`) : ma capture automatique cherchait un lien `<a>` | P0-2 | ouverte — à traiter par la refonte |
| AUD-011 | Majeure | Les PDF ne contiennent ni synthèse de 2 pages (valeur, maturité, limites, risques) ni lecture de la `SYNTHESE_ECARTS_PAR_CRITICITE.md` (fichier restreint hors PDF) | P1-1 | ouverte — à traiter par la refonte |
| AUD-012 | Majeure | [V] p.2 ; [A] grep | P0-4 / P1-2 | ouverte — à traiter par la refonte |
| AUD-013 | Majeure | Écrans importants absents : accusé de réception d'une annonce, fiche d'installation (relevés, entretien), échange de tour, Documentation/RETEX, bas de l'accueil (indicateurs, bloc Supervision), prêt à appareiller avec session ouverte, vue mobile (le chapitre 1 | P1-3 | ouverte — à traiter par la refonte |
| AUD-014 | Mineure | [V] captures `p_maintenance_1_saisie`, `p_anomalie_3_description`, `parametres` | P2 | ouverte — à traiter par la refonte |
| AUD-015 | Mineure | [V] | P2 | ouverte — à traiter par la refonte |
| AUD-016 | Mineure | [A] différence de pixels 0,0 à 4,6 % | P1-3 | ouverte — à traiter par la refonte |
| AUD-017 | Mineure | [V] p.21 ; [A] grep | P2 | ouverte — à traiter par la refonte |
| AUD-018 | Mineure | [V] ; étendue non mesurée [?] | P2 | ouverte — à traiter par la refonte |
| AUD-019 | Mineure | [V] p.1, 14, 82 | P2 | ouverte — à traiter par la refonte |
| AUD-020 | Mineure | [A][V] `schemas_lisibilite.csv` | AUD-036 | fusionnée dans AUD-036 |
| AUD-021 | Mineure | Recomptage `def test_` indenté : 3 912 [C] ; 3 963 exécutés non rejoués [R] | P2 | ouverte — à traiter par la refonte |
| AUD-022 | Amélioration | [C][N][V] | P1-6 | ouverte — à traiter par la refonte |
| AUD-023 | Amélioration | [A] S02… absents de la liste des schémas ; [V] | P1-2 | ouverte — à traiter par la refonte |
| AUD-024 | Amélioration | [C] `settings.py:422-424` ; plan des chapitres | P1-4 | ouverte — à traiter par la refonte |
| AUD-025 | Mineure | [N] `navigateur_droits.md` | P1-3 | ouverte — à traiter par la refonte |
| AUD-026 | Amélioration | [?] | P1-6 | ouverte — à traiter par la refonte |
| AUD-027 | Mineure | [C] `ticket_list.html:28` | P2 | ouverte — à traiter par la refonte |
| AUD-028 | Mineure | [V] listing | P2 | ouverte — à traiter par la refonte |
| AUD-029 | Mineure | [V] | P2 | ouverte — à traiter par la refonte |
| AUD-030 | Mineure | « scan web `assets/scan/<uuid>/` » : le chemin réel est `/scan/<uuid>/` (`assets/web_urls.py:72` ; annexe C correcte) | P0-2 | ouverte — à traiter par la refonte |
| AUD-031 | Majeure | Annexe générée de 4 900 mots (79 % de l'annexe F) : lignes tronquées par « … » (« Une correcti… », « L… »), fragments de tableau (« \ | P0-6 | ouverte — à traiter par la refonte |
| AUD-032 | Mineure | Tableaux Markdown non rendus : p.37 (« Routes web », source `restreint/13_logistique_technique.md:20-22`) et p.79 (§23.9, source `23_configuration_deploiement_exploitation.md:119-123`, tableau collé au paragraphe) apparaissent en barres verticales brutes | P0-6 | ouverte — à traiter par la refonte |
| AUD-033 | Majeure | Des plages de décisions sont citées comme « cible, non développée » alors que certaines sont déjà réalisées : `DEC-PER-01` (tâches périodiques générées depuis les fiches) et `DEC-PER-04` (historiques conservés) vs `maintenance/tasks.py:66` et `OccurrenceStatus | P0-3 | ouverte — à traiter par la refonte |
| AUD-034 | Majeure | Densité : 18 pages du diffusable et 26 du restreint sont remplies à moins de 70 % (11 et 15 à moins de 50 %) ; les compléments techniques (1 à 3 pages par chapitre) répètent chacun un cartouche de 5 lignes ; le restreint ne contient pas les chapitres de base q | P1-8 (architecture) | ouverte — à traiter par la refonte |
| AUD-035 | Majeure | Les schémas de circuit cible ne se distinguent pas des schémas de fonctionnement réel : seule la légende dit « cible » ; l'image seule (cadre, couleur, mention) est identique à S16, S20, S30, S32 | P0-7 | ouverte — à traiter par la refonte |
| AUD-036 | Mineure | Sur 42 schémas : 22 bons, 7 moyens, 10 faibles (listes de cases sans information relationnelle : S02, S14, S22, S24, S27, S36, S37, S38, S40, S42), 1 difficile (S09), 1 illisible (S10) ; S02 montre 6 groupes quand le tableau juste dessous en compte 11 | P1-5 | ouverte — à traiter par la refonte |
| AUD-037 | Mineure | Rubriques « bis » : traces d'édition (insertions tardives) | P2 | ouverte — à traiter par la refonte |
| AUD-038 | Mineure | Deux chiffres pour le même inventaire ; l'annexe F.4 est datée de l'ensemble 4 et n'est plus à jour (la branche compte d'autres commits) | P2 | ouverte — à traiter par la refonte |

# Décisions du PO et état dans l'état B

> L'état est déduit du plan en lots (V1.2) ou vérifié dans le code (colonne « Méthode »). « À instruire » signifie que le dossier ne l'a pas établi : ce n'est pas un constat de non-réalisation.

| Décision | Règle | Lot(s) | État dans l'état B | Méthode |
|---|---|---|---|---|
| DEC-ANO-01 | Anomalie = problème technique à suivre ; intervention = action effectuée pour le traiter. | L22 | non développée | plan en lots (V1.2) : lot non livré dans l'état B |
| DEC-ANO-02 | Une anomalie peut nécessiter plusieurs interventions. | L22 | non développée | plan en lots (V1.2) : lot non livré dans l'état B |
| DEC-ANO-03 | La clôture d'une intervention ne clôture pas automatiquement l'anomalie. | L22 | non développée | plan en lots (V1.2) : lot non livré dans l'état B |
| DEC-ANO-04 | Le chef de secteur décide de la suite : intervention supplémentaire, demande d'information, ouverture d'anomalie, clôture justifiée. | L22 | non développée | plan en lots (V1.2) : lot non livré dans l'état B |
| DEC-ANO-05 | Préserver les liens tâches ↔ interventions ↔ anomalies ↔ matériels ↔ historique. | L22 | non développée | plan en lots (V1.2) : lot non livré dans l'état B |
| DEC-APP-01 | Chaque départ génère des contrôles à partir des fiches de référence applicables. | L23 | non développée | plan en lots (V1.2) : lot non livré dans l'état B |
| DEC-APP-02 | Circuit : section ou secteur → service → COMANAV. | L23 | non développée | plan en lots (V1.2) : lot non livré dans l'état B |
| DEC-APP-03 | Les modifications des références suivent leur propre circuit d'approbation. | L23 | non développée | plan en lots (V1.2) : lot non livré dans l'état B |
| DEC-APP-04 | Référence approuvée modifiée : les préparations ouvertes sont actualisées. | L23 | non développée | plan en lots (V1.2) : lot non livré dans l'état B |
| DEC-APP-05 | Les réponses toujours valables sont conservées. | L23 | non développée | plan en lots (V1.2) : lot non livré dans l'état B |
| DEC-APP-06 | Les contrôles modifiés ou ajoutés sont rouverts. | L23 | non développée | plan en lots (V1.2) : lot non livré dans l'état B |
| DEC-APP-07 | Les contrôles supprimés sont archivés. | L23 | non développée | plan en lots (V1.2) : lot non livré dans l'état B |
| DEC-APP-08 | Les signatures affectées sont invalidées. | L23 | non développée | plan en lots (V1.2) : lot non livré dans l'état B |
| DEC-APP-09 | Les préparations clôturées conservent leur version historique. | L23 | non développée | plan en lots (V1.2) : lot non livré dans l'état B |
| DEC-APP-10 | Les contrôles obligatoires sont traités avant validation. | L23 | non développée | plan en lots (V1.2) : lot non livré dans l'état B |
| DEC-APP-11 | Les réserves sont explicites, justifiées et tracées, dans les limites des règles de sécurité. | L23 | non développée | plan en lots (V1.2) : lot non livré dans l'état B |
| DEC-APP-12 | Les contrôles critiques non dérogeables ne peuvent pas être contournés. | L23 | non développée | plan en lots (V1.2) : lot non livré dans l'état B |
| DEC-APP-13 | Matrix ne délivre pas l'autorisation opérationnelle d'appareiller. | L23 | réalisée | vérifié dans le code de l'état B |
| DEC-APP-14 | Fiche de référence d'appareillage : le chef de secteur propose les contrôles et leur classification (obligatoire, critique) ; le chef de service examine et valide la prop | — | non développée (A17) | vérifié dans le code de l'état B |
| DEC-BLQ-01 | Un équipier peut déclarer une tâche « Bloquée » avec motif. | L17 | non développée | plan en lots (V1.2) : lot non livré dans l'état B |
| DEC-BLQ-02 | Le responsable est informé du blocage. | L17 | non développée | plan en lots (V1.2) : lot non livré dans l'état B |
| DEC-BLQ-03 | Le chef peut débloquer et reprogrammer sans obligation de créer une anomalie. | L17 | non développée | plan en lots (V1.2) : lot non livré dans l'état B |
| DEC-BLQ-04 | Le chef de secteur décide si un défaut technique nécessite une anomalie. | L17 | non développée | plan en lots (V1.2) : lot non livré dans l'état B |
| DEC-BLQ-05 | Une tâche non terminée en fin de journée n'est pas reportée en silence ; état explicite « Non réalisée — À reprogrammer ». | L17 | non développée | plan en lots (V1.2) : lot non livré dans l'état B |
| DEC-CLO-01 | À la création/planification, case « Validation du responsable requise ». | L15 | non développée | plan en lots (V1.2) : lot non livré dans l'état B |
| DEC-CLO-02 | Sans l'option : l'équipier termine directement ; la réalisation est enregistrée. | L15 | non développée | plan en lots (V1.2) : lot non livré dans l'état B |
| DEC-CLO-03 | Avec l'option : l'équipier déclare terminé, la tâche passe « À valider » ; le chef approuve ou demande une correction motivée. | L15 | non développée | plan en lots (V1.2) : lot non livré dans l'état B |
| DEC-CLO-04 | Le chef de secteur valide directement, chef de section absent, sans suppléance. | L15 | non développée | plan en lots (V1.2) : lot non livré dans l'état B |
| DEC-CLO-05 | Les visas techniques obligatoires restent distincts de la validation facultative. | L15 | non développée | plan en lots (V1.2) : lot non livré dans l'état B |
| DEC-COL-01 | Plusieurs marins peuvent participer à une même tâche. | — | à instruire ⚪ | aucun rattachement |
| DEC-COL-02 | Matrix propose comme coordinateur le participant au grade le plus élevé. | L16 | non développée | plan en lots (V1.2) : lot non livré dans l'état B |
| DEC-COL-03 | En cas d'égalité de grade, le chef choisit. | L16 | non développée | plan en lots (V1.2) : lot non livré dans l'état B |
| DEC-COL-04 | Le chef peut désigner un autre participant comme coordinateur. | L16 | non développée | plan en lots (V1.2) : lot non livré dans l'état B |
| DEC-COL-05 | Le coordinateur peut déclarer le travail réalisé, mais ne remplace pas une autorité de visa technique. | L16 | non développée | plan en lots (V1.2) : lot non livré dans l'état B |
| DEC-DRT-01 | Les droits métier découlent de la fonction exercée et du périmètre de responsabilité, pas uniquement du grade ni du niveau hiérarchique. | L09 | non développée | plan en lots (V1.2) : lot non livré dans l'état B |
| DEC-DRT-02 | Un administrateur technique ne devient pas automatiquement autorité de validation métier ; il désigne les titulaires sans viser à leur place. | L06 | écart (A1) | vérifié dans le code de l'état B |
| DEC-DRT-03 | Consultation des documents de maintenance autorisés des autres sections du secteur ; pas de modification ni de clôture hors périmètre. | — | à instruire ⚪ | aucun rattachement |
| DEC-DRT-04 | Accès intersectoriels et documents sensibles : droits appropriés requis. | — | à instruire ⚪ | aucun rattachement |
| DEC-DRT-05 | Éviter les suppressions physiques qui détruisent l'historique. | L02, L03, L04 | réalisée (lot livré dans l'état B) | plan en lots (V1.2) et comptes rendus de lots |
| DEC-DRT-06 | Un compte dont le rattachement professionnel est incomplet n'accède pas aux informations opérationnelles d'un secteur sans autorisation. | L07 | non développée | plan en lots (V1.2) : lot non livré dans l'état B |
| DEC-DUR-01 | Matrix actualise automatiquement la durée indicative des maintenances à partir des temps réellement constatés. | L20 | non développée | plan en lots (V1.2) : lot non livré dans l'état B |
| DEC-DUR-02 | Conserver la durée initiale. | L20 | non développée | plan en lots (V1.2) : lot non livré dans l'état B |
| DEC-DUR-03 | Conserver l'historique des estimations. | L20 | non développée | plan en lots (V1.2) : lot non livré dans l'état B |
| DEC-DUR-04 | Distinguer temps écoulé et charge totale en heures-personnes. | L20 | non développée | plan en lots (V1.2) : lot non livré dans l'état B |
| DEC-DUR-05 | Éviter que interventions exceptionnellement longues, attentes et interruptions faussent l'estimation. | L20 | non développée | plan en lots (V1.2) : lot non livré dans l'état B |
| DEC-DUR-06 | Le chef de secteur peut corriger manuellement la durée. | L20 | non développée | plan en lots (V1.2) : lot non livré dans l'état B |
| DEC-DUR-07 | Ne pas modifier automatiquement consignes techniques ou de sécurité. | L20 | non développée | plan en lots (V1.2) : lot non livré dans l'état B |
| DEC-FDS-01 | Le BSC prépare les feuilles de service ; il n'est pas une autorité parallèle au COMAEQ. | — | à instruire ⚪ | aucun rattachement |
| DEC-FDS-02 | Le COMAEQ, ou un suppléant officiellement habilité, approuve la feuille. | L08, L09 | non développée | plan en lots (V1.2) : lot non livré dans l'état B |
| DEC-FDS-03 | Après approbation, publication numérique. | — | à instruire ⚪ | aucun rattachement |
| DEC-FDS-04 | Le BSC assure l'impression A4 pour l'affichage. | — | à instruire ⚪ | aucun rattachement |
| DEC-FDS-05 | Une modification après publication entraîne une nouvelle version officielle. | L09 | non développée | plan en lots (V1.2) : lot non livré dans l'état B |
| DEC-FDS-06 | Matrix signale la nécessité de réimprimer et remplacer une feuille déjà affichée. | L27 | non développée | plan en lots (V1.2) : lot non livré dans l'état B |
| DEC-FDS-07 | Échanges de tours : la décision finale revient au COMAEQ ou à son suppléant officiellement habilité. | — | écart (A2) | vérifié dans le code de l'état B |
| DEC-FDS-08 | Les fractions de service à quai sont configurables par bâtiment. | L27 | non développée | plan en lots (V1.2) : lot non livré dans l'état B |
| DEC-FDS-09 | Écarts signalés et justifiés, sans blocage automatique injustifié. | L27 | non développée | plan en lots (V1.2) : lot non livré dans l'état B |
| DEC-FDS-10 | Exigences opérationnelles et réglementaires restent applicables. | — | à instruire ⚪ | aucun rattachement |
| DEC-FDS-11 | La création d'une feuille n'est pas ouverte à n'importe quel équipier. | — | à instruire ⚪ | aucun rattachement |
| DEC-FDS-12 | Prendre en compte deux équipages ; chaque équipage a sa feuille, sans validation croisée par le seul grade. | — | à instruire ⚪ | aucun rattachement |
| DEC-FDS-13 | Le BSC ou le chef de liste peut instruire la demande d'échange ; il ne dispose pas automatiquement de l'autorité de validation finale. | — | à instruire ⚪ | aucun rattachement |
| DEC-FDS-14 | Listes de quarts et de gardes : le chef de liste prépare et propose ; le COMAEQ ou son suppléant officiellement habilité approuve et publie. Toute modification après publ | — | écart (A3) | vérifié dans le code de l'état B |
| DEC-MAT-01 | Transfert entre secteurs d'un même service : approbation du chef de service. | L13 | non développée | plan en lots (V1.2) : lot non livré dans l'état B |
| DEC-MAT-02 | Transfert entre deux services : approbation des deux chefs de service, puis application par l'administrateur habilité. | L13 | non développée | plan en lots (V1.2) : lot non livré dans l'état B |
| DEC-MAT-03 | Les tâches ouvertes suivent le matériel et sont réattribuées si nécessaire. | L13 | non développée | plan en lots (V1.2) : lot non livré dans l'état B |
| DEC-MAT-04 | L'historique des interventions et des tâches clôturées reste conservé. | L13 | non développée | plan en lots (V1.2) : lot non livré dans l'état B |
| DEC-MUT-01 | Un marin conserve son compte Matrix lorsqu'il change de bâtiment. | L25 | non développée | plan en lots (V1.2) : lot non livré dans l'état B |
| DEC-MUT-02 | Le nouveau bâtiment demande le rattachement ; l'ancien est informé et peut confirmer le départ. | L25 | non développée | plan en lots (V1.2) : lot non livré dans l'état B |
| DEC-MUT-03 | Sans réponse, une autorité habilitée régularise avec justification et journalisation. | L25 | non développée | plan en lots (V1.2) : lot non livré dans l'état B |
| DEC-MUT-04 | Anciens droits retirés à la date effective de mutation ; nouveaux droits attribués selon l'affectation d'accueil. | L25 | non développée | plan en lots (V1.2) : lot non livré dans l'état B |
| DEC-MUT-05 | L'historique est conservé. | L25 | non développée | plan en lots (V1.2) : lot non livré dans l'état B |
| DEC-MUT-06 | Les tâches ouvertes sont réattribuées ou signalées « non affectées à un responsable ». | L04 | non développée | plan en lots (V1.2) : lot non livré dans l'état B |
| DEC-MUT-07 | Compte d'un marin quittant le bâtiment ou la Marine : désactivé ou transféré selon le cas, sans destruction d'historique. | L04 | non développée | plan en lots (V1.2) : lot non livré dans l'état B |
| DEC-ORG-01 | Structure : Bâtiment → Service → Secteur → Section facultative → Matériels et installations. | — | à instruire ⚪ | aucun rattachement |
| DEC-ORG-02 | Un secteur peut n'avoir aucune section ; le secteur reste alors l'échelon responsable. | L12 | non développée | plan en lots (V1.2) : lot non livré dans l'état B |
| DEC-ORG-03 | Les matériels sont toujours rattachés à une entité responsable. | — | à instruire ⚪ | aucun rattachement |
| DEC-ORG-04 | Distinguer grade, fonction occupée, périmètre de responsabilité, spécialité, brevets/formations/habilitations. Les brevets ne sont pas des grades. | — | à instruire ⚪ | aucun rattachement |
| DEC-ORG-05 | Prendre en compte FEM, BE, BAT, BS, BST et les évolutions récentes (BHT, C-CDM). | — | à instruire ⚪ | aucun rattachement |
| DEC-ORG-06 | Configuration plutôt que code : aucune règle susceptible d'évoluer n'est codée en dur. | — | à instruire ⚪ | aucun rattachement |
| DEC-OUT-01 | Signaler : outil manquant, inutile, inadapté, instruction ambiguë, information manquante. | L26 | non développée | plan en lots (V1.2) : lot non livré dans l'état B |
| DEC-OUT-02 | Remarques conservées et visibles du chef de secteur. | L26 | non développée | plan en lots (V1.2) : lot non livré dans l'état B |
| DEC-OUT-03 | La liste d'outillage n'est jamais modifiée automatiquement. | L26 | non développée | plan en lots (V1.2) : lot non livré dans l'état B |
| DEC-OUT-04 | Le chef décide de modifier ou non la fiche de référence. | L26 | non développée | plan en lots (V1.2) : lot non livré dans l'état B |
| DEC-OUT-05 | Procédures techniques et de sécurité : validations applicables conservées. | L26 | non développée | plan en lots (V1.2) : lot non livré dans l'état B |
| DEC-PER-01 | Les tâches périodiques sont générées à partir des fiches de maintenance et des matériels concernés. | L19 | partielle | vérifié dans le code de l'état B |
| DEC-PER-02 | Périodicités : hebdomadaire, mensuelle, trimestrielle, annuelle, biennale, quinquennale. | L19 | non développée | plan en lots (V1.2) : lot non livré dans l'état B |
| DEC-PER-03 | Prochaine échéance calculée depuis la réalisation effective, sauf calendrier fixe réglementaire ou technique. | L19 | non développée | plan en lots (V1.2) : lot non livré dans l'état B |
| DEC-PER-04 | Les historiques sont conservés, retards compris. | L19 | réalisée | vérifié dans le code de l'état B |
| DEC-PRE-01 | Le module d'absences est limité aux corrections nécessaires (un système extérieur gère les absences). | — | à instruire ⚪ | aucun rattachement |
| DEC-PRE-02 | Pas de module autonome de passation ; préserver les fonctions existantes utiles. | — | réalisée | vérifié dans le code de l'état B |
| DEC-PRE-03 | Conserver les exports PDF, Excel et CSV de pilotage, puis en améliorer la qualité. | — | réalisée | vérifié dans le code de l'état B |
| DEC-PRE-04 | QR et inspections mobiles non prioritaires : reportés, sans suppression précipitée de l'existant. | — | réalisée | vérifié dans le code de l'état B |
| DEC-PRE-05 | Préserver le fonctionnement local sur le réseau du bord. | — | à instruire ⚪ | aucun rattachement |
| DEC-PRE-06 | Architecture de déploiement, PKI, sauvegarde et sécurité des SI : à soumettre aux experts compétents. | L01, L21 | réalisée (lot livré dans l'état B) | plan en lots (V1.2) et comptes rendus de lots |
| DEC-QUA-01 | Les formations et habilitations enregistrées ne bloquent pas automatiquement l'attribution ni l'exécution des tâches ordinaires ; le responsable humain choisit. | L18 | non développée | plan en lots (V1.2) : lot non livré dans l'état B |
| DEC-QUA-02 | Les qualifications connues peuvent être affichées à titre informatif. | L18 | non développée | plan en lots (V1.2) : lot non livré dans l'état B |
| DEC-QUA-03 | Une information manquante ou périmée ne bloque pas l'attribution. | L18 | non développée | plan en lots (V1.2) : lot non livré dans l'état B |
| DEC-QUA-04 | Distinguer deux situations : (1) tâches ordinaires, jamais bloquées par les qualifications enregistrées ; (2) visas techniques, fonctions de service et signatures officie | L18 | non développée | plan en lots (V1.2) : lot non livré dans l'état B |
| DEC-RTX-01 | Circuit RETEX : auteur → chef de section si présent → chef de secteur → chef de service. | L11 | écart (A15) | vérifié dans le code de l'état B |
| DEC-RTX-02 | Une demande de correction doit être motivée. | L11 | non développée | plan en lots (V1.2) : lot non livré dans l'état B |
| DEC-RTX-03 | La correction entraîne une nouvelle version et les validations nécessaires. | L11 | non développée | plan en lots (V1.2) : lot non livré dans l'état B |
| DEC-RTX-04 | Traçabilité de qui a proposé, modifié, validé ou rejeté. | L11 | non développée | plan en lots (V1.2) : lot non livré dans l'état B |
| DEC-SUP-01 | La suppléance est explicite, temporaire, limitée à une fonction et un périmètre, activée par une autorité compétente, traçable. | L08 | non développée | plan en lots (V1.2) : lot non livré dans l'état B |
| DEC-SUP-02 | Une seule personne exerce la responsabilité active d'un même périmètre à un instant donné. | L08 | non développée | plan en lots (V1.2) : lot non livré dans l'état B |
| DEC-SUP-03 | Le retour anticipé ou la fin de suppléance suit les règles de validation retenues. | L08 | non développée | plan en lots (V1.2) : lot non livré dans l'état B |
| DEC-SUP-04 | Les actes du suppléant restent attribués à leur auteur. | L08 | non développée | plan en lots (V1.2) : lot non livré dans l'état B |
| DEC-SUP-05 | Le titulaire retrouve un récapitulatif des actions réalisées pendant son absence. | L08 | non développée | plan en lots (V1.2) : lot non livré dans l'état B |
| DEC-SUP-06 | Les qualifications réglementaires nécessaires à certains visas restent obligatoires pour le suppléant (voir DEC-QUA-04). | L08 | non développée | plan en lots (V1.2) : lot non livré dans l'état B |
| DEC-SUP-07 | La note Notion « pas de nouveau système de délégation en V1 » est une question de périmètre et de calendrier de développement, non une annulation de la décision fonctionn | L08 | non développée | plan en lots (V1.2) : lot non livré dans l'état B |
| DEC-TAC-01 | Le chef de section attribue les tâches de sa section. | — | à instruire ⚪ | aucun rattachement |
| DEC-TAC-02 | Le chef de secteur supervise, attribue directement et réaffecte. | — | à instruire ⚪ | aucun rattachement |
| DEC-TAC-03 | Le chef de service dispose de la supervision correspondant à sa fonction. | — | à instruire ⚪ | aucun rattachement |
| DEC-TAC-04 | Trois priorités : normale, haute, urgente. | L14 | écart (A13) | vérifié dans le code de l'état B |
| DEC-TAC-05 | Une priorité imposée par le chef de secteur ne peut pas être abaissée par le chef de section. | L14 | écart (A13) | vérifié dans le code de l'état B |
| DEC-TAC-06 | Les changements d'attribution et de priorité sont tracés et notifiés aux personnes concernées. | L14 | non développée | plan en lots (V1.2) : lot non livré dans l'état B |
| DEC-UX-01 | À l'ouverture : tâches du jour, tours de service, actions en attente, urgences, informations utiles. | L24 | partielle | vérifié dans le code de l'état B |
| DEC-UX-02 | Éviter grands espaces vides et défilement inutile ; réduire les textes explicatifs permanents ; cartes cliquables. | L24 | non développée | plan en lots (V1.2) : lot non livré dans l'état B |
| DEC-UX-03 | Recherche globale centrée et utile. | L24 | non développée | plan en lots (V1.2) : lot non livré dans l'état B |
| DEC-UX-04 | Permettre d'épingler des entrées du menu. | L24 | non développée | plan en lots (V1.2) : lot non livré dans l'état B |
| DEC-UX-05 | Afficher clairement les tours de service à venir, à valider et effectués. | L24 | non développée | plan en lots (V1.2) : lot non livré dans l'état B |
| DEC-UX-06 | Notifications lues conservées dans le centre mais retirées de la liste principale. | L24 | non développée | plan en lots (V1.2) : lot non livré dans l'état B |
| DEC-UX-07 | Corriger les boutons inactifs et les parcours de navigation défaillants. | L24 | non développée | plan en lots (V1.2) : lot non livré dans l'état B |
| DEC-UX-08 | Terminologie « Mes tours de services ». | L24 | écart (A11) | vérifié dans le code de l'état B |
| DEC-UX-09 | Recherche de personnes : informations professionnelles pertinentes, sous réserve des droits. | L24 | non développée | plan en lots (V1.2) : lot non livré dans l'état B |
| DEC-UX-10 | Interface adaptée aux utilisateurs expérimentés, sans aides envahissantes ; aide progressive réactivable. | L24 | non développée | plan en lots (V1.2) : lot non livré dans l'état B |
| DEC-UX-11 | Le calendrier reste un élément central. | L24 | non développée | plan en lots (V1.2) : lot non livré dans l'état B |
