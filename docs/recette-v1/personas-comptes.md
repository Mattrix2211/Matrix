# Personas, comptes et permissions

Les noms affichés des comptes de démonstration (`seed_demo`) **ne sont pas** ceux des personas Notion : on note le compte réellement utilisé, on n'invente aucun identifiant. Mot de passe de démonstration : voir `docs/DEMO.md`.

Le rôle technique (`RoleLevel`) et la fonction (chef de liste, référent formation, `fonction_coma`) sont des données distinctes du grade : le grade affiché dans les fixtures n'a aucun effet sur les droits.

## Personas permanents

| Persona (Notion) | Compte de démo (prénom affiché, grade fixture) | Rôle / rattachement dans le code | Écart avec Notion |
|---|---|---|---|
| MOT Lucas Morel, équipier | `equipier_a` (Karim, Matelot) | `EQUIPIER`, Propulsion › Moteurs › section Moteurs bâbord, équipage A | Identité différente (attendu). Cohérent. |
| QM1 Julien Martin, équipier expérimenté | `equipier_a3` (Julien, Quartier-maître, Mécanique) — créé par `seed_recette` | `EQUIPIER`, Propulsion › Moteurs › section Moteurs bâbord, équipage A | **Écart R-01 levé** : qualifications déclarées (« Entretien des pompes d'incendie », requise par la fiche de maintenance, et « Conduite du réseau incendie », proche de l'échéance) ; contrôle trimestriel de la « Pompe d'incendie principale » attribué, avec procédure publiée consultable depuis l'installation. `equipier_a2` (Lina) reste sans données propres. |
| PM Claire Bernard, chef de section | `chef_section_a` (Jade, Quartier-maître) | `CHEF_SECTION`, section Moteurs bâbord, équipage A | Grade fixture différent (PM vs QM), sans effet sur les droits. |
| LV Antoine Le Goff, chef de service | `chef_service_a` (Gaël, Maître) | `CHEF_SERVICE`, Propulsion, équipage A | Grade fixture différent (sans effet). |

## Rôles complémentaires

