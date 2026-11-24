# Lot L29 — cartographie des points d'entrée et preuve d'application des autorisations

> **DOCUMENT PROVISOIRE — DIFFUSION RESTREINTE.** Données fictives uniquement ; aucun secret. Le lot est livré sur sa branche, **non fusionné** ; sa clôture attend la validation du PO.

Références : `docs/DECISIONS_PO.md` (ARB-01 et les décisions qui dépendent du socle), `docs/PLAN_LOTS_REPRISE.md` (fiche L29, §3 bis).

## 1. Ce que le lot fournit

| Élément | Fichier | Rôle |
|---|---|---|
| Point de contrôle commun | `matrix/core/habilitation.py` | `evaluer(user, action, …)` rend une décision explicable (facteur refusant, motif) en composant les mécanismes existants : compte actif, module activé, niveau d'écriture sur le service. Aucune règle nouvelle. Adopté par `calendar_app/deplacement_views.py`. |
| Inventaire des points d'entrée | `matrix/core/points_entree.py` | Routes web et API (méthodes, protections lisibles dans le code), modèles d'administration, tâches Celery. Lecture seule. |
| Registre déclaratif | `matrix/core/registre_acces.py` | Pour chaque famille de points : classe, contrôles attendus, module, sensibilité, écarts connus (avec le lot correctif), suites de tests existantes. Aucun point ne peut rester sans règle. |
| Cartographie | `manage.py cartographier_points_entree` | Produit le tableau du §3. |
| Preuve par exécution | `matrix/tests/habilitation/` | Appels réels avec des profils types ; voir §4. |

Le registre **ne prouve rien** : il dit ce qui est attendu. La preuve est l'exécution des accès.

## 2. Architecture retenue

- **Composer, pas remplacer.** `habilitation.evaluer` s'appuie sur `ecriture_service` et `modules` ; aucun second système d'autorisation. Les facteurs forment une liste ordonnée (`FACTEURS`) : les lots suivants y ajoutent le plancher non contournable (L06), la délégation et la suppléance (L08), l'état de module généralisé (L34) sans toucher aux appelants.
- **Lecture : bornage des listes inchangé.** Ce qu'un marin lit reste borné par les requêtes de périmètre (`scope_filters_for_user`). `evaluer` ne contrôle en lecture que le compte et le module, et **refuse** (erreur de programmation) qu'on lui passe un objet à lire, pour qu'aucun appelant ne croie à tort que l'accès à l'objet est vérifié.
- **Une seule source pour l'équipage à terre.** `EquipageATerreMiddleware` refuse toute écriture à terre par défaut et porte seul les exemptions de chemins ; le socle ne les duplique pas. Une écriture à terre est éprouvée par exécution (V11, code 403 exigé).
- **Pas de monolithe.** Trois modules courts et indépendants : décision, inventaire, registre.
- **Défense côté serveur.** Aucun masquage d'interface n'est tenu pour une protection.
- **Migration progressive.** Un seul appel existant est migré (déplacement d'un ticket ou d'une occurrence), couvert par `calendar_app.tests.test_calendar_event_move_perimetre` ; les autres appelants passeront à `evaluer` au fil des lots qui les modifient (L32 en particulier). `Action.VALIDER` n'existe pas encore : une validation est une écriture avec `niveau_requis` jusqu'à L06 et L10.

## 3. Cartographie des points d'entrée

Générée par `python manage.py cartographier_points_entree`.

