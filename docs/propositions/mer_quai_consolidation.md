# Mer / Quai — passe de consolidation après la recette indépendante

Statut : **corrections techniques faites dans le périmètre validé ; règles métier non tranchées présentées en options, rien d'implémenté sur ces points.**
Aucun merge dans `main`, aucun déploiement, aucune suppression.

## 1. Vérification des constats de l'audit

Chaque constat a été reproduit sur le code (sondes jetables, puis tests permanents).

### 1.1 Défauts confirmés — corrigés
| Constat | Ce qui a été constaté | Correction |
|---|---|---|
| Alertes tardives trompeuses | Liste publiée 40 min après l'heure prévue : le rappel « la prise d'effet approche », l'alerte et l'escalade partaient en même temps | Plus de rappel après l'heure prévue ; l'escalade se compte depuis le déclenchement **réel** de l'alerte (voir §6) |
| Refus de droit mal exprimés | « HTTP 0 » du rapport = redirection non suivie par le script ; le vrai statut était **302 avec message** pour le COMAEQ ou le commandant qui tentait d'activer, et **400** pour une publication sans droit | **403** pour qui voit la liste, 404 pour qui ne la voit pas (politique d'erreurs validée) ; voir §7 |
| Tentatives refusées non tracées | Aucune trace | Journal d'audit `tentative_refusee` (acteur, action, objet) sur activation, report, retrait, publication, terminer un créneau, mouvements, délais, remplaçants et réglages de chef de liste |
| Notifications sans régime ni icône | Principe D7 validé, non implémenté | Fait (§8) |
| Accumulation de bandeaux sur la fiche de liste | Jusqu'à neuf blocs d'information empilés | Réduits, sans masquer une alerte bloquante (§9) |

### 1.2 Comportements conformes, à documenter
| Constat | Documentation |
|---|---|
| Les désignations de chef de liste **non typées** gardent leurs droits sur les quarts et les services à quai | Choix conservateur de la migration (« ne pas élargir, ne pas restreindre en silence »). Écart assumé et transitoire à D11, tant que chaque désignation n'est pas qualifiée : inventaire et procédure au §2 |
| `intervalles_par_mode()` n'est pas consommée par les contrôles de conflit | Exact : les contrôles utilisent l'instant d'activation (règle du §3). La fonction reste l'API centrale du découpage par mode, testée, prête à servir si le PO retient l'option B du §3 |
| Activation avant l'heure prévue possible (14 h 32 pour 17 h 30 dans R01) | Règle actuelle documentée au §5 ; aucune nouvelle restriction sans validation |
| Actions de gestion « génériques » (ajouter ou supprimer un créneau, proposer, paramètres) : 404 pour qui voit la liste sans être gestionnaire | Comportement antérieur au chantier, conservé pour ne pas modifier d'autres écrans ; seules les actions sensibles du chantier renvoient 403. Harmonisation possible : **décision D-A** |

### 1.3 Décisions métier qui nécessitent votre arbitrage
| # | Sujet | Où |
|---|---|---|
| D-A | Harmoniser les refus des actions de gestion génériques (404 → 403 pour qui voit la liste) | §1.2 |
| D-B | Contrôles de conflit : statu quo, classification par régime, ou classification complète | §3 |
| D-C | Échanges de tour : aligner sur D3 ou garder le blocage strict | §4 |
| D-D | Activation avant l'heure prévue : libre, avec confirmation, ou avec motif | §5 |
| D-E | Qualification des désignations historiques : qui, quand | §2 |
| D-F | Données de démonstration des deux bâtiments absents | §10 |

## 2. Habilitations historiques (D11)

**Inventaire** : `python manage.py analyser_designations_chef_de_liste` (lecture seule) liste chaque désignation sans type avec son niveau, le constat « droits actuels sur les quarts à la mer ET les services à quai » et une indication d'usage (ambiguë si le niveau porte des quarts et des services à quai, usage unique constaté sinon). La page « Chefs de liste » affiche le même constat à ceux qui peuvent désigner.

