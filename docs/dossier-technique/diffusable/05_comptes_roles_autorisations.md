# Chapitre 5 — Comptes, fonctions, grades, rôles et autorisations

> **Pour qui :** responsables, administrateurs, développeurs. **Diffusion :** générale (mécanismes détaillés et matrice des droits dans la partie restreinte du dossier et la partie restreinte du dossier).
> **Ce que vous y trouverez :** ce qu'est un compte Matrix, la différence entre grade, fonction, rôle, périmètre et brevet, comment Matrix décide si une action est permise, comment se règlent les droits, et comment on gère les comptes.
> **État décrit :** état B (`6d6d0be`), non fusionné dans `main`.

---

## 5.1 Le compte et le profil

Chaque marin possède un **compte** (identifiant de connexion) auquel est attaché un **profil**. Le profil est créé automatiquement avec le compte, avec le rôle le plus bas (équipier). Il porte :

| Donnée | Rôle dans Matrix |
|---|---|
| **Rôle** | Profil d'accès (neuf possibles, §5.3) |
| **Rattachement** | Unité, service, secteur, section : **définit le périmètre** du marin |
| **Équipage** | « A », « B »… sur un bâtiment à double équipage (obligatoire dans ce cas) |
| **Grade**, **spécialité**, **fonction de service**, **matricule**, date de naissance | Informations d'identification, choisies dans des listes configurables |
| **Fonction de commandant adjoint** | Pour un état-major : COMAEQ, COMOPS, COMANAV ou COMAVIA ; sert à aiguiller les visas |
| **Préférences** | Thème clair ou sombre, menu replié, heures des notifications du matin (08 h par défaut) et du soir (18 h) ; **jamais un contrôle d'accès** |
| **Mot de passe provisoire** | Indicateur : le marin doit en choisir un nouveau à sa prochaine connexion |

L'identifiant est construit sous la forme `prenom.nom` (accents retirés), avec un numéro en cas d'homonyme.

## 5.2 Cinq notions à ne jamais confondre

C'est le cœur du modèle de droits de Matrix, repris de la directive du PO : **le grade n'ouvre aucun droit à lui seul.**

| Notion | Question | Exemple | Dans Matrix |
|---|---|---|---|
| **Grade** | Quel est son rang ? | Matelot, maître… | Information d'identification. 🔵 Un « rang » configurable du grade est prévu pour désigner le coordinateur d'une tâche collective (lot L16) |
| **Fonction exercée** | Que fait-elle réellement ? | Chef de liste, BSC, COMAEQ | Désignations dans les modules (chef de liste, titulaire de COMA, référent de formation) et fonction de service du profil |
| **Rôle** | Quel profil d'accès a-t-elle dans Matrix ? | Chef de secteur | Neuf rôles ordonnés ; détermine un niveau |
| **Périmètre** | Sur quoi agit-elle ? | Sa section, son secteur… | Déduit du rattachement |
| **Brevet / qualification** | Que sait-elle faire ? | BHT, C-CDM… | Module formation (chapitre 14) ; informatif pour les tâches ordinaires |

**Un exemple pour fixer les idées** (personnage fictif). Le maître Durand est rattaché à la section « Propulsion » du secteur « Machine », service « Énergie » de son bâtiment.
- Son **grade** est « maître » : c'est son rang. Dans Matrix, il sert à l'afficher, à l'identifier, et (plus tard) à proposer un coordinateur de tâche collective. **Il ne lui donne aucun droit.**
- Sa **fonction** : il est désigné chef de liste des services à quai de sa section, et exerce la fonction de service « gradé de coupée ». Ces fonctions lui ouvrent des droits **précis** (préparer et proposer une liste de sa section), indépendants de son rang.
- Son **rôle** dans Matrix est « chef de section » : c'est son profil d'accès. Il lui donne un niveau (2 sur 9) qui lui permet, par exemple, d'attribuer des tâches.
- Son **périmètre** est sa section : il ne voit et ne modifie que ce qui relève de la section « Propulsion ».
- Sa **qualification** : il détient, dans le module formation, des validations (par exemple une habilitation incendie, exemple fictif). Matrix les **affiche**, et peut les exiger pour tenir certains postes ; elles ne bloquent pas l'attribution d'une tâche ordinaire.

