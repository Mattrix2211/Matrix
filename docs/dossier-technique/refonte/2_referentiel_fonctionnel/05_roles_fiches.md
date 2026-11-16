<!-- partie: Organisation et rôles -->
# Fiches de rôle

<div class="ligne-public"><b>Public :</b> responsables, commandement · <b>Ce que vous y trouverez :</b> une fiche par rôle : ce que la personne fait, ce qu'elle voit, ce qu'elle ne peut pas faire, et où le suivre dans le guide utilisateur · <b>Règles complètes :</b> [[RF:05_roles_et_autorisations]]</div>

Un rôle est un **profil d'accès** ; il n'est ni un grade ni une fonction. Les seuils ci-dessous sont les **valeurs par défaut** ; chaque bâtiment peut les régler. Un niveau suffisant n'est qu'une condition : le **périmètre** (et, pour certains circuits, la **fonction exercée**) s'y ajoute toujours. Deux désignations ouvrent des droits sans changer le rôle : le **chef de liste** et le **rédacteur de la feuille de service (BSC)**.

## Équipier (niveau 1)

| Rubrique | Contenu |
|---|---|
| Qui | Marin d'exécution |
| Ce qu'il fait 🟢 | Ouvre « Aujourd'hui » ; démarre une tâche, signale un blocage avec son motif, rend compte, la termine ; exécute une maintenance guidée ; signale une anomalie ; déclare ses absences ; se crée une tâche personnelle, **privée tant qu'il ne la partage pas** ; propose ou accepte un échange de tour ; accuse réception des annonces |
| Ce qu'il voit | Ses tâches, ses maintenances assignées, ses quarts et services, ses formations, les annonces qui le visent |
| Ce qu'il ne peut pas faire | Attribuer une tâche, créer un matériel, corriger un compte rendu terminé, publier une liste ou une annonce |
| Désignations possibles | BSC (rédacteur de la feuille de service), chef de liste : droits dans leur domaine seulement |
| Où dans le guide | Parcours du guide utilisateur : ma journée, une tâche, une maintenance, une anomalie, mon tour de service ([[GU:00_matrix_en_une_page]])|

## Chef de section (niveau 2)

| Rubrique | Contenu |
|---|---|
| Qui | Encadre une section |
| Ce qu'il fait 🟢 | Tout ce que fait l'équipier ; attribue des tâches aux marins de sa section ; suit leur avancement ; crée et modifie un matériel et un plan de maintenance ; valide une absence déclarée dans sa section ; exécute ou commente une maintenance qui n'est pas la sienne ; prend en compte, traite et convertit une anomalie |
| Ce qu'il voit | Sa section et son équipage ; la synthèse de section |
| Ce qu'il ne peut pas faire | Supprimer un matériel, corriger un compte rendu terminé ; **publier** une liste (s'il est chef de liste, il la prépare et la **propose**) |
| Désignations possibles | Chef de liste |
| Où dans le guide | Synthèse du chef de section ; parcours « Du côté du chef » |

## Chef de secteur (niveau 3)

| Rubrique | Contenu |
|---|---|
| Qui | Encadre un secteur |
| Ce qu'il fait 🟢 | Tout ce que fait le chef de section ; **corrige un compte rendu de maintenance terminé** (motif obligatoire, saisie d'origine conservée) ; voit le bloc « Supervision » de l'accueil ; supervise et réaffecte les tâches de son secteur ; vise la feuille de service au palier « secteur » |
| Ce qu'il voit | Son secteur : retards, validations en attente, tickets ouverts |
| Ce qu'il ne peut pas faire | Supprimer un matériel, publier une liste ou une annonce |
| Particularité | Seul niveau, avec les niveaux supérieurs, à voir le bouton « Enregistrer la correction » d'une maintenance « En validation » (écart A20) |
| Où dans le guide | Accueil du chef de secteur ; « Quand l'échéance reste En validation » |

## Chef de service (niveau 4)

