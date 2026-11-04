# Mer / Quai — complément au plan technique : mode opérationnel du bâtiment

Statut : **proposition à relire par le PO**. Aucune migration liée au mode opérationnel global n'est écrite tant que ce document n'est pas validé.
Référence : `mer_quai_plan_technique.md` (état initial), commits `71d54ca` à `0b26107` (étapes 1 à 6).

## 0. Ce qui est décidé, fait, en cours, en attente

| Sujet | État |
|---|---|
| Activation par le chef de liste, publication prévisionnelle, conflits, alertes H−30/H/H+15, mouvements, échanges différés, terminaison automatique | **Terminé** (étapes 1 à 6) |
| Repli de l'escalade et de l'alerte d'accostage vers le commandant en second (CSD), supervision seulement | **Terminé** (voir §1) |
| Report et retrait de la prévision réservés au chef de liste désigné | **Terminé** (le commandant, le COMAEQ et le CSD sont refusés ; tests) |
| États d'échange visibles (demandé, validé en attente, appliqué, bloqué + motif) et résolution d'un échange bloqué | **Terminé** |
| Mode opérationnel MER / QUAI du bâtiment | **Proposé ici**, en attente de relecture |
| Remplaçant temporaire du chef de liste | **Proposé ici** (§5.2), en attente de décisions |
| Écran de configuration des délais | **Matrice proposée ici** (§5.1), écran non ouvert |
| Régularisation d'un quart à la transition | **Proposition de procédure** (§5.3), aucun code, pas de GO |
| Vues A/B adaptées au mode | **À faire** après validation du modèle (la partie sans dépendance au mode peut avancer) |
| Stades d'alerte, mouillage, organisations particulières | **Hors périmètre V1.1** (le modèle reste extensible, §2.4) |

## 1. Analyse des six étapes au regard du nouvel état MER / QUAI

| Élément existant | Constat | Adaptation |
|---|---|---|
| `MouvementBatiment` (accostage / appareillage, auteur, fonction, heure effective, heure de saisie, annulation motivée, remplacement) | Il porte déjà la chronologie qui détermine le mode. `regime_du_batiment()` en déduit « QUAI » ou « MER » du dernier mouvement valide. | Le réutiliser comme **source unique** du mode (§2). Ajouter l'ancien et le nouveau mode figés sur chaque mouvement, et un mouvement d'initialisation. |
| Contrôle de chronologie (alternance, pas de date future) | Suffisant pour deux modes. | Aucun changement ; il s'appuie sur le mode au lieu du type. |
| Alertes d'accostage | Déjà distinguées (aucune liste / prévisionnelle non activée), persistantes au report. | Repli COMAEQ vacant → **CSD** (fait). Déclenchement inchangé : mouvement valide de type accostage. |
| Alertes d'activation (rappel, alerte, escalade) | Indépendantes du mode. | Repli CSD (fait). Rien d'autre. |
| Activation d'une liste à quai | Aujourd'hui possible quel que soit le régime du bâtiment. | **Décision D2** : l'autoriser seulement en mode QUAI, ou aussi à la mer pour préparer ? |
| Conflits à l'activation | Comparent des intervalles bruts, sans tenir compte du régime. Une journée de transition peut donc produire un faux conflit. | Comparer les **intervalles effectivement applicables** par mode (§3.1). |
| Prédicat « créneau en vigueur » (`applicables()`) | Tient compte de l'application et de la prise d'effet, pas du mode. | Reste valable pour les listes à quai ; les quarts reçoivent un prédicat équivalent par mode. |
| Échanges prévisionnels | Conformes aux décisions. | Seule l'interface est complétée (fait) : états visibles, motif du blocage, nouvelle tentative, abandon motivé. |
| Calendrier, iCal, journée, équité, passation | Distinguent déjà prévisionnel et en vigueur. | Ajouter la priorité d'affichage selon le mode (§3.3), sans masquer l'autre mode. |

## 2. Modèle de mode opérationnel proposé