| Rôle (Notion) | Compte candidat | Observé dans les fixtures | Écart |
|---|---|---|---|
| Chef de secteur et chef de liste (SM Hélène Roussel) | `chef_secteur_a` (Hélène) | `CHEF_SECTEUR` Moteurs + `ChefDeListe` limité au secteur Moteurs ; référent de la formation « Lutte contre l'incendie » | Cumule aussi la fonction de référent formation : **à ne pas confondre** dans les missions. |
| Équipier d'un autre service (QM1 Noémie Laurent, électricité) | `equipier_elec_a` (Nora) | `EQUIPIER`, service Énergie › Électricité | Cohérent. |
| COMAEQ | `coma_comaeq` (Éloïse) | `ETAT_MAJOR`, `fonction_coma="COMAEQ"` | Cohérent. |
| COMANAV | `coma_comanav` (Denis) | `ETAT_MAJOR`, `fonction_coma="COMANAV"` | Cohérent. |
| Chef de secteur équipage B à terre | `chef_secteur_b` (Ivan) | `CHEF_SECTEUR` Moteurs, équipage B | Cohérent. |
| Commandant en second | `second_a` (Cécile) | `COMMANDANT_EN_SECOND`, équipage A | Cohérent. |
| Commandants A/B | `cdt_a` (Anne), `cdt_b` (Benoît) | `COMMANDANT`, équipages A et B | Cohérent. |
| Soutien à terre | `terre_classe` (Tessa), `terre_securite` (Ugo), `terre_chef_securite` (Vera) | `CHEF_SERVICE`, sans navire (« à terre ») | Le rôle technique est `CHEF_SERVICE` : à vérifier que la distinction avec la chaîne embarquée repose bien sur l'absence de navire et non sur le rôle. |
| Référent formation | `referent_formation_a` (Solène, Second-maître) — créé par `seed_recette` | `EQUIPIER`, Sécurité › Pompiers, équipage A ; `ReferentFormation` de « Conduite du réseau incendie » (Bretagne) uniquement | **Écart R-03 levé** : référent « pur », ni chef de secteur ni `ChefDeListe`. Une candidature à instruire dans son ressort et une candidature hors ressort (« Travaux en hauteur ») existent. `chef_secteur_a` reste référent de « Lutte contre l'incendie » (cumul de fonctions, à ne pas confondre). |
| COMA équipage B (Bretagne) et Normandie — créés par `seed_recette` | `coma_comanav_b` (Thibault, COMANAV), `coma_comaeq_b` (Margaux, COMAEQ) ; `coma_comanav_nor` (Olivier, COMANAV), `coma_comaeq_nor` (Pauline, COMAEQ) | `ETAT_MAJOR` avec `fonction_coma`, rattachés au bâtiment (et à l'équipage B pour la Bretagne), titulaires des services qui en dépendent (Propulsion/Énergie : COMANAV ; Sécurité : COMAEQ) | La Normandie reçoit un service « Sécurité » (COMAEQ) pour le COMAEQ. **Service sans titulaire volontaire** : COMOPS de l'équipage B (service Opérations, Bretagne), pour tester un visa en attente avec message d'absence de COMA. Pour tester un poste COMAEQ vacant (feuille de service), retirer la fonction de `coma_comaeq_nor` dans l'administration. |
| Autres | `coma_comops`, `chef_secteur_elec_a`, `chef_secteur_incendie_a`, `equipier_incendie_a`, `marin_b` (équipier B), `admin_navire`, `admin`, bâtiment Normandie (`cdt_nor`, `chef_secteur_nor`, `equipier_nor`) | Présents | Normandie répond à l'exigence « autre bâtiment ». |

## Données de recette (`seed_recette`)

`python manage.py seed_recette` complète `seed_demo` (lancé automatiquement s'il manque) avec des données fictives préfixées `[Recette]`, même mot de passe de démonstration. Elle est idempotente, additive (aucun objet de démonstration modifié) et ne s'exécute qu'avec `DJANGO_DEBUG=1` ou `MATRIX_RECETTE=1`. Elle ajoute les comptes `equipier_a3`, `referent_formation_a` et les COMA fictifs de l'équipage B et de la Normandie, la maintenance de la pompe d'incendie avec sa documentation, des tâches en retard ou proches, des absences, un conflit de planning (absence de Julien sur un quart publié), des notifications, des annonces à accuser, une demande et un fil de discussion, pour Bretagne (équipages A et B), l'Énergie › Électricité et la Normandie.

## Écarts entre sources à arbitrer (ne sont pas des défauts avérés)

1. **Synthèse de passation.** La page Notion « Décisions » (état au 10/10, PR #6/#7) indique que la synthèse de passation automatique planifiée a été retirée et que sa reprise exige une nouvelle décision métier. La PR #8 livre `SynthesePassation` et `ParametresPassation` (org), générée à la validation de la relève et « activée par défaut ». La PR dit relayer une décision métier ; **à faire confirmer par le Product Owner** que cette décision postérieure couvre bien cette implémentation.
2. **Double équipage.** Notion : pas de modèle `org.Equipage` ; le code utilise les codes A/B du profil (`equipage`). Conforme à la page Notion. Les notions d'organisation « en miroir » restent hors V1.
3. **Maintenance de Julien** : jeu de données fourni par `seed_recette` (voir plus haut).
4. **Aucune hypothèse** n'est faite sur la pratique interne réelle de la Marine : toute question de ce type est relayée au Product Owner.

## Permissions réellement implémentées : où vérifier

Rôles et niveaux : `matrix/core/roles.py` (`RoleLevel`, `NIVEAU_VISION_COMMANDEMENT`). Droits par rôle × écran : matrice administrable (`RolePermission`). Périmètres : `scope_filters_for_user` / `build_scope_q`. Équipage actif et lecture seule : `matrix/core/equipage.py`. Ces points sont audités par `qa-securite`, pas par les marins.
