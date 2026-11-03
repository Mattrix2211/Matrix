# Matrice de permissions — modules sans service

Statut : **proposition pour arbitrage**. Aucun droit n'est modifié par ce document ni par le code de cette étape.
Sources : code de Matrix (seuils du registre `matrix/core/role_thresholds.py`, services de chaque module),
Notion « Organigramme et rôles » (fait foi sur les responsabilités). Le Guide du marin 2023 n'est pas disponible
dans mon environnement : rien n'est recoupé avec lui.

## 1. Règles de lecture

- **Niveaux de rôle** : 1 Équipier, 2 Chef de section, 3 Chef de secteur, 4 Chef de service, 5 Commandant adjoint
  (rôle `ETAT_MAJOR`), 6 Commandant en second, 7 Commandant, 8 Administrateur du bâtiment, 9 Administrateur général.
- **Fonction** (COMANAV, COMOPS, COMAEQ, COMAVIA) : attribut du marin de niveau 5. Il ne donne pas de droit par son
  seul intitulé ; le rattachement des services (`Service.commandant_adjoint`) le fait.
- **Équipage à terre** : lecture seule dans tous les modules (déjà appliqué par le middleware).
- Colonnes : **L** lecture, **C** création, **M** modification, **V** validation, **P** publication.
  « — » = l'action n'existe pas dans le module. « Seuil » = valeur par défaut du registre, réglable.
- « Actuel » décrit le code **aujourd'hui** ; « Proposé » ne s'applique qu'après votre arbitrage.

## 2. Constat transversal

Le niveau 5 franchit tous les seuils ≤ 5 et son périmètre est le bâtiment entier. Ces modules ne portent pas de
service **propriétaire** unique : le bornage par `Service.commandant_adjoint` ne s'y applique donc pas tel quel.
Pour chacun, la question est : *quel objet métier le COMA modifie-t-il, et à qui appartient-il ?*

| Module | Objet porte-t-il un service ? | Conséquence |
|---|---|---|
| Tâches | Non (une personne assignée) | Périmètre = marins de la chaîne de l'attribuant |
| Formations | Non (fiche globale partagée) | Droits par personne et par session |
| Documents | Oui, optionnel (bâtiment, service, secteur, section) | Bornable par service cible |
| RETEX | Non (bâtiment) ; **domaine** avec COMA référent | Bornable par domaine |
| Programme | Oui, optionnel | Événement bâtiment = coordination ; événement de service bornable |
| Absences | Non (une personne) | Périmètre = marins de la chaîne |
| Déplacement calendrier | **Oui pour tickets et occurrences** | Voir risque R1 |
| Postes | Oui, optionnel | Bornable par service cible |

## 3. Matrice par module

### 3.1 Tâches (seuil `tache_attribution` = chef de section, 2)

| Fonction / rôle | Actuel | Proposé |
|---|---|---|
| Équipier | L, C, M ses tâches et celles où il est participant | Inchangé |
| Chef de section, secteur, service | L équipe ; C/M attribuer et réaffecter dans son périmètre hiérarchique | Inchangé |
| COMANAV, COMOPS, COMAEQ | L et attribuer à **tout le bâtiment** | L bâtiment ; attribuer aux marins des services rattachés, plus aux chefs de service de tout le bâtiment pour une demande de coordination |
| COMAVIA | Idem | Attribuer à son personnel aviation |
| Commandant, second | Idem | Inchangé |
| V / P | — | — |

Risque : un COMAEQ peut charger directement un marin du service d'un autre COMA, sans passer par son chef de service.
Restriction proposée : attribution directe aux marins des services rattachés ; vers un autre service, passage par le
chef de service concerné (la tâche lui est adressée, il la réattribue).

### 3.2 Formations (création `ADMIN_NAVIRE` ; validation, prérequis, places `CHEF_SECTION` ; proposition bord `CHEF_SECTEUR` ; validation bord `CHEF_SERVICE`)

| Fonction / rôle | Actuel | Proposé |
|---|---|---|
| Équipier | L ses formations ; demande/candidature | Inchangé |
| Chef de section / secteur | M prérequis, affecter des marins, valider (niveau hiérarchie) ; proposer une formation de bord (secteur) | Inchangé |
| Chef de service | V formation de bord | Inchangé |
| COMANAV, COMOPS, COMAEQ, COMAVIA | Toutes les actions du chef de service, bâtiment entier | V des formations de bord et des candidatures de **leurs services** ; L bâtiment ; pas de V sur le personnel d'un autre COMA |
| Commandant, second | Inchangé | Inchangé |
| Référent formation du bâtiment (BRH) | Désignation existante | Inchangé |