### 2.1 Principe : le mode est un résultat, pas un champ libre
Chaque bâtiment a **un mode courant unique** (`MER` ou `QUAI`), **déduit de la chronologie des mouvements confirmés** et non saisi directement. Raison : un champ « mode » sur le bâtiment pourrait diverger de l'historique, ne permettrait pas de corriger un mouvement sans réécrire le passé et ne dirait pas quel était le mode à une heure donnée.

- Appareillage confirmé → mode `MER`. Accostage confirmé → mode `QUAI`.
- Le programme (appareillage ou accostage prévus) **n'a aucun effet** sur le mode ; il sert à anticiper.
- Le mode est indépendant des listes : publier ou activer une liste ne change jamais le mode, et changer de mode n'active jamais une liste.

### 2.2 Données ajoutées à `MouvementBatiment`
- `mode_avant`, `mode_apres` : figés à l'enregistrement (audit « ancien mode / nouveau mode »). Vides si le mode précédent était inconnu.
- Un type **`INITIALISATION`** : déclare explicitement le mode de départ d'un bâtiment (valeur vérifiée, auteur, fonction, motif obligatoire). Même habilitation que les autres mouvements (COMAEQ ou commandant à bord) et mêmes contrôles de traçabilité.
- Rien d'autre : pas de champ sur `Ship`, pas de table supplémentaire pour la V1.1.

### 2.3 Lecture du mode (API interne)
- `mode_du_batiment(ship, instant=None)` : mode à un instant donné (courant par défaut) ; `None` si inconnu.
- `intervalles_par_mode(ship, debut, fin)` : découpage d'une plage horaire en intervalles `MER` / `QUAI` / `inconnu`.
- Les consommateurs (quarts, listes, calendrier, accueil, notifications) n'interrogent **que ces fonctions**, jamais le type de mouvement. Un futur mode ne change donc que ces deux fonctions.

### 2.4 Évolutivité (sans rien implémenter)
Trois axes indépendants, chacun avec sa propre chronologie historisée selon le même patron :
1. **Situation du bâtiment** : MER / QUAI aujourd'hui (le mouillage s'y ajoutera sans toucher aux autres axes).
2. **Stade d'alerte** : futur, table distincte ; aucune règle SA déduite de la situation.
3. **Organisation de service** : futur, table distincte (postes tenus, équipes mobilisées).

Aucun de ces deux derniers axes n'est créé, ni anticipé dans le schéma.

## 3. Impacts

### 3.1 Quarts, listes et conflits
- Un **quart publié** reste applicable pendant sa période de validité et dans le régime MER. Un quart futur n'est jamais affiché « en cours » : « en cours » = mode MER ET heure comprise dans le créneau.
- **Conflit** = recouvrement de deux créneaux d'un même marin **à l'intérieur d'un même intervalle de régime**. Un quart avant l'accostage et un service après l'accostage, le même jour, ne sont pas un conflit.
- **Décision D3** : pour un recouvrement au-delà de l'horizon confirmé (aucun mouvement ne couvre encore la période), proposer un **avertissement non bloquant** « à confirmer lors de la transition », réévalué à chaque mouvement, plutôt qu'un blocage.
- Les 30 chevauchements historiques restent conservés ; le diagnostic reste en lecture seule ; la nouvelle règle ne réécrit aucune affectation passée.

### 3.2 Échanges
Aucun changement de circuit ni d'autorisation. Les contrôles d'application utilisent déjà les créneaux en vigueur ; ils utiliseront les intervalles par mode quand le modèle sera validé.

### 3.3 Calendrier, accueil, notifications, vues A/B
- **Calendrier** : le mode courant fixe le **filtre par défaut** (quarts à la mer en MER, tours à quai en QUAI). L'autre mode reste à un clic et ses historiques restent consultables.
- **Accueil** : **aucune modification sans présentation préalable**. Proposition à valider (**D8**) : un seul indicateur discret « MER » / « QUAI » dans le bandeau, sans autre changement.
- **Notifications** : étiquetage par régime pour prioriser l'affichage, sans en supprimer. Liste des notifications concernées à valider (**D7**).
- **Vues A (par jour) et B (par marin)** : indicateur de mode, marqueur « prévisionnel », distinction planifié / applicable, « Non renseigné » pour les heures réellement travaillées, version mobile ; une seule interface qui adapte son contexte.
- Le mode **n'attribue aucune permission**.

