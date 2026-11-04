# Mer / quai — activation manuelle, alertes : plan technique (avant migrations)

Statut initial : **plan soumis au PO. Aucun code, aucune migration.** (L'implémentation a depuis suivi l'ordre ci-dessous.) Décisions PO reprises telles quelles : 4 états, activation explicite par le seul chef de liste habilité (jamais le COMAEQ), aucune activation automatique, alertes H−30 / H / H+15 configurables, alerte immédiate à l'accostage confirmé, report/annulation avec motif, pas de suppression de données historiques.

## Avancement et décisions PO intégrées (mis à jour)

Documents liés : `mer_quai_mode_operationnel_complement.md` (modèle du mode MER / QUAI, **validé par le PO**, décisions D1 à D11 arbitrées) et `notifications_par_regime.md` (classification des notifications, **en attente de validation D7**).

| Lot | Contenu | État |
|---|---|---|
| Étapes 1 à 6 (`71d54ca` à `0b26107`) | Application des listes à quai, publication prévisionnelle, activation par le chef de liste, conflits, alertes H−30 / H / H+15, mouvements, modules, échanges différés, terminaison automatique | Terminé |
| Repli CSD, états d'échange visibles | Escalade et alerte d'accostage vers le commandant en second ; échange validé / en attente / appliqué / bloqué, nouvelle tentative, abandon motivé | Terminé |
| D11 — habilitations (`d2e6a9f`) | Chef de liste des quarts distinct du chef de liste des services à quai ; désignations historiques conservées et signalées « à préciser », précision explicite, diagnostic en lecture seule | Terminé |
| Mode MER / QUAI (`7178b8a`) | Mode déduit des mouvements confirmés (`mode_du_batiment`, `intervalles_par_mode`), initialisation explicite et tracée, consultation à une date passée, correction recalculant la chronologie ; activation refusée hors mode QUAI confirmé (D2, D9) | Terminé |
| Recouvrements (`a4fa883`) | Conflit applicable bloquant / avertissement futur non bloquant (D3) | Terminé |
| Vues A / B et indicateur (`f2802e4`) | Vue par jour, vue par marin (heures réelles « Non renseigné »), indicateur MER / QUAI sur accueil, index et fiches, mobile | Terminé |
| Délais d'alerte et remplaçant (`99493bd`) | Écran de configuration (droits et bornes D5), remplaçant temporaire (D4) | Terminé |
| D6 (`259cf05`, `f9b8564`) | Terminer un créneau de quart à l'heure effective | Terminé |
| Catalogue des notifications (D7) | Classification MER / QUAI / COMMUNES / TRANSITION | **Proposé, en attente de validation** |
| Recette | Parcours navigateur complets, suites complètes SQLite et PostgreSQL, dossier de recette | Voir le dossier de recette |

Hors périmètre V1.1, conformément au PO : stades d'alerte, mouillage, organisations de service particulières.

## 0. Constat sur l'existant (lu dans le code)

