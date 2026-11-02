# Droits du COMAEQ — état des lieux et matrice à arbitrer

Statut : **proposition pour arbitrage**. Aucun droit n'est modifié par ce document.
Sources : Notion « Organigramme et rôles » (fait foi), code de Matrix, mesures sur la base de démonstration.
Le Guide du marin 2023 n'est pas disponible dans mon environnement : les responsabilités ci-dessous sont
celles de Notion et n'ont pas été recoupées avec le guide.

## 1. Responsabilités exactes (Notion)

| Fonction | Responsabilité |
|---|---|
| COMAEQ | Vie à bord, service courant, coordination du personnel à quai, adjoint protection, conduite nautique en liaison avec le COMOPS |
| COMANAV | Conservation du bâtiment et des équipements, adjoint sécurité, gestion technique des matériels, logistique opérationnelle |
| COMOPS | Opérations, conduite des opérations, activité à la mer, comptes rendus opérationnels |
| COMAVIA | Aviation et sécurité aérienne (unités concernées) |

Règles de fond posées par Notion :

- La fonction est **attribuée à une personne**, elle ne donne pas de permission générale par son seul intitulé.
- **Chaque service est rattaché au commandant adjoint réellement compétent** ; les workflows résolvent ce
  rattachement au lieu d'utiliser « état-major » ou un commandant adjoint générique.
- Double équipage : deux équipages en miroir, chacun avec sa chaîne ; l'équipage à terre garde un accès adapté.
- Le grade, l'appartenance à l'unité et les droits sur d'autres unités sont trois notions distinctes.

## 2. Règles actuelles dans Matrix

### Comment un COMAEQ est reconnu

Un marin de rôle `ETAT_MAJOR` (niveau 5) dont la fonction est `COMAEQ`. Le rattachement d'un service à son
commandant adjoint est porté par `Service.commandant_adjoint`.

### Ce qu'il obtient aujourd'hui, par construction

1. **Périmètre bâtiment entier.** Son profil n'a ni service, ni secteur, ni section : son périmètre est le
   bâtiment, donc toutes les données de tous les services.
2. **Niveau 5.** Il franchit tous les seuils d'action fixés à 5 ou moins (tableau ci-dessous).

C'est exactement l'« accès global parce qu'il est COMAEQ » que vous ne voulez pas figer : le **niveau
d'état-major**, commun au COMAEQ, au COMOPS, au COMANAV et au COMAVIA, ouvre les mêmes actions à tous.

### Actions ouvertes par le seul niveau 5 (seuils par défaut ≤ 5)

| Domaine | Actions concernées (extrait du registre) |
|---|---|
| Matériels, installations | Créer ou modifier ; supprimer (seuil 4) ; gérer les tâches d'entretien ; rattachement parent/enfant ; configurer les ponts |
| Maintenance | Créer ou modifier occurrences, plans et exécutions ; exécuter la maintenance d'un tiers ; corriger un compte rendu terminé |
| Fiches de maintenance | Rédiger ou proposer une version ; proposer une fiche flotte |
| Logistique | Gérer le stock de pièces |
| Quarts et services | Publier une liste (seuil 4) ; configurer les rubriques de la feuille de service |
| Feuille de service | Viser comme chef de secteur ou de service (seuils 3 et 4) |
| Tâches, annonces, programme | Attribuer des tâches ; publier une annonce ; saisir le programme du bâtiment (seuil 5) |
| Documents, RETEX, postes | Rédiger, valider et publier un document ; valider un RETEX ; créer les postes du bord |

Actions **hors de portée** du niveau 5 : valider une modification de l'organisation sécurité/protection
(seuil 7), activer un module (6), modifier la structure de l'unité (8), réinitialiser un mot de passe (8),
gérer les grades et spécialités (9).

### Règles propres au COMAEQ déjà codées

| Règle | Portée |
|---|---|
| Visa final de la feuille de service et publication | Seul le titulaire de l'équipage de la feuille ; poste vacant : le commandant de cet équipage |
| Désignation des rédacteurs de la feuille | COMAEQ de l'équipage, pour son équipage seulement |
| Correction d'en-tête et renvoi au rédacteur (nouveau) | Même autorité que son visa, aux paliers de visa ; correction légère seulement |
| Visa des circuits routés par service | Le titulaire du commandant adjoint dont dépend le service concerné |