## 4. Initialisation et compatibilité
- La migration ajoute des colonnes **nullables** et ne déduit **aucun mode** de l'existence d'une liste publiée.
- Tant qu'un bâtiment n'est pas initialisé, son mode est **« Non renseigné »** : affichage neutre (les deux régimes visibles), aucune règle dépendant du mode appliquée, alertes liées aux mouvements inchangées.
- Initialisation explicite : action « Initialiser le mode » pour le COMAEQ ou le commandant, et commande de gestion équivalente (valeur obligatoire, auteur, motif, trace d'audit). Pour la démonstration : même service, valeur confirmée par le PO (**D1**), jamais déduite des listes.
- **Consultation historique** : aucune règle de mode n'est appliquée aux données antérieures à l'initialisation ; les listes historiques gardent leur période d'application. Les règles de transition ne s'appliquent qu'aux mouvements postérieurs.
- **Correction d'un mouvement** : annulation motivée, mode recalculé à partir de la chronologie, alertes recalculées, historique conservé ; les affectations déjà réalisées ne sont jamais réécrites silencieusement (D10 ci-dessous).

## 5. Droits

### 5.1 Écran de configuration des délais (matrice proposée)
Les délais (rappel 30 min avant, alerte à l'heure prévue, escalade 15 min après) sont portés par `ConfigurationActivation` (un par bâtiment). Droit proposé via le registre de seuils existant (`REGISTRE_ACTIONS`, action nouvelle, configurable par bâtiment) :

| Profil | Voir | Modifier |
|---|---|---|
| Commandant | oui | **oui** (seuil par défaut) |
| COMAEQ titulaire | oui | **oui** |
| Administrateur d'unité | oui | oui, via le seuil configurable |
| Commandant en second | oui | non |
| Chef de liste | oui (pour ses listes) | non |
| Autres | non | non |

Contrôles : rappel entre 0 et 1 440 min, alerte entre 0 et 120 min, escalade entre 1 et 240 min (bornes à valider, **D5**) ; chaque modification auditée (ancienne et nouvelle valeur, auteur, heure). L'écran n'est pas ouvert avant votre validation de cette matrice.

### 5.2 Remplaçant temporaire du chef de liste
Étendre `ChefDeListe` (pas de système parallèle) avec : début et fin de validité, auteur de la désignation, motif, personne remplacée. Toutes les vérifications ne retiennent que les désignations **actives à l'instant**. Désignation par un responsable ayant déjà le droit de désigner un chef de liste sur ce périmètre exact ; refus hors périmètre ; aucune délégation générale. **D4** : le remplaçant a-t-il tous les droits du chef de liste ou seulement activer / reporter / retirer ? durée maximale (configurable) ?

### 5.3 Régularisation d'un quart à la transition — état des lieux et procédure proposée (aucun code)
**Qui peut aujourd'hui modifier un quart ?**
- Le **chef de liste désigné pour le périmètre exact** de la liste de quarts (et de son équipage).
- La **supervision du commandement** : niveau commandant et au-dessus, sur son bâtiment uniquement. Le commandant en second est en lecture seule.
- La **publication** relève d'un seuil distinct (`liste_service_publication`, par défaut chef de service) avec périmètre.
- **Point d'attention** : la désignation d'un chef de liste (`ChefDeListe`) porte sur un périmètre (bâtiment, service, secteur ou section), **pas sur un type de liste**. Un chef de liste désigné pour un périmètre gère donc à la fois les listes de quarts et les listes de services à quai de ce **même** périmètre exact. Ce droit existe déjà ; il n'est pas créé par le mode MER / QUAI, mais il va à l'encontre de l'intention « aucun droit indirect sur les quarts » dès que les deux listes partagent le périmètre (**D11**).

**Ce qui existe :** ajouter ou supprimer un créneau (motif obligatoire sur liste publiée, audit, notification du marin) et republier avec motif (nouvelle version). Il n'existe pas d'action « terminer un créneau à l'heure effective ».

**Procédure proposée :** (1) le conflit est présenté, à l'activation, au chef de liste à quai **et** au chef de liste des quarts concernés (notification + fil de discussion sur l'objet, sans droit nouveau) ; (2) le **chef de liste des quarts** (ou la supervision du commandement, à défaut) utilise une nouvelle action « Terminer le créneau à l'heure effective » ; (3) l'activation reste bloquée tant que le recouvrement subsiste.

**Contrôles serveur :** liste de quarts publiée ; droits = ceux déjà existants sur cette liste ; nouvelle fin comprise entre le début et l'ancienne fin ; la partie déjà écoulée n'est jamais modifiée ; motif obligatoire ; refus à toute personne sans droit sur la liste de quarts (le chef de liste à quai n'a aucun droit propre sur elle, sauf si sa désignation couvre le même périmètre exact, voir le point d'attention ci-dessus).
**Conséquences :** l'affectation du marin est conservée sur la partie restante ; le marin est notifié ; une nouvelle version de la liste est figée ; les conflits et alertes sont recalculés ; les heures réellement travaillées restent « Non renseigné ».
**Traçabilité :** audit (auteur, fonction, créneau, ancienne et nouvelle fin, motif), historique des versions, aucun écrasement silencieux.
Conclusion : **aucun droit nouveau n'est nécessaire** ; l'action réutilise les droits existants. Elle n'est pas implémentée sans votre GO (**D6**). Si vous voulez qu'un chef de liste à quai n'ait **jamais** de droit sur les quarts, il faut distinguer la désignation par type de liste (ajout d'un type à `ChefDeListe`) : c'est un changement de droits, à décider (**D11**).

