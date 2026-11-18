<!-- couvre: diffusable/16_preparation_appareillage.md | Chapitre 16 — Préparation à l'appareillage -->
<!-- couvre: diffusable/16_preparation_appareillage.md | 16.1 Ce que Matrix ne dit pas -->
<!-- couvre: diffusable/16_preparation_appareillage.md | 16.2 Aujourd'hui 🟢 — une session datée, une liste de points -->
<!-- couvre: diffusable/16_preparation_appareillage.md | Pour le marin -->
<!-- couvre: diffusable/16_preparation_appareillage.md | Les quatre familles de points -->
<!-- couvre: diffusable/16_preparation_appareillage.md | Pour le chef -->
<!-- couvre: diffusable/16_preparation_appareillage.md | 16.3 Ce que Matrix ne contient pas encore 🔵 -->
<!-- couvre: diffusable/16_preparation_appareillage.md | 16.4 Interactions avec les autres modules -->
<!-- couvre: diffusable/16_preparation_appareillage.md | 16.5 Cas particuliers -->
<!-- couvre: diffusable/16_preparation_appareillage.md | 16.6 Limites et éléments non vérifiés -->
<!-- partie: Modules -->
# Préparation à l'appareillage

<div class="ligne-public"><b>Public :</b> marins, responsables, développeurs · <b>Ce que vous y trouverez :</b> ce que Matrix propose aujourd'hui pour préparer un départ (une session datée, une liste de points de vigilance à cocher, une signature de clôture), ce que Matrix **ne fait pas** (autoriser l'appareillage), et le circuit **cible** décidé par le PO — présentés séparément</div>

**Écran de référence :** [[GU:13_parcours_appareillage]] (captures de l'état B sur une instance de démonstration).

## Ce que Matrix ne dit pas

> **Matrix est un outil de suivi de la préparation. Il ne délivre pas l'autorisation réelle d'appareiller.**

**Matrix ne délivre pas l'autorisation opérationnelle d'appareiller** (`DEC-APP-13`, décision du PO). La session d'appareillage **atteste qu'une préparation a été menée et clôturée**, pas que le bâtiment est apte à appareiller. Le code le précise : la signature **atteste la clôture de la session**, pas l'aptitude du bâtiment (⚪ l'affichage de cette précision à l'écran n'a pas été vérifié).

## Aujourd'hui 🟢 — une session datée, une liste de points

![Appareillage actuel](../schemas/svg/S32_appareillage_reel.svg)

### Pour le marin

> Exemple fictif : le matelot Durand, avant un départ.

1. Il ouvre **« Prêt à appareiller »** (accessible à **tout marin du bâtiment**, dans le menu).
2. S'il y a une **session ouverte**, il voit la **liste de points à vérifier**, regroupés en quatre familles, avec une **barre de progression**.
3. Il **coche** un point qu'il a vérifié sur le terrain ; Matrix enregistre **qui** a coché et **quand**. Il peut **décocher**.
4. Il consulte l'**historique** des sessions déjà clôturées.

Les points ne sont pas saisis à la main : Matrix les **calcule une seule fois, à l'ouverture**.

### Les quatre familles de points

Sur les **installations critiques** du bâtiment :

| Famille | Ce qui déclenche un point |
|---|---|
| **Essai ou relevé en attente** | Une maintenance non terminée d'une installation critique (triée par échéance) |
| **Relevé technique manquant ou ancien** | Heures de marche, vibration ou isolement non à jour |
| **Dérive détectée non résolue** | Une alerte de dérive ([[RF:11_fiche_materiel_installations]]) encore active |
| **Pièce de stock sous seuil** | Une pièce de stock au-dessous de son seuil minimal ([[RF:13_fiche_logistique]]) |

La liste est **figée** : même si la situation évolue pendant la préparation, **l'état constaté à l'ouverture reste la référence**. Une session sans point est possible (« aucun point de vigilance détecté »).

### Pour le chef

| Action | Qui (état B) | Règle |
|---|---|---|
| Cocher un point | Tout marin du bâtiment (à bord) | Session encore ouverte ; le **commandant en second consulte sans cocher ni signer** |
| **Ouvrir** une session | **Chef de secteur ou plus** | **Une seule session ouverte par bâtiment** |
| **Signer et clôturer** | **Chef de secteur ou plus** | **Confirmation explicite** obligatoire ; sans elle, rien n'est enregistré et le refus est tracé |

