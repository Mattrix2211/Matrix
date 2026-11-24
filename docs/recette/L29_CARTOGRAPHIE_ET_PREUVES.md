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

`matrix/tests/habilitation/` : **46 tests**.

| Fichier | Ce qu'il prouve |
|---|---|
| `test_inventaire.py` | Tout point d'entrée a une règle ; toute règle correspond à un point ; contrôles, modules, suites de couverture et lots cités existent ; chaque adresse d'essai résout bien la vue annoncée ; toute route d'API déclare une classe de permission. |
| `test_acces_anonyme.py` | Aucune route non publique n'est atteinte sans connexion, par GET, POST, PUT, PATCH, DELETE, OPTIONS et HEAD ; identifiants HTTP invalides, requêtes JSON et HTMX refusés ; les trois routes publiques ne livrent aucune donnée. |
| `test_matrice_profils.py` + `verifications.py` | 17 accès sensibles appelés pour de bon par 5 à 15 profils (marin, chefs, état-major, second, commandants, administrateurs, autre bâtiment, équipage à terre, soutien à terre). Le résultat attendu est la cible des décisions du PO ; un écart du code actuel est enregistré tel quel et échoue le jour où il est corrigé. |
| `test_admin.py` | Les 59 modèles d'administration sont fermés aux visiteurs, aux comptes ordinaires, aux comptes « staff » sans droit ; un compte qui peut seulement voir ne déclenche aucune action ni modification ; toute action personnalisée exige une permission. |
| `test_traitements.py` | Les 20 tâches planifiées s'exécutent ; l'alerte de stock ne touche que le périmètre de la pièce ; l'écart A25 est enregistré pour cette tâche. |
| `test_detection.py` | Sur un site volontairement piégé (routes ouvertes), le dispositif signale la route oubliée, la route ouverte aux visiteurs, un profil qui atteint ce qui devrait lui être refusé et un écart connu corrigé. |
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

## 5. Constats de l'inventaire

Trois accès non authentifiés à du code d'écriture ont été découverts **en exécutant** l'inventaire, et corrigés par L29 :
1. **F1** — Les écritures de l'API de maintenance (occurrences, exécutions, démarrage et clôture) franchissaient la permission pour un visiteur non connecté, le seuil d'action étant celui d'un équipier. Aucune donnée n'a pu être créée dans les essais (périmètre et validation arrêtaient la requête ; une création valide terminait en erreur serveur), mais le code d'écriture était atteint.
2. **F2** — Les modifications et suppressions de sessions de formation par l'API, et la création n'indiquant que des présences, franchissaient la permission pour un visiteur non connecté.
3. **F3** — Un compte « staff » qui pouvait seulement voir la liste des références de bâtiments pouvait lancer « archiver » et « restaurer ».

Ces trois constats sont des **durcissements** : ils ne modifient aucune règle métier et ne touchent que des appels que l'interface n'émet pas.

À **qualifier lors des lots L06 et suivants** (aucune décision prise ici) : l'administrateur d'unité lit les tickets et les passations de son bâtiment ; il peut modifier les seuils de rôle de son bâtiment sans plancher (ARB-01 règle 7, non éprouvé par exécution).

## 6. Limites de la preuve