Risque : la fiche de formation est globale (portabilité entre navires) ; la restriction ne porte donc que sur les
**validations de personnes** (candidatures, qualifications), pas sur la fiche.

### 3.3 Documents (rédaction `CHEF_SECTION` ; validation/publication/archivage `CHEF_SERVICE` ; cible = nœud de périmètre)

| Fonction / rôle | Actuel | Proposé |
|---|---|---|
| Équipier | L documents de son périmètre | Inchangé |
| Chef de section / secteur / service | C/M dans son nœud ; chef de service : V, P | Inchangé |
| COMANAV, COMOPS, COMAEQ, COMAVIA | C/M/V/P sur tout nœud du bâtiment | C/M/V/P sur les nœuds de leurs services **et** sur le nœud bâtiment ; L partout. Un document d'un service d'un autre COMA : C en proposition, V par le COMA compétent |
| Commandant, second | Inchangé | Inchangé |

Le circuit proposer → valider → publier existe déjà : la restriction consiste à router la validation vers le COMA
du service cible (règle déjà utilisée pour les fiches de maintenance).

### 3.4 RETEX (validation `CHEF_SERVICE` ; domaines avec COMA référent)

| Fonction / rôle | Actuel | Proposé |
|---|---|---|
| Tout marin | C un RETEX, L les RETEX du bâtiment | Inchangé |
| Chef de service | V (refuser, clore, décider les actions) | V sur les RETEX de ses services seulement |
| COMA | V tous les domaines (le COMA référent passe seulement en premier dans la liste des valideurs) | V les domaines dont il est **référent** ; L les autres ; V d'un autre domaine par délégation explicite |
| Commandant, second | V tout | Inchangé |

Risque faible, mais la liste « valideurs » ne tient pas lieu de règle : n'importe quel niveau ≥ 4 valide aujourd'hui
n'importe quel domaine.

### 3.5 Programme du bâtiment (saisie `ETAT_MAJOR` ou délégation `DelegationProgramme` ; types `ADMIN_NAVIRE`)

| Fonction / rôle | Actuel | Proposé |
|---|---|---|
| Tout marin | L | Inchangé |
| COMA | C/M/P tout événement, bâtiment et services, et délégation du droit | C/M/P événements du **bâtiment** (escales, arrêts techniques, exercices : coordination) et de leurs services ; événement d'un service d'un autre COMA : proposition |
| Délégataire | C/M selon sa cible | Inchangé |
| Types d'événements | Admin du bâtiment | Inchangé |

Le mécanisme de délégation existe déjà pour ce module (modèle de délégation par marin) : c'est le gabarit à
généraliser pour la « délégation explicite ».

### 3.6 Absences (gestion et validation `CHEF_SECTION` + marin dans le périmètre)

| Fonction / rôle | Actuel | Proposé |
|---|---|---|
| Marin | C sa propre absence ; L la sienne | Inchangé |
| Chef de section / secteur / service | V, M les absences des marins de son périmètre | Inchangé |
| COMA | V/M les absences de **tout** le bâtiment | V/M celles de ses services et des chefs de service ; L les autres (utile à la coordination) |
| Commandant, second | Inchangé | Inchangé |

Les données d'absence sont sensibles (motif) : à lire par le COMA en vue « disponibilité » sans le motif pour les
services qui ne sont pas les siens.

### 3.7 Déplacement des événements du calendrier

| Type d'événement | Actuel | Proposé |
|---|---|---|
| Personnel | Son propriétaire seulement | Inchangé |
| Occurrence de maintenance | Assigné ; sinon niveau ≥ 2 **et** périmètre. Pas de contrôle du service rattaché | Même règle que la maintenance : COMA seulement sur ses services rattachés (voir R1) |
| Ticket correctif | Niveau ≥ 2 et périmètre. Pas de contrôle du service rattaché | Idem |
| Session de formation | Niveau ≥ 2 et affectation personnelle | Inchangé |