**Procédure de qualification, explicite et sans élargissement automatique** :
1. Le responsable ouvre « Chefs de liste » ; chaque désignation historique porte « À préciser » et son usage constaté (information, jamais une attribution).
2. Il choisit **lui-même** un ou deux types (quarts à la mer, services à quai) et valide.
3. La désignation historique est remplacée par les seules désignations choisies ; l'opération est auditée (auteur, titulaire, niveau, types). Un choix vide ne change rien.
4. Aucune création de désignation sans type n'est possible par l'interface ; aucune migration ne modifie une désignation existante.
5. Tant qu'une désignation n'est pas qualifiée, ses effets actuels sont conservés (aucun retrait silencieux non plus).

**Tests explicites** (`quarts/tests/test_habilitations_historiques.py`) : un chef de liste à quai ne peut ni ajouter ni supprimer un créneau de quart, ni proposer ou publier un quart, ni terminer un créneau (statut réel, refus effectif, données et versions inchangées) ; une désignation à quai ne crée aucun droit sur les quarts ; la qualification n'ajoute que les types choisis ; l'inventaire ne modifie rien.

## 3. Contrôles de conflit et `intervalles_par_mode()`

### Règle actuelle (activation)
À l'instant d'activation, on ne regarde que la partie des créneaux **postérieure à cet instant** (jamais de rétroactivité) :
- deux services à quai en vigueur qui se recouvrent → **conflit bloquant** ;
- un quart déjà **en cours** en même temps que le service → **conflit bloquant** ;
- un quart qui ne recouvre le service que **dans le futur** → **avertissement non bloquant**, réévalué à chaque mouvement, modification de liste ou activation ;
- un recouvrement entièrement antérieur à l'activation (par exemple un service de 24 h qui chevauche l'accostage) est ignoré.

### Les trois classes demandées
| Classe | Définition proposée |
|---|---|
| Conflit confirmé et bloquant | Deux affectations simultanément applicables dans un régime **confirmé** (deux services à quai ; ou un quart encore en cours pendant le service) |
| Recouvrement futur incertain, non bloquant | Chevauchement situé après l'horizon confirmé : le régime peut encore changer |
| Recouvrement apparent entre deux régimes | Chevauchement dû au seul découpage horaire d'un créneau qui enjambe une transition confirmée (la partie avant l'accostage relève de la mer, la partie après du quai) |