| Nature | Points d'entrée | Dont écriture possible |
|---|---|---|
| Pages web | 185 | 129 |
| API (hors suffixes de format) | 89 | 73 |
| Administration (modèles) | 59 | 59 |
| Tâches Celery | 20 | 20 |
Variantes d'API à suffixe de format (même vue que la route de base) : 82. Routes d'administration générées : 365.
| Règle | Classe | Points | Contrôles attendus | Module | Lecture sensible | Écarts connus | Suites existantes |
|---|---|---|---|---|---|---|---|
| PUB-CONNEXION | public | 3 | — | — | non | — | — |
| WEB-DECONNEXION | authentifie | 1 | authentifie | — | non | — | — |
| WEB-MEDIA | authentifie | 1 | authentifie, proprietaire_objet, perimetre_batiment | — | oui | — | matrix.tests.test_etancheite_equipage_peripherie, matrix.tests.test_etancheite_equipage_vues |
| WEB-PASSATION | authentifie | 2 | authentifie, queryset_perimetre | — | oui | A14, NE-06 : la synthèse n'est pas bornée à la section ou au service → L30 | — |
| WEB-TABLEAUX | authentifie | 12 | authentifie, queryset_perimetre | — | oui | A25 : l'accueil et les tableaux affichent des données d'un module désactivé → L34 | matrix.tests.test_etancheite_equipage_vues |
| WEB-ECHANGES | authentifie | 2 | authentifie, queryset_perimetre, seuil_role | quarts | non | A2 : la validation revient à qui gère la liste, non au COMAEQ → L10 | — |
| WEB-FEUILLE-SERVICE | authentifie | 5 | authentifie, middleware_equipage_a_terre, proprietaire_objet | quarts | oui | — | quarts.tests.test_feuille_service_circuit_bsc, matrix.tests.test_securite_ecritures |
| WEB-QUARTS | authentifie | 8 | authentifie, queryset_perimetre, seuil_role, niveau_sur_service | quarts | non | A1, A3, A4 : l'administrateur d'unité franchit les seuils d'autorité métier → L06 | matrix.tests.test_securite_terre_second, matrix.tests.test_etancheite_equipage_vues |
| WEB-ABSENCES | authentifie | 1 | authentifie, queryset_perimetre | absences | oui | ARB-06 : périmètre de lecture des absences et protection du motif à poser avant tout affichage du motif (non affiché aujourd'hui) → L32 | — |
| WEB-TACHES | authentifie | 5 | authentifie, queryset_perimetre, seuil_role, niveau_sur_service | taches | oui | ARB-06 : écriture non bornée au périmètre dans ce module → L32 | — |
| WEB-FORMATIONS | authentifie | 5 | authentifie, queryset_perimetre, seuil_role, niveau_sur_service | training | non | ARB-06 : écriture non bornée au périmètre dans ce module → L32 | — |
| WEB-DOCUMENTATION | authentifie | 5 | authentifie, queryset_perimetre, seuil_role, niveau_sur_service | documentation | non | ARB-06 : écriture non bornée au périmètre dans ce module → L32 | — |
| WEB-RETEX | authentifie | 5 | authentifie, queryset_perimetre, seuil_role, niveau_sur_service | retex | non | ARB-06 : écriture non bornée au périmètre dans ce module → L32 | — |
| WEB-DEMANDES | authentifie | 5 | authentifie, queryset_perimetre | demandes | non | — | — |
| WEB-ANNONCES | authentifie | 4 | authentifie, queryset_perimetre | annonces | non | — | — |
| WEB-PROGRAMME | authentifie | 5 | authentifie, queryset_perimetre | programme | non | — | — |
| WEB-POSTES | authentifie | 3 | authentifie, queryset_perimetre | postes | non | — | — |
| WEB-MAINTENANCE | authentifie | 14 | authentifie, queryset_perimetre, seuil_role, niveau_sur_service | maintenance | oui | — | matrix.tests.test_ecriture_commandants_adjoints, maintenance.tests.test_web_scope_leak |
| WEB-LOGISTIQUE | authentifie | 18 | authentifie, queryset_perimetre, seuil_role, niveau_sur_service | logistics | oui | — | matrix.tests.test_ecriture_commandants_adjoints, logistics.tests.test_web_scope_leak |
| WEB-MATERIEL | authentifie | 48 | authentifie, queryset_perimetre, seuil_role, niveau_sur_service | assets | oui | — | matrix.tests.test_ecriture_commandants_adjoints |
| WEB-RAPPORTS | authentifie | 1 | authentifie, queryset_perimetre | reports | oui | — | — |
| WEB-CALENDRIER | authentifie | 9 | authentifie, queryset_perimetre, niveau_sur_service | — | oui | A25 : le calendrier affiche des événements d'un module désactivé → L34 | calendar_app.tests.test_calendar_event_move_perimetre, calendar_app.tests.test_popover_permissions |
| WEB-COMPTES | authentifie | 9 | authentifie, seuil_role, queryset_perimetre | — | oui | — | accounts.tests.test_scope_leak_users_web, accounts.tests.test_directory_permissions |
| WEB-REGLAGES | authentifie | 1 | authentifie, seuil_role, middleware_equipage_a_terre | — | oui | — | — |
| WEB-PERSONNEL | authentifie | 13 | authentifie, queryset_perimetre | — | oui | — | matrix.tests.test_global_search |
| API-COMPTES | authentifie | 11 | authentifie, seuil_role, queryset_perimetre | — | oui | — | accounts.tests.test_scope_leak_users_api, accounts.tests.test_scope_leak_userprofile_api |
| API-ORG | authentifie | 11 | authentifie, seuil_role, queryset_perimetre | — | oui | — | org.tests.test_scope_navire |
| API-MATERIEL | authentifie | 23 | authentifie, queryset_perimetre, seuil_role, niveau_sur_service | assets | oui | A25 : le module désactivé reste actif par ce point d'entrée → L34 | assets.tests.test_scope_leak |
| API-MAINTENANCE | authentifie | 9 | authentifie, queryset_perimetre, seuil_role, niveau_sur_service | maintenance | oui | A25 : le module désactivé reste actif par ce point d'entrée → L34 | maintenance.tests.test_scope_leak |
| API-LOGISTIQUE | authentifie | 8 | authentifie, queryset_perimetre, seuil_role, niveau_sur_service | logistics | oui | A25 : le module désactivé reste actif par ce point d'entrée → L34 | logistics.tests.test_scope_leak |
| API-FORMATIONS | authentifie | 11 | authentifie, queryset_perimetre, seuil_role, niveau_sur_service | training | oui | ARB-06 : écriture non bornée au périmètre dans ce module → L32 ; A25 : le module désactivé reste actif par ce point d'entrée → L34 | training.tests.test_scope_requirements |
| API-DISCUSSIONS | authentifie | 7 | authentifie, queryset_perimetre | — | oui | — | threads.tests.test_scope_leak, threads.tests.test_permissions |
| API-NOTIFICATIONS | authentifie | 7 | authentifie, proprietaire_objet | — | non | — | — |
| API-TABLEAUX | authentifie | 2 | authentifie, queryset_perimetre | — | oui | — | — |
| ADMIN-COMPTES | administration | 4 | droit_admin_django | — | oui | — | — |
| ADMIN-ORGANISATION | administration | 9 | droit_admin_django | — | oui | — | org.tests.test_archivage, org.tests.test_suppression_unites |
| ADMIN-AUTRES | administration | 46 | droit_admin_django | — | oui | A25 : le module désactivé reste actif par ce point d'entrée → L34 | — |
| TACHE-GLOBALE | traitement | 5 | perimetre_batiment | — | non | — | — |
| TACHE-MAINTENANCE | traitement | 3 | perimetre_batiment | maintenance | non | A25 : le module désactivé reste actif par ce point d'entrée → L34 | — |
| TACHE-NOTIFICATIONS | traitement | 10 | perimetre_batiment | — | non | A25 : le module désactivé reste actif par ce point d'entrée → L34 | — |
| TACHE-ANNONCES | traitement | 2 | perimetre_batiment | annonces | non | A25 : le module désactivé reste actif par ce point d'entrée → L34 | — |
| Tâche | Planifiée | Règle |
|---|---|---|
| annonces.tasks.diffuser_annonces | oui | TACHE-ANNONCES |
| annonces.tasks.rappeler_accuses_annonces | oui | TACHE-ANNONCES |
| maintenance.tasks.compute_overdue | oui | TACHE-MAINTENANCE |
| maintenance.tasks.generate_installation_occurrences | oui | TACHE-MAINTENANCE |
| maintenance.tasks.generate_occurrences | oui | TACHE-MAINTENANCE |
| matrix.core.tasks.appliquer_releves_echues | oui | TACHE-GLOBALE |
| matrix.core.tasks.purger_brouillons | oui | TACHE-GLOBALE |
| matrix.core.tasks.purger_sessions | oui | TACHE-GLOBALE |
| notifications.tasks.detect_installation_drift | oui | TACHE-NOTIFICATIONS |
| notifications.tasks.generate_installation_maintenance_notifications | oui | TACHE-NOTIFICATIONS |
| notifications.tasks.generate_installation_notifications | oui | TACHE-NOTIFICATIONS |
| notifications.tasks.notify_expiring_training | oui | TACHE-NOTIFICATIONS |
| notifications.tasks.notify_low_stock | oui | TACHE-NOTIFICATIONS |
| notifications.tasks.notify_ma_journee | oui | TACHE-NOTIFICATIONS |
| notifications.tasks.notify_ma_journee_demain | oui | TACHE-NOTIFICATIONS |
| notifications.tasks.notify_maintenance_echeance_proche | oui | TACHE-NOTIFICATIONS |
| notifications.tasks.notify_overdue_occurrences | oui | TACHE-NOTIFICATIONS |
| notifications.tasks.notify_taches_en_retard | oui | TACHE-NOTIFICATIONS |
| quarts.tasks.signaler_divergences_feuilles | oui | TACHE-GLOBALE |
| quarts.tasks.traiter_echeances_activation | oui | TACHE-GLOBALE |
Protections lisibles dans le code des routes : {'fonction': 22, 'mixin': 545, 'permission': 169}.

**Limites de l'inventaire.** Il couvre les routes (web, API, administration), les modèles d'administration et les tâches Celery. Il ne couvre pas : les commandes de gestion (`manage.py`, hors du réseau ; 19 dans le dépôt), les récepteurs de signaux Django (ils réagissent à des écritures déjà contrôlées ; trois `m2m_changed` dans `training/models.py`), ni les accès directs à la base. Aucun WebSocket ni webhook n'existe. Les 82 variantes d'API à suffixe de format partagent la vue de leur route de base ; les 365 routes d'administration sont générées par les 59 modèles enregistrés.

## 4. Preuve par exécution

`matrix/tests/habilitation/` : **50 tests**, 41 règles du registre, 17 vérifications exécutées.

| Fichier | Ce qu'il prouve |
|---|---|
| `test_inventaire.py` | Tout point d'entrée a une règle (couverture par préfixe) ; l'instantané des 202 routes d'écriture oblige à valider toute route ajoutée, retirée ou reclassée ; toute règle correspond à un point ; contrôles, modules, suites de couverture et lots cités existent ; chaque adresse d'essai résout bien la vue annoncée ; toute route d'API déclare une classe de permission. |
| `test_acces_anonyme.py` | Aucune route non publique n'est atteinte sans connexion, par GET, POST, PUT, PATCH, DELETE, OPTIONS et HEAD ; identifiants HTTP invalides, requêtes JSON et HTMX refusés ; les trois routes publiques ne livrent aucune donnée. |
| `test_matrice_profils.py` + `verifications.py` | 17 accès sensibles appelés pour de bon par 1 à 16 profils (20 profils distincts) (marin, chefs, état-major, second, commandants, administrateurs, autre bâtiment, équipage à terre, soutien à terre). Le résultat attendu est la cible des décisions du PO ; un écart du code actuel est enregistré tel quel et échoue le jour où il est corrigé. |
| `test_admin.py` | Les 59 modèles d'administration : lecture fermée aux visiteurs, comptes ordinaires et comptes « staff » sans droit ; ajout refusé à un compte sans droit (15 modèles) ; sur les références de bâtiments, un compte qui peut seulement voir ne déclenche aucune action ni modification, et un compte qui peut modifier peut archiver (témoin positif) ; toute action personnalisée exige une permission. |
| `test_traitements.py` | Les 20 tâches planifiées s'exécutent ; l'alerte de stock ne touche que le périmètre de la pièce ; l'écart A25 est enregistré pour cette tâche. |
| `test_detection.py` | Sur un site volontairement piégé (routes ouvertes), le dispositif signale la route oubliée du registre, la route ouverte aux visiteurs, une route d'écriture ajoutée sous un préfixe déjà couvert (par l'instantané), un profil qui atteint ce qui devrait lui être refusé et un écart connu corrigé. |
| `test_socle.py` | Parité de `evaluer` avec `niveau_ecriture_sur` pour 15 profils et 3 niveaux ; refus du visiteur et du compte désactivé ; module désactivé ; lecture d'objet refusée comme usage. |

