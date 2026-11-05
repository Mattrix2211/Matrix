# Scénarios de recette par profil

Chaque scénario a été rejoué dans le navigateur (références `Jnn` : captures dans `captures_parcours/`, journal dans `journal_parcours.json`).
Dates relatives à aujourd'hui. Les actions modifient la base de démonstration : `--reinitialiser` pour repartir de zéro.

## Matelot équipier — `equipier_a`
1. Accueil : « À faire », « Ma journée », « Mes tours de service », alerte prioritaire. (J01, J03 : les 22 liens « Ouvrir » répondent)
2. Quarts et tours de service : « Mon prochain tour », « À traiter : 1 échange en attente de votre accord ». (J10)
3. Accepter l'échange (Plus → Mes échanges). Attendu : « en attente du chef de liste » ; un avertissement de recouvrement futur avec un quart peut s'afficher (démonstration de la règle des échanges). (J10)
4. Tâches : cinq tâches dont une bloquée (gants en rupture : voir Logistique, vue chef). (J05)
5. Maintenance : fiche « Contrôle et graissage du treuil » (EPI, consignes, étapes, points de contrôle). (J06)
6. Signaler une anomalie : assistant en quatre étapes. (J07)
7. Notifications : panneau, « Tout marquer comme lu ». (J09)
8. **Restrictions** : pas de création de feuille de service (403, J21), pas de vue « Par marin », pas de « Créer une liste » (J22).

## Chef de secteur et chef de liste — `chef_secteur_a`
1. Quarts : « Par marin (responsables) » : postes à pourvoir, charge, échange à valider. (captures `quarts_B`)
2. Valider l'échange accepté. (J11) Attendu : tours permutés, notifications.
3. Onglet « Listes » : brouillon avec poste non pourvu, proposée, publiées, effectuée.
4. **Conflit d'affectation** : liste « Permanence prévisionnelle — conflit d'affectation » : activer → refus « Activation bloquée », rien n'est modifié. (J12)
5. Activer la liste publiée par le COMAEQ (scénario COMAEQ). (J14)
6. Logistique : stock avec ruptures et seuils, « Mes tickets ».

## BSC — `equipier_a2`
Feuille de service : créer, rédiger, proposer ; seuls les rédacteurs désignés écrivent. (J24)

## COMAEQ — `coma_comaeq`
1. Quarts → « À traiter » : « Service à quai — proposé… : à publier » → publier à titre prévisionnel avec une prise d'effet. (J13)
2. Feuille de service : circuit de visa. (J25)
3. **Restriction** : ne peut pas activer une liste.

## Commandant — `cdt_a`
Mouvements du bâtiment (appareillage / accostage), délais d'alerte. (J26)

## Bénébig (QUAI) — `chef_liste_abe`, `cdt_abe`, `historique_abe`
1. Activation anticipée avec confirmation. (J15) — 2. Liste en retard : alerte, report avec motif. (J16)
3. `historique_abe` n'a aucun droit avant qualification (J23) ; `cdt_abe` le qualifie (J17).

## Chevallier (MER) — `chef_liste_jch`, `comaeq_jch`
Activation refusée à la mer (J18) → accostage par le COMAEQ (J19) → activation (J20).

## Cas particuliers présents dans les données
Absence (permissions, stage, repos), retard (maintenances en retard, liste en retard), conflit (activation bloquée), échange refusé / rejeté / annulé, tâche bloquée, permission insuffisante (J21 à J23), rupture de stock, anomalie urgente.
