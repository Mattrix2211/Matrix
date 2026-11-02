# Modales, panneaux, pages — et lisibilité des quarts et tours de service

Statut : **propositions pour arbitrage**. Aucune modification profonde des quarts n'est faite.

## 1. Quand une modale, un panneau latéral ou une page

Règle de décision retenue, appliquée dans cette itération :

| Critère | Modale centrée | Panneau latéral | Page complète |
|---|---|---|---|
| Durée de l'opération | Quelques secondes | Une à deux minutes | Plusieurs minutes |
| Nombre de champs | 0 à 1 (motif) | 3 à 8 | Plus de 8, ou étapes |
| Besoin de voir la page derrière | Non | **Oui** | Non |
| Reprise après interruption | Inutile | Utile (saisie conservée) | Indispensable (brouillon) |
| Mobile | Plein écran | Plein écran | Natif |

### Application aux cas rencontrés

| Cas | Choix | Raison |
|---|---|---|
| Confirmer une suppression, un visa, une publication | Modale | Décision binaire, rapide ; focus sur l'action sûre |
| Annuler un élément publié (motif obligatoire) | Modale avec champ motif | Un seul champ ; l'erreur s'affiche sous le champ |
| Désigner ou retirer un rédacteur de la feuille | **Panneau latéral** | On garde la feuille sous les yeux ; liste et ajout dans le même écran |
| Attribuer une tâche, ajouter ma tâche personnelle | **Panneau latéral** | Plusieurs champs, mais la liste des tâches reste visible |
| Corriger l'en-tête d'une feuille (COMAEQ) | Bloc repliable dans la page | Les valeurs corrigées sont celles affichées à côté |
| Rédiger une fiche de maintenance, créer un plan | Page complète | Longs formulaires, étapes, brouillon |
| Signaler une anomalie | Page complète | Photo, localisation, description : saisie mobile guidée |
| Rédiger la feuille de service | Page complète | Document de référence, circuit de visa |

### Principes communs

- **Annuler et Échap ne perdent rien** : la page d'origine est intacte, le focus revient sur le bouton déclencheur.
- **L'erreur de saisie reste dans le contexte** : sous le champ concerné, jamais dans un message séparé.
- **Une erreur d'action ne vide pas le formulaire** : le message s'affiche dans le dialogue ou le panneau.
- **Pas de modale par défaut** : une action ordinaire et réversible s'exécute directement.

## 2. Quarts à la mer et tours de service à quai : lisibilité

### Constat sur la page actuelle (`quarts/liste_detail.html`)

- La fiche empile : en-tête, état, bouton d'impression, onglets, puis une grille « planning » où chaque
  créneau répète poste, horaires, marin, note, bouton d'échange et bouton de suppression.
- Les actions de chaque créneau (échanger, supprimer) occupent autant de place que l'information.
- Le planning en semaines ne distingue pas visuellement un quart à la mer (horaires) d'un tour à quai
  (fonction).
- Sur mobile, une semaine entière se lit en bloc : peu de repères pour savoir « quand je suis de service ».

### Règles métier à conserver

- Quarts à la mer **distincts** des tours de service à quai.
- Tableaux de quart imprimables par équipe.
- Aucun détail de quart injecté dans la feuille de service.
- Aucune gestion imposée des relèves internes des trois gradés de coupée.

### Proposition A — Liste lisible par jour (recommandée)

Une colonne principale « qui est de service quand », une colonne latérale « ce qui m'attend ».

| Zone | Contenu |
|---|---|
| Colonne principale | Un bloc par jour : date en tête ; quarts à la mer sous forme de **tableau horaire** (poste, horaires, marin) ; tours à quai sous forme de **liste par fonction** |
| Colonne latérale (collante) | Mon prochain tour ; mes actions en attente (échange à traiter) ; état de la liste (brouillon, proposée, publiée) |
| Actions | Regroupées dans un menu de ligne ou apparaissant au survol et au clavier ; jamais répétées en gros sur chaque créneau |
| Mobile | Colonne latérale en tête (« mon prochain tour »), puis une carte par jour |

Gain attendu (non mesuré, à confirmer sur prototype) : une ligne par créneau au lieu d'un bloc, donc moins de défilement, et
l'espace récupéré sert aux tableaux horaires.

### Proposition B — Vue par marin

Un tableau marins en lignes, jours en colonnes. Utile au chef de liste pour équilibrer la charge, moins pour
le marin. À proposer en **onglet supplémentaire**, pas en remplacement.

### Proposition C — Conserver la grille, alléger les actions

Le moins invasif : on garde la grille en semaines, on retire les boutons de chaque créneau au profit d'un
menu « ⋯ » et d'un panneau latéral de détail au clic. Gain moindre, risque minimal.

### Recommandation

A pour la lecture quotidienne, B en onglet pour le pilotage, avec un prototype et des captures à 1920, 1366
et 390 px **avant** toute généralisation. Je n'engage rien sans votre choix.

## 3. Questions pour le PO

1. Choisir entre A, B ou C pour les quarts et tours.
2. Valider la table de décision du §1 comme règle commune de Matrix.
3. Les tableaux de quart par équipe doivent-ils rester une impression séparée de l'écran, ou doit-on
   pouvoir imprimer directement la vue « par jour » ?