### Protections existantes prouvées
Cloisonnement des annuaires et des tickets par bâtiment et par service (V03, V04) ; tâche privée lisible de son seul acteur (V02) ; écriture d'un état-major bornée aux services rattachés et refus du commandant en second (V05, V06) ; seuils d'écriture et d'attribution de rôle par API et par le web (V07, V09, V13, V16) ; écriture refusée à l'équipage à terre, acceptée à bord (V11, V12) ; activation de module réservée au seuil configuré (V15) ; administration Django fermée sans droit (V14, `test_admin.py`).

### Nouvelles protections introduites par L29
- **N1** — `RolePermission.has_permission` (`matrix/core/permissions.py`) exige désormais un compte connecté pour toute méthode.
- **N2** — `TrainingSessionPermission.has_permission` (`training/views.py`) exige un compte connecté.
- **N3** — `ReferenceBatimentAdmin` : les actions « archiver » et « restaurer » exigent la permission de modification (`org/admin.py`).
- **N4** — le socle, l'inventaire, le registre, la cartographie et leurs tests.

### Écarts connus enregistrés tels quels (corrigés par les lots suivants)
| Écart | Preuve | Lot |
|---|---|---|
| A14 : un chef de section lit dans la passation une tâche d'une autre section ; un chef de service d'un autre service et un commandant adjoint hors de ses services lisent le même contenu | V01 | L30 |
| ARB-01/02 : l'administrateur d'unité lit la passation | V01 | L06, L30 |
| A1 : l'administrateur d'unité déplace un ticket et fait avancer son état | V05, V06 | L06 |
| ARB-01 règle 4 : l'administrateur d'unité s'attribue lui-même une autorité de commandant (API et web) | V08, V17 | L06 |
| ARB-06 : un commandant adjoint modifie la tâche d'un service qui n'est pas le sien | V10 | L32 |
| A25 : une tâche planifiée notifie encore pour un module désactivé | `test_traitements.py` | L34 |
| A25 (API, administration, accueil, calendrier) et A2 (validation des échanges) | déclarés d'après l'audit du 12/11/2026, **non exécutés** par ce lot | L34, L10 |