### Cas types et résultat selon l'option
Marin M ; accostage confirmé à 10:00 ; activation à 10:30.
| Cas | Option A (règle actuelle) | Option B (classification par `intervalles_par_mode`) |
|---|---|---|
| 1. Quart 06:00–10:00, service 10:00–18:00 | Aucun recouvrement | Idem |
| 2. Quart 08:00–12:00 (encore en cours), service 10:00–18:00 | **Bloquant** | Recouvrement « apparent » : le quart est hors régime depuis 10:00 ; **à régulariser** (« Terminer à l'heure effective ») mais **non bloquant** *ou* bloquant selon votre choix |
| 3. Quart demain 09:00–13:00, service demain 06:00–18:00 | Avertissement | Avertissement |
| 4. Deux services à quai qui se recouvrent | **Bloquant** | **Bloquant** |
| 5. Service 00:00–24:00, quart 06:00–10:00 (avant l'accostage) | Ignoré (antérieur) | Ignoré (« apparent ») |
| 6. Quart déjà terminé | Ignoré | Ignoré |

**Impact** : seul le cas 2 change. Il touche le cas le plus concret d'un accostage (un quart qui n'a pas été clôturé à l'heure de l'accostage). **Option A** : un quart en cours bloque, ce qui force la régularisation avant l'activation (cohérent avec « Matrix ne raccourcit jamais un quart »). **Option B** : l'activation passe et la régularisation est signalée. Je recommande **A** pour le cas 2 (décision 12 déjà validée) et de n'ouvrir `intervalles_par_mode()` aux contrôles que si vous voulez afficher, dans l'écran des conflits, la classe « apparent » en plus des deux autres (affichage seulement, sans changer le blocage).

Aucune modification automatique des affectations dans aucune option.

## 4. Échanges de tour et décision D3

### Règle actuelle
`conflits_marin()` traite comme **bloquant** tout autre service en vigueur **ou tout quart publié** du marin qui recouvre le tour, y compris dans le futur et y compris sur la partie du créneau antérieure à l'activation. L'échange est contrôlé à la demande, à l'acceptation, à la validation et, pour un échange préparé, à l'activation.

### Écart avec D3
Un quart futur dont le régime n'est pas confirmé bloque donc un échange, alors qu'il n'est qu'un avertissement pour l'activation.

### Options
| Option | Comportement | Impact |
|---|---|---|
| A — statu quo | Un quart qui recouvre bloque toujours l'échange | Strict, simple, mais refuse des échanges que l'activation aurait acceptés |
| **B — alignement sur D3 (recommandée)** | Bloquant : deux services à quai qui se recouvrent, quart **déjà en cours**, absence, habilitation manquante, tour commencé, délai non respecté. Avertissement affiché (au chef de liste à la validation, au marin à l'acceptation) : quart **futur** dont le régime n'est pas confirmé. **Revérification à l'application** : tout ce qui est devenu confirmé et simultané bloque, rien d'incompatible n'est appliqué | Même règle pour l'activation et les échanges ; une partie de créneau antérieure à la prise d'effet n'est plus comptée |
| C — B, plus confirmation explicite du marin | B avec, pour un avertissement, une case « j'ai pris connaissance » avant d'accepter | Un clic de plus, trace explicite |

Exemples : échange d'un tour de 06:00 à 18:00 demain vers un marin qui a un quart demain 09:00–13:00 → A bloque, B/C avertissent puis revérifient le jour J ; vers un marin qui a un quart en cours maintenant → bloqué dans les trois options ; deux services à quai recouvrants → bloqué dans les trois options.

## 5. Activation avant l'heure prévue

**Règle actuelle** : après publication, le chef de liste (ou son remplaçant) peut activer à tout moment tant que le mode est QUAI et qu'aucun conflit bloquant n'existe. Il n'existe aucun délai minimal. La prise d'effet est l'instant d'activation (jamais l'heure prévue) ; l'heure prévue est conservée à côté ; les alertes sont fermées ; les marins affectés sont prévenus. Exemple R01 : activation à 14 h 32, prise d'effet prévue à 17 h 30, écart de trois heures, sans message ni motif.

| Option | Comportement | Remarque |
|---|---|---|
| A — statu quo | Libre | Aucun garde-fou, l'écart est seulement visible sur la fiche |
| **B — confirmation (recommandée)** | Si l'activation est plus de N minutes avant l'heure prévue, la fenêtre de confirmation l'indique (« activation 3 h avant l'heure prévue ») ; aucune restriction | Un clic de plus, aucune règle nouvelle |
| C — motif | Motif obligatoire au-delà de N minutes | Trace plus riche, geste plus lourd |
| D — blocage | Interdit avant l'heure prévue | Peu réaliste : la réalité précède souvent le planning |

N serait réglable par bâtiment (par exemple 30 minutes). **Rien n'est implémenté sans votre choix.**

## 6. Alertes tardives — règle appliquée (technique, dans le périmètre validé)
Chronologie pour une liste publiée 40 minutes **après** l'heure prévue (H) :
| Instant | Avant | Après correction |
|---|---|---|
| Publication + 1 minute | Rappel « la prise d'effet approche » + alerte + escalade | **Alerte seule** : « la liste devait prendre effet à H et n'est pas activée » |
| + 15 minutes | — | **Escalade** au COMAEQ (ou au commandant en second) |
| Rappel | Possible après H | **Jamais après H** |
Règles : le rappel n'existe que s'il précède l'heure prévue ; l'escalade attend le délai configuré **depuis le déclenchement réel de l'alerte** (publication tardive ou retard de traitement) ; une alerte n'est créée qu'une fois par version de prévision ; un report repart sur un cycle normal. Tests : `AlertesTardivesTests`.

## 7. Refus serveur — statut réellement renvoyé
| Action refusée | Profil | Statut | Effet |
|---|---|---|---|
| Activer, reporter, retirer une prévision | commandant, COMAEQ, commandant en second, marin (voit la liste) | **403** | rien modifié ; tentative tracée |
| Idem | utilisateur qui ne voit pas la liste | **404** | rien modifié |
| Publier une liste | chef de liste sans droit de publication | **403** | rien modifié ; tracé |
| Terminer un créneau de quart | chef de liste à quai, marin | **403** | créneau, versions inchangés ; tracé |
| Déclarer, corriger ou initialiser un mouvement | non habilité | **403** | aucun mouvement ; tracé |
| Modifier les délais d'alerte | lecture seule (second, administrateur, chef de liste) | **403** | rien enregistré ; tracé ; 404 pour les autres profils |
| Désigner ou révoquer un remplaçant, qualifier une désignation | non responsable | **403** | rien créé ; tracé |
| Activation à la mer, mode non renseigné, conflit bloquant, motif manquant | habilité | **302** vers la fiche avec le message métier | rien modifié |
Tests : `quarts/tests/test_refus_serveur.py` (statut, refus effectif, données inchangées, trace).

## 8. Notifications : régime et icônes (D7 validé)
- Régime porté par la notification (MER, QUAI, COMMUNES par défaut, TRANSITION), **étiquette de priorité, jamais un filtre**. Étiquetage : quarts → MER ; services à quai, feuille de service, activation, alertes, échanges, remplaçants → QUAI ; accostage sans liste et régularisation de quart touchant le quai → TRANSITION ; programme, relèves et le reste → COMMUNES.
- Répartition dans le panneau : le régime du mode courant, COMMUNES et TRANSITION d'abord ; l'autre régime dans « Autres régimes (n) » (replié, jamais supprimé). « Urgente » = niveau **Urgent** ou **action à traiter** : elle reste toujours dans le premier groupe. Mode non renseigné : aucun regroupement.
- Icône par catégorie, tirée de la table centrale des icônes : quarts (horloge), services et calendrier, échanges (flèches), maintenance (outils), tâches (liste de contrôle), messagerie (bulle), documents (fichier), alertes (triangle), validations (coche) ; déduite de l'objet visé ou posée explicitement ; libellé de catégorie présent pour les lecteurs d'écran ; la couleur de la carte reste la gravité.
- Correction de mon catalogue initial : « urgente » désignait le niveau « attention » ou « danger » ; le niveau « attention » s'affiche « Important », seul « Urgent » (danger) est urgent.

## 9. Fiche de liste : moins de bandeaux
- L'état, le mode et la mention « prévisionnelle ou activée » tiennent sur **une seule rangée**.
- Les trois alertes d'activation ouvertes ne s'empilent plus : seule la **plus avancée** est affichée.
- Les avertissements **non bloquants** sont repliés (« n — non bloquants ») ; ils restent consultables.
- Le **conflit bloquant** reste un bandeau visible ; l'alerte d'escalade aussi.

## 10. Bâtiments de démonstration absents
**Disponible** : la base de démonstration contient les bâtiments Bretagne et Normandie (unités Matrix) ; la Bretagne est initialisée QUAI (valeur fictive validée). Jacques Chevallier et Auguste Bénébig sont présents seulement dans le **référentiel des bâtiments** (catalogue, `ReferenceBatiment`), pas comme unités Matrix : aucun mode n'a pu leur être attribué.
**Proposition (non exécutée)** : créer deux unités de démonstration reliées à leur référence, avec un commandant et un COMAEQ fictifs **nommés « démonstration »**, puis initialiser leur mode (Chevallier MER, Bénébig QUAI) avec le motif existant « situation fictive de démonstration validée par le PO ». Aucune donnée présentée comme réelle ; suppression possible en une commande dédiée. **Décision D-F.**