### 3.8 Postes du bord (`poste_gestion` = chef de service)

| Fonction / rôle | Actuel | Proposé |
|---|---|---|
| Marin | L son poste | Inchangé |
| Chef de service | C/M postes et affectations dans son nœud | Inchangé |
| COMA | C/M postes et affectations sur tout nœud, y compris les services des autres COMA | Sur les services rattachés ; ailleurs, proposition au chef de service |
| Affectation à un poste exigeant des formations | Contrôlée | Inchangé |

## 4. Risques identifiés

| # | Risque | Gravité | Module |
|---|---|---|---|
| R1 | **Un COMA peut replanifier l'occurrence ou le ticket d'un service qui n'est pas le sien** via le glisser-déposer du calendrier. Ces deux objets portent un service : la règle déjà validée (écriture bornée aux services rattachés) devrait s'y appliquer. C'est un trou de la clôture, pas un module « sans service » | Moyenne | Calendrier |
| R2 | Attribution directe d'une tâche à un marin d'un autre COMA | Moyenne | Tâches |
| R3 | Validation d'absences et de candidatures de personnel d'un autre service | Moyenne | Absences, Formations |
| R4 | Validation d'un document ou d'un RETEX hors de son domaine | Faible | Documents, RETEX |
| R5 | Création de postes dans un service tiers | Faible | Postes |
| R6 | Programme : aucun risque d'écriture concurrente tant que l'événement est bâtiment | Faible | Programme |

## 5. Restrictions proposées, par ordre de priorité

1. **R1 (recommandé tout de suite, hors arbitrage « transverse »)** : appliquer au déplacement calendrier des
   occurrences et tickets le contrôle `niveau_ecriture_sur`, comme dans le reste de la maintenance. Ce n'est pas un
   droit transversal : ces objets ont un service. Je ne le fais pas sans votre accord explicite.
2. Documents, postes, programme de service : borner la **cible** (nœud) aux services rattachés, hors nœud bâtiment.
3. Absences et formations : borner la **validation de personnes** aux services rattachés ; garder la lecture.
4. RETEX : valider seulement les domaines dont le COMA est référent.
5. Tâches : attribution directe aux services rattachés ; coordination vers un autre service via son chef.

Rien n'est bloqué avant votre choix. Chaque restriction serait livrée avec des tests positifs et négatifs par
fonction (COMANAV, COMOPS, COMAEQ, COMAVIA), par chef de service, chef de secteur, et par équipage A/B.

## 6. Délégation explicite

Pour les cas où un COMA doit agir sur un service qui n'est pas le sien (absence d'un collègue, coordination
ponctuelle) :

- **Option 1 (recommandée)** : généraliser `DelegationProgramme` en une délégation par marin, **service**, module et
  date de fin, accordée par le commandant ou le commandant en second, tracée dans l'`AuditLog`. Un modèle, aucun
  système parallèle de rôles.
- **Option 2** : rattacher temporairement le service au COMA (`Service.commandant_adjoint`), plus simple mais elle
  masque la délégation dans la configuration et change aussi la validation.

## 7. Services sans commandant adjoint (décision validée)

Lecture seule par défaut pour les commandants adjoints lorsqu'aucun rattachement n'est configuré. Garde-fous :

- Les **chefs de service, chefs de secteur, chefs de section** (niveaux 2 à 4) ne sont **pas** concernés : leur
  écriture reste bornée à leur périmètre, comme avant.
- Le commandant, le second et les administrateurs gardent leurs droits.
- Une délégation explicite (§6) pourra rouvrir l'écriture pour un COMA donné.
- Tests déjà en place : `test_ecriture_commandants_adjoints` (chef de service et chef de secteur de la Navigation
  écrivent ; COMANAV, COMOPS, COMAEQ écrivent seulement sur leurs services ; état-major sans fonction : lecture).

## 8. Questions pour le PO

1. Appliquer R1 maintenant (calendrier occurrences et tickets) ?
2. Valider l'ordre de priorité du §5, module par module.
3. Absences : le COMA voit-il le motif des services qui ne sont pas les siens ? (je propose non.)
4. Délégation : option 1 ou 2 ? Qui l'accorde (commandant, second) ?
5. RETEX : le COMA référent est-il seul valideur de son domaine, ou le chef de service concerné aussi ?
