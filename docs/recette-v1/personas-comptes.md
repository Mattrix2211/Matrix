# Personas, comptes et permissions

Les noms affichés des comptes de démonstration (`seed_demo`) **ne sont pas** ceux des personas Notion : on note le compte réellement utilisé, on n'invente aucun identifiant. Mot de passe de démonstration : voir `docs/DEMO.md`.

Le rôle technique (`RoleLevel`) et la fonction (chef de liste, référent formation, `fonction_coma`) sont des données distinctes du grade : le grade affiché dans les fixtures n'a aucun effet sur les droits.

## Personas permanents

| Persona (Notion) | Compte de démo (prénom affiché, grade fixture) | Rôle / rattachement dans le code | Écart avec Notion |
|---|---|---|---|
| MOT Lucas Morel, équipier | `equipier_a` (Karim, Matelot) | `EQUIPIER`, Propulsion › Moteurs › section Moteurs bâbord, équipage A | Identité différente (attendu). Cohérent. |
| QM1 Julien Martin, équipier expérimenté | `equipier_a2` (Lina, Matelot) | `EQUIPIER`, même section, équipage A | **Qualifications « explicitement déclarées » : non établies** (aucune qualification propre à ce compte repérée dans `seed_demo`). **Pas de maintenance attribuée** à ce compte : les occurrences assignées vont à `equipier_incendie_a` ; ses tâches de démo sont « en retard » et « bloquée ». La mission Julien de Notion (maintenance pompe incendie) n'a donc pas de jeu de données. |
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
| Référent formation | `chef_secteur_a` pour « Lutte contre l'incendie » (`ReferentFormation`) | Fonction rattachée à un cours et à un navire | Notion demande de ne pas présumer son existence : **il existe** dans les fixtures mais cumulé avec chef de secteur/chef de liste. Un référent « pur » (grade quelconque, sans rôle de chef) n'existe pas : fixture de test à créer **après accord**. |
| Autres | `coma_comops`, `chef_secteur_elec_a`, `chef_secteur_incendie_a`, `equipier_incendie_a`, `marin_b` (équipier B), `admin_navire`, `admin`, bâtiment Normandie (`cdt_nor`, `chef_secteur_nor`, `equipier_nor`) | Présents | Normandie répond à l'exigence « autre bâtiment ». |

## Écarts entre sources à arbitrer (ne sont pas des défauts avérés)

1. **Synthèse de passation.** La page Notion « Décisions » (état au 10/10, PR #6/#7) indique que la synthèse de passation automatique planifiée a été retirée et que sa reprise exige une nouvelle décision métier. La PR #8 livre `SynthesePassation` et `ParametresPassation` (org), générée à la validation de la relève et « activée par défaut ». La PR dit relayer une décision métier ; **à faire confirmer par le Product Owner** que cette décision postérieure couvre bien cette implémentation.
2. **Double équipage.** Notion : pas de modèle `org.Equipage` ; le code utilise les codes A/B du profil (`equipage`). Conforme à la page Notion. Les notions d'organisation « en miroir » restent hors V1.
3. **Maintenance de Julien** : voir plus haut (fixture manquante).
4. **Aucune hypothèse** n'est faite sur la pratique interne réelle de la Marine : toute question de ce type est relayée au Product Owner.

## Permissions réellement implémentées : où vérifier

Rôles et niveaux : `matrix/core/roles.py` (`RoleLevel`, `NIVEAU_VISION_COMMANDEMENT`). Droits par rôle × écran : matrice administrable (`RolePermission`). Périmètres : `scope_filters_for_user` / `build_scope_q`. Équipage actif et lecture seule : `matrix/core/equipage.py`. Ces points sont audités par `qa-securite`, pas par les marins.