S'il est muté dans une autre section, son grade, sa fonction de gradé de coupée et ses qualifications le suivent ; son **périmètre** et sa désignation de chef de liste, eux, changent ou disparaissent.

Le cahier des charges parlait d'un modèle combinant rôle, attributs, périmètre et responsabilité. L'état B en réalise **le rôle, le périmètre, des attributs ciblés (équipage, fonction de commandant adjoint) et les désignations de responsabilité**, pas un moteur d'attributs général.

## 5.3 Les neuf rôles

Les rôles sont ordonnés du plus bas au plus haut. Le niveau numérique sert à comparer ; il n'est pas affiché.

| Niveau | Rôle | Ce qu'il est |
|---|---|---|
| 1 | **Équipier** | Marin d'exécution |
| 2 | **Chef de section** | Encadre une section |
| 3 | **Chef de secteur** | Encadre un secteur |
| 4 | **Chef de service** | Encadre un service |
| 5 | **État-major** | Commandant adjoint (COMAEQ, COMOPS, COMANAV, COMAVIA) ; n'écrit que dans les services de sa fonction |
| 6 | **Commandant en second** | Vision globale, suppléant du commandant ; écritures limitées aux responsabilités attribuées |
| 7 | **Commandant** | Commandement du bâtiment (ou de l'équipage) |
| 8 | **Administrateur d'unité** | Administre le bâtiment : comptes, structure, réglages |
| 9 | **Administrateur général** | Administre toute la flotte ; équivalent du superutilisateur |

Deux désignations **ne sont pas des rôles** : le **chef de liste** (désigné dans le module quarts) et le **référent de formation**. Elles ouvrent des droits dans leur domaine sans toucher au rôle. De même, le responsable de spécialité et le responsable de classe sont des désignations à l'échelle de la flotte.

## 5.4 Comment Matrix décide si une action est permise

À chaque action d'écriture, le serveur pose trois questions, dans cet ordre. L'écran peut masquer un bouton, mais **c'est toujours le serveur qui décide**, jamais l'affichage.

![Décision d'une action](../schemas/svg/S06_calcul_droits.svg)

*Schéma S06 — Les contrôles successifs appliqués à une demande d'écriture.*

1. **Mon statut m'autorise-t-il à écrire ?** L'équipage à terre et le soutien à terre sont en lecture seule, sauf quelques actions explicitement prévues (chapitre 4).
2. **Mon niveau est-il suffisant ?** Chaque action a un **seuil** : le rôle minimal requis. Le seuil dépend du bâtiment (§5.5).
3. **L'objet est-il dans mon périmètre ?** Une action n'est possible que sur des objets rattachés à mon unité, mon service, mon secteur ou ma section.

Pour l'état-major, un contrôle supplémentaire s'applique : il n'écrit que sur les services rattachés à sa fonction de commandant adjoint ; ailleurs, il garde la lecture et les droits d'un équipier.

Enfin, certains circuits exigent une **fonction précise**, quel que soit le niveau : par exemple le visa de la feuille de service revient au COMAEQ compétent du service et de l'équipage concerné, et non à « un état-major ». Un administrateur désigne le titulaire d'une fonction, **sans pouvoir viser à sa place**.

## 5.4 bis — Sept personnes, sept journées, et deux désignations (BSC, chef de liste)

Pour comprendre ce que les droits changent concrètement, voici ce que peuvent faire sept personnes fictives d'un même bâtiment. Le tableau est **généré depuis les valeurs par défaut du code** (`outils/generer_exemples_droits.py`) ; il indique si le **niveau** de la personne atteint le seuil de l'action. Ce n'est qu'une des conditions : le **périmètre** (et, pour certains circuits, la **fonction exercée**) s'y ajoute toujours.

| Action (valeur par défaut du seuil) | Matelot (équipier) | Chef de section | Chef de secteur | Chef de service | COMAEQ (état-major) | Commandant | Administrateur technique (unité) |
|---|---|---|---|---|---|---|---|
| Exécuter une maintenance (EQUIPIER) | oui | oui | oui | oui | oui | oui | oui |
| Attribuer une tâche à un marin (CHEF_SECTION) | non | oui | oui | oui | oui | oui | oui |
| Créer ou modifier un matériel (CHEF_SECTION) | non | oui | oui | oui | oui | oui | oui |
| Supprimer un matériel, action groupée (CHEF_SERVICE) | non | non | non | oui | oui | oui | oui |
| Corriger un compte rendu de maintenance terminé (CHEF_SECTEUR) | non | non | oui | oui | oui | oui | oui |
| Voir le bloc Supervision de la page Aujourd'hui (CHEF_SECTEUR) | non | non | oui | oui | oui | oui | oui |
| Publier une liste de quarts ou de gardes (seuil) (CHEF_SERVICE) | non | non | non | oui | oui | oui | oui |
| Viser une feuille de service au palier du chef de service (seuil) (CHEF_SERVICE) | non | non | non | oui | oui | oui | oui |
| Publier une annonce (CHEF_SERVICE) | non | non | non | oui | oui | oui | oui |
| Activer ou désactiver un module du bâtiment (COMMANDANT_EN_SECOND) | non | non | non | non | non | oui | oui |
| Réinitialiser un mot de passe (ADMIN_NAVIRE) | non | non | non | non | non | non | oui |
| Modifier la structure du bâtiment (ADMIN_NAVIRE) | non | non | non | non | non | non | oui |

> **Comment lire « oui ».** « Oui » signifie « le niveau suffit », pas « peut le faire partout ». Un chef de service publie une liste **de son service**, pas celle d'un autre. Le COMAEQ (état-major) n'écrit que dans **les services rattachés à sa fonction**. Le visa de la feuille de service n'est pas ouvert « à un niveau » mais à des **fonctions** (voir ci-dessous) : la ligne correspondante du tableau n'indique que le seuil du palier « chef de service ».

**Le matelot (équipier).** Il ouvre « Aujourd'hui » : ses tâches, les maintenances qui lui sont assignées, ses quarts et services, ses formations du jour, les annonces qui le visent. Il démarre une tâche, signale un blocage avec son motif, rend compte et la termine ; il exécute une maintenance guidée ; il déclare ses absences ; il se crée une tâche personnelle, **privée tant qu'il ne la partage pas** ; il répond à une proposition d'échange de tour et en propose lui-même. Il ne peut pas attribuer une tâche, créer un matériel, valider ou publier quoi que ce soit.

**Le chef de section.** Tout ce que fait le matelot, plus : il attribue des tâches aux marins de **sa section** (et de son équipage), suit leur avancement, crée et modifie un matériel, un plan de maintenance, valide une absence déclarée par un marin de sa section. S'il est désigné chef de liste, il prépare et **propose** une liste ; il ne la publie pas. Il ne supprime pas un matériel, ne corrige pas un compte rendu terminé.

**Le chef de secteur.** En plus : il corrige un compte rendu de maintenance terminé (motif obligatoire, saisie d'origine conservée), voit le bloc « Supervision » de sa page d'accueil (retards, validations en attente de son secteur), supervise et réaffecte les tâches de son secteur. Il vise la feuille de service au palier « secteur » lorsque le rédacteur en dépend.

**Le chef de service.** En plus : il supprime un matériel, lance une action groupée, **publie** les listes de quarts et de gardes **de son service** (la liste doit porter exactement son périmètre), vise la feuille de service au palier « service », publie des annonces ciblées dans son périmètre, valide les documents et les retours d'expérience.

**Le COMAEQ (état-major).** Il porte la vie à bord et le service courant. Dans Matrix, il écrit **uniquement** dans les services rattachés à la fonction COMAEQ. **Il vise la feuille de service** : ce visa lui revient en tant que **titulaire de la fonction COMAEQ** de son équipage, et non parce qu'il est « état-major ». Il désigne les rédacteurs (le BSC) de la feuille de son équipage. Il déclare l'accostage et l'appareillage du bâtiment. 🔵 *Règle cible validée par le PO, non appliquée :* il décide des échanges de tours et approuve et publie les listes de quarts et de gardes (voir §5.11).

**Le BSC (rédacteur de la feuille de service).** Le BSC est le marin **désigné nominativement par le COMAEQ** de son équipage pour préparer la feuille de service. Son droit de rédiger vient de **cette désignation**, pas de son grade ni de son rôle : un matelot désigné rédige ; un commandant non désigné ne rédige pas. Il **prépare et propose** la feuille ; il **ne la vise pas** et **ne la publie pas** : elle passe par le visa du chef de secteur, du chef de service, puis du COMAEQ. Il n'est pas une autorité parallèle au COMAEQ. S'il change d'équipage ou quitte le bâtiment, sa désignation cesse de donner un droit.

**Le chef de liste.** Le chef de liste est un marin **désigné pour un périmètre précis et un type de liste** : « quarts à la mer » ou « services à quai ». Il **prépare** la liste (créneaux, affectations) et la **propose** à la publication ; pour une liste à quai, il **active** la liste publiée à titre prévisionnel. Son droit vient de **cette désignation**, pas de son grade ; une désignation sans type ne donne aucun droit. Il ne publie pas, sauf s'il relève par ailleurs du commandement ou atteint le seuil de publication de son périmètre.

**Le commandant.** Vision et supervision du bâtiment : il gère les comptes jusqu'au niveau état-major, active ou désactive des modules, propose la relève de l'équipage, valide l'organisation d'alerte, gère les listes de son bâtiment (création, publication) au titre de la supervision. Si le poste de COMAEQ est vacant, **lui seul** (et pas son second) peut viser la feuille de service de son équipage, de façon tracée et signalée ; un COMAEQ simplement absent n'ouvre pas cette exception.

**L'administrateur technique (administrateur d'unité).** Il administre la **plateforme et le bâtiment** : crée les comptes, règle les seuils et les modules, modifie la structure, réinitialise les mots de passe, désigne les titulaires de fonctions (le COMAEQ, par exemple), applique la configuration. 🔵 **Règle validée par le PO : il n'a aucun visa métier** : il désigne les titulaires sans viser à leur place. ⚠️ **Écart d'implémentation** : dans l'état B, son niveau lui fait atteindre les seuils de la plupart des actions métier (colonne de droite du tableau). Seules des règles propres à certains circuits l'en écartent (visa du COMAEQ, rédaction de la feuille de service). Cet écart n'est **pas** la règle souhaitée ; il est traité par le lot L06 (voir §5.11 et le registre des écarts (partie restreinte du dossier)).

### Qui prépare, qui valide, qui autorise la publication

Trois responsabilités à ne pas confondre. Le tableau distingue **le fonctionnement actuel (état B)** de la **règle cible validée par le PO**.

| Objet | Qui **prépare** | Qui **valide / vise** | Qui **autorise la publication** (actuel 🟢) | Règle cible 🔵 |
|---|---|---|---|---|
| **Feuille de service** | Le **BSC** (ou délégué), désigné par le COMAEQ | Visas successifs : chef de secteur, chef de service, puis **COMAEQ** titulaire (secours : commandant de l'équipage si le poste est vacant) | La publication suit le dernier visa (COMAEQ) ; refusée si le contenu a changé depuis | Conforme (`DEC-FDS-01`, `-02`, `-11`, `-12`) ; s'y ajoute l'impression A4 et la réimpression versionnée (non développées) |
| **Liste de quarts à la mer** | Le **chef de liste « quarts »** désigné pour le périmètre | — (pas de visa intermédiaire) | Le commandement, ou un rôle atteignant le seuil de publication **dont le périmètre personnel est exactement celui de la liste** | Le **COMAEQ ou son suppléant habilité** approuve et publie (`DEC-FDS-14`) : **écart**, lot L09 |
| **Liste de services à quai** | Le **chef de liste « quai »** désigné pour le périmètre | — | Idem ; l'**activation** (rendre la liste applicable) revient au **seul chef de liste désigné** ou à son remplaçant, jamais au COMAEQ | Publication : COMAEQ ou suppléant habilité (`DEC-FDS-14`) ; activation : inchangée |
| **Échange de tour de service à quai** | Les deux marins (demande, accord) | Aujourd'hui : qui **gère la liste** | — | Le chef de liste ou le BSC **instruit** ; le **COMAEQ ou son suppléant habilité décide** (`DEC-FDS-07`, `-13`) : **écart**, lot L10 |

**À retenir.** Celui qui **prépare** une feuille (le BSC) n'est pas celui qui prépare une **liste** (le chef de liste), et ni l'un ni l'autre n'est, par construction, celui qui **valide** et **autorise la publication**. Aucun de ces droits ne se déduit du seul grade.

## 5.5 Les seuils par action : la configuration plutôt que le code

Plutôt que de coder « un chef de section peut créer un matériel » dans le programme, Matrix tient un **registre de 35 actions**, chacune avec un rôle minimal par défaut. Exemples (valeurs par défaut) :

| Action | Seuil par défaut |
|---|---|
| Créer ou modifier un matériel | Chef de section |
| Supprimer un matériel, lancer une action groupée | Chef de service |
| Corriger un compte rendu de maintenance terminé | Chef de secteur |
| Publier une liste de quarts ou de gardes | Chef de service |
| Activer ou désactiver un module | Commandant en second |
| Modifier la structure du bâtiment | Administrateur d'unité |
| Modifier les grades, spécialités, rôles disponibles (toute la flotte) | Administrateur général |

La **matrice complète** est l'annexe B (restreinte).

- **Qui règle ?** L'administrateur d'unité règle chaque seuil de **son** bâtiment, dans Réglages › Sécurité. Les actions de portée « flotte » (référentiels communs) ne se règlent que par l'administrateur général.
- **Tant que rien n'est réglé, le comportement est celui des valeurs par défaut**, qui reproduisent les droits d'origine.
- **Prise en compte immédiate.** Un changement est vu dès la requête suivante, sur tous les processus du serveur.
- Les seuils sont une **condition**, pas une autorisation : le périmètre reste vérifié.

## 5.6 Ce que chacun voit : le périmètre de lecture

Le périmètre est **le niveau de rattachement le plus fin renseigné** sur le profil : un chef de section rattaché à sa section voit celle-ci ; un chef de secteur rattaché à son secteur voit le secteur. Un profil qui n'est rattaché qu'à un secteur (sans renseigner l'unité) est tout de même rattaché à son bâtiment, par la hiérarchie.

Cas particuliers :
- **Administrateur général** : toute la flotte (ou le bâtiment choisi dans le sélecteur).
- **Responsable de spécialité ou de classe, sans bâtiment** : les bâtiments qu'il suit, en consultation.
- **Sans aucun rattachement** : Matrix ne montre rien plutôt que de montrer ce qui n'est pas dans le périmètre.

## 5.7 Les cas particuliers à connaître

| Cas | Règle appliquée |
|---|---|
| **Commandant en second** | Vision globale, mais **l'écriture n'est pas héritée de son grade** : ses actions passent par des responsabilités attribuées et des circuits explicites (la publication d'annonces sur son bâtiment lui est ouverte). Il supplée le commandant pour la validation de la relève. |
| **État-major** | Écrit uniquement dans les services dont le commandant adjoint est sa fonction. Un service dont le commandant adjoint n'est pas configuré n'est rattaché à aucune fonction : un état-major n'y écrit donc pas. |
| **Équipage à terre** | Lecture seule du bâtiment, avec sa propre feuille de service. |
| **Soutien à terre** (responsable de classe ou de spécialité sans bâtiment) | Consulte et commente ; n'écrit que dans les circuits prévus (catalogue flotte, par exemple). **Aucun droit automatique sur le bord, quel que soit le grade.** |
| **Administrateur d'unité** | Administre le bâtiment : comptes, structure, réglages. Son niveau (8) dépasse tous les seuils métier par défaut. 🔵 Le PO a décidé qu'il ne doit avoir **aucun visa métier** (voir §5.11). |
| **Administrateur général** | Seul niveau multi-bâtiments ; équivalent du superutilisateur. |

## 5.8 Gérer les comptes

La gestion se fait dans l'**Annuaire** (visible à partir du commandant en second) et par l'API.

- **Qui peut gérer quel rôle.** On ne gère que des rôles **inférieurs ou égaux au sien** selon une table unique, appliquée à l'écran comme à l'API :

![Qui gère qui](../schemas/svg/S07_gestion_des_roles.svg)

*Schéma S07 — Gestion des comptes par rôle.*

Hors administrateur général, on n'agit que sur les comptes de **son propre bâtiment**, jamais sur l'administrateur général, et on peut toujours modifier **son propre** compte. Le commandant en second **ne gère aucun compte**.

- **Créer un compte** : on choisit le rôle (dans la limite de ses droits), l'identité, la fonction, l'unité, le service, le secteur, la section et l'équipage. Les rattachements sont **validés contre le périmètre de l'appelant avant toute création** : on ne peut pas rattacher un marin à un bâtiment qu'on ne gère pas.
- **Modifier**, **action en masse** (changer rôle, unité, service, secteur, section, fonction, grade, spécialité), **export Excel** de l'annuaire.
- **Mot de passe.** Un compte créé n'a pas de mot de passe utilisable. L'administrateur du bâtiment (seuil configurable) **réinitialise** : Matrix génère un mot de passe provisoire de 14 caractères, **affiché une seule fois**, jamais enregistré en clair ni écrit dans le journal. Le marin doit le remplacer à sa première connexion : tant qu'il ne l'a pas fait, seules la page de changement et la déconnexion lui sont ouvertes.
- **Supprimer un compte** est possible (par l'annuaire, jamais sur soi-même). La suppression est tracée. 🔵 Le PO a décidé de **désactiver plutôt que supprimer** (lot L04, non lancé) ; l'état d'un compte « désactivé » existe déjà au sens du système d'authentification et n'est pas bloquant pour l'archivage d'unités, mais il n'y a pas, dans l'annuaire, de bouton de désactivation.
- **Chaque acte est tracé** dans le journal d'audit : création, modification, changement de rôle, réinitialisation, suppression, connexion et déconnexion.

## 5.9 Les listes configurables

Grades, spécialités, fonctions de service, fonctions de quart, types d'absence et rôles attribuables sont des **listes de référence** modifiables sans toucher au programme : on peut ajouter une valeur, l'activer ou la désactiver. Ces référentiels sont communs à toute la flotte ; ils ne se modifient qu'au niveau « administrateur général » par défaut. Les désignations de **responsable de spécialité** et de **responsable de classe de navire** se font à l'échelle de la flotte, au même niveau.

## 5.10 Se connecter, rester connecté

- Authentification par identifiant et mot de passe ; le mot de passe doit passer les contrôles standards (longueur, pas trop courant, pas entièrement numérique, pas trop proche de l'identité).
- **Déconnexion automatique après 15 minutes d'inactivité** par défaut (réglable entre 1 minute et 8 heures), avec un avertissement 60 secondes avant. Cela protège les **postes partagés** du bord. Les requêtes automatiques (compteur de notifications, brouillons) ne comptent pas comme une activité.
- **Brouillons** : un formulaire en cours est enregistré avant la déconnexion et peut être repris (conservation de 30 jours par défaut).
- **Postes partagés** : une écriture est refusée si la page a été ouverte pour **un autre marin** que celui connecté, ce qui évite d'enregistrer au nom d'un collègue qui s'est connecté entre-temps.

## 5.11 Fonctionnement cible 🔵 (décisions du PO, non développées)

| Sujet | Règle validée | Lot |
|---|---|---|
| **Exclure l'administrateur technique des actes métier** | L'administrateur technique gère la plateforme, désigne les titulaires, applique un transfert approuvé ; il n'a **aucun visa métier** | L06 |
| **Rattachement incomplet et validation des rôles** | Un rattachement obligatoire et cohérent ; une fonction exercée n'ouvre pas d'accès de sa seule dénomination | L07 |
| **Suppléance explicite** | Une autorité compétente active une suppléance bornée dans le temps, tracée ; un suppléant officiel n'existe que par ce mécanisme | L08 |
| **Droits par fonction** | Les visas viennent de la fonction exercée et du périmètre, pas du niveau seul | L09 |
| **Désactiver plutôt que supprimer un compte** | Historique et traces conservés | L04 |
| **Rang des grades configurable** | Pour proposer le coordinateur d'une tâche collective ; valeurs saisies par le PO | L16 |
| **Sécurité d'accès** | Avec les SIC | L21 |
| **Import de comptes** | Annoncé, non développé | — |
| **Fonctions annexes** | « Adjudant de compagnie » et « OSS » : reconnues comme **fonctions** attribuées à des personnes, ni grades, ni permissions générales ; leur rattachement dépend de l'unité. Ce n'est pas un feu vert d'implémentation | — |

### Écarts d'implémentation à connaître

Les quatre écarts suivants opposent une **décision du PO** à un **comportement actuel du code**. Le comportement actuel n'est **pas** la règle métier souhaitée ; il est décrit pour que personne ne le prenne pour tel. Chaque écart est détaillé (règle validée, comportement observé, sources, conséquences, lot) dans le registre des écarts (partie restreinte du dossier). Aucune décision n'est rouverte ici.

| Écart | Règle métier validée (PO) | Comportement actuel (état B) | Lot de correction |
|---|---|---|---|
| **Administrateur technique** | Il n'a aucun visa métier ; il désigne les titulaires sans viser à leur place (`DEC-DRT-02`) | Son niveau atteint les seuils de la plupart des actions métier ; seuls certains circuits l'en écartent | L06 |
| **Échanges de tours** | La décision finale revient au COMAEQ ou à son suppléant habilité ; le chef de liste ou le BSC instruit (`DEC-FDS-07`, `DEC-FDS-13`) | La validation revient à qui **gère la liste** : chef de liste désigné, ou commandement (`peut_valider_echange`) | L10 |
| **Publication des listes de quarts et de gardes** | Le chef de liste prépare et propose ; le COMAEQ ou son suppléant habilité approuve et publie (`DEC-FDS-14`) | Publie : le commandement, ou tout rôle atteignant le seuil « chef de service » **dont le périmètre personnel est exactement celui de la liste** ; la fonction COMAEQ n'intervient pas | L09 |
| **Commandant en second** | Vision globale ; écritures limitées aux responsabilités attribuées, pas à un seuil de grade (Notion « 13 — Décisions ») | L'écriture héritée de son grade lui est retirée, mais certaines vues comparent le seuil à **son grade** et d'autres à son **niveau d'écriture** : son pouvoir varie selon la vue | Non identifié ; **les responsabilités doivent être explicites et attribuées dans un cadre autorisé, jamais déduites du grade** ; qui les attribue est **à confirmer** (registre des écarts, B2) |

## 5.12 Limites et éléments non vérifiés

- 🟢 Les contrôles décrits sont couverts par des tests de l'état B (`accounts/tests/`, dont la matrice des droits, les fuites de périmètre et la réinitialisation de mot de passe). La suite complète passe sur SQLite ; ⚪ PostgreSQL, Windows et navigateur n'ont pas été rejoués.
- ⚪ Les pages Notion « 02 — RH, postes, qualifications » et « 03 — Formation, stages » décrivent des objets cibles (poste, aptitudes, profondeur de relève, couverture de fonctions) qui **ne sont pas des fonctions actuelles**.
- ⚪ L'ordre exact des grades et la liste des brevets ne sont pas dans le code ; ils sont à fournir par le PO (informations manquantes IM-01 et IM-02 du dossier V1.2).
- ⚪ Le détail action par action de ce que peut faire un administrateur d'unité est établi dans les chapitres qui traitent chaque circuit.

---

**Sources (état B).** Code de l'état B : rôles, profils, périmètres, journal d'audit, seuils de rôle configurables, contrôle d'écriture, déconnexion automatique (références ligne par ligne dans la partie restreinte du dossier). Notion : « Organigramme et rôles », « 13 — Décisions », « 02 — RH, postes… ». Décisions : `DEC-DRT-*`, `DEC-SUP-*`, `DEC-ORG-04` (dossier V1.2, `A_REGISTRE_DECISIONS.md`). Tests : `accounts/tests/test_matrice_droits.py`.
