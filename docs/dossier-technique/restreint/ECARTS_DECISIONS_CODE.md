# Registre des écarts entre décisions du PO et comportement du code

> **Diffusion restreinte.** **Pour qui :** PO, responsables métier, développeurs, administrateurs. Tenu à jour à chaque ensemble. **État du code décrit :** état B (`6d6d0be`), non fusionné dans `main`.
> **Règle de ce registre.** On ne rouvre **aucun arbitrage** du PO. Pour chaque écart : la règle métier validée, le comportement observé dans le code, les sources, les conséquences fonctionnelles ou de sécurité, le lot de correction prévu. Le comportement actuel n'est jamais présenté comme la règle souhaitée. **Aucune correction de code** n'est faite ici.
> **Vocabulaire.** *Écart d'implémentation* : le code fait autre chose que ce qu'une décision validée demande. *Décision non encore développée* : le code ne contredit pas la décision, il ne la réalise pas encore (traité dans les chapitres, § « fonctionnement cible »).

---

## Partie A — Écarts d'implémentation (partie 1 : quatre écarts désignés par le PO)

### A1. Administrateur technique et actes métier

| Rubrique | Contenu |
|---|---|
| **Règle validée** | Un administrateur technique ne devient pas automatiquement autorité de validation métier : il désigne les titulaires, sans viser à leur place. Application mécanique d'un transfert approuvé autorisée. (`DEC-DRT-02`, source S1 §4, DP-09, cahier §5, Notion « 13 — Décisions ») |
| **Comportement observé** | Le niveau numérique de l'administrateur d'unité (8) est supérieur ou égal à tous les seuils par défaut des actions métier du registre (annexe B, colonne « Admin. unité »). Dans les circuits des quarts, il franchit la **supervision du commandement** (`NIVEAU_SUPERVISION_GLOBALE_LISTE = COMMANDANT`, `quarts/models.py:147`) : il peut gérer et **publier** les listes de son bâtiment (`peut_publier_liste`, `quarts/models.py:355`), **valider ou refuser** un échange de tours (`peut_valider_echange`, `quarts/echanges.py:205`) et viser aux paliers « secteur » et « service » de la feuille de service (`_supervision_sur_navire`, `quarts/models.py:1977`). Le visa du COMAEQ et la rédaction de la feuille de service lui restent fermés (`peut_viser_comaeq` `:2215` ; `peut_rediger_feuille_service` `:2065`). |
| **Sources** | `matrix/core/roles.py:4` (niveaux) ; `matrix/core/role_thresholds.py:45` (seuils) ; `quarts/models.py:147,355,1977,2065,2215` ; `quarts/echanges.py:205` ; annexe B ; dossier V1.2 `A_REGISTRE_DECISIONS.md` (`DEC-DRT-02`), `M_PLAN_DEVELOPPEMENT.md` (L06) |
| **Conséquences** | *Fonctionnelles* : un administrateur technique peut trancher des échanges et publier des listes alors que la règle le lui interdit. *Sécurité / traçabilité* : l'acte est tracé au nom de l'administrateur, mais il brouille la séparation des pouvoirs voulue entre administration de la plateforme et autorité métier. Pas de contournement d'authentification : l'écart est dans la **répartition** des droits. |
| **Lot de correction** | **L06** — Exclusion de l'administrateur technique des actes métier (non lancé) |

### A2. Échanges de tours