- `Quart` (mer) et `ServiceGarde` (quai) partagent `ListeServiceAbstract` : `BROUILLON → PROPOSEE → PUBLIEE`. **« Publiée » vaut aujourd'hui « applicable »** : feuille de service, échanges, calendrier, tableau de bord, passation et iCal ne lisent que `PUBLIEE`.
- Modules qui lisent `PUBLIEE` (à adapter) : `quarts/` (models, listes_views, feuille_service_views, services, echanges, web_views), `dashboard/` (aujourdhui, passation), `calendar_app/` (evenements_sources, ical_views).
- Seul contrôle de chevauchement : `quarts/echanges.py::conflits_marin` (à l'échange). Ni la publication ni la création ne contrôlent l'exclusivité mer/quai.
- Chef de liste : `ChefDeListe` (désignation pour le périmètre **exact**, dans l'équipage) ; `peut_gerer_liste` ajoute la supervision du commandement ; `peut_publier_liste` = seuil `liste_service_publication` + périmètre.
- Tâches planifiées existantes : Celery beat toutes les minutes (`appliquer_releves_echues`) **et** application paresseuse à la lecture : même schéma réutilisable pour les alertes.

## 1. Modèles et états réutilisés

- **Réutilisés** : `ServiceGarde` (liste à quai), ses statuts de circuit `BROUILLON/PROPOSEE/PUBLIEE`, `ChefDeListe`, `titulaires_comaeq`, `Notification`, `AuditLog`, versions de liste, Celery beat.
- **Les 4 états PO** se lisent ainsi (champ nouveau `application`, orthogonal au circuit de validation existant) :

| État PO | Circuit (existant) | `application` (nouveau) |
|---|---|---|
| Brouillon | `BROUILLON` ou `PROPOSEE` | — |
| Prévisionnelle publiée | `PUBLIEE` | `PREVISIONNELLE` |
| Active | `PUBLIEE` | `ACTIVE` |
| Terminée / archivée | `PUBLIEE` | `TERMINEE` |

- **`Quart` (mer) inchangé** : publié = applicable (cf. question 1).

## 2. Modifications de données (migrations, après votre accord)

1. `ServiceGarde` : `application` (défaut `PREVISIONNELLE` pour les nouvelles listes), `prise_effet_prevue` (date-heure), `prise_effet` (date-heure effective), `active_par`, `active_le`, `terminee_par`, `terminee_le`, `version_prevision` (entier, incrémenté à chaque report).
2. **Nouveau** `MouvementBatiment` : bâtiment, type (`APPAREILLAGE` / `ACCOSTAGE`), date-heure effective, déclaré par, note. (Source de la confirmation d'accostage ; l'appareillage sert aux journées de transition.)
3. **Nouveau** `AlerteActivation` : liste, étape (`RAPPEL`, `ALERTE`, `ESCALADE`, `ACCOSTAGE`), échéance, `version_prevision`, statut (`OUVERTE` / `CLOTUREE`), motif de clôture, horodatages ; **contrainte d'unicité (liste, étape, version_prevision)** : protège contre les doublons si plusieurs traitements s'exécutent en parallèle.
4. **Nouveau** `ConfigurationActivation` (un par bâtiment) : `rappel_avant_min=30`, `alerte_apres_min=0`, `escalade_apres_min=15`, modifiable par l'administrateur du bâtiment.
5. **Migration de données de compatibilité** : toute liste `PUBLIEE` existante (quai) devient `application=ACTIVE`, `prise_effet=publiee_le`, `active_par=publiee_par` (marquée « historique »). **Aucune ligne supprimée ni modifiée dans ses affectations.**

## 3. Chef de liste habilité

Habilité = `ChefDeListe` **désigné pour le périmètre exact de la liste**, compte actif, **de l'équipage de la liste** (pas l'autre équipage), vérifié côté serveur. Le COMAEQ n'a pas le droit d'activer ; il reste destinataire de l'escalade. Questions 2 et 3 ci-dessous pour les cas limites (commandant, COMAEQ désigné chef de liste).

## 4. Confirmation de l'accostage

Un utilisateur habilité enregistre un `MouvementBatiment(ACCOSTAGE, date-heure)`. Dans la **même transaction**, Matrix vérifie s'il existe une liste à quai `ACTIVE` couvrant cet instant pour l'équipage à bord ; sinon il crée une `AlerteActivation(ACCOSTAGE)` immédiate pour les chefs de liste concernés. **Aucune activation automatique.** Qui est « habilité » : question 4.

## 5. Rappels et escalade

Pour une liste `PREVISIONNELLE` avec `prise_effet_prevue = H` : échéances calculées H − 30 min (rappel, chef de liste), H (alerte : confirmer l'activation ou reporter), H + 15 min (escalade au COMAEQ de l'équipage, priorité haute, **sans droit d'activer**). Déclenchement par une tâche beat à la minute + vérification paresseuse à la lecture ; chaque alerte est créée une seule fois (`get_or_create` sous contrainte d'unicité + verrou de ligne). **Report** : nouveau H, `version_prevision` incrémenté, alertes ouvertes de l'ancienne version clôturées (« reportée »), nouvelles échéances posées. **Activation, annulation** : toutes les alertes ouvertes sont clôturées avec leur motif ; l'historique est conservé. Délais lus dans `ConfigurationActivation`.

## 6. Effets sur échanges et affectations

- **Échanges** : possibles seulement sur une liste `ACTIVE` ; absents sur une prévisionnelle. `conflits_marin` ne considère que les intervalles **applicables** (liste à quai `ACTIVE` sur `[max(début, prise d'effet), fin]`, quarts publiés).
- **Activation** : contrôle des conflits réels **par marin et par intervalle horaire** ; contrôle d'**exclusivité de régime par jour** (un quart applicable et un tour applicable le même jour ne coexistent que le jour de la prise d'effet, et seulement si les intervalles ne se chevauchent pas pour un même marin). Conflits listés avec les noms et heures ; confirmation demandée en l'absence de conflit bloquant.
- **Feuille de service, calendrier, tableau de bord, passation, iCal** : ne lisent que `ACTIVE` (et affichent la prévisionnelle avec la mention « prévisionnel » aux chefs et aux marins concernés, jamais comme tour applicable). Le rectificatif de feuille se calcule sur les tours **actifs**. Une version de liste est figée à l'activation.
- **Notifications** : publication prévisionnelle → marins informés « prévisionnel, non applicable » ; activation → marins informés « applicable à partir de … ».
- **Équipages A/B** : listes et alertes bornées à l'équipage de la liste ; accostage appliqué à l'équipage à bord ; chef de liste de l'équipage propriétaire seulement.

## 7. Compatibilité avec les listes historiques