| Rubrique | Contenu |
|---|---|
| Qui | Encadre un service |
| Ce qu'il fait 🟢 | Tout ce que fait le chef de secteur ; supprime un matériel et lance une action groupée ; **publie** les listes de quarts et de gardes **de son service** (la liste doit porter exactement son périmètre) ; vise la feuille de service au palier « service » ; publie des annonces ciblées ; valide documents et retours d'expérience ; valide les absences |
| Ce qu'il voit | Son service |
| Ce qu'il ne peut pas faire | Agir dans un autre service ; activer un module |
| Où dans le guide | Vue d'ensemble du service ; absences |

## État-major : commandant adjoint (niveau 5)

| Rubrique | Contenu |
|---|---|
| Qui | COMAEQ, COMOPS, COMANAV, COMAVIA |
| Ce qu'il fait 🟢 | Écrit **uniquement** dans les services rattachés à sa fonction. Le COMAEQ **vise la feuille de service** (en tant que titulaire de la fonction, non parce qu'il est état-major), désigne les rédacteurs de la feuille de son équipage et déclare l'accostage et l'appareillage ; le COMANAV signe le prêt à appareiller |
| Ce qu'il voit | Les services de sa fonction |
| Ce qu'il ne peut pas faire | Écrire dans un service dont le commandant adjoint n'est pas configuré |
| Cible 🔵 | Le COMAEQ ou son suppléant habilité approuve et publie les listes et décide des échanges de tours (écarts A2 et A3) ; suppléance générale non développée (B1) |
| Où dans le guide | Feuille de service ; prêt à appareiller |

## Commandant en second (niveau 6)

| Rubrique | Contenu |
|---|---|
| Qui | Vision globale ; suppléant du commandant |
| Ce qu'il fait 🟢 | Voit tout le bâtiment ; publie des annonces sur son bâtiment ; supplée le commandant pour la validation de la relève ; atteint par défaut le seuil d'activation des modules |
| Ce qu'il ne peut pas faire | **Son écriture n'est pas héritée de son grade** : ses actions passent par des responsabilités attribuées et des circuits explicites ; il ne gère aucun compte |
| Écart | Même acte refusé par l'interface de programmation et accepté par l'écran (A4) ; qui attribue ses responsabilités reste à confirmer (B2) |

## Commandant (niveau 7)

| Rubrique | Contenu |
|---|---|
| Qui | Commandement du bâtiment ou de l'équipage |
| Ce qu'il fait 🟢 | Gère les comptes jusqu'au niveau état-major ; active ou désactive des modules ; propose la relève ; valide l'organisation d'alerte ; gère les listes de son bâtiment au titre de la supervision. Si le poste de COMAEQ est vacant, **lui seul** peut viser la feuille de service de son équipage, de façon tracée et signalée |
| Ce qu'il ne peut pas faire | Agir hors de son bâtiment |

## Administrateur d'unité (niveau 8)

| Rubrique | Contenu |
|---|---|
| Qui | Administre la plateforme et le bâtiment |
| Ce qu'il fait 🟢 | Crée les comptes, règle les seuils et les modules, modifie la structure, réinitialise les mots de passe, désigne les titulaires de fonctions (le COMAEQ, par exemple) |
| Règle validée 🔵 | **Aucun visa métier** : il désigne les titulaires sans viser à leur place |
| Écart | Dans l'état B, son niveau lui fait atteindre les seuils par défaut des actes métier : il peut trancher des échanges et publier des listes (écart A1) |

## Administrateur général (niveau 9)

| Rubrique | Contenu |
|---|---|
| Qui | Seul niveau multi-bâtiments ; équivalent du superutilisateur |
| Ce qu'il fait 🟢 | Administre toute la flotte ; règle les référentiels communs (grades, spécialités, rôles disponibles) ; seul à régler les actions de portée flotte |
| Particularité | Hors de ce rôle, on n'agit que sur les comptes de son propre bâtiment |

## Soutien à terre et équipage à terre

Le **soutien à terre** (responsable de classe ou de spécialité sans bâtiment) consulte et commente ; il n'écrit que dans les circuits prévus, **sans aucun droit automatique sur le bord**, quel que soit son grade. L'**équipage à terre** lit son bâtiment en lecture seule et tient sa propre feuille de service.