## 5. Durcissements F1, F2 et F3 (validés par le PO, conservés dans L29)

Trois accès à du code d'écriture ont été découverts en **exécutant** l'inventaire (F1, F2) et lors de la première relecture indépendante (F3), puis corrigés. Chacun est référencé dans le registre des anomalies (`docs/recette/04_REGISTRE_ANOMALIES.md` et `.csv`).

| Réf. | Anomalie | Origine | Correction | Preuves de recette |
|---|---|---|---|---|
| F1 — ANO-015 | Les écritures de l'API de maintenance (occurrences, exécutions, démarrage, clôture) franchissaient la permission pour un visiteur non connecté. Aucune donnée créée dans les essais (périmètre et validation arrêtaient la requête ; une création valide finissait en erreur serveur), mais le code d'écriture était atteint. | `RolePermission.has_permission` ne vérifiait la connexion que pour les lectures ; le seuil d'écriture de la maintenance est celui d'un équipier, niveau que prend un visiteur anonyme. | `matrix/core/permissions.py` : connexion exigée pour toute méthode. | `test_acces_anonyme` : `test_l_ecriture_anonyme_de_l_api_de_maintenance_est_refusee` et balayage de toutes les routes et méthodes ; suites SQLite et PostgreSQL. |
| F2 — ANO-016 | Les PUT, PATCH et DELETE des sessions de formation, et un POST ne portant que sur les présences, franchissaient la permission pour un visiteur non connecté. | `TrainingSessionPermission.has_permission` renvoyait vrai pour ces méthodes sans vérifier la connexion. | `training/views.py` : connexion exigée en tête de `has_permission`. | `test_l_ecriture_anonyme_de_l_api_de_formation_est_refusee` et balayage ; suites SQLite et PostgreSQL. |
| F3 — ANO-017 | Un compte « staff » qui pouvait seulement voir la liste des références de bâtiments pouvait lancer « archiver » et « restaurer ». | Les deux actions n'exigeaient aucune permission propre (relecture indépendante). | `org/admin.py` : `permissions=["change"]` sur les deux actions. | `test_admin` : `test_un_compte_qui_ne_peut_que_voir_ne_declenche_aucune_action_ni_modification` et `test_toute_action_personnalisee_d_administration_exige_une_permission` ; suites SQLite et PostgreSQL. |