Ces règles sont déjà **fines** (par équipage, par service routé). Le défaut se situe dans les droits
d'écriture par seuil, qui sont **larges**.

### Mesure sur la base de démonstration

Le COMAEQ de démonstration est de niveau 5 avec un périmètre « bâtiment » : il voit les quatre services du
bâtiment dans ses filtres (mesuré) et, d'après les seuils, peut écrire dans les domaines ci-dessus pour chacun
d'eux, y compris des services rattachés au COMANAV ou au COMOPS (déduit du registre, à vérifier par tests).

## 3. Matrice proposée (à arbitrer)

Principe proposé : **lecture large, écriture et validation bornées à la responsabilité**.

- **Lecture** : le bâtiment, pour la transparence du commandement, hors données sensibles (RH, médical).
- **Création et modification** : les services rattachés à sa fonction, plus ses domaines propres
  (service courant, feuille de service, vie à bord, quai).
- **Validation** : les circuits dont il est le commandant adjoint compétent (routage par service).
- **Équipage** : toujours limité à son équipage pour écrire ; l'équipage à terre lit seulement.

| Domaine | Lecture | Création | Modification | Validation |
|---|---|---|---|---|
| Feuille de service | Bâtiment, son équipage | Non (rédacteur désigné) | Correction légère tracée, son équipage | Visa final, renvoi : oui |
| Quarts, tours de service, quai | Bâtiment | Oui (service courant) | Oui | Publication : oui |
| Tâches | Bâtiment | Pour ses services et son équipage | Idem | — |
| Maintenance préventive | Bâtiment | Services rattachés à COMAEQ | Idem | Visa des fiches de ses services |
| Maintenance corrective, tickets | Bâtiment | Services rattachés | Services rattachés | Clôture : services rattachés |
| Matériels, installations | Bâtiment | Services rattachés | Services rattachés | Fiches : visa si COMAEQ compétent |
| Anomalies | Bâtiment | Tout marin signale | Services rattachés | Traitement : services rattachés |
| Annonces | Bâtiment | Oui (bâtiment) | Les siennes | — |
| Programme du bâtiment | Bâtiment | Oui | Oui | — |
| Personnel, annuaire | Selon son périmètre | Non | Non | — |
| Organisation sécurité/protection | Bâtiment | — | — | Hors niveau 5 (seuil 7) |
| Documents, RETEX | Bâtiment | Oui | Les siens | Si commandant adjoint compétent |

## 4. Points d'arbitrage

1. **Écriture bornée aux services rattachés ?** C'est le cœur du sujet. Aujourd'hui, un COMAEQ écrit dans
   tous les services. La matrice ci-dessus le limite à ceux où `Service.commandant_adjoint = COMAEQ`.
2. **Services sans rattachement configuré** : aucun commandant adjoint ne les couvre. Proposition : lecture
   seule pour tous les états-majors, écriture réservée au commandant et à l'administrateur de l'unité, avec
   un avertissement visible.
3. **Domaines propres au COMAEQ** (service courant, quai, vie à bord) : confirmer qu'ils couvrent bien les
   quarts, les tours de service, la feuille de service et le programme, et rien d'autre.
4. **Lecture bâtiment pour tous les états-majors** : confirmer, ou la limiter aux services rattachés.
5. **Suppression** : un COMAEQ peut-il supprimer dans ses services (seuil 4 aujourd'hui), ou seulement archiver ?
6. **Rôle `ETAT_MAJOR` commun** : le garder pour les quatre fonctions, avec des droits qui dépendent de la
   fonction, ou séparer les rôles. Je recommande de garder le rôle et de faire dépendre les droits de la
   fonction et du rattachement des services : c'est ce que dit Notion, sans nouveau modèle.

## 5. Mise en œuvre envisagée (après arbitrage)

Aucun nouveau système parallèle : on étend `RolePermission` et `scope_filters_for_user`, avec un périmètre
« services rattachés à ma fonction » pour les états-majors. Chaque domaine du tableau reçoit des tests
d'accès autorisé et interdit, équipage A et équipage B compris. Rien n'est figé avant votre réponse.