- Règles sensibles sans preuve exécutée de ce lot (liste exacte dans `SANS_PREUVE_EXECUTEE`) : elles reposent sur des suites existantes (colonne « Suites existantes ») ou relèvent d'un lot : validation des échanges, feuille de service, quarts, matériel, logistique, maintenance, formations, documentation, retex, API de découverte, administration hors comptes.
- Les contrôles déclarés dans le registre ne sont pas confrontés au code, hormis la présence d'une classe de permission pour chaque route d'API.
- Administration : lecture, ajout et modification sont éprouvés par échantillon (15 modèles pour l'écriture).
- Aucun test de charge, de navigateur ni de réseau.
- Résultats obtenus sur SQLite et PostgreSQL 16 ; Windows, Safari et iPhone ne sont pas exécutés.

## 7. Résultats des tests

Périmètre : 14 applications qui portent des permissions, des API ou des tâches (`accounts assets calendar_app dashboard logistics maintenance matrix notifications org quarts taches training threads absences`). Référence : commit `ebe2577`, mêmes commandes (`manage.py test <apps> --parallel 4`), même machine.

| Moteur | État | Tests | Réussis | Échecs | Erreurs | Ignorés |
|---|---|---|---|---|---|---|
| SQLite | référence `ebe2577` | 3804 | 3787 | 0 | 0 | 17 |
| SQLite | candidat L29 | 3850 | 3833 | 0 | 0 | 17 |
| PostgreSQL 16 | référence `ebe2577` | 3804 | 3782 | 0 | 0 | 22 |
| PostgreSQL 16 | candidat L29 | 3850 | 3828 | 0 | 0 | 22 |

L'écart de 46 tests est exactement `matrix.tests.habilitation`. Aucune régression, aucun test supprimé ni modifié dans les suites existantes. Les tests ignorés sont ceux qui dépendent du moteur (verrous PostgreSQL, bases simulées SQLite), identiques à la référence.

Une première exécution SQLite du candidat avait signalé 2 échecs dans `test_inventaire` : une tâche Celery définie par un test (`test_coherence_configuration`) était prise pour un point d'entrée du site quand la suite complète tourne. L'inventaire ignore désormais les tâches définies par des tests ; la suite SQLite a été rejouée en entier sur le code final (résultat ci-dessus). L'exécution PostgreSQL a été faite sur ce même code final.

Non exécutés : suite complète du projet (réservée au candidat final à l'intégration), Windows, Safari, iPhone, lecteur d'écran.

## 8. Relecture indépendante

Relecture par un agent distinct, lecture seule. Verdict initial « à corriger », aucun bloquant. Traitement :

| Remarque | Suite donnée |
|---|---|
| Actions d'administration sans permission (importante) | Corrigée (N3) et prouvée. |
| Le socle divergeait du middleware ; lecture d'objet trompeuse ; code non utilisé (importante) | Socle simplifié : facteur « équipage à terre », `VALIDER`, `service_id`, `strict` et `exception_a_terre` retirés ; lecture d'objet refusée ; une seule source pour l'équipage à terre. |
| Monde sans profil d'autre bâtiment ni soutien à terre (importante) | Ajoutés (`cdt_abe`, `admin_abe`, `soutien_terre`) et étendus aux accès V03, V04, V07, V13, V15, V16. |
| Surfaces d'élévation sans preuve : réglages, comptes web (importante) | Ajout de V15 (activation de module), V16 et V17 (attribution de rôle par le web). Restent sans preuve exécutée de ce lot : quarts, échanges, feuille de service (voir §6). |
| Contrôles déclarés non confrontés au code (importante) | Partiellement : toute route d'API doit déclarer une permission ; la confrontation complète reste une limite documentée (§6). |
| Cloisonnement des tâches seulement éprouvé pour l'alerte de stock | Formulations corrigées (docstring, justification des règles). |
| Test de données publiques sur base vide | Corrigé (monde fictif). |
| Un 404 d'adresse passe pour un refus | Exigence d'un profil témoin ou d'un code exact (V09, V11). |
| Commandes de gestion et signaux non inventoriés | Exclusion déclarée (§3) ; pas de test. |
| Adresses d'essai, méthodes OPTIONS/HEAD, authentification HTTP, JSON et HTMX | Ajoutés. |
| Champs déclaratifs non lus, lots des vérifications non contrôlés, date en dur, vocabulaire du middleware | `nature` retiré ; modules et lots vérifiés ; date calculée ; vocabulaire renommé `middleware_equipage_a_terre`. Le champ `justification` des règles reste purement documentaire. |
