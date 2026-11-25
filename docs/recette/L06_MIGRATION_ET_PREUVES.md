# Lot L06 — séparation des autorités technique et métier : migration et preuves

> **DOCUMENT PROVISOIRE — DIFFUSION RESTREINTE.** Données fictives uniquement ; aucun secret. Lot livré sur sa branche, **non fusionné** ; clôture soumise à la validation du PO.

Décisions : `docs/DECISIONS_PO.md` ARB-01, ARB-06, AC-01, AC-02. Plan : `docs/PLAN_LOTS_REPRISE.md` fiche L06. Base de travail : `c355310` (L29 validé).

## 1. Ce que fait le lot

- **Deux rôles indépendants.** `UserProfile.administrateur_technique` (droits techniques d'unité) est distinct du rôle métier (`role`). Ils se cumulent explicitement ; un administrateur technique seul a le niveau métier d'un équipier. Le rôle `ADMIN_NAVIRE` est retiré de l'échelle métier : conservé uniquement comme valeur obsolète pour les migrations historiques, `UserProfile.save()` le refuse. `RoleLevel.ADMIN_NAVIRE` n'est plus que le palier des droits techniques (`niveau_pour_action`).
- **Trois statuts d'administration distincts (AC-11)** : administrateur général Matrix (rôle `MASTER_ADMIN`), administrateur technique du bâtiment (indicateur), superutilisateur Django (`is_superuser`) ; `matrix.core.roles.statuts_d_administration`. Voir les limites au §12 et la question n° 1 du §13.
- **Aucune déduction.** Un nouvel administrateur ne reçoit aucun droit métier. La migration ne déduit jamais une fonction du statut d'administrateur et n'en promeut aucun (AC-01, AC-14).
- **Planchers d'autorité (AC-02).** `ActionSeuil.plancher` : structure et administration de l'unité, activation des modules, types de programme exigent au moins le commandant ; le paramétrage peut renforcer, jamais abaisser.
- **Seuils métier (AC-13).** Seul le commandement (ou l'administrateur général) modifie un seuil métier ; l'administrateur technique seul consulte les seuils (lecture seule dans l'onglet « Sécurité ») et règle les seuils techniques.
- **Auto-attribution refusée.** Personne ne modifie son propre rôle ni ses droits techniques ; l'administrateur technique ne désigne aucune autorité métier ; le commandant (et l'administrateur général) désigne et révoque le commandant en second (AC-10), le second ne s'attribue rien et ne désigne pas son successeur.
- **Réinitialisation des mots de passe (AC-12).** Niveaux de protection (`accounts/services.py`) : équipier à chef de service sans autre autorité → administrateur technique ; commandant adjoint, second, commandant, administrateur technique, compte cumulant une autorité, une désignation ou des droits Django → administrateur général ; administrateur général et superutilisateur → procédure de récupération locale. Mot de passe provisoire expirant, remplacé par le titulaire, sessions invalidées, titulaire notifié, essais répétés verrouillés (compteur en base `EchecConnexion`, partagé entre processus, `accounts/authentification.py`) ; l'échéance n'est pas modifiable par l'API.
- **Initialisation des premières autorités (AC-09)** : `manage.py initialiser_autorites_batiment` (une fois par bâtiment, verrou en base) ; récupération exceptionnelle : `manage.py recuperer_acces_administrateur`.
- **Fonctions à confirmer (AC-14)** : migration `0025` ; espace « Fonctions à confirmer » dans l'annuaire, compteur, décisions historisées.
- **Réutilisation du socle L29** : registre d'accès, matrice exécutée (`matrix/tests/habilitation/`), vérifications V01 à V26 ; aucun système d'autorisation parallèle.

## 2. Inventaire initial des usages

| Mesure à `c355310` | Valeur |
|---|---|
| Références à `ADMIN_NAVIRE` hors tests et migrations (code, gabarits, commentaires) | 46 |
| Références dans les tests (42 fichiers) | 101 |
| Appels de comparaison de niveau (`user_role_level`, `niveau_ecriture`) | 114 |
| Seuils du registre fixés au palier 8 | 4 (structure, administration de l'unité, réinitialisation de mot de passe, types de programme) |
| Constantes de niveau 8 hors registre | 2 (création de formation, guide de style) |

Destination de chaque usage : droit **technique** (indicateur : réinitialisation de mot de passe, création de formation, guide de style, onglet « Sécurité », attribution des droits techniques) ; droit **métier** relevé au commandant (structure et administration de l'unité, types de programme, modules, relève, tableau COMANAV, délais d'activation) ; supprimé (désignation d'autorités par l'administrateur).

## 3. Matrice de correspondance des comptes (avant / après)

| Compte avant migration | Après migration | Justification |
|---|---|---|
| `ADMIN_NAVIRE`, avec ou sans fonction de commandant adjoint renseignée sur la fiche | rôle `EQUIPIER` + `administrateur_technique` | un administrateur d'unité n'exerçait aucune fonction (le champ n'est actif que pour l'état-major) : rien n'est déduit (AC-01). La valeur de la fiche est retirée de la fiche et journalisée (`fonction_a_confirmer`) : le retour arrière la rétablit, une autorité habilitée la confirme |
| Tout autre rôle | inchangé, `administrateur_technique` faux | aucune élévation |
| Désignations indépendantes du rôle (chef de liste, rédacteur BSC, référent de formation, responsable de spécialité) | inchangées | elles ne dérivent pas du rôle |

Chaque conversion écrit une ligne d'audit `l06_migration_role` (ancien rôle, nouveau rôle, fonction à confirmer, sans mot de passe). Une fonction métier non établie doit être **confirmée par une autorité habilitée** après migration : aucun outil de confirmation n'est livré (voir `docs/recette/L06_PROPOSITION_INITIALISATION.md`).

**Absence d'élévation, démontrée** : aucun compte ne change de rôle autrement que de `ADMIN_NAVIRE` (niveau 8) vers `EQUIPIER` (1) ; sur la base fictive de 11 comptes, 8 comptes non administrateurs sont inchangés, 3 administrateurs convertis, 3 lignes d'audit.

## 4. Migration, sauvegarde, restauration (environnements de test, données fictives)

Migration `accounts/0024_administrateur_technique` : ajout du champ, mise à jour des choix, conversion des comptes (`RunPython`), sens inverse restaurant `ADMIN_NAVIRE` d'après le journal.

Procédure rejouée sur les deux moteurs, depuis une base créée par le code `c355310` et peuplée de comptes fictifs (trois administrateurs, dont un avec fonction de commandant adjoint sur la fiche, et un autre titulaire de la même fonction) :

| Étape | SQLite | PostgreSQL 16 |
|---|---|---|
| Sauvegarde avant migration (copie de fichier / `pg_dump -Fc`) | faite | faite (1,6 Mo) |
| Migration vers L06 | `0024` appliquée, 3 comptes convertis, 3 lignes d'audit | idem |
| Retour arrière (`migrate accounts 0023`) | profils identiques à l'état initial, aucune ligne d'audit | idem |
| Restauration depuis la sauvegarde (base neuve) | profils identiques à l'état initial | idem |

Conditions de retour arrière : le retour arrière du schéma restaure les rôles d'origine **tant que le journal n'est pas purgé** ; les comptes créés ou modifiés après migration ne sont pas reconstitués. La seule garantie de retour est la sauvegarde préalable. Aucun retour arrière sur une base sans sauvegarde. Un merge ne vaut pas garantie de réversibilité.

## 5. Droits avant / après (matrice complète)

| Acte | Admin d'unité (avant) | Administrateur technique seul | Commandant | Administrateur général |
|---|---|---|---|---|
| Publier, viser, valider échanges et listes ; déplacer un ticket | oui (niveau 8) | non | selon ses droits | niveau 9 (voir §12) |
| Lire la passation, le tableau COMANAV | oui | non | oui | oui |
| Relève d'équipage, onglet Équipage | oui | non | oui | oui |
| Structure de l'unité, archivage, double équipage, fuseau, modules, types de programme | oui | non | oui (plancher) | oui |
| Seuils de rôle métier | tout abaissement | lecture seule | modifier, jamais sous un plancher | oui |
| Seuils techniques (ex. réinitialisation) | oui | oui | non (sauf cumul) | oui |
| Désigner une autorité (rôle) | jusqu'au sien | aucune | second, adjoints, chefs, équipiers | tous sauf lui-même |
| Désigner le commandant | oui | non | non | oui |
| Se donner un rôle ou des droits | oui | non | non | non (tiers seulement) |
| Attribuer les droits techniques à un compte qui n'en a pas | n/a | oui (annuaire, API) | non | oui |
| Retirer les droits techniques d'un administrateur technique | n/a | non (administrateur général) | non | oui |
| Confirmer, corriger, refuser une fonction à confirmer | n/a | non | oui (son bâtiment) | oui |
| Réinitialiser le mot de passe : équipier à chef de service | oui | oui | non | oui |
| Réinitialiser : adjoint, second, commandant, administrateur technique, compte cumulant | oui | non | non | oui |
| Réinitialiser : administrateur général | oui | non | non | récupération locale |
| Créer une formation du catalogue | oui | oui | non | oui |
| Annuaire | lecture et écriture | lecture, droits techniques, mots de passe | lecture et écriture | oui |
| Initialiser un bâtiment, récupérer l'accès | n/a | non (commande serveur) | non | non (commande serveur) |

Superutilisateur Django : accès à l'administration Django et, aujourd'hui, mêmes droits d'application que l'administrateur général (§12).

## 6. Critères d'acceptation

| Critère | Preuve |
|---|---|
| CA-L06-1 Un administrateur seul ne valide, ne publie ni ne vise aucun acte | V01, V05, V06, `test_l06_autorites` (`peut_publier_liste`, `peut_gerer_liste`) |
| CA-L06-2 Un administrateur ne s'attribue pas d'autorité | V08, V17, V09, V20 |
| CA-L06-3 Cumul administrateur + fonction possible | `cdt_admin` : V01, V05, V13, V15, V18 ; `test_le_cumul_garde_les_deux_roles_independants` |
| CA-L06-4 Seuil inférieur au plancher refusé ; pas d'auto-élévation par abaissement | V21, V26, `test_les_autorites_minimales_ne_peuvent_pas_etre_abaissees`, V24 (jumeau sans plancher) |
| CA-L06-5 Le second n'a que ses prérogatives | V05, V06, V15 (le second ne gère plus les modules) |
| CA-L06-6 Tout changement d'habilitation est tracé | audit `changement_role`, `update_role_threshold`, `l06_migration_role` |
| CA-L06-7 Migration des comptes sans élévation, réversible | `test_l06_migration`, procédure du §4 sur SQLite et PostgreSQL |
| CA-L06-8 Aucune déduction de fonction | `test_aucun_droit_metier_deduit_du_statut_d_administrateur`, migration |
| CA-L06-9 Droits légitimes préservés | V18, V22, V25 ; suites complètes inchangées hors tests adaptés (§7) |
| CA-L06-10 Initialisation unique et verrouillée, sans secret ni contournement permanent | `accounts/tests/test_initialisation_et_recuperation.py` (usage unique, contrainte en base, cumul explicite, administrateur général refusé, récupération séparée et sans secret dans l'audit) |
| CA-L06-11 Commandant en second désigné et révoqué par le commandant ou l'administrateur général seulement | `matrix/tests/habilitation/test_l06_statuts.py` (désignation, révocation, historique, refus technique, état-major, second) ; `test_core_permissions` |
| CA-L06-12 Trois statuts d'administration distincts, cumul explicite | `statuts_d_administration` (`test_l06_statuts`) ; limites et question au PO : §12 et §13 |
| CA-L06-13 Réinitialisation selon le niveau de protection le plus élevé, provisoire, expirante, sessions révoquées, titulaire notifié, essais répétés verrouillés | `accounts/tests/test_reinitialisation_ac12.py` ; V22, V23 ; `test_l06_autorites` (échéance non modifiable, comptes d'administration Django, retrait des droits d'un pair) ; test des relations vers le compte |
| CA-L06-14 Aucun seuil métier modifiable par l'administrateur technique seul ; planchers intacts ; modifications historisées | V24, V26, V21 ; `SeuilsTechniqueTests` |
| CA-L06-15 Fonction non confirmée sans droit ; confirmation, correction, refus ; concurrence, auto-attribution, cohérence | `accounts/tests/test_fonctions_a_confirmer.py` ; `test_l06_migration` (demande créée par la migration) |
| Parité web / API / administration, accès directs aux fonctions masquées | `test_l06_statuts` (`InterfaceTechniqueTests`, parité), `test_l06_autorites` (`ApiProfilsTests`) |

## 7. Écarts L29 : corrigés par L06 et restants

| Vérification L29 | Écart d'origine | État après L06 |
|---|---|---|
| V01 | l'administrateur lisait la passation | **corrigé** |
| V01 | un chef de section, un chef d'un autre service et un adjoint hors de ses services lisent le même contenu | **restant** (L30) |
| V05, V06 | l'administrateur déplaçait un ticket et le faisait avancer | **corrigés** |
| V08, V17 | l'administrateur s'attribuait le rôle de commandant (API et web) | **corrigés** |
| V10 | un adjoint modifie la tâche d'un autre service | **restant** (L32) |
| A25 sur l'alerte de stock | tâche planifiée active malgré le module désactivé | **restant** (L34) |
| A3 (seuil de publication), A4 (second, écran et API) | | **restants** (L08) |

Nouvelles vérifications : V13 (organisation), V15 (modules), V16, V25 (attribution de rôle par le web), V18 (désignation légitime par l'API), V19, V20 (droits techniques), V21, V24, V26 (seuils), V22, V23 (mot de passe).

## 8. Tests existants adaptés

46 fichiers de tests ont été modifiés ou ajoutés. Règle appliquée : un test qui créait un « administrateur d'unité » pour exercer un acte métier crée désormais un commandant ; un test qui exerçait un droit technique crée un administrateur technique ; un test qui affirmait qu'un droit disparu était acquis a été réécrit pour affirmer le nouveau refus. Aucun test n'a été supprimé ni ignoré.

Changements observables voulus par les décisions : le commandant en second ne gère plus les modules ; l'état-major ne désigne plus les chefs de service ; le commandant peut modifier la structure, l'administration de l'unité et le fuseau (il le pouvait déjà via ses seuils configurables, désormais plancher) ; la désignation du commandant en second et du commandant n'est plus possible que par l'administrateur général.

## 9. Résultats des tests

Suites complètes (`manage.py test --parallel 4 --noinput`), même machine, mêmes réglages. Références : `c355310` (L29) et l'état intermédiaire `326387b` (code de `2fa183a`).

| Exécution | Moteur | Tests | Résultat | Ignorés |
|---|---|---|---|---|
| Référence `c355310` | SQLite | 4021 | OK | 20 |
| Référence `c355310` | PostgreSQL 16 | 4021 | OK | 22 |
| Intermédiaire `326387b` | SQLite | 4045 | OK | 20 |
| Intermédiaire `326387b` | PostgreSQL 16 | 4045 | OK | 22 |
| **Final `e004ee6`** | SQLite | **4083** | OK | 20 |
| **Final `e004ee6`** | PostgreSQL 16 | **4083** | OK | 22 |

+62 tests par rapport à la référence ; aucun supprimé ni affaibli ; mêmes tests ignorés qu'en référence sur chaque moteur. Les tests existants modifiés l'ont été par décision du PO (§8 et AC-10, AC-12, AC-13) : commandant en second désigné par le commandant ; la réinitialisation relève de l'administration technique même si son seuil est abaissé ; l'administrateur technique ne règle plus un seuil métier ; le compte d'un administrateur technique est modifiable pour sa fonction métier. Le test dépendant de l'heure (`test_poste_vacant_visible_sans_relève_interne`) est fiabilisé sans toucher à ses assertions.

Migrations 0024 à 0027, retour arrière et restauration, rejoués sur les deux moteurs avec des données fictives : 3 administrateurs convertis en équipier + droits techniques, 3 lignes d'audit, 1 fonction à confirmer en attente, aucune anomalie de cohérence ; retour arrière et restauration identiques à l'état initial (`migration_sqlite.log`, `migration_pg.log` de l'archive, §14).

## 10. Relectures indépendantes

| Relecture | État relu | Verdict | Suites |
|---|---|---|---|
| 1 | `fb51920` | **À corriger** (désignation de fonction par l'API, périmètre, drapeau, traçabilité, seuils, désignations, migration) | corrigées dans `dedb41d` |
| 2 | `dedb41d` | **À corriger** (abaissement de seuils de circuits, désignations incomplètes, promotion à la migration, seuil au palier obsolète, test creux) | corrigées dans `24b26b8`, `7621ade` |
| 3 | `7621ade` | Valide avec réserves (comptes d'administration Django réinitialisables, mineurs) | corrigées dans `326387b` |
| 4 | `432733e` (lot complet, AC-09 à AC-14) | Valide avec réserves : échéance du mot de passe provisoire modifiable par l'API, verrouillage local au processus, retrait des droits d'un pair puis reprise de son compte, mineurs | corrigées dans `e004ee6` |
| 5 | **`e004ee6`, état final testé** | **Valide avec réserves, aucun bloquant, aucune élévation de privilège, aucun défaut n'exige de correction du code** | — |

La dernière relecture favorable porte exactement sur le dernier état de code testé (`e004ee6`) ; les commits suivants ne modifient que la documentation et l'archive des preuves. Mineurs de la relecture 5, non corrigés (aucun ne justifiait de rouvrir le code) : compteur d'échecs non atomique sur SQLite (pertes d'incréments, `database is locked` possible sous forte concurrence ; PostgreSQL : verrou de ligne) ; table `EchecConnexion` sans purge (une ligne par identifiant essayé) ; une requête API Basic fausse compte deux échecs. Ils sont repris au §13.

## 11. Réserves du rapport intermédiaire : corrigées et résiduelles

| Réserve | État |
|---|---|
| Cohérence web / API sur le rôle d'un compte technique | **corrigée** : le commandant modifie la fonction métier, jamais le drapeau technique (web et API) ; la suppression d'un compte technique reste à l'administrateur général |
| Annuaire absent de la navigation du technique ; gestion des droits techniques par l'API seulement | **corrigées** : entrée « Annuaire » ; menu « Attribuer / Retirer les droits techniques » (jamais sur soi-même, audité) ; l'onglet « Sécurité » est joint depuis « Paramètres » |
| Liste manuelle des désignations sensibles | **centralisée** (`niveaux_de_protection`) ; un test échoue si une relation vers le compte n'est ni dans `DESIGNATIONS` ni dans la liste des relations examinées |
| Test dépendant de l'heure | **corrigé** : instant de référence maîtrisé pour la démonstration et le jour testé (le défaut venait d'un écart entre l'instant de création des créneaux et la date calculée ensuite, autour de minuit) ; assertions inchangées |
| Références obsolètes à `ADMIN_NAVIRE` | **corrigées** dans le code, les gabarits et la documentation vivante ; restent la valeur obsolète du modèle, la migration 0024 et l'historique des documents archivés |
| Conservation des preuves | **archive** `L06_preuves.tar.gz` avec empreinte SHA-256 (§14) |

Résiduelles : `statuts_d_administration` et `anomalies_de_coherence` ne sont utilisées que par les tests et les rapports (classification et contrôle de cohérence, sans comportement d'exécution) ; navigation (le lien « Paramètres » ouvre l'onglet notifications ; l'onglet « Sécurité » se choisit dans la page) ; confirmation d'une fonction : la fonction n'est appliquée que si aucun autre titulaire actif ne la tient ; les comptes Django `is_staff` ou à droits Django sont protégés au niveau « administrateur général » ; l'administrateur général et le superutilisateur Django restent équivalents dans l'application (§12).

## 12. Frontière de confiance et mesures d'exploitation

Les contrôles de Matrix sont **applicatifs**. Un superutilisateur Django, un opérateur qui a accès au serveur, à la base de données ou aux sauvegardes, ou qui peut exécuter du code, **peut contourner ces contrôles** : cela n'est pas empêché techniquement et ce document ne le prétend pas. Mesures d'exploitation nécessaires :
- limiter le nombre de superutilisateurs Django et d'opérateurs système ; comptes nominatifs, jamais partagés ;
- exécuter l'initialisation et la récupération (commandes de gestion) uniquement depuis le serveur, sur autorisation écrite dont la référence est consignée (`--autorisation`) ;
- protéger et journaliser l'accès au serveur et à la base ; sauvegardes chiffrées ou à accès restreint ; contrôle périodique du journal d'audit (`AuditLog`) : `initialisation_batiment`, `recuperation_acces`, `changement_droits_techniques`, `changement_role`, `reinitialisation_mot_de_passe`, `fonction_a_confirmer_*` ;
- ne jamais ouvrir l'administration Django au réseau du bord en dehors d'une intervention ;
- limite de portée de L06 : l'administrateur général (rôle `MASTER_ADMIN`) et le superutilisateur Django conservent le niveau 9 dans l'application, y compris sur des actes métier courants. Le retirer exige de classer chaque acte (gouvernance ou métier) : voir la question n° 1 du §13. La migration 0024/0025 n'attribue aucun droit à ces comptes.

## 13. Questions au PO et points à arbitrer

1. **Administrateur général : retrait des droits métier courants (AC-11).** Un essai de retrait du niveau 9 sur les écritures métier fait échouer 32 tests existants, qui sont des actes de gouvernance (créer ou supprimer un bâtiment, configurer le plan d'un navire, rattacher des marins à une section, définir des exigences de formation de la flotte). Quels actes relèvent de la gouvernance (maintenus) et lesquels du métier courant (retirés) ? Faut-il aussi dissocier le superutilisateur Django de l'administrateur général dans l'application ? Non implémenté sans cette classification.
2. **Remise du mot de passe provisoire (AC-12).** Il est remis oralement par l'autorité habilitée (affiché une seule fois). Un autre moyen de remise sans messagerie (pli, jeton imprimé) est-il souhaité ?
3. **Récupération d'un administrateur général** : commande serveur avec autorisation consignée ; une double validation (deux opérateurs) est-elle exigée ?
4. **Durée de validité du mot de passe provisoire** (48 h par défaut) et **seuil d'essais** (5 essais, 15 minutes) : configurables par l'environnement ; valeurs à confirmer.
5. **Gestion des administrateurs techniques** : l'administrateur technique d'un bâtiment attribue les droits techniques à un compte qui n'en a pas ; **le retrait** des droits d'un administrateur technique existant est réservé à l'administrateur général (sinon un technique pourrait retirer les droits d'un pair puis réinitialiser son mot de passe). Faut-il aussi réserver l'attribution à l'administrateur général ?
7. **Catalogue de formations** : tout administrateur technique de bâtiment écrit le catalogue commun à la flotte (comportement hérité de l'ancien administrateur d'unité). Est-ce compatible avec « aucun droit métier automatique » ?
8. **Mineurs de la relecture finale, non corrigés** : compteur d'échecs de connexion non atomique sur SQLite ; table `EchecConnexion` sans purge ; une requête API Basic fausse compte deux échecs (verrou plus strict en API).
9. **Risques acceptés** : (a) un administrateur technique obtient l'autorité complète d'un chef de service en réinitialisant son compte (garde-fous : trace et notification du titulaire) ; (b) quiconque connaît un identifiant peut le verrouiller 15 minutes ; (c) le mot de passe provisoire ouvre plusieurs sessions jusqu'au changement obligatoire ou à l'expiration ; (d) un retour arrière de la migration ne restaure pas un compte dont le rôle a changé depuis (par exemple après confirmation d'une fonction).
6. **Délégations** : la désignation d'une autorité habilitée à modifier les seuils (AC-13, AC-02) attend L08.

## 14. Archive des preuves

`docs/recette/preuves/L06_preuves.tar.gz` (empreinte SHA-256 dans `L06_preuves.tar.gz.sha256`, même dossier) : références Git testées, environnements, commandes, résultats complets, journaux de migration et de restauration, rapports de relecture, empreinte SHA-256 (fichier `SHA256SUMS`), après vérification de l'absence de secrets. Fournie séparément au PO ; un chemin temporaire n'est pas un archivage durable.