Migration en `ACTIVE` (§2.5) : **comportement inchangé**. Nouveau contrôle d'exclusivité appliqué **uniquement aux nouvelles activations**, jamais rétroactivement. Une commande **en lecture seule** `analyser_chevauchements_mer_quai` classe les chevauchements historiques ; rien n'est supprimé.
**Analyse des 30 chevauchements historiques (démonstration de base)** : 27 quai × mer, 3 quai × quai ; trois marins fictifs (`equipier_a`, `equipier_a2`, `chef_secteur_a`) ; une seule paire de mer : « Quart machine — par tiers » ; côté quai : 3 « Fraction de service à quai » (03, 05 et 07/11, 7 chacune) et la « Garde de nuit — Propulsion » (6) ; les 3 quai × quai sont les fractions contre la garde de nuit. Cause : le jeu de départ superpose quarts et services sur les mêmes jours. Traitement proposé : **conservés et signalés** comme « chevauchement historique connu » ; la correction du jeu de démonstration (si vous la voulez) se fait en régénérant la démo, pas en effaçant.

## 8. Tests prévus (positifs et négatifs)

Une liste prévisionnelle ne devient jamais active seule (heure dépassée, bâtiment à quai déclaré) ; seul le chef de liste désigné active (refus : COMAEQ, chef de service non désigné, commandant selon décision, autre équipage, marin, anonyme) ; confirmation exigée ; atomicité (échec → rien d'écrit) ; double activation ; report décale alertes sans doublon ; activation/annulation clôturent les alertes en conservant l'historique ; accostage sans liste active → alerte, avec liste active → aucune ; exécution concurrente des vérifications (unicité) ; conflit d'affectation réel bloquant ; **journée de transition sans fausse double affectation** (quart le matin, tour l'après-midi) et avec chevauchement horaire réel refusé ; échanges absents sur prévisionnelle ; feuille/calendrier/iCal/passation/dashboard n'affichent pas une prévisionnelle comme applicable ; données historiques inchangées après migration ; équipages A/B ; délais configurables.

## Ordre de livraison (commits)

1. Migration + états + compatibilité historique (aucun changement de comportement). 2. Service d'activation + droits + bouton « Activer la liste » + confirmation. 3. Contrôles de conflits et d'exclusivité. 4. Alertes (modèle, beat, configuration, report, annulation). 5. Accostage confirmé. 6. Adaptation calendrier, feuille, échanges, dashboard, passation, iCal, notifications. 7. Vues A/B : repères visuels « prévisionnel », mobile, indicateurs séparés. 8. Recette : parcours réels capturés (prévisionnelle → rappel → alerte → escalade → activation ; report ; accostage ; transition ; échange sur liste active).

## Questions nécessitant votre décision avant de coder

1. **Quarts à la mer** : restent-ils « publié = applicable » (ma recommandation) ou ont-ils aussi un état prévisionnel et une activation ?
2. **Commandant / supervision** : le commandant (ou l'administrateur) peut-il activer, ou strictement le seul chef de liste désigné (ma recommandation : strictement le chef de liste désigné) ?
3. **COMAEQ désigné chef de liste** : interdire la désignation, ou lui retirer le seul droit d'activer ?
4. **Qui confirme l'accostage** : état-major et commandant (même habilitation que la saisie du programme) ? le commandant en second (lecture seule aujourd'hui) peut-il le déclarer ? (ma recommandation : états-majors et commandant, délégation possible.)
5. **Pas de liste prévisionnelle à l'accostage** : l'alerte va-t-elle aux chefs de liste désignés du bâtiment, ou aussi au COMAEQ immédiatement ?
6. **COMAEQ vacant à l'escalade** : repli sur le commandant de l'équipage (comme pour le visa) ?
7. **Publication directe** : en plus de « Publier à titre prévisionnel », offrez-vous « Publier et activer » (même contrôles, même confirmation, toujours manuel) pour les listes courantes d'un bâtiment à quai, afin de ne pas imposer deux clics hebdomadaires ?
8. **Prise d'effet prévue** : obligatoire à la publication prévisionnelle (sans elle, pas d'alertes) ? (recommandé : oui.)
9. **Fin de liste** : passage à « Terminée » automatique à la date de fin, ou action manuelle du chef de liste ?
10. **Prise d'effet en milieu de période** : les tours d'une liste activée à l'heure T s'appliquent-ils à partir de T seulement (ma recommandation) ?
11. **Heures réellement travaillées** : aucune donnée ne les saisit aujourd'hui. Afficher « non renseigné » tant qu'aucune source n'est définie, ou définir une saisie (qui, quand) ?
12. **Quart empiétant sur une activation** : si des quarts à la mer applicables recouvrent encore les tours après T, l'activation est-elle bloquée jusqu'à ce que le chef du quart termine son quart (ma recommandation), ou le quart est-il raccourci automatiquement avec trace ?
