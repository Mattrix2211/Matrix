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
| A12 | Impression A4 de la feuille de service par le BSC et signalement de réimpression d'une feuille affichée (`DEC-FDS-04`, `DEC-FDS-06`) | Aucune page imprimable ni alerte de réimpression pour la feuille de service ; seule la fiche d'une **liste** a un rendu imprimable | `matrix/templates/quarts/liste_detail.html` (impression) ; absence dans `feuille_service_detail.html` | Le BSC imprime avec les moyens du navigateur ; pas d'alerte de remplacement d'un affichage | L27 |
| A13 | Trois priorités : normale, haute, urgente ; priorité du chef de secteur non abaissable par le chef de section (`DEC-TAC-04`, `DEC-TAC-05`) | Deux priorités : normale, urgente ; pas de règle d'abaissement | `taches/models.py:38-43` | Perte d'un niveau de nuance ; pas de règle de hiérarchie des priorités | L14 |
| A14 *(à confirmer)* | Synthèse de passation : un chef de section ne consulte que **sa propre section** (Notion « 13 — Décisions », recette V1) | `syntheses_visibles` (`dashboard/passation.py:53`) ouvre les synthèses du bâtiment à tout chef (seuil de supervision des tâches) de l'un des deux équipages ; aucune borne par section trouvée dans `dashboard/passation.py` | `dashboard/passation.py:53,220` ; Notion « 13 » | Un chef de section pourrait lire la synthèse entière (qualifications, annonces, listes) ; **non vérifié en exécution** | Non identifié |

---

## Partie B — Décisions absentes, ambiguës ou non tranchées (signalées séparément, sans réponse inventée)

| # | Point | Pourquoi c'est ouvert | Source |
|---|---|---|---|
| B1 | **« Suppléant officiellement habilité » du COMAEQ** (`DEC-FDS-02`, `DEC-FDS-07`, `DEC-FDS-14`) : qu'est-ce qui rend un suppléant « officiel » ? | Les décisions l'exigent sans définir le mécanisme. Le dossier V1.2 propose qu'il le soit par une suppléance explicite activée par l'autorité compétente (`IM-06`), mais cette proposition est une **proposition technique non validée**. Tant que L08 n'existe pas, le seul secours codé est le commandant de l'équipage pour la **feuille de service** quand le poste COMAEQ est **vacant** | `J_TRIAGE_ET_ARBITRAGES.md` (IM-05, IM-06) ; `DEC-SUP-01` ; `quarts/models.py:2210` |
| B2 | **Commandant en second : « responsabilités attribuées »** | La règle dit que ses droits découlent de responsabilités attribuées, sans dire **par qui** ni **par quel mécanisme** elles sont attribuées, ni la liste de ses actes. L'harmonisation (A4) ne peut pas être spécifiée sans cela | Notion « 13 — Décisions » |
| B3 | **Échanges de quarts à la mer.** `DEC-FDS-07` parle d'« échanges de tours » sans préciser s'ils couvrent les **quarts à la mer** ou seulement les **services à quai** | Le code ne gère l'échange que pour les **listes de services de garde** (« non étendu aux quarts », docstring de `quarts/echanges.py`). La décision ne tranche pas l'extension | `quarts/echanges.py:1` ; `DEC-FDS-07` |
| B4 | **Autorité de déclaration d'un accostage ou d'un appareillage** | Le code l'ouvre au titulaire COMAEQ ou au commandant de l'équipage à bord (`fonction_habilitee`, `quarts/mouvements.py`). Je n'ai trouvé cette règle ni dans le registre des 125 décisions, ni dans les pages Notion lues ; elle est décrite dans les propositions `docs/propositions/mer_quai_*.md` (état B) comme validée par le PO. À confirmer qu'elle est bien une décision et non une hypothèse de réalisation | `quarts/mouvements.py:27` ; `docs/propositions/mer_quai_plan_technique.md` |
| B5 | **Qui désigne le chef de liste des quarts à la mer** | Le code ouvre la désignation à qui atteint un seuil et couvre exactement le périmètre ; le registre des décisions n'en parle pas (le chef de liste est cité comme rôle transverse dans Notion « 13 ») | `quarts/listes_views.py` (désignation) ; Notion « 13 » |
| B6 | **« Fin de journée »** d'une tâche non terminée (`DEC-BLQ-05`) | Heure de fin de journée à fixer par bâtiment (`IM-09`) ; proposition technique non validée | `J_TRIAGE_ET_ARBITRAGES.md` (IM-09) |
| B7 | **Ordre des grades** pour proposer un coordinateur de tâche collective (`DEC-COL-02`) | Valeurs à saisir par le PO (`IM-02`) | idem |
| B8 | **Conservation des notifications lues, des estimations et des journaux** | Durées non définies (`IM-10`) | idem |

---

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

## Limites

- 🟢 Les comportements « observés » sont ceux du code de l'état B, lus et recoupés avec les tests ; ⚪ aucun n'a été rejoué en exécution sur une instance, sauf mention contraire.
- ⚪ Les écarts A14 (passation) et B4 (accostage) sont **à confirmer** : ils reposent sur l'absence de restriction trouvée dans le code ou de décision trouvée dans le registre.
- 🔵 Les décisions de la partie C ne sont pas contredites par le code : elles ne sont pas encore développées.
- Les identifiants `DEC-…` renvoient au registre du dossier V1.2 (branche `claude/eager-hopper-2cbcqh`, commit `6cc1557`) ; aucune décision n'est rouverte.

---

**Sources.** Code de l'état B (références en ligne) ; dossier V1.2 : `A_REGISTRE_DECISIONS.md`, `A1_DECISIONS_S1_S2.md`, `J_TRIAGE_ET_ARBITRAGES.md`, `M_PLAN_DEVELOPPEMENT.md` ; Notion « 13 — Décisions Matrix et gouvernance fonctionnelle » ; propositions `docs/propositions/mer_quai_*.md` (état B).