| Rubrique | Contenu |
|---|---|
| **Règle validée** | La décision finale revient au COMAEQ ou à son suppléant officiellement habilité. Le BSC ou le chef de liste peut **instruire** la demande, mais n'a pas automatiquement l'autorité de décision finale. Cette décision **remplace** la note Notion du 28/10 (« le chef de liste habilité valide »). (`DEC-FDS-07`, `DEC-FDS-13` ; sources S1 §7, S3 ; `J_TRIAGE_ET_ARBITRAGES.md` §2) |
| **Comportement observé** | Un échange accepté par le marin sollicité attend « le chef de liste » (`STATUT_ACCEPTE` : « En attente du chef de liste »). La validation et le refus sont ouverts à qui **gère la liste** (`peut_valider_echange`, `quarts/echanges.py:205`, qui s'appuie sur `peut_gerer_liste`, `quarts/models.py:297`) : le chef de liste désigné pour le périmètre exact de la liste, ou le commandement du bâtiment (niveau commandant et au-dessus). Aucune règle ne désigne le COMAEQ ni un suppléant. À défaut de chef de liste désigné, la notification va au créateur de la liste (`chefs_de_liste_a_notifier`, `quarts/echanges.py:176`). |
| **Sources** | `quarts/echanges.py:176,205,342` ; `quarts/models.py:297,855` ; `docs/dossier-technique-v12/J_TRIAGE_ET_ARBITRAGES.md` (CT-01) ; `B_CARTOGRAPHIE.md` (circuit « Échange de tours ») |
| **Conséquences** | *Fonctionnelles* : l'autorité qui tranche n'est pas celle décidée ; un chef de liste (qui peut être un chef de section) valide seul un échange de service à quai. Le COMAEQ n'est ni notifié ni habilité. *Sécurité* : sans suppléance officielle, la règle cible ne peut pas être appliquée telle quelle (voir B3). |
| **Lot de correction** | **L10** — Échanges de tours décidés par le COMAEQ (non lancé) ; dépend de la suppléance explicite (L08) |

### A3. Publication des listes de quarts et de gardes

| Rubrique | Contenu |
|---|---|
| **Règle validée** | Le chef de liste **prépare et propose** ; le COMAEQ ou son suppléant officiellement habilité **approuve et publie**. Toute modification après publication est tracée et donne lieu à une nouvelle version officielle si nécessaire. (`DEC-FDS-14`, S4 arbitrage C-1) |
| **Comportement observé** | Le chef de liste propose (`proposer`, `quarts/models.py` : statut `PROPOSEE`) ; la publication (`publier`) est ouverte à `peut_publier_liste` (`quarts/models.py:355`) : (a) le commandement du bâtiment (commandant, administrateur d'unité, administrateur général sur son périmètre) ; (b) tout rôle atteignant le seuil configurable `liste_service_publication` (**chef de service** par défaut) **et** dont le périmètre personnel est **exactement** celui de la liste ; le commandant en second est explicitement exclu (`_perimetre_dans_scope_utilisateur`, `:308`). La **fonction COMAEQ n'intervient pas** : un COMAEQ ne publie que si sa propre portée est celle de la liste ou s'il est commandement. |
| **Sources** | `quarts/models.py:297,308,355,373,423` ; `matrix/core/role_thresholds.py` (clé `liste_service_publication`) ; `A1_DECISIONS_S1_S2.md` (`DEC-FDS-14`), `J_TRIAGE_ET_ARBITRAGES.md` (CT-04, C-1) |
| **Conséquences** | *Fonctionnelles* : la publication relève d'un chef de service du périmètre ou du commandement ; l'autorité fonctionnelle « vie à bord » n'est pas mobilisée. *Sécurité* : le seuil est réglable par bâtiment : un bâtiment peut l'abaisser et élargir qui publie. |
| **Lot de correction** | **L09** — Visas par fonction et listes publiées (non lancé ; découpé en trois) |

### A4. Droits du commandant en second

| Rubrique | Contenu |
|---|---|
| **Règle validée** | Le commandant en second est le remplaçant désigné du commandant et a une **vision globale**. Ses droits d'écriture **découlent de ses responsabilités métier réelles**, et non d'un simple seuil « commandant ou plus ». Il publie des annonces sur son bâtiment, garde la suppléance du commandant pour la validation de la relève, n'a pas le visa COMA. (Notion « 13 — Décisions » 10/10 et recette V1 ; dossier V1.2 `DEC-DRT-01`) |
| **Comportement observé** | Deux familles de comparaison coexistent. Pour l'**API** et les vues qui utilisent `niveau_ecriture`, son écriture héritée du grade est **retirée** (il retombe au niveau équipier, `ROLES_SANS_ECRITURE_HERITEE`, `matrix/core/roles.py:50`), sauf action explicitement ouverte (`annonce_publication`). Pour de **nombreuses vues web**, le seuil est comparé à son **grade** (`user_role_level`) : il peut alors gérer les modules (`matrix/views.py:289`), saisir le programme (`programme/services.py:47`), proposer des fiches (`assets/fiche_validation.py:130`), voir l'annuaire (`matrix/core/navigation.py`). Dans les circuits des quarts, il est exclu de la désignation, du visa et de la publication (`quarts/models.py:308`). |
| **Sources** | `matrix/core/roles.py:50,53` ; `niveau_pour_action` (`matrix/core/role_thresholds.py:273`) ; gestion des modules (`matrix/views.py:289`) ; `programme/services.py:47` ; `assets/fiche_validation.py:130` ; annexe B (colonne ✱) ; Notion « 13 — Décisions » |
| **Conséquences** | *Fonctionnelles* : ce que le second peut faire dépend de la page utilisée, non d'une liste de responsabilités qui lui sont attribuées. *Sécurité* : un même acte peut être refusé par l'API et accepté par l'écran correspondant. |
| **Lot de correction** | Aucun lot identifié ne traite spécifiquement l'harmonisation (voir B2). Liens : L07 (rattachement et validation des rôles), L09 (visas par fonction). |

---

## Partie A bis — Autres écarts relevés à l'ensemble 1

| # | Règle ou document de référence | Comportement observé | Sources | Conséquences | Lot |
|---|---|---|---|---|---|
| A5 | Règles du projet : « garder des identifiants stables (UUID, NNO) pour de futures API » (`CLAUDE.md`) | UUID et NNO existent côté matériel, catalogue, ticket, objets de la feuille de service ; ni compte, ni unité, ni tâche, ni liste | `couverture/etat_B/MODELES.md` ; `assets/models.py:259,496,736,798` | Un futur interfaçage devra s'appuyer sur d'autres identifiants pour les personnes et les unités ; pas d'effet sur le fonctionnement actuel | Aucun (périmètre à décider) |
| A6 | `docs/REFERENCE.md` §4 « Les 14 apps Django » | L'état B contient 21 applications et le noyau (paquet `matrix/core`) | `docs/REFERENCE.md:74` (section) ; `INSTALLED_APPS` | Documentation du dépôt en retard ; pas d'effet fonctionnel | L28 (dette documentaire) |
| A7 | Cahier §35 : « RBAC + ABAC + périmètre + responsabilité » | Rôle + périmètre + attributs ciblés (équipage, fonction de commandant adjoint) + désignations ; pas de moteur d'attributs général | chapitre 5 | Les règles à attributs sont codées au cas par cas (« configuration plutôt que code » partielle) | — |
| A8 | Cahier §8, §10, §11 (génération automatique des tours) ; §20 (rondes) ; organisation « miroir » | Génération abandonnée (décision du 09/10) ; rondes retirées ; organisation miroir retirée | chapitres 1, 4, 18 | Documentation du cahier partiellement obsolète ; **le dossier décrit le code** | Alignement Notion par le PO |
| A9 | Principe « Internet n'existe pas » | Tenu par le code ; `boto3` et `requests` déclarés sans usage constaté | chapitre 18 | Aucune ; observation d'exploitation | — |
| A10 | Vocabulaire cible de Notion 11 (mission, capacité, dérogation…) | Sans équivalent dans le code | chapitre 19 | Cible non développée | — |

> **Correction par rapport au rapport de l'ensemble 1.** L'écart « QR codes hors V1 / génération de QR encore présente » n'en est pas un : la décision `DEC-PRE-04` (S1 §13, S2) dit que les QR et les inspections mobiles sont **non prioritaires, reportés, sans suppression précipitée de l'existant**, et la tranche DP-06 précise que **la route QR reste**. Le comportement du code est conforme. Les chapitres 18 et le rapport sont corrigés en conséquence.

---

## Partie A ter — Écarts relevés à l'ensemble 2

| # | Règle validée | Comportement observé | Sources | Conséquences | Lot |
|---|---|---|---|---|---|
| A11 | « Mes tours de **services** » (`DEC-UX-08`, S1 §12 ; `CT-06`) | L'accueil affiche « Mes tours de **service** » | `matrix/templates/dashboard/aujourdhui.html:57` | Libellé : purement visuel | Lot UX (L24) |
| A12 | **Fonctionnement cible** : impression A4 de la feuille de service par le BSC, signalement de la nécessité de réimprimer une feuille déjà affichée, et **réimpression avec versionnement** (`DEC-FDS-04`, `DEC-FDS-05`, `DEC-FDS-06`) | Les versions de la feuille sont conservées (`VersionFeuilleService`, `quarts/models.py:1815`), mais aucune page imprimable ni alerte de réimpression n'existe pour la feuille ; seule la fiche d'une **liste** a un rendu imprimable | `matrix/templates/quarts/liste_detail.html` (impression) ; absence dans `feuille_service_detail.html` | Le BSC imprime avec les moyens du navigateur ; pas d'alerte de remplacement d'un affichage | L27 |
| A13 | Trois priorités : normale, haute, urgente ; priorité du chef de secteur non abaissable par le chef de section (`DEC-TAC-04`, `DEC-TAC-05`) | Deux priorités : normale, urgente ; pas de règle d'abaissement | `taches/models.py:38-43` | Perte d'un niveau de nuance ; pas de règle de hiérarchie des priorités | L14 |
| A14 *(non vérifié)* | Synthèse de passation : un chef de section ne consulte que **sa propre section** (Notion « 13 — Décisions », recette V1) | Contrôles côté serveur examinés : `PassationView.get_queryset` (`dashboard/passation.py:311`) appelle `syntheses_visibles` (`:53`), qui filtre par bâtiment et équipage, sans borne par section ; le contenu figé couvre tout le bâtiment (`contenu_passation`, `:220`) ; aucun test de borne par section trouvé. **La limitation à la section n'est donc pas démontrée.** Écart conservé comme **non vérifié** : il n'est pas conclu à une violation tant qu'un chef de section réel n'a pas été rejoué | `dashboard/passation.py:53,220,306` ; Notion « 13 » | Si la borne manque, un chef de section lirait la synthèse entière (qualifications, annonces, listes) | Non identifié |

## Partie A quater — Écarts relevés à l'ensemble 3

| # | Règle validée | Comportement observé | Sources | Conséquences | Lot |
|---|---|---|---|---|---|
| A15 | Circuit RETEX : auteur → chef de section → chef de secteur → chef de service (`DEC-RTX-01`) ; correction motivée, nouvelle version (`DEC-RTX-02`, `DEC-RTX-03`) | Une seule étape : tout habilité du bâtiment (seuil `retex_validation`, chef de service) valide ou refuse ; les fonctions citant le COMA référent passent en premier dans la notification ; pas de demande de correction | `retex/services.py:54` (`valideurs`), `peut_valider` ; seuil dans `matrix/core/role_thresholds.py` | Un RETEX peut être validé sans visa de la hiérarchie directe de l'auteur ; pas de boucle de correction | L11 |
| A16 | Diffusion « flotte » : proposé à l'organisme destinataire | La diffusion « flotte » **marque** le RETEX ; aucune transmission n'existe | `retex/models.py` (`diffusion`, `organisme`) | L'organisme n'est jamais saisi ni notifié par Matrix ; qui transmet est **à confirmer** | L11 |
| A17 | Préparation à l'appareillage : contrôles issus de fiches de référence approuvées ; circuit section/secteur → service → COMANAV ; contrôles obligatoires, critiques non dérogeables, réserves (`DEC-APP-01`, `DEC-APP-02`, `DEC-APP-10` à `DEC-APP-12`, `DEC-APP-14`) | Les points sont calculés à l'ouverture depuis l'état des installations critiques ; une seule signature (chef de secteur ou plus) ; ni classification, ni réserve, ni fiche de référence | `_points_de_vigilance_navire` (`dashboard/web_views.py:367`) ; `SessionAppareillageSignerView` (`dashboard/web_views.py:664`) | Aucun circuit COMANAV ; la signature atteste la clôture de la session, pas l'aptitude. Compatibilité avec les procédures du bord **à confirmer avant implémentation** | L23 |
| A18 | Transfert de matériel entre secteurs et entre services avec approbations (`DEC-MAT-01` à `DEC-MAT-04`) | Aucun circuit ; réaffectation par l'affectation en masse | `assets/` (aucune vue de transfert) | Pas de trace d'approbation du transfert ni de suivi des tâches ouvertes | L13 |
| A19 | Demande de places : l'organisme de formation répond dans un **dossier vivant** (timeline, fil, transmission, prise en compte) — cible Notion « 03 » | L'organisme est une **unité de type École ou Centre de formation** ; un référent de la formation dans cette unité attribue ou refuse (`_attribuer_places`) ; le demandeur est notifié. Pas de timeline, pas de fil systématique, pas d'étape « transmise à l'organisme » pour la demande de places | `_attribuer_places` (`training/web_views.py:1311`) ; `org/models.py` | Cible non développée ; correction par rapport au rapport E3 (qui disait que l'organisme n'était pas un acteur) | Cible Notion « 03 » |
| A20 | Occurrence non conforme : état « En validation » (pas de règle de sortie décidée par le PO) | L'état est atteint par un verdict non conforme. **Aucune action de validation dédiée** ; seule sortie : correction du compte rendu par un chef de secteur ou plus (motif obligatoire, conformité finale conforme). Exclue du calcul des retards ; aucun lien automatique ticket → occurrence | `maintenance/web_views.py:283` ; `maintenance/perimetre.py:18` ; `maintenance/views.py:167` | **Risque de blocage** : occurrence « En validation » indéfiniment, sans alerte de retard, y compris après réparation. Parties non rejouées (annulation manuelle) : non vérifié | Non identifié (à décider par le PO) |
| A21 | Périodicités nommées, remarques d'outillage, durée indicative (`DEC-PER-01` à `04`, `DEC-OUT-01` à `05`, `DEC-DUR-*`) | Non développé | `maintenance/models.py:18` | Cible, non contradictoire | Plan V1.2 |

## Partie A quinquies — Écarts et contradictions relevés à l'ensemble 4

| # | Règle validée ou affirmation | Comportement observé | Sources | Conséquences | Lot |
|---|---|---|---|---|---|
| A22 | Le projet suppose Python 3.12 ou plus (README, dépendances) | Le script d'installation annonce « Python 3.8 ou supérieur » | `setup.bat:11` ; `README.md` | Une installation sur un Python ancien échouerait tard ; incohérence de documentation uniquement | L28 |
| A23 | Sécurité d'accès avec les SIC : HTTPS, limitation des connexions (cible) | En production, redirection HTTPS et cookies sécurisés actifs ; **ni limitation des tentatives de connexion, ni HSTS, ni réglage de proxy inverse** ; origines CSRF de confiance codées sur `localhost` ; aucun serveur HTTPS ni serveur d'application livré | `matrix/settings.py:413` | Cible non développée ; l'architecture réelle de mise en service reste à définir avec les SIC | L21 |
| A24 | Sauvegarde, restauration, supervision, conservation des journaux (à fournir, `IM-10` pour les durées) | **Rien n'existe** dans le dépôt : ni script, ni documentation | recherche dans tout le dépôt (termes « sauvegarde », « backup », `dumpdata`, `pg_dump`) | Aucun plan de reprise ; durées de conservation des notifications, journaux et estimations non définies (B8) | À définir avec les SIC |
| A25 | Les modules désactivés « n'existent plus » pour le bâtiment (principe de configuration par bâtiment) | Seules les **pages web** sont bloquées ; l'API, les tâches planifiées et les enchaînements internes continuent | `matrix/core/modules.py` ; `matrix/core/middleware.py:210` | Choix volontaire du code pour ne pas casser les enchaînements ; à connaître des intégrateurs | — |
| A26 | Neuf modules sans API (quarts, absences, tâches, annonces, demandes, programme, postes, documentation, RETEX) | Aucune route `/api/` ; pilotage par les pages seulement | `couverture/etat_B/ROUTES.md` | Aucune intégration possible sur ces objets ; cohérent avec la phase 7 « différée » | Phase 7 |



---

## Partie B — Points à confirmer (décisions existantes appliquées ; règle cible non inventée)

Principe retenu : **une décision PO existante qui répond au sujet est appliquée** ; sinon, le dossier garde le **fonctionnement actuel vérifié** et marque la règle cible **« à confirmer »**, sans inventer de règle.

| # | Décision existante applicable | Fonctionnement actuel vérifié | Règle cible |
|---|---|---|---|
| B1 — Suppléance du COMAEQ | `DEC-SUP-01` : la suppléance est **explicitement désignée, activée par une autorité compétente, temporaire, limitée à une fonction et à un périmètre, et tracée** ; `DEC-SUP-02`, `DEC-SUP-04`, `DEC-SUP-05`, `DEC-SUP-07` | Aucun mécanisme général. Seuls secours codés : le commandant de l'équipage peut viser la feuille de service et désigner les rédacteurs quand le poste COMAEQ est **vacant** (`quarts/models.py:2210`) ; remplacement temporaire d'un chef de liste des services à quai (`quarts/remplacement.py:27`) | Le principe est décidé. **La procédure exacte de désignation du suppléant du COMAEQ est à confirmer** (lot L08) |
| B2 — Commandant en second | Notion « 13 — Décisions » : vision globale ; écritures limitées aux **responsabilités attribuées** ; il ne tient pas ses droits automatiquement de son grade | Écriture héritée du grade retirée (API) mais seuil comparé au grade dans plusieurs vues web (A4) | Les responsabilités doivent être **explicites et attribuées dans un cadre autorisé** ; qui les attribue, par quel mécanisme et dans quelles limites est **à confirmer** |
| B3 — Échanges et quarts à la mer | `DEC-FDS-07` : « échanges de tours » sans préciser le périmètre ; `DEC-FDS-13` | Échanges limités aux **services à quai** d'une même liste (`quarts/echanges.py:1`) | **Ne pas généraliser** aux quarts à la mer sans validation métier : à confirmer |
| B4 — Accostage et appareillage | Aucune décision du registre des 125 ; les propositions `mer_quai_*` (état B) décrivent la règle comme validée | Déclaration par le **titulaire COMAEQ** ou le **commandant de l'équipage à bord** (`fonction_habilitee`, `quarts/mouvements.py:27`) ; correction par annulation motivée | Le fonctionnement actuel est documenté ; **l'autorité cible est à confirmer** |
| B5 — Chef de liste des quarts | Notion « 13 » : le chef de liste crée et publie les listes de service et de gardes (**décision antérieure**, remplacée par `DEC-FDS-14` pour la publication) ; `D11` (mer/quai) : chef de liste des quarts **distinct** du chef de liste des services à quai | Désignation par supervision ou par un niveau chef de service dont le périmètre couvre celui visé (`quarts/listes_views.py:163`) | Qui désigne : **à confirmer** |
| B6 — « Fin de journée » d'une tâche | `DEC-BLQ-05` (état « Non réalisée — À reprogrammer ») | Aucune notion de fin de journée | Heure par bâtiment (`IM-09`) : **à confirmer** |
| B7 — Ordre des grades | `DEC-COL-02` | Le grade est un texte sans rang | Valeurs à saisir par le PO : **à confirmer** (`IM-02`) |
| B8 — Conservation | Aucune décision | Notifications, journaux et estimations non purgés | Durées **à confirmer** (`IM-10`) |

## Partie C — Décisions validées non encore développées (non contradictoires)

Elles ne sont pas des écarts : le code ne les contredit pas, il ne les réalise pas encore. Elles figurent en « fonctionnement cible » des chapitres.

| Décision | Objet | Lot | Chapitre |
|---|---|---|---|
| `DEC-CLO-01/03` | Validation facultative du responsable et statut « À valider » | L15 | 10 |
| `DEC-COL-01/05` | Tâche collective, coordinateur | L16 | 10 |
| `DEC-BLQ-03/05` | Reprogrammation et « Non réalisée — À reprogrammer » | L17 | 10 |
| `DEC-SUP-*` | Suppléance explicite | L08 | 5, 8 |
| `DEC-UX-04/09` | Épinglage du menu, recherche de personnes | L24 | 9, 17 |
| Cahier §18 | Espaces de groupe et messagerie de groupe | — | 9 |
| Cahier §37 | Recherche universelle étendue (service, événement, discussion) | — | 9 |
| `DEC-FDS-08` | Composition-type d'une fraction de service à quai (GO du PO requis) | L27 | 8 |

---

## Partie D — Propositions à valider par le PO (🟣, pas des décisions)

Ces points ont été proposés ou relevés ; **aucun n'est décidé** et aucun n'est rattaché à un lot lancé. Le dossier les décrit comme propositions.

| # | Proposition | Origine | Garde-fous demandés | Chapitre |
|---|---|---|---|---|
| D1 | **Ticket de suivi pour une installation déclarée non conforme**, comme pour le matériel mobile | Retenue comme proposition cible par le PO, « à valider » | Un ticket ne clôture jamais automatiquement une anomalie ; il n'autorise jamais une remise en service | 12, 25 |
| D2 | **Règle de sortie de l'état « En validation »** et alerte de retard associée (A20) | Constat du dossier | Aucune règle inventée | 12, 25 |
| D3 | **Transmission d'un RETEX à un organisme** : destinataires, canaux, responsabilités | Précision du PO : acte distinct de la validation et du statut | À confirmer avec les procédures métier ; le marquage « flotte » n'est pas une transmission | 15, 25 |
| D4 | **Autorité de classification « critique »** d'un contrôle d'appareillage | `DEC-APP-14` (principe validé) ; compatibilité avec les procédures du bord non vérifiée | À confirmer avant tout développement | 16, 25 |
| D5 | Favoris épinglés, recherche de personnes limitée, formulaires RH configurables | Observations de recette (PO-18 à PO-20) | « À faire plus tard » ; droits et confidentialité à spécifier | 17, 25 |
| D6 | Observations de recette PO-01 à PO-16, PO-21 (ergonomie, accueil, notifications, fiches de démonstration) | Notion « Recette UX V1.1 » | Qualification et arbitrage du PO avant toute correction | 17 |
| D7 | Sauvegarde, restauration, supervision, conservation des journaux | Aucune source | À définir avec les SIC / l'exploitant | 23 |

## Limites

- 🟢 Les comportements « observés » sont ceux du code de l'état B, lus et recoupés avec les tests ; ⚪ aucun n'a été rejoué en exécution sur une instance, sauf mention contraire.
- ⚪ Les écarts A14 (passation) et B4 (accostage) sont **à confirmer** : ils reposent sur l'absence de restriction trouvée dans le code ou de décision trouvée dans le registre.
- 🔵 Les décisions de la partie C ne sont pas contredites par le code : elles ne sont pas encore développées.
- Les identifiants `DEC-…` renvoient au registre du dossier V1.2 (branche `claude/eager-hopper-2cbcqh`, commit `6cc1557`) ; aucune décision n'est rouverte.

---

**Sources.** Code de l'état B (références en ligne) ; dossier V1.2 : `A_REGISTRE_DECISIONS.md`, `A1_DECISIONS_S1_S2.md`, `J_TRIAGE_ET_ARBITRAGES.md`, `M_PLAN_DEVELOPPEMENT.md` ; Notion « 13 — Décisions Matrix et gouvernance fonctionnelle » ; propositions `docs/propositions/mer_quai_*.md` (état B).