Ces durcissements ne modifient aucune règle métier et ne touchent que des appels que l'interface n'émet pas.

À **qualifier lors des lots L06 et suivants** (aucune décision prise ici) : l'administrateur d'unité lit les tickets et les passations de son bâtiment ; il peut modifier les seuils de rôle de son bâtiment sans plancher (ARB-01 règle 7, non éprouvé par exécution).

## 6. Cinq états à ne pas confondre

| État | Sens | Ce qui l'établit |
|---|---|---|
| **Point d'entrée inventorié** | La route, le modèle d'administration ou la tâche existe et a une règle. | `points_entree` et `test_inventaire` (couverture **par préfixe** : une nouvelle route d'écriture hérite de sa famille ; l'instantané des 202 routes d'écriture oblige à la valider). |
| **Protection déclarée** | Le registre dit quels contrôles sont attendus. | `registre_acces.py` ; seule la présence d'une classe de permission est confrontée au code pour l'API. Aucune preuve par elle-même. |
| **Protection effectivement vérifiée** | Un accès réel a donné le résultat attendu. | Balayage anonyme de toutes les routes ; vérifications V02 à V17 ; `test_admin` ; `test_traitements`. |
| **Anomalie connue reproduite** | L'écart existe encore ; le test l'enregistre tel quel. | `ecarts_connus` (V01, V05, V06, V08, V10, V17), `test_traitements` (A25) ; il échoue le jour où l'écart disparaît. |
| **Anomalie corrigée** | Écart supprimé et prouvé. | F1, F2 et F3 uniquement (§5). |

L'état de chaque règle du registre :

| Règle | Points inventoriés | Protection déclarée | Protection vérifiée par exécution | Anomalie connue reproduite | Anomalie corrigée par L29 | Preuve restante (lot) |
|---|---|---|---|---|---|---|
| PUB-CONNEXION | 3 | — | — | — | — | — |
| WEB-DECONNEXION | 1 | authentifie | anonyme seulement | — | — | — |
| WEB-MEDIA | 1 | authentifie, proprietaire_objet, perimetre_batiment | anonyme seulement | — | — | L30 |
| WEB-PASSATION | 2 | authentifie, queryset_perimetre | anonyme + V01 | V01 | — | — |
| WEB-TABLEAUX | 12 | authentifie, queryset_perimetre | anonyme seulement | — | — | L30 |
| WEB-ECHANGES | 2 | authentifie, queryset_perimetre, seuil_role | anonyme seulement | — | — | L10 |
| WEB-FEUILLE-SERVICE | 5 | authentifie, middleware_equipage_a_terre, proprietaire_objet | anonyme seulement | — | — | L33 |
| WEB-QUARTS | 8 | authentifie, queryset_perimetre, seuil_role, niveau_sur_service | anonyme seulement | — | — | L06 |
| WEB-ABSENCES | 1 | authentifie, queryset_perimetre | anonyme seulement | — | — | L32 |
| WEB-TACHES | 5 | authentifie, queryset_perimetre, seuil_role, niveau_sur_service | anonyme + V02, V10, V11, V12 | V10 | — | — |
| WEB-FORMATIONS | 5 | authentifie, queryset_perimetre, seuil_role, niveau_sur_service | anonyme seulement | — | — | L32 |
| WEB-DOCUMENTATION | 5 | authentifie, queryset_perimetre, seuil_role, niveau_sur_service | anonyme seulement | — | — | L32 |
| WEB-RETEX | 5 | authentifie, queryset_perimetre, seuil_role, niveau_sur_service | anonyme seulement | — | — | L32 |
| WEB-DEMANDES | 5 | authentifie, queryset_perimetre | anonyme seulement | — | — | — |
| WEB-ANNONCES | 4 | authentifie, queryset_perimetre | anonyme seulement | — | — | — |
| WEB-PROGRAMME | 5 | authentifie, queryset_perimetre | anonyme seulement | — | — | — |
| WEB-POSTES | 3 | authentifie, queryset_perimetre | anonyme seulement | — | — | — |
| WEB-MAINTENANCE | 14 | authentifie, queryset_perimetre, seuil_role, niveau_sur_service | anonyme seulement | — | — | L32 |
| WEB-LOGISTIQUE | 18 | authentifie, queryset_perimetre, seuil_role, niveau_sur_service | anonyme seulement | — | — | L32 |
| WEB-MATERIEL | 48 | authentifie, queryset_perimetre, seuil_role, niveau_sur_service | anonyme seulement | — | — | L32 |
| WEB-RAPPORTS | 1 | authentifie, queryset_perimetre | anonyme seulement | — | — | L32 |
| WEB-CALENDRIER | 9 | authentifie, queryset_perimetre, niveau_sur_service | anonyme + V05 | V05 | — | — |
| WEB-COMPTES | 9 | authentifie, seuil_role, queryset_perimetre | anonyme + V16, V17 | V17 | — | — |
| WEB-REGLAGES | 1 | authentifie, seuil_role, middleware_equipage_a_terre | anonyme + V15 | — | — | — |
| WEB-PERSONNEL | 13 | authentifie, queryset_perimetre | anonyme seulement | — | — | L34 |
| API-COMPTES | 11 | authentifie, seuil_role, queryset_perimetre | anonyme + V03, V07, V08, V09 | V08 | — | — |
| API-ORG | 11 | authentifie, seuil_role, queryset_perimetre | anonyme + V13 | — | — | — |
| API-MATERIEL | 23 | authentifie, queryset_perimetre, seuil_role, niveau_sur_service | anonyme seulement | — | — | L32 |
| API-MAINTENANCE | 9 | authentifie, queryset_perimetre, seuil_role, niveau_sur_service | anonyme seulement | — | F1 | L32 |
| API-LOGISTIQUE | 8 | authentifie, queryset_perimetre, seuil_role, niveau_sur_service | anonyme + V04, V06 | V06 | — | — |
| API-FORMATIONS | 11 | authentifie, queryset_perimetre, seuil_role, niveau_sur_service | anonyme seulement | — | F2 | L32 |
| API-DISCUSSIONS | 7 | authentifie, queryset_perimetre | anonyme seulement | — | — | L32 |
| API-NOTIFICATIONS | 7 | authentifie, proprietaire_objet | anonyme seulement | — | — | — |
| API-TABLEAUX | 2 | authentifie, queryset_perimetre | anonyme seulement | — | — | L30 |
| ADMIN-COMPTES | 4 | droit_admin_django | ouverture sans droit + V14 + staff sans droit | — | — | — |
| ADMIN-ORGANISATION | 9 | droit_admin_django | ouverture sans droit seulement + staff sans droit | — | F3 | L06 |
| ADMIN-AUTRES | 46 | droit_admin_django | ouverture sans droit seulement + staff sans droit | — | — | L34 |
| TACHE-GLOBALE | 5 | perimetre_batiment | exécution des tâches | — | — | — |
| TACHE-MAINTENANCE | 3 | perimetre_batiment | exécution des tâches | — | — | — |
| TACHE-NOTIFICATIONS | 10 | perimetre_batiment | exécution des tâches + alerte de stock | A25 (tâche de stock) | — | — |
| TACHE-ANNONCES | 2 | perimetre_batiment | exécution des tâches | — | — | — |

« anonyme seulement » : seule l'absence d'accès sans connexion est vérifiée pour cette famille ; les contrôles par profil reposent sur les suites existantes ou sur le lot nommé en dernière colonne.

## 7. Preuves restantes et lot responsable

Chaque règle sensible sans vérification exécutée dans L29 (dictionnaire `SANS_PREUVE_EXECUTEE`, vérifié par test : égalité exacte avec les règles sensibles non exercées, et lot présent au plan) :

| Lot | Règles dont la preuve par profil reste à produire |
|---|---|
| L06 | `ADMIN-ORGANISATION`, `WEB-QUARTS` |
| L10 | `WEB-ECHANGES` |
| L30 | `API-TABLEAUX`, `WEB-MEDIA`, `WEB-TABLEAUX` |
| L32 | `API-DISCUSSIONS`, `API-FORMATIONS`, `API-MAINTENANCE`, `API-MATERIEL`, `WEB-ABSENCES`, `WEB-DOCUMENTATION`, `WEB-FORMATIONS`, `WEB-LOGISTIQUE`, `WEB-MAINTENANCE`, `WEB-MATERIEL`, `WEB-RAPPORTS`, `WEB-RETEX` |
| L33 | `WEB-FEUILLE-SERVICE` |
| L34 | `ADMIN-AUTRES`, `WEB-PERSONNEL` |

Ces règles sont rattachées aux fiches de lots de `docs/PLAN_LOTS_REPRISE.md`. L29 n'est pas étendu pour les traiter.

## 8. Limites de la preuve

- Les contrôles déclarés ne sont pas confrontés au code, hormis la présence d'une classe de permission pour chaque route d'API.
- Administration : ajout éprouvé par échantillon (15 modèles), modification et action éprouvées sur les références de bâtiments seulement.
- L'inventaire déduit les méthodes de la vue : une écriture faite par un GET (effet de bord) n'est pas comptée comme écriture, et le middleware d'équipage à terre ne filtre que les méthodes non sûres. Limite antérieure à L29, à examiner en L32.
- Aucun test de charge, de navigateur ni de réseau ; Windows, Safari et iPhone non exécutés.

## 9. Résultats des tests

Suite **complète** du projet (`manage.py test --parallel 4`), exécutée sur le code final du lot (commit `5590678`) et sur une référence comparable : l'état `ebe2577`, même commande, même machine, mêmes moteurs. Seul le document de preuves a été modifié après ces exécutions.

| Moteur | État | Tests | Réussis | Échecs | Erreurs | Ignorés |
|---|---|---|---|---|---|---|
| SQLite | référence `ebe2577` | 3971 | 3951 | 0 | 0 | 20 |
| SQLite | candidat L29 `5590678` | 4021 | 4001 | 0 | 0 | 20 |
| PostgreSQL 16 | référence `ebe2577` | 3971 | 3949 | 0 | 0 | 22 |
| PostgreSQL 16 | candidat L29 `5590678` | 4021 | 3999 | 0 | 0 | 22 |

- L'écart de 50 tests est exactement `matrix.tests.habilitation` ; aucun test existant n'est modifié, retiré ou ignoré en plus.
- Les tests ignorés sont ceux qui dépendent du moteur (verrous PostgreSQL, bases simulées SQLite), identiques à la référence.
- Les exécutions partielles de la première phase (14 applications, 3804 puis 3850 tests) sont remplacées par ces suites complètes.
- Non exécutés : Windows, Safari, Firefox, iPhone, lecteur d'écran.


## 10. Relectures indépendantes

**Première relecture** (avant le premier rapport) : verdict « à corriger », sans bloquant. Corrigé : actions d'administration sans permission (F3), socle simplifié (facteur « équipage à terre », `VALIDER`, `service_id`, `strict`, `exception_a_terre` retirés ; lecture d'objet refusée), profils d'autres bâtiments et de soutien à terre ajoutés, vérifications V15 à V17, témoin positif ou code exact exigé, test de données publiques sur un monde non vide, commandes de gestion et signaux déclarés hors inventaire.

