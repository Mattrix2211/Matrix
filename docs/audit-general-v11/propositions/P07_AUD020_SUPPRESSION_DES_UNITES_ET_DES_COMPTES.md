# P07 — AUD-020 (et AUD-021, AUD-028, AUD-034) : suppression d'unités et de comptes (proposition technique détaillée)

**Statut : proposition ; aucune modification applicative sans l'autorisation du PO.** Criticité **P0** (perte d'information et élargissement implicite des accès). Défaut **préexistant** : identique sur `main` (vérifié par exécution) et sur la V1.1.

## 1. Cause racine

Quatre causes cumulées :
1. **La suppression est un simple `queryset.delete()`** sans examen des dépendances : écran de Réglages (`matrix/views.py:641-675`, actions `delete_service`, `delete_sector`, `delete_section`), interface programmable `DELETE /api/org/{services|sectors|sections}/<id>/` (méthode `destroy` par défaut de DRF, `org/views.py`) et suppression de compte (`accounts/web_views.py:349, 460`).
2. **Le choix des `on_delete` est porté par chaque clé étrangère, sans politique d'ensemble** : vers une section, 9 relations en cascade et 6 en remise à NULL ; vers un secteur 13 / 7 / 3 protégées ; vers un service 12 / 6 / 3 ; vers un bâtiment 33 en cascade (`sondes/fk.py`). Les objets d'**historique métier** (listes de quart et de garde, annonces, documents, fiches, désignations) sont en **cascade**, alors que seuls matériel, installations et stocks sont protégés.
3. **Le périmètre d'un marin est déduit du niveau le plus fin renseigné** (`accounts/models.py:87-96`) : une remise à NULL **élargit** son accès (section → secteur → service → bâtiment).
4. **L'archivage existe sans effet** (AUD-028) : les quatre champs `archived` (`org/models.py`) ne sont lus par aucune règle, donc il n'existe pas de voie de remplacement à la suppression.

## 2. Conséquences concrètes (mesurées)