## 6. Décisions encore nécessaires

| # | Décision | Recommandation |
|---|---|---|
| D1 | Mode initial des bâtiments de démonstration (Bretagne, Chevallier, Bénébig) | À fournir par le PO ; proposition : Bretagne = QUAI |
| D2 | Activation d'une liste à quai autorisée seulement en mode QUAI ? | Oui, avec message explicite à la mer ; préparer et publier restent possibles |
| D3 | Recouvrement au-delà de l'horizon confirmé : avertissement non bloquant ? | Oui |
| D4 | Droits et durée maximale du remplaçant | Droits limités à activer / reporter / retirer ; durée maximale configurable |
| D5 | Matrice et bornes de configuration des délais | Voir §5.1 |
| D6 | GO pour l'action « Terminer le créneau à l'heure effective » | Valider la procédure du §5.3 |
| D7 | Notifications à étiqueter par régime | Proposition à établir avec vous à partir du catalogue existant |
| D8 | Indicateur MER / QUAI dans le bandeau de l'accueil | Indicateur seul, sans autre changement |
| D9 | Mode « Non renseigné » : affichage neutre des deux régimes | Oui |
| D10 | Correction d'un mouvement ancien : recalcul du mode et des alertes, jamais des affectations passées | Oui |
| D11 | Distinguer la désignation de chef de liste par type (quarts / services à quai) pour supprimer tout droit indirect sur les quarts ? | Oui si l'intention est stricte ; migration conservatrice : les désignations existantes couvrent les deux types jusqu'à décision |

## 7. Ordre de réalisation proposé après relecture
1. Migration : champs `mode_avant` / `mode_apres`, type d'initialisation, fonctions `mode_du_batiment` et `intervalles_par_mode`, initialisation des bâtiments de démonstration.
2. Conflits par intervalles de régime ; activation conditionnée au mode (selon D2).
3. Vues A/B adaptées au mode, indicateur MER / QUAI, version mobile.
4. Écran de configuration, remplaçant temporaire, action de régularisation (selon vos GO).
5. Parcours navigateur complets avec captures, suites complètes SQLite et PostgreSQL, ZIP de bilan.
