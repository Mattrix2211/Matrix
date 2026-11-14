# Écarts du logiciel (A1 à A26)

## A1 — Administrateur technique et actes métier

| Rubrique | Contenu |
|---|---|
| **Règle validée** | Un administrateur technique ne devient pas automatiquement autorité de validation métier : il désigne les titulaires, sans viser à leur place. Application mécanique d'un transfert approuvé autorisée. (`DEC-DRT-02`, source S1 §4, DP-09, cahier §5, Notion « 13 — Décisions ») |
| **Constat dans l'état B** | Le niveau numérique de l'administrateur d'unité (8) est supérieur ou égal à tous les seuils par défaut des actions métier du registre (annexe B, colonne « Admin. unité »). Dans les circuits des quarts, il franchit la **supervision du commandement** (`NIVEAU_SUPERVISION_GLOBALE_LISTE = COMMANDANT`, `quarts/models.py:147`) : il peut gérer et **publier** les listes de son bâtiment (`peut_publier_liste`, `quarts/models.py:355`), **valider ou refuser** un échange de tours (`peut_valider_echange`, `quarts/echanges.py:205`) et viser aux paliers « secteur » et « service » de la feuille de service (`_supervision_sur_navire`, `quarts/models.py:1977`). Le visa du COMAEQ et la rédaction de la feuille de service lui restent fermés (`peut_viser_comaeq` `:2215` ; `peut_rediger_feuille_service` `:2065`). |
| **Conséquences** | *Fonctionnelles* : un administrateur technique peut trancher des échanges et publier des listes alors que la règle le lui interdit. *Sécurité / traçabilité* : l'acte est tracé au nom de l'administrateur, mais il brouille la séparation des pouvoirs voulue entre administration de la plateforme et autorité métier. Pas de contournement d'authentification : l'écart est dans la **répartition** des droits. |
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
| **Profils concernés** | exécutants ; chefs de secteur ; responsables des installations |
| **Lot de correction prévu** | Non identifié (à décider par le PO) |
| **Vérifications** | test 12/11/2026 (18 tests) ; navigateur 12/11/2026 : bouton « Enregistrer la correction » visible du seul chef de secteur et au-delà |
| **Niveau de preuve** | [T][N] |
| **Statut** | documenté, non arbitré (pas une autorisation de modifier le logiciel) |

## A21 — Périodicités nommées, remarques d'outillage, durée indicative

| Rubrique | Contenu |
|---|---|
| **Règle validée** | Périodicités nommées, remarques d'outillage, durée indicative (DEC-PER-01, DEC-PER-02, DEC-PER-03, DEC-PER-04, DEC-OUT-01, DEC-OUT-02, DEC-OUT-03, DEC-OUT-04, DEC-OUT-05, `DEC-DUR-*`) |
| **Constat dans l'état B** | Non développé |
| **Conséquences** | Cible, non contradictoire |
| **Profils concernés** | chefs de secteur |
| **Lot de correction prévu** | Plan V1.2 |
| **Niveau de preuve** | [C] |
| **Statut** | documenté, non arbitré (pas une autorisation de modifier le logiciel) |

## A22 — Version de Python annoncée par l'installation

| Rubrique | Contenu |
|---|---|
| **Règle validée** | Le projet suppose Python 3.12 ou plus (README, dépendances) |
| **Constat dans l'état B** | Le script d'installation annonce « Python 3.8 ou supérieur » |
| **Conséquences** | Une installation sur un Python ancien échouerait tard ; incohérence de documentation uniquement |
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
| **Profils concernés** | intégrateurs |
| **Lot de correction prévu** | Phase 7 |
| **Niveau de preuve** | [C] |
| **Statut** | documenté, non arbitré (pas une autorisation de modifier le logiciel) |