**Seconde relecture** (état final du code) : verdict **OK**, aucun bloquant. Les trois durcissements sont jugés corrects, complets et sans effet de bord pour un utilisateur légitime ; la parité du socle avec les mécanismes existants est confirmée ; aucun changement métier observable hors le compte « staff » qui perd « archiver » et « restaurer » (F3). Deux remarques importantes et six mineures, traitées :

| Remarque | Suite |
|---|---|
| Nombre de tests du document inexact (47 contre 46) | Chiffres recalculés sur le code final (50 tests) et suites rejouées. |
| La détection ne signale une route d'écriture ajoutée que sous un préfixe nouveau | Instantané des 202 routes d'écriture à valider explicitement, avec un test de détection sur un préfixe déjà couvert ; la couverture par préfixe est dite telle partout. |
| Lots de `SANS_PREUVE_EXECUTEE` non rattachés aux fiches du plan | Chaque fiche (L06, L10, L30, L32, L33, L34) liste ses règles. |
| « 5 à 15 profils » inexact | Corrigé (1 à 16). |
| Administration : portée de la preuve et témoin positif de F3 | Texte corrigé ; témoin positif ajouté. |
| Liste des règles sans preuve non exhaustive | Remplacée par le tableau du §7. |
| Écriture par GET non inventoriée | Limite ajoutée au §8. |
| Docstring de `habilitation.py` trop longue | Raccourcie. |