Une fois signée, la session est **clôturée et figée** : plus aucune modification. La signature enregistre **le signataire et la date** et est **auditée**. L'**administrateur général** n'ouvre pas de session (il n'est rattaché à aucun bâtiment) mais consulte l'historique de toute la flotte.

L'équipage **à terre** ne voit pas les points issus des occurrences de maintenance (hors commandement).

## Ce que Matrix ne contient pas encore 🔵

![Appareillage cible](../schemas/svg/S33_appareillage_cible.svg)

Décisions du PO (dossier V1.2) :
- `DEC-APP-01` : chaque départ génère des **contrôles à partir de fiches de référence applicables**.
- `DEC-APP-02` : circuit **section ou secteur → service → COMANAV**.
- `DEC-APP-14` (**principe validé par le PO, conservé comme fonctionnement cible**) : le **chef de secteur propose** les contrôles et leur classification (**obligatoire**, **critique**) ; le **chef de service examine** la proposition ; le **COMANAV approuve le référentiel**, y compris les contrôles obligatoires et critiques. ⚪ La compatibilité avec les procédures opérationnelles du bord **n'est pas vérifiée** : à confirmer avant tout développement (lot L23).
- `DEC-APP-03`, `DEC-APP-04`, `DEC-APP-05`, `DEC-APP-06`, `DEC-APP-07`, `DEC-APP-08`, `DEC-APP-09` : une modification de référence suit **son propre circuit d'approbation** ; les préparations ouvertes sont **actualisées** (réponses toujours valables conservées, contrôles modifiés ou ajoutés **rouverts**, supprimés **archivés**, signatures affectées **invalidées**) ; les préparations clôturées **gardent leur version historique**.
- `DEC-APP-10`, `DEC-APP-12` : les contrôles obligatoires sont traités **avant validation** ; un contrôle **critique non dérogeable ne se contourne pas**.
- `DEC-APP-11` : une **réserve** est explicite, justifiée et tracée, dans les limites des règles de sécurité.

| | Aujourd'hui | Cible |
|---|---|---|
| Origine des contrôles | **Calculés** à partir de l'état de l'installation critique | **Fiches de référence** approuvées |
| Classification | Aucune (tous équivalents) | Obligatoire, critique, non dérogeable |
| Circuit de signature | **Une** signature : chef de secteur ou plus | Section/secteur → service → **COMANAV** |
| Réserves | Absentes | Explicites, justifiées, tracées |
| Évolution d'une référence | Sans objet | Actualisation, réouverture, invalidation |
| Autorisation d'appareiller | **Jamais délivrée par Matrix** | Idem (`DEC-APP-13`) |

⚪ **À confirmer.** Qui, concrètement, valide la **classification** « critique » et comment elle s'accorde aux procédures du bord (`DEC-APP-14`) — aucune règle n'est inventée ici.

## Interactions avec les autres modules

| Module | Lien |
|---|---|
| Installations critiques ([[RF:11_fiche_materiel_installations]]) | Source des points : relevés, critique |
| Maintenance ([[RF:12_fiche_maintenance]]) | Occurrences non terminées, dérives |
| Logistique ([[RF:13_fiche_logistique]]) | Pièces sous seuil |
| Formations ([[RF:14_fiche_formations]]) | Cible : qualifications des postes critiques |
| Accueil, pilotage ([[RF:06_fiche_accueil_pilotage]]) | Entrée « Prêt à appareiller » |
| Quarts ([[RF:08_fiche_quarts_services_feuille]]) | ⚪ Le mode du bâtiment (mer/quai) n'intervient pas dans l'ouverture d'une session |

## Cas particuliers

- **Session déjà ouverte** : l'ouverture d'une seconde est refusée avec un message.
- **Aucun bâtiment associé** au profil : l'ouverture est impossible.
- **Commandant en second** : consulte uniquement (voir le registre des points « à confirmer », B2).
- **Double équipage** : bornage par équipage appliqué aux occurrences.

## Limites et éléments non vérifiés

- 🟢 Tests de l'état B : `dashboard` (rejoués sur l'état B avec les six autres paquets de l'ensemble 3 : 1 491 tests OK, 1 ignoré ; rapport de lot conservé dans les archives).
- 🟢 L'écran « Prêt à appareiller » (sans session puis avec session ouverte) a été rejoué sur l'instance de démonstration le 16/11/2026 ; ⚪ le renseignement des contrôles et la signature n'ont pas été rejoués.
- ⚪ Aucune fiche de référence d'appareillage n'existe dans le code ; le cahier des charges et les pages Notion de procédures opérationnelles ne sont pas décrits comme existants.
- ⚪ Le lien entre le mode MER/QUAI et la préparation n'est pas établi.

**Sources (état B).** Décisions `DEC-APP-01`, `DEC-APP-02`, `DEC-APP-03`, `DEC-APP-04`, `DEC-APP-05`, `DEC-APP-06`, `DEC-APP-07`, `DEC-APP-08`, `DEC-APP-09`, `DEC-APP-10`, `DEC-APP-11`, `DEC-APP-12`, `DEC-APP-13`, `DEC-APP-14` (dossier V1.2). Références dans la partie restreinte du dossier.

## Écarts et décisions du registre

Les tableaux ci-dessous sont **générés depuis le registre central** : le statut et l'état de chaque entrée y sont tenus ; cette fiche n'en donne aucun autre. Une proposition 🟣 n'est pas une décision ; « non développée » signifie seulement que le lot correspondant n'est pas livré dans l'état B.

### Écarts, points à confirmer et propositions

@ecarts A17 B2 B4 D4

### Décisions du PO

@decisions DEC-APP-01 DEC-APP-02 DEC-APP-03 DEC-APP-04 DEC-APP-05 DEC-APP-06 DEC-APP-07 DEC-APP-08 DEC-APP-09 DEC-APP-10 DEC-APP-11 DEC-APP-12 DEC-APP-13 DEC-APP-14