| Opération | Effet mesuré |
|---|---|
| Supprimer la section « Moteurs bâbord » | 4 marins passent du périmètre section au périmètre secteur ; aucune alerte ; le journal ne note que l'identifiant |
| Supprimer le service « Propulsion » du bâtiment Jacques Chevallier | suppression de 2 désignations de chef de liste, 1 liste de garde (3 créneaux), 1 liste de quart ; mise à NULL du rattachement de personnes, matériels, anomalies, demandes |
| Supprimer un bâtiment (Auguste Bénébig) | 3 listes de garde, 9 créneaux, 1 mouvement du bâtiment, 3 désignations, types de programme et domaines RETEX |
| Supprimer un secteur portant du matériel | erreur 500 sans message (AUD-021) : aucune donnée perdue mais aucun guidage |
| Supprimer un compte (commandant ou administrateur d'unité, un clic, sans confirmation côté serveur) | 6 tâches sur 37 et 3 difficultés sur 4 supprimées ; 13 lignes d'audit perdent leur auteur (`AuditLog.actor` → NULL) ; 53 créneaux de quart et de garde deviennent « sans titulaire » (2 → 55) ; la trace « qui a fait quoi » est effacée |
| Archiver (API) | accepté, sans aucun effet ; section archivée toujours proposée dans les formulaires |

## 3. Correction recommandée

**Principe** : la suppression physique n'est possible que pour une unité ou un compte **jamais utilisé** ; sinon, archivage ou désactivation, avec transfert des personnes.

1. **Couche de service unique** (`org/structure_services.py`) : `dependances(unite)` (comptes, par modèle, des relations en cascade, en remise à NULL et protégées, à partir du collecteur de suppression de Django, **sans rien supprimer**) ; `peut_supprimer(unite)` vrai seulement si le total est nul ; `supprimer(unite, auteur)` lève `SuppressionRefusee(dependances)` sinon. **Tous** les chemins l'appellent : écran de Réglages, `destroy` de l'API (réponse 409 avec le détail), administration Django (`has_delete_permission`).
2. **Politique des `on_delete`** : passer en `PROTECT` les relations vers section, secteur, service et bâtiment portées par des objets d'historique (listes, annonces, documents, fiches, désignations, exigences de formation, postes, programme, types) et par `UserProfile` (plus de remise à NULL silencieuse). Le comportement d'`on_delete` étant appliqué par Django en Python, la migration ne modifie **aucune donnée** et, pour la plupart des moteurs, aucun schéma.
3. **Archivage effectif** : `archived` est respecté par les sélecteurs (formulaires d'affectation, `resoudre_affectation_dans_perimetre`, `marins_du_perimetre`, listes de choix, création d'objets), la lecture historique restant ouverte ; l'archivage d'une unité occupée passe par l'**assistant de transfert** (P04) ou est refusé.
4. **Pas d'élargissement implicite** : un marin dont l'unité est archivée ou transférée passe à l'état « à compléter » (P01), jamais à un périmètre plus large.
5. **Messages** : l'exception de protection est interceptée ; texte en français : « Cette unité porte 6 marins, 4 installations, 2 listes… Archivez-la ou transférez son contenu. »
6. **Comptes** : le bouton « Supprimer » est remplacé par « Désactiver » (`is_active` faux, traçable, réversible) ; la suppression physique reste réservée aux comptes sans historique (même fonction `dependances`) ; `AuditLog.actor` passe en protection ou conserve un instantané du nom (champ texte) pour ne jamais perdre l'auteur.
7. **Journal** : une ligne par catégorie (« 4 marins réaffectés vers X »), avec avant et après.
8. **Interface programmable** : même service, mêmes refus ; la clé `structure_navire_ecriture` continue de borner qui peut agir.

## 4. Risques de régression

| Risque | Détail |
|---|---|
| Tests existants | 42 fichiers de test utilisent des suppressions ; 9 appels explicites aux actions de suppression d'unité ou de compte : ils encodent le comportement actuel et sont à réécrire avec la décision du PO (jamais supprimés pour obtenir du vert) |
| Passage en `PROTECT` | des chemins qui suppriment aujourd'hui en cascade (par exemple un nettoyage de démonstration) échouent : à inventorier avec la recherche de `.delete()` hors tests |
| Archivage effectif | 260 appels de périmètre dans 48 fichiers : un filtre ajouté au mauvais endroit masque des données ; à introduire dans les sélecteurs communs, avec tests par module |
| Désactivation de compte | les écrans qui supposent qu'un compte supprimé disparaît (annuaire, assignations) doivent masquer les comptes désactivés sans casser l'historique |
| Interface programmable | les clients éventuels attendent `204` à la suppression : le passage à `409` est un changement de contrat |

## 5. Tests de non-régression à créer

1. Supprimer une section occupée par des marins est refusé : section et marins inchangés, message listant les dépendances.
2. Même test pour secteur, service, bâtiment ; l'API répond `409` avec le détail.
3. Supprimer une unité vide et jamais utilisée réussit ; une ligne de journal est écrite.
4. Aucun compte ne change de périmètre après un refus de suppression (périmètre avant = après).
5. L'archivage d'une section occupée est refusé tant que les marins n'ont pas de destination ; après transfert, les marins ont le périmètre de la destination.
6. Une section archivée n'est plus proposée dans les formulaires de création et d'édition, ni acceptée par `resoudre_affectation_dans_perimetre`, mais ses listes, annonces et documents restent lisibles.
7. Le renommage conserve l'historique (identifiants stables, noms des journaux inchangés).
8. La désactivation d'un compte conserve tâches, difficultés, créneaux, journal avec le nom de l'auteur ; la suppression d'un compte avec historique est refusée.
9. La suppression d'un secteur portant du matériel produit un message en français, jamais une erreur 500.
10. Chaque cascade existante vers l'historique est couverte par un test qui échoue si elle réapparaît (parcours automatique des relations vers `Section`, `Sector`, `Service`, `Ship`).
11. Double archivage et réactivation : idempotents.
12. Suite complète verte sur SQLite et sur PostgreSQL.

## 6. Conséquences sur les données existantes

- **Aucune donnée n'est modifiée par la correction** ; la migration d'`on_delete` est neutre sur les données.
- **Contrôle préalable en lecture seule** (commande `verifier_structure`) : liste les comptes actifs sans section alors que leur secteur en compte (état « à compléter »), les secteurs vides, les objets orphelins (marin, matériel, anomalie, demande à rattachement NULL provenant d'anciennes suppressions) et les journaux d'audit sans auteur (`actor` NULL).
- **Pertes déjà subies** (comptes supprimés, unités supprimées) **ne sont pas récupérables** par le correctif : seule la sauvegarde permet de les restaurer, d'où le lien avec AUD-031 (sauvegarde et restauration).
- **Sauvegarde obligatoire avant déploiement** de la migration (même si elle est neutre).
- **Rattachements `NULL` existants** : traités par l'état « à compléter » de P01 avec période de grâce configurable.
