# Lot L06 — séparation des autorités technique et métier : migration et preuves

> **DOCUMENT PROVISOIRE — DIFFUSION RESTREINTE.** Données fictives uniquement ; aucun secret. Lot livré sur sa branche, **non fusionné** ; clôture soumise à la validation du PO. Décisions : ARB-01, ARB-06, AC-01, AC-02, AC-09 à AC-21 (`docs/DECISIONS_PO.md` §9 à §11).

Décisions : `docs/DECISIONS_PO.md` ARB-01, ARB-06, AC-01, AC-02. Plan : `docs/PLAN_LOTS_REPRISE.md` fiche L06. Base de travail : `c355310` (L29 validé).

## 1. Ce que fait le lot

- **Deux rôles indépendants.** `UserProfile.administrateur_technique` (droits techniques d'unité) est distinct du rôle métier (`role`). Ils se cumulent explicitement ; un administrateur technique seul a le niveau métier d'un équipier. Le rôle `ADMIN_NAVIRE` est retiré de l'échelle métier (valeur obsolète conservée pour les migrations historiques, `save()` la refuse). `RoleLevel.ADMIN_NAVIRE` n'est plus que le palier des droits techniques (`niveau_pour_action`).
- **Trois statuts d'administration distincts (AC-11, AC-15).** *Administrateur général Matrix* : indicateur `UserProfile.administrateur_general`, indépendant du rôle métier ; il porte la gouvernance globale et **aucun droit métier courant** (`RoleLevel.MASTER_ADMIN` n'est plus un niveau atteint par un rôle : la gouvernance est exercée par des contrôles explicites, jamais par une exception fondée sur le niveau 9). *Administrateur technique du bâtiment* : indicateur, administration technique de son périmètre. *Superutilisateur Django* : `is_superuser`, réservé aux interventions techniques exceptionnelles ; **il ne confère plus aucune prérogative de gouvernance ni fonction métier** dans les interfaces applicatives ordinaires. `matrix.core.roles.statuts_d_administration` les distingue.
- **Gouvernance de l'administrateur général (AC-15), explicite.** Création et administration des bâtiments, structure et plan des bâtiments, désignation et révocation du commandant et du commandant en second, rattachement des marins aux bâtiments, droits techniques, référentiels communs de la flotte, catalogue commun de formations et exigences communes, configuration générale de Matrix. Chaque acte est déclaré (`ActionSeuil.gouvernance`, contrôles dédiés) ; **non conférés** : circuits métier d'un bâtiment, échanges de garde, visa des feuilles, maintenance, passations confidentielles, modules, relève, supervision de commandement, fonctions courantes du commandant. Une fonction métier ne s'exerce que si elle lui a été explicitement attribuée (rôle du profil), dans son périmètre.
- **Aucune déduction.** Un nouvel administrateur ne reçoit aucun droit métier ; les migrations ne déduisent jamais une fonction d'un statut (AC-01, AC-14) et n'attribuent aucun droit à un administrateur général existant (rôle métier minimal).
- **Planchers et seuils (AC-02, AC-13).** Les planchers ne s'abaissent jamais. Seul le commandement modifie un seuil métier ; l'administrateur technique seul consulte les seuils (lecture seule) et règle les seuils techniques ; l'administrateur général n'en règle aucun métier.
- **Désignations (AC-10, AC-19).** Le commandant et l'administrateur général désignent et révoquent le commandant en second ; personne ne se désigne ni ne modifie ses propres droits. **Seul l'administrateur général attribue et révoque les droits techniques**, nominativement, avec justification obligatoire et trace d'audit.
- **Réinitialisation du mot de passe par code à usage unique (AC-12, AC-16).** Le mot de passe provisoire est supprimé. Une autorité habilitée (matrice AC-12, niveau de protection le plus élevé en cas de cumul) déclenche une demande ; Matrix génère un code temporaire (seule son empreinte salée est conservée), valable 30 minutes, 5 essais, remis au titulaire après vérification de son identité ; le titulaire définit lui-même son mot de passe sur une page publique ; le code est alors invalidé et les sessions anciennes tombent ; le code n'authentifie jamais. **Pour un compte porteur d'une autorité, deux codes sont exigés et le second n'est généré que lorsqu'un second responsable distinct et compétent a validé l'identité depuis sa propre session : l'initiateur seul ne peut pas terminer le parcours.**
- **Récupération d'un administrateur général (AC-17).** Deux opérateurs habilités distincts, chacun authentifié séparément (identité système du processus + phrase secrète personnelle), en deux exécutions locales, justification obligatoire, autorisation de 30 minutes, deux codes, traçabilité complète, sessions anciennes révoquées. Sans administrateur général disponible, les opérateurs peuvent en désigner un parmi les comptes existants. Procédure simplifiée de développement impossible en production.
- **Limitation des connexions (AC-18).** Compteur par couple (identifiant, source réseau) + compteur global détectant l'attaque répartie ; blocage progressif (15, 30, 60 minutes… plafonné) ; un tiers ne peut pas verrouiller le marin depuis son poste habituel ; compteurs atomiques sur SQLite et PostgreSQL ; chaque échec compté une fois ; purge automatique après 30 jours ; compteurs techniques distincts des journaux d'audit ; paramètres réglables dans des bornes non contournables.
- **Initialisation (AC-09)** : `manage.py initialiser_autorites_batiment` (une fois par bâtiment, verrou en base). **Fonctions à confirmer (AC-14)** : migration 0025, espace dédié, compteur, décisions historisées. **Catalogue des formations (AC-20)** : le référentiel commun n'est plus modifiable par l'administrateur technique ; commun = administrateur général, local = commandement.
- **Réutilisation du socle L29** : registre d'accès, matrice exécutée (`matrix/tests/habilitation/`), vérifications V01 à V28 ; aucun système d'autorisation parallèle.

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
| `MASTER_ADMIN` (administrateur général existant) | rôle `EQUIPIER` + `administrateur_general` (migration 0028) | la gouvernance est conservée, **aucun droit métier n'est attribué** ni retiré à tort ; une fonction métier devra lui être explicitement attribuée (AC-15) |
| Compte portant un mot de passe provisoire (migration 0029) | mot de passe rendu inutilisable ; réinitialisation par code | le mécanisme provisoire est supprimé (AC-16) ; aucune session ni connexion ne reste ouverte par un ancien provisoire |
| Superutilisateur Django sans rôle `MASTER_ADMIN` | inchangé (aucun statut applicatif attribué) | le superutilisateur n'est pas un administrateur général (AC-15) ; aucune attribution injustifiée |
| Tout autre rôle | inchangé, indicateurs faux | aucune élévation |
| Désignations indépendantes du rôle (chef de liste, rédacteur BSC, référent de formation, responsable de spécialité) | inchangées | elles ne dérivent pas du rôle |

Chaque conversion écrit une ligne d'audit `l06_migration_role` (ancien rôle, nouveau rôle, fonction à confirmer, sans mot de passe). Une fonction métier non établie doit être **confirmée par une autorité habilitée** après migration : aucun outil de confirmation n'est livré (voir `docs/recette/L06_PROPOSITION_INITIALISATION.md`).

**Absence d'élévation, démontrée** : aucun compte ne change de rôle autrement que de `ADMIN_NAVIRE` (niveau 8) vers `EQUIPIER` (1) ; sur la base fictive de 11 comptes, 8 comptes non administrateurs sont inchangés, 3 administrateurs convertis, 3 lignes d'audit.

## 4. Migration, sauvegarde, restauration (environnements de test, données fictives)

Migrations `accounts` : `0024` (indicateur technique, conversion des administrateurs d'unité sans promotion, sens inverse d'après le journal) ; `0025` (fonctions à confirmer, échéance du mot de passe provisoire) ; `0026` (verrou d'initialisation d'un bâtiment) ; `0027` (compteur d'échecs, remplacé par 0029) ; `0028` (indicateur d'administrateur général, rôle `MASTER_ADMIN` converti sans attribution, réversible) ; `0029` (demandes de réinitialisation, opérateurs de récupération, compteurs de connexion ; suppression du mot de passe provisoire dont les comptes porteurs reçoivent un mot de passe inutilisable).

Procédure rejouée sur les deux moteurs, depuis une base créée par le code `c355310` et peuplée de comptes fictifs (trois administrateurs, dont un avec fonction de commandant adjoint sur la fiche, et un autre titulaire de la même fonction) :

| Étape | SQLite | PostgreSQL 16 |
|---|---|---|
| Sauvegarde avant migration (copie de fichier / `pg_dump -Fc`) | faite | faite (1,6 Mo) |
| Migration vers L06 | `0024` à `0029` appliquées, 3 administrateurs convertis, 3 lignes d'audit, 1 fonction à confirmer, 1 administrateur général converti, 1 mot de passe provisoire invalidé | idem |
| Retour arrière (`migrate accounts 0023`) | profils identiques à l'état initial, aucune ligne d'audit | idem |
| Restauration depuis la sauvegarde (base neuve) | profils identiques à l'état initial | idem |

Conditions de retour arrière : le retour arrière du schéma restaure les rôles d'origine **tant que le journal n'est pas purgé** ; les comptes créés ou modifiés après migration ne sont pas reconstitués. La seule garantie de retour est la sauvegarde préalable. Aucun retour arrière sur une base sans sauvegarde. Un merge ne vaut pas garantie de réversibilité.

## 5. Droits avant / après (matrice définitive des autorités)

Légende : **G** = gouvernance (explicite) ; **M** = métier ; **T** = technique. Les colonnes « seul » désignent un compte sans autre statut.

| Acte | Classe | Admin d'unité (avant) | Admin. technique seul | Commandant | Admin. général seul | Superutilisateur Django seul |
|---|---|---|---|---|---|---|
| Publier, viser, valider échanges et listes ; déplacer un ticket ; visa feuilles ; maintenance | M | oui (niveau 8) | non | selon ses droits | **non** | non |
| Lire la passation confidentielle, la Vue COMANAV, la supervision de maintenance | M | oui | non | oui (commandement) | **non** | non |
| Relève d'équipage, activation des modules, types de programme | M | oui | non | oui (plancher) | **non** | non |
| Seuils de rôle métier | M | tout abaissement | lecture seule | modifier, jamais sous un plancher | **non** | non |
| Seuils techniques (ex. réinitialisation) | T | oui | oui | non (sauf cumul) | oui | non |
| Créer, supprimer, configurer un bâtiment ; structure, plan, fuseau, double équipage | G | oui | non | structure : oui (plancher) | **oui** | non |
| Référentiels communs de la flotte, configuration générale | G | oui | non | non | **oui** | non |
| Désigner le commandant | G | oui | non | non | **oui** | non |
| Désigner et révoquer le commandant en second | G | oui | non | **oui** | **oui** | non |
| Désigner les autres autorités (adjoints, chefs, équipiers) | M | jusqu'au sien | non | oui | **non** | non |
| Rattacher un marin à un bâtiment | G | oui | non | dans son bâtiment | **oui** | non |
| Attribuer / retirer les droits techniques (nominatif, justifié, audité) | G | n/a | **non** | non | **oui** | non |
| Se donner un rôle ou des droits | — | oui | non | non | non | non |
| Confirmer, corriger, refuser une fonction à confirmer | M | n/a | non | oui (son bâtiment) | non | non |
| Réinitialiser : équipier à chef de service sans autre autorité | T | oui | oui | non | oui | non |
| Réinitialiser : adjoint, second, commandant, administrateur technique, compte cumulant | T | oui | non | non | oui | non |
| Valider l'identité d'un titulaire porteur d'autorité (second responsable) | — | n/a | oui (autre administrateur technique, hors initiateur) | non | oui (autre que l'initiateur) | non |
| Réinitialiser un administrateur général | — | oui | non | non | non (récupération locale à deux opérateurs) | non |
| Catalogue commun de formations ; exigences communes | G | oui | **non** | non | **oui** | non |
| Exigences locales de formation (rattachées à un bâtiment) | M | oui | non | **oui** (son bâtiment) | non | non |
| Désigner un référent de formation, programmer les sessions, valider une qualification | M | oui | non | selon son rôle | **non** | non |
| Supervision globale de la flotte (Vue flotte), tableaux spécialité et classe | G (lecture) | oui | non | non | oui | non |
| Annuaire | — | lecture et écriture | lecture, mots de passe | lecture et écriture | gouvernance (désignations, rattachement, droits techniques) | non |
| Administration Django (`/admin/`) | T | — | non | non | non | **oui** (intervention exceptionnelle) |
| Initialiser un bâtiment, récupérer l'accès d'un administrateur général | — | n/a | non | non | non | non (commandes serveur, opérateurs habilités) |

Un administrateur général qui s'est vu **explicitement attribuer** un rôle métier (par exemple commandant d'un bâtiment) exerce cette fonction dans le périmètre correspondant, sans plus.

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
| CA-L06-16 AC-15 : l'administrateur général exerce la gouvernance sans fonction métier ; aucun acte métier ne lui est conféré ; une fonction attribuée s'exerce dans son périmètre | `test_l06_gouvernance` (`GouvernanceTests`), V05, V06, V15, V26, V27, V28 ; matrice `test_permissions_matrix` (colonne administrateur général) ; classification des 32 tests (§15) |
| CA-L06-17 AC-15 : le superutilisateur Django n'a aucune prérogative applicative | `test_l06_gouvernance.test_superutilisateur_django_sans_fonction_applicative`, `test_core_permissions`, `test_core_scopes`, `test_barre_superieure` |
| CA-L06-18 AC-16 : code à usage unique ; expiré, incorrect, réutilisé, d'un autre compte ou d'une autre demande refusé ; le code n'authentifie pas ; sessions révoquées ; aucun secret en clair | `accounts/tests/test_reinitialisation_codes.py`, `test_reinitialisation_mot_de_passe.py` (`CodeEtConnexionTests`) |
| CA-L06-19 AC-16 : vérification d'identité indépendante imposée aux comptes porteurs d'autorité ; l'initiateur seul ne termine pas le parcours | `VerificationIndependanteTests`, `InterfaceVerificationTests` |
| CA-L06-20 AC-17 : récupération d'un administrateur général par deux opérateurs authentifiés séparément ; un seul opérateur ne peut pas ; procédure simplifiée impossible en production | `accounts/tests/test_initialisation_et_recuperation.py` (`RecuperationTests`) |
| CA-L06-21 AC-18 : valeurs par défaut, comptage exact (API comprise), atomicité, blocage progressif, expiration, purge sans toucher à l'audit, pas de verrouillage par un tiers, adresse partagée | `accounts/tests/test_limitation_connexion.py` |
| CA-L06-22 AC-19 : seul l'administrateur général attribue et révoque les droits techniques, avec justification et audit ; ni création, ni révocation, ni auto-modification par un technique | `test_l06_autorites` (`ApiProfilsTests`), `test_l06_statuts` (`InterfaceTechniqueTests`), V19, V20 |
| CA-L06-23 AC-20 : le référentiel commun n'est plus modifiable par l'administrateur technique ; exigences communes = administrateur général, locales = commandement | `test_l06_gouvernance.CatalogueFormationsTests`, `training/tests/test_scope_requirements.py`, `test_securite_ecritures` |

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

__RESULTATS__

## 10. Relectures indépendantes

__RELECTURES__

## 11. Réserves : corrigées et résiduelles

| Réserve | État |
|---|---|
| Parité web, API et administration Django sur le rôle d'un compte technique | **corrigée** : une autorité métier modifie la fonction métier sans toucher au drapeau technique ; mêmes règles d'attribution (matrice de gestion partagée) au web et à l'API ; l'administration Django journalise rôle et indicateurs |
| Interface des administrateurs techniques | **corrigée** : annuaire dans la navigation, réinitialisation et vérifications d'identité, onglet « Sécurité » en lecture ; la gestion des droits techniques n'est plus de leur ressort (AC-19) : l'administrateur général la trouve dans l'annuaire (justification obligatoire) ; aucune fonction non autorisée n'est affichée |
| Liste manuelle des désignations sensibles | **centralisée** (`niveaux_de_protection`) ; un test échoue si une relation vers le compte n'est ni protégée (`DESIGNATIONS`) ni examinée (`relations_utilisateur_examinees.txt`) |
| Test dépendant de l'heure (`test_poste_vacant_visible_sans_relève_interne`) | **corrigé** : instant de référence maîtrisé pour la démonstration et le jour testé (le défaut venait d'un écart entre l'instant de création des créneaux et la date calculée ensuite, autour de minuit) ; assertions inchangées |
| Références obsolètes à `ADMIN_NAVIRE` | **corrigées** dans le code, les gabarits et la documentation vivante ; restent la valeur obsolète du modèle, les migrations historiques et les documents archivés |
| Conservation des preuves | **archive** `L06_preuves.tar.gz` versionnée avec empreinte SHA-256 (§14) |

Résiduelles : navigation (le lien « Paramètres » ouvre l'onglet notifications ; l'onglet « Sécurité » se choisit dans la page) ; un administrateur général qui s'est vu attribuer un rôle métier exerce cette fonction avec les accès de lecture de gouvernance (fleet) en plus — la lecture de flotte n'est pas bornée à son périmètre de fonction ; `statuts_d_administration` et `anomalies_de_coherence` ne sont utilisées que par les tests et les rapports ; mineurs de la dernière relecture de la phase précédente (compteur, purge, double comptage) **corrigés** par AC-18.

## 12. Frontière de confiance et mesures d'exploitation

Les contrôles de Matrix sont **applicatifs**. Un superutilisateur Django, un opérateur qui a accès au serveur, au code, à la base de données ou aux sauvegardes, ou qui peut exécuter du code, **peut contourner ces contrôles** : la dissociation de l'administrateur général Matrix et du superutilisateur Django (AC-15) supprime les prérogatives applicatives du second dans les interfaces ordinaires, elle ne l'empêche pas d'utiliser l'administration Django ni de modifier les données ; ce document ne prétend pas le contraire. Mesures d'exploitation nécessaires :
- limiter le nombre de superutilisateurs Django et d'opérateurs système ; comptes nominatifs, jamais partagés ;
- exécuter l'initialisation et la récupération (commandes de gestion) uniquement depuis le serveur, sur autorisation écrite dont la référence est consignée (`--autorisation`, `--justification`) ;
- fournir à chacun des deux opérateurs de récupération un compte système **distinct** (jamais root ou un compte de service commun : la commande refuse une identité déjà habilitée et deux opérateurs sur le même compte rendraient la procédure inutilisable) et une phrase secrète personnelle ;
- derrière un mandataire inverse, `REMOTE_ADDR` est l'adresse du mandataire : tous les marins partagent alors la même source et cinq échecs d'un tiers bloquent l'identifiant pour tous. Aucun en-tête transmis n'est cru par défaut ; l'usage d'un mandataire de confiance exige un réglage explicite et documenté de l'exploitant ;
- protéger et journaliser l'accès au serveur et à la base ; sauvegardes chiffrées ou à accès restreint ; contrôle périodique de l'`AuditLog` : `initialisation_batiment`, `recuperation_*`, `changement_droits_techniques`, `changement_administrateur_general`, `changement_role`, `reinitialisation_*`, `connexion_limitee*`, `fonction_a_confirmer_*` ;
- ne jamais ouvrir l'administration Django au réseau du bord en dehors d'une intervention ;
- l'attribution du statut d'administrateur général est une intervention d'exploitation (administration Django ou récupération à deux opérateurs) : elle est tracée mais non justifiée dans l'administration Django.

## 13. Questions au PO et hypothèses de mise en œuvre à valider

Aucune décision métier nouvelle n'a été inventée ; les points suivants sont des interprétations techniques à confirmer :
1. **Supervision en lecture** : la Vue flotte et les tableaux par spécialité ou par classe de navire sont classés « gouvernance » (lecture seule, conservée par l'administrateur général) ; la Vue COMANAV, la supervision de maintenance, les anomalies et les plannings sont classés « métier » (non conférés). La feuille de service publiée (contenu commun) reste lisible par l'administrateur général ; le travail en cours du circuit de visa ne l'est pas.
2. **« Compte disposant d'une autorité métier » (AC-16)** : interprété comme tout rôle d'au moins chef de section, toute fonction de commandant adjoint, toute désignation répertoriée, tout compte à droits d'administration. Un équipier sans désignation est réinitialisé par une seule autorité.
3. **Facteur d'authentification préalable** (seconde option d'AC-16) : non retenu ; le second responsable suffit. Si le bâtiment n'a qu'un administrateur technique, c'est l'administrateur général qui vérifie.
4. **Habilitation des opérateurs de récupération** : par la commande d'installation, deux opérateurs au plus ; comment l'exploitation désigne-t-elle ces deux personnes et leurs comptes système ?
5. **Lecture de flotte d'un administrateur général cumulant un rôle métier** : sa fonction s'exerce dans son bâtiment, mais ses accès de lecture de gouvernance ne sont pas bornés par cette fonction.

## 14. Archive des preuves

`docs/recette/preuves/L06_preuves.tar.gz` (empreinte SHA-256 dans `L06_preuves.tar.gz.sha256`, même dossier) : références Git testées, environnements, commandes, résultats complets, journaux de migration et de restauration, rapports de relecture, sommes de contrôle de chaque fichier, après vérification de l'absence de secrets. Un chemin temporaire n'est pas un archivage durable : l'archive est versionnée avec la branche et fournie séparément au PO.

## 15. Classification des 32 tests de l'expérience de retrait des droits métier (AC-15)

Expérience : retrait du niveau 9 sur les écritures métier de l'administrateur général (journal `essai_retrait_niveau9_administrateur_general_sqlite.log` de l'archive). Pour chaque test : l'acte, sa classe (gouvernance, administration technique ou métier), l'autorité légitime, le comportement retenu, et la justification de l'état du test. Aucun privilège excessif n'est conservé pour maintenir une suite verte : le niveau 9 n'existe plus ; la gouvernance est exercée par des contrôles explicites (`ActionSeuil.gouvernance`, `est_administrateur_general`).

| N° | Test (module · classe) | Acte | Classe | Autorité légitime | Comportement retenu | Modification du test et justification |
|---|---|---|---|---|---|---|
| 1 | `assets.test_plan_navire_web` · `PlanNavirePerimetreTests.test_master_admin_peut_choisir_le_navire_via_selecteur` | Consulter le plan visuel d'un autre bâtiment | Gouvernance (structure des bâtiments) | Administrateur général | Conservé | Le compte est déclaré administrateur général (indicateur) : le superutilisateur Django seul ne l'est plus (AC-15) |
| 2 | idem · `test_master_admin_peut_configurer_un_pont_de_nimporte_quel_navire` | Configurer un pont (plan du bâtiment) | Gouvernance (structure) | Administrateur général | Conservé (`plan_navire_configuration` déclaré gouvernance) | Idem |
| 3 | `assets.test_securite_dossiers_emplacements` · `DossiersPerimetreTests.test_gestion_flotte_garde_tous_les_droits` | Supprimer un dossier de rangement du matériel | Métier | Chef de service du périmètre | Refusé à l'administrateur général | Renommé `test_administrateur_general_ne_gere_pas_les_dossiers_de_materiel_par_son_statut`, assertion inversée : le rangement du matériel n'est pas de la gouvernance |
| 4 | `matrix.tests.habilitation.test_detection` · `test_une_nouvelle_route_d_ecriture_dans_une_famille_connue_change_l_instantane` | Détection d'une route d'écriture ajoutée | Contrôle du dispositif (aucun acte) | — | Instantané régénéré | Les routes `reinitialisation/` et `users/verifications/` sont les nouvelles routes d'écriture validées (règles `PUB-REINITIALISATION`, `WEB-COMPTES`) |
| 5 | `matrix.tests.habilitation.test_inventaire` · `test_toute_route_d_ecriture_est_validee_explicitement` | Idem | Idem | — | Idem | Idem (`instantane_routes_ecriture.txt`) |
| 6 à 9 | `matrix.test_permissions_matrix` · `AssetMatriceTests` : création, modification, suppression (web et API) | Créer, modifier, supprimer un matériel | Métier | Chef de section (écriture), chef de service (suppression) | Refusé à l'administrateur général | La colonne `MASTER_ADMIN` sort de l'échelle des niveaux de la matrice ; un sous-test dédié exécute chaque acte avec un administrateur général sans fonction et exige le refus |
| 10 | idem · `CorrectiveTicketMatriceTests.test_transition_statut_reservee_chef_section` | Faire avancer un ticket correctif | Métier | Chef de section | Refusé | Idem |
| 11 à 13 | idem · `InstallationMaintenanceMatriceTests` : création, modification, suppression | Gérer l'entretien d'une installation | Métier | Chef de section / chef de service | Refusé | Idem |
| 14 à 16 | idem · `InstallationMatriceTests` : création, modification, suppression | Gérer une installation | Métier | Chef de section / chef de service | Refusé | Idem |
| 17 à 19 | idem · `PlanNaviePositionMatriceTests` : placement, repositionnement, retrait d'épingle | Positionner un matériel sur le plan | Métier (la configuration des ponts reste de la gouvernance) | Chef de service | Refusé | Idem ; le contrôle est désormais explicite dans la vue (`place_pin`, `remove_pin`) |
| 20 à 21 | idem · `StockPieceMatriceTests` : création, modification | Gérer une pièce de stock | Métier | Chef de section | Refusé | Idem |
| 22 | `matrix.test_releves_datees_web` · `ApiEtAdministrationTests.test_creation_d_un_batiment_exige_un_fuseau_explicite` | Créer un bâtiment | Gouvernance | Administrateur général | Conservé | Compte déclaré administrateur général (fixture) |
| 23 | `matrix.test_securite_terre_second` · `DefinitionTests.test_administrateur_general_n_est_pas_du_soutien` | Niveau d'écriture de l'administrateur général | Définition | — | Niveau métier minimal (équipier) : aucun droit métier par le statut | Attendu `MASTER_ADMIN` → `EQUIPIER`, avec commentaire ; l'assertion « n'est pas du soutien à terre » est inchangée |
| 24 | `org.test_archivage` · `MaterielEtComptesDesactivesTests.test_l_affectation_en_masse_a_une_section_active_reste_possible` | Rattacher des installations à une section | Métier | Commandement du bâtiment | Refusé à l'administrateur général | L'acteur devient le commandant du bâtiment (le test vérifie la règle d'archivage, non le droit) |
| 25 | idem · `test_l_affectation_en_masse_d_installations_a_une_section_archivee_est_refusee` | Idem | Métier | Commandement | Idem | Idem |
| 26 à 28 | idem · `StockEtListesTests` : nouvelle pièce en secteur actif / archivé, pièce déjà archivée modifiable | Gérer le stock | Métier | Commandement / chef de section | Refusé à l'administrateur général | L'acteur devient le commandant du bâtiment |
| 29 | `org.test_scope_navire` · `ScopeNavireTests.test_master_admin_peut_supprimer_un_navire` | Supprimer un bâtiment | Gouvernance | Administrateur général | Conservé | Compte déclaré administrateur général (fixture) |
| 30 | `org.test_serializers_perimetre` · `SerializersOrgPerimetreTests.test_administrateur_general_sans_perimetre_non_restreint` | Créer un secteur dans n'importe quel bâtiment | Gouvernance (structure) | Administrateur général | Conservé (`structure_navire_ecriture` déclaré gouvernance) | Compte déclaré administrateur général |
| 31 | `training.test_lecture_dossiers` · `PerimetreMarinSansRattachementTests.test_administrateur_general_garde_la_flotte_entiere` | Consulter la flotte ; valider une candidature à une formation | Consultation de périmètre : gouvernance ; validation d'une qualification : métier | Autorité métier habilitée | Périmètre conservé ; **validation refusée** | L'assertion de validation est inversée (AC-20 : validation des qualifications individuelles = autorité métier) |
| 32 | `training.test_scope_requirements` · `ScopeTrainingRequirementTests.test_administrateur_general_voit_tout_et_cree_une_exigence_flotte_entiere` | Définir une exigence commune de formation | Gouvernance | Administrateur général | Conservé (exigence commune) ; l'exigence locale exige le commandement | Compte déclaré administrateur général ; les tests d'exigences locales passent à un commandant (AC-20) |


## 16. Tests existants modifiés, renommés ou retirés (depuis `14babb4`)

Aucun test n'a été supprimé ni affaibli pour obtenir une suite verte : les tests retirés sont remplacés par des tests de même objet sur le mécanisme décidé (AC-16, AC-17, AC-18) ou renommés avec assertion inversée lorsque la décision change le comportement (AC-15, AC-20). Les listes sont produites par comparaison syntaxique des fichiers de tests entre `14babb4` et le code final.

| Fichier | Tests modifiés, renommés ou retirés | Justification |
|---|---|---|
| `accounts/tests/test_admin_navire_limites.py` | modifiés : `test_api_refuse_de_modifier_un_profil_master_admin`, `test_web_refuse_de_modifier_un_profil_master_admin` | Le compte d'administrateur général est un indicateur : l'assertion « rôle MASTER_ADMIN inchangé » devient « indicateur administrateur_general inchangé » ; un administrateur technique ne modifie toujours pas ce compte (AC-15). Un test sur le périmètre est ajouté : l'administrateur technique ne change plus ship/service/secteur. |
| `accounts/tests/test_directory_permissions.py` | modifiés : `test_role_commandant_en_second_visible_dans_l_annuaire` | AC-10 : le commandant et l'administrateur général désignent le commandant en second ; ce dernier figure dans les rôles proposés (l'ancien commentaire « le commandant ne le désigne pas » est périmé). |
| `accounts/tests/test_initialisation_et_recuperation.py` | retirés ou renommés : `test_emet_un_mot_de_passe_provisoire_pour_un_administrateur_general_seulement` ; ajoutés : `_parcours`, `setUp`, `test_aucun_administrateur_general_disponible_les_operateurs_en_designent_un`, `test_authentification_independante_de_chaque_operateur`, `test_commande_en_deux_executions_avec_phrases_saisies_et_identites_distinctes`, `test_deux_codes_et_deux_operateurs_distincts_permettent_la_recuperation`, `test_habilitation_limitee_a_deux_operateurs_et_phrase_solide`, `test_justification_obligatoire_compte_cible_et_delai`, `test_la_procedure_simplifiee_en_developpement_reste_tracee_et_ne_laisse_aucun_operateur`, `test_la_procedure_simplifiee_est_impossible_en_production`, `test_les_sessions_anterieures_sont_revoquees`, `test_un_seul_operateur_ne_peut_pas_valider_sa_propre_demande` | AC-17 : la récupération simple par un opérateur unique est remplacée par la procédure à deux opérateurs (tests ajoutés). |
| `accounts/tests/test_matrice_droits.py` | modifiés : `marin`, `setUp`, `test_reinitialisation_par_role_seuil_par_defaut` | AC-15, AC-16, AC-19 : administrateur général déclaré par indicateur ; onglets « modules » et « équipage » non conférés ; réinitialisation = demande de code (`reinitialisation_demandee`) ; le commandant modifie le compte d'un administrateur technique (parité web/API) ; un seuil abaissé n'habilite pas le commandement à réinitialiser. |
| `accounts/tests/test_reinitialisation_ac12.py` | retirés ou renommés : `setUp`, `test_essais_repetes_verrouillent_meme_avec_le_bon_mot_de_passe`, `test_le_mot_de_passe_provisoire_expire`, `test_le_verrouillage_expire_avec_la_fenetre`, `test_reinitialisation_tracee_notifiee_sans_secret_et_sessions_revoquees`, `test_usage_unique_apres_changement_le_provisoire_ne_sert_plus` | AC-16, AC-18 : les tests du mot de passe provisoire (expiration, connexion, verrouillage par identifiant) sont remplacés par `test_reinitialisation_codes.py` et `test_limitation_connexion.py` ; le tableau des autorités de réinitialisation est conservé. |
| `accounts/tests/test_reinitialisation_mot_de_passe.py` | modifiés : `test_action_groupee_borne_au_batiment`, `test_commandant_et_chef_de_service_ne_peuvent_pas`, `test_marin_d_un_autre_navire_et_soi_meme_refuses` ; retirés ou renommés : `setUp`, `test_l_authentification_basic_de_l_api_n_echappe_pas_a_l_obligation`, `test_le_changement_leve_l_obligation`, `test_page_de_changement_et_deconnexion_restent_accessibles`, `test_toute_page_renvoie_vers_le_changement`, `test_un_mot_de_passe_refuse_ne_leve_pas_l_obligation`, `test_l_administrateur_obtient_un_mot_de_passe_provisoire_affiche_une_fois` ; ajoutés : `setUp`, `test_changer_son_mot_de_passe_depuis_le_profil_reste_possible`, `test_le_code_ne_permet_pas_de_se_connecter_ni_d_appeler_l_api`, `test_l_administrateur_obtient_un_code_a_usage_unique_affiche_une_fois` | AC-16 : le mot de passe provisoire est supprimé ; les tests de droits et de périmètre sont conservés (acteurs, cibles, action groupée, seuil) et portent sur la demande de code ; le code n'authentifie pas ; le mécanisme de changement obligatoire est remplacé (voir les tests retirés). |
| `accounts/tests/test_scope_leak_userprofile_api.py` | modifiés : `setUp` | Fixture : le compte est déclaré administrateur général (indicateur du profil) ; le superutilisateur Django seul ne l'est plus (AC-15). Assertions inchangées. |
| `accounts/tests/test_scope_leak_users_api.py` | modifiés : `setUp` | Fixture : le compte est déclaré administrateur général (indicateur du profil) ; le superutilisateur Django seul ne l'est plus (AC-15). Assertions inchangées. |
| `accounts/tests/test_scope_leak_users_web.py` | modifiés : `setUp` | Fixture : le compte est déclaré administrateur général (indicateur du profil) ; le superutilisateur Django seul ne l'est plus (AC-15). Assertions inchangées. |
| `annonces/tests/test_rappel_accuse.py` | modifiés : `test_modification_validee_et_tracee` | Fixture : le compte est déclaré administrateur général (indicateur du profil) ; le superutilisateur Django seul ne l'est plus (AC-15). Assertions inchangées. |
| `assets/tests/test_liste_materiel_scripts.py` | modifiés : `setUp` | Fixture : le compte est déclaré administrateur général (indicateur du profil) ; le superutilisateur Django seul ne l'est plus (AC-15). Assertions inchangées. |
| `assets/tests/test_plan_navire_web.py` | modifiés : `setUp` | Fixture : le compte est déclaré administrateur général (indicateur du profil) ; le superutilisateur Django seul ne l'est plus (AC-15). Assertions inchangées. |
| `assets/tests/test_securite_dossiers_emplacements.py` | retirés ou renommés : `test_gestion_flotte_garde_tous_les_droits` ; ajoutés : `test_administrateur_general_ne_gere_pas_les_dossiers_de_materiel_par_son_statut` | AC-15 : le rangement du matériel n'est pas de la gouvernance ; test renommé, assertion inversée. |
| `calendar_app/tests/test_perimetre_creneaux.py` | retirés ou renommés : `test_master_admin_voit_les_creneaux_de_la_flotte` ; ajoutés : `test_administrateur_general_ne_voit_pas_les_creneaux_de_la_flotte_par_son_statut` | AC-15 : les plannings de quart sont du métier courant ; l'administrateur général ne les voit plus par son statut ; test renommé, assertion inversée. |
| `dashboard/tests/test_passation.py` | modifiés : `test_activation_reservee_a_l_administrateur_general_et_tracee`, `test_echec_n_annule_pas_la_validation_de_secours` | Fixture : le compte est déclaré administrateur général (indicateur du profil) ; le superutilisateur Django seul ne l'est plus (AC-15). Assertions inchangées. |
| `dashboard/tests/test_supervision.py` | retirés ou renommés : `test_master_admin_sans_perimetre_voit_tout` ; ajoutés : `test_administrateur_general_ne_supervise_pas_la_maintenance_par_son_statut` | AC-15 : la supervision des retards de maintenance est du métier courant ; test renommé, assertion inversée. |
| `dashboard/tests/test_vue_comanav.py` | modifiés : `test_comanav_commandement_et_admin_ont_acces` ; retirés ou renommés : `test_administrateur_sans_batiment_choisi` ; ajoutés : `test_administrateur_general_sans_batiment_n_a_pas_la_vue_comanav` | AC-15 : la Vue COMANAV est une supervision de commandement ; l'administrateur général n'y accède pas par son statut (refus 403 attendu). |
| `dashboard/tests/test_vue_comanav_fuites.py` | modifiés : `test_qualifications_d_un_autre_navire_ecartees` | Acteur : commandant du bâtiment (la fuite inter-bâtiments reste éprouvée) ; l'administrateur général ne consulte plus cette supervision (AC-15). |
| `logistics/tests/test_anomalies.py` | retirés ou renommés : `test_admin_sans_perimetre_voit_tout` ; ajoutés : `test_administrateur_general_ne_consulte_pas_les_anomalies_par_son_statut` | AC-15 : les anomalies relèvent du métier courant ; test renommé, assertion inversée (404). |
| `maintenance/tests/test_rbac_occurrence.py` | modifiés : `test_suppression_occurrence_interdite_via_api` | Fixture : le compte est déclaré administrateur général (indicateur du profil) ; le superutilisateur Django seul ne l'est plus (AC-15). Assertions inchangées. |
| `matrix/tests/habilitation/test_acces_anonyme.py` | modifiés : `test_les_routes_publiques_sont_les_seules_declarees_telles` | Nouvelle route publique déclarée : `reinitialisation/` (page du titulaire, AC-16). |
| `matrix/tests/habilitation/test_l06_autorites.py` | modifiés : `test_le_technique_ne_peut_pas_retirer_les_droits_d_un_pair_pour_reprendre_son_compte`, `test_les_valeurs_de_formulaire_du_drapeau_sont_interpretees` ; retirés ou renommés : `test_l_attribution_et_le_retrait_du_drapeau_sont_traces`, `test_l_echeance_du_mot_de_passe_provisoire_n_est_pas_modifiable_par_l_api` ; ajoutés : `test_seul_l_administrateur_general_attribue_et_retire_les_droits_techniques_avec_justification` | Tests de la phase précédente ajustés à AC-13, AC-19 : l'administrateur technique ne règle plus aucun seuil métier ; seul l'administrateur général attribue et révoque les droits techniques, avec justification ; l'échéance du mot de passe provisoire n'existe plus. |
| `matrix/tests/habilitation/test_l06_migration.py` | ajoutés : `_migrer`, `tearDown`, `test_administrateur_general_converti_sans_attribution_puis_retour_arriere`, `test_un_mot_de_passe_provisoire_existant_est_invalide` | Migrations 0028 et 0029 : tests ajoutés ; le schéma final de référence devient 0029 ; la migration 0024 ne promeut toujours personne. |
| `matrix/tests/habilitation/test_l06_statuts.py` | modifiés : `test_les_trois_statuts_sont_distincts_et_cumulables` ; retirés ou renommés : `test_le_technique_gere_les_droits_techniques_par_l_annuaire_sans_le_menu_metier` ; ajoutés : `test_seul_l_administrateur_general_voit_et_utilise_la_gestion_des_droits_techniques` | AC-19 et AC-15 : la gestion des droits techniques est réservée à l'administrateur général (annuaire, justification) ; le superutilisateur Django n'est plus un statut d'administration applicatif. |
| `matrix/tests/test_barre_superieure.py` | retirés ou renommés : `test_superutilisateur_affiche_administrateur_general` ; ajoutés : `test_administrateur_general_affiche_son_statut_et_le_superutilisateur_django_non` | AC-15 : seul l'indicateur d'administrateur général affiche « Administrateur général ». |
| `matrix/tests/test_coherence_configuration.py` | modifiés : `setUp`, `test_admin_django_modification_et_suppression` | Seuils et modules : actes de commandement, l'acteur devient un commandant (AC-13, AC-15) ; l'administration Django est éprouvée avec un superutilisateur Django. |
| `matrix/tests/test_core_permissions.py` | retirés ou renommés : `test_administrateur_technique_modifie_sans_changer_de_role_et_attribue_les_droits_techniques`, `test_superutilisateur_toujours_autorise_en_ecriture` ; ajoutés : `test_administrateur_technique_modifie_sans_changer_de_role_et_n_attribue_pas_les_droits_techniques`, `test_superutilisateur_django_n_est_pas_autorise_par_son_statut` | AC-10, AC-15, AC-19 : le commandant désigne le commandant en second ; le superutilisateur Django n'est plus autorisé par son statut ; l'administrateur technique n'attribue plus les droits techniques. |
| `matrix/tests/test_core_scopes.py` | retirés ou renommés : `test_superutilisateur_est_toujours_master_admin` ; ajoutés : `test_superutilisateur_django_n_est_pas_administrateur_general` | AC-15 : le superutilisateur Django n'est pas un administrateur général. |
| `matrix/tests/test_creation_unite.py` | modifiés : `setUp`, `setUp` | Fixture : le compte est déclaré administrateur général (indicateur du profil) ; le superutilisateur Django seul ne l'est plus (AC-15). Assertions inchangées. |
| `matrix/tests/test_dette_ux1.py` | modifiés : `setUp`, `test_sans_choix_toute_la_flotte_puis_filtre_sur_le_batiment_courant`, `test_master_admin_sans_specialite_ni_classe_ne_voit_pas_les_entrees` | Fixture : administrateur général déclaré (EntreesTransverses) ; le filtre du bâtiment courant est éprouvé sur la portée « flotte entière » elle-même, la consultation systématique des anomalies n'étant plus conférée (AC-15). |
| `matrix/tests/test_fuites_sans_rattachement.py` | modifiés : `test_administrateur_general_voit_toujours_la_flotte` | AC-15 : l'administrateur général voit toujours la flotte pour les équipements, installations et stocks ; il ne consulte plus les anomalies par son statut. |
| `matrix/tests/test_global_search.py` | modifiés : `test_maitre_voit_toutes_les_personnes` | Fixture : le compte est déclaré administrateur général (indicateur du profil) ; le superutilisateur Django seul ne l'est plus (AC-15). Assertions inchangées. |
| `matrix/tests/test_message_tags_toasts.py` | modifiés : `setUp` | Fixture : le compte est déclaré administrateur général (indicateur du profil) ; le superutilisateur Django seul ne l'est plus (AC-15). Assertions inchangées. |
| `matrix/tests/test_modules_activables.py` | modifiés : `setUp` ; retirés ou renommés : `test_master_admin_peut_choisir_le_navire_et_basculer` ; ajoutés : `test_administrateur_general_n_active_pas_les_modules_par_son_statut` | AC-15 : l'activation des modules est un acte de commandement ; l'administrateur général est refusé (403), le test d'activation par un commandant existe par ailleurs. |
| `matrix/tests/test_navigation_laterale.py` | modifiés : `test_aucun_lien_mort`, `test_groupes_dans_l_ordre_du_chapitre_7`, `test_libelles_du_chapitre_7_en_supervision` | Fixture administrateur général ; la Vue COMANAV n'est plus proposée à l'administrateur général (AC-15) ; la Vue flotte, les tableaux spécialité et classe restent proposés. |
| `matrix/tests/test_organisme_formation.py` | modifiés : `test_annuaire_affiche_le_badge_de_lunite_dun_marin`, `test_annuaire_regroupe_les_unites_par_type_dans_le_selecteur`, `setUp`, `setUp` | Catalogue commun de formations : le compte qui l'écrit est l'administrateur général (indicateur), l'administrateur technique n'y écrit plus (AC-20). Assertions de comportement inchangées. |
| `matrix/tests/test_parametres_navigation.py` | modifiés : `setUp`, `test_chaque_onglet_repond_et_marque_son_lien_actif`, `test_libelles_conformes_ux_20_8` ; retirés ou renommés : `test_superuser_voit_les_quatre_sections_et_tous_les_reglages` ; ajoutés : `test_administrateur_general_voit_les_sections_de_gouvernance_sans_les_actes_de_commandement` | AC-15 : l'administrateur général voit les sections de gouvernance, sans l'équipage (relève) ni les modules (actes de commandement) ; libellés et onglets attendus ajustés. |
| `matrix/tests/test_permissions_matrix.py` | modifiés : `assert_seuil`, `client_pour`, `setUpTestData` | Matrice rôle × ressource : le niveau MASTER_ADMIN sort de l'échelle ; un sous-test exécute chaque acte avec un administrateur général sans fonction (refus attendu, hors actes ouverts à tous et référentiels communs). |
| `matrix/tests/test_recherche_rapide.py` | modifiés : `test_maitre_voit_la_flotte` | Fixture : le compte est déclaré administrateur général (indicateur du profil) ; le superutilisateur Django seul ne l'est plus (AC-15). Assertions inchangées. |
| `matrix/tests/test_releves_datees_web.py` | modifiés : `test_administration_django_exige_un_fuseau_pour_un_nouveau_batiment`, `test_administration_django_ne_ecrase_pas_une_releve_appliquee_entre_temps`, `test_creation_d_unite_par_les_reglages_exige_un_fuseau`, `test_edit_ship_ne_reecrit_pas_l_equipage` | Fixture : le compte est déclaré administrateur général (indicateur du profil) ; le superutilisateur Django seul ne l'est plus (AC-15). Assertions inchangées. |
| `matrix/tests/test_responsables_transverses.py` | modifiés : `setUp` | Fixture : le compte est déclaré administrateur général (indicateur du profil) ; le superutilisateur Django seul ne l'est plus (AC-15). Assertions inchangées. |
| `matrix/tests/test_securite_ecritures.py` | modifiés : `test_session_avec_presences_non_supprimable`, `test_suppression_de_formation_et_de_session` ; retirés ou renommés : `test_creation_de_formation_reservee_a_l_administration` ; ajoutés : `test_creation_de_formation_reservee_a_l_administrateur_general` | AC-20 : le catalogue commun et la programmation des sessions ne sont plus écrits par l'administrateur technique ; l'administrateur général crée et supprime une formation vierge ; supprimer une session à présences reste refusé au rôle non habilité. |
| `matrix/tests/test_securite_terre_second.py` | modifiés : `test_administrateur_general_n_est_pas_du_soutien` | AC-15 : niveau d'écriture de l'administrateur général = niveau minimal (aucun droit métier par le statut). |
| `matrix/tests/test_serializers_cles_serveur.py` | modifiés : `_client_chef_formation` | Catalogue commun de formations : le compte qui l'écrit est l'administrateur général (indicateur), l'administrateur technique n'y écrit plus (AC-20). Assertions de comportement inchangées. |
| `matrix/tests/test_settings_notifications.py` | modifiés : `setUp` | Fixture : le compte est déclaré administrateur général (indicateur du profil) ; le superutilisateur Django seul ne l'est plus (AC-15). Assertions inchangées. |
| `matrix/tests/test_styleguide.py` | modifiés : `test_administrateurs_autorises` | AC-15 : le superutilisateur Django n'est pas un administrateur technique (403) ; l'administrateur technique reste autorisé. |
| `org/tests/test_archivage.py` | modifiés : `setUp`, `test_l_affectation_en_masse_a_une_section_active_reste_possible`, `test_l_affectation_en_masse_d_installations_a_une_section_archivee_est_refusee`, `setUp` | Acte métier : l'acteur devient le commandement du bâtiment ; l'administrateur général n'exerce plus cet acte par son statut (AC-15). Le test vérifie la règle d'archivage ou de périmètre, non le droit de l'acteur. |
| `org/tests/test_referentiel_batiments.py` | modifiés : `setUp` | Fixture : le compte est déclaré administrateur général (indicateur du profil) ; le superutilisateur Django seul ne l'est plus (AC-15). Assertions inchangées. |
| `quarts/tests/test_feuille_service_a_terre.py` | modifiés : `test_administrateurs_ne_redigent_ni_ne_visent_par_le_seul_role` ; retirés ou renommés : `test_administrateur_general_lit_sans_pouvoir_ecrire` ; ajoutés : `test_administrateur_general_lit_la_feuille_publiee_sans_pouvoir_ecrire` | AC-15 : l'administrateur général lit la feuille publiée (contenu commun) ; le travail en cours du circuit de visa n'est pas le sien (403). |
| `quarts/tests/test_trace_creneaux.py` | modifiés : `test_admin_trace_ajout_et_suppression_sur_liste_publiee` | Fixture : le compte est déclaré administrateur général (indicateur du profil) ; le superutilisateur Django seul ne l'est plus (AC-15). Assertions inchangées. |
| `taches/tests/test_taches.py` | modifiés : `test_formulaire_des_reglages_reserve_au_maitre_admin` | Fixture : le compte est déclaré administrateur général (indicateur du profil) ; le superutilisateur Django seul ne l'est plus (AC-15). Assertions inchangées. |
| `threads/tests/test_permissions.py` | modifiés : `test_only_author_can_update_message` | Fixture : le compte est déclaré administrateur général (indicateur du profil) ; le superutilisateur Django seul ne l'est plus (AC-15). Assertions inchangées. |
| `training/tests/test_api_champs_proprietaire.py` | modifiés : `setUp` | Catalogue commun de formations : le compte qui l'écrit est l'administrateur général (indicateur), l'administrateur technique n'y écrit plus (AC-20). Assertions de comportement inchangées. |
| `training/tests/test_api_formation_bord.py` | modifiés : `test_creation_ignore_gere_par_le_bord_et_statut_force`, `test_formation_organisme_modifiable_par_l_administration_seulement` | Catalogue commun de formations : le compte qui l'écrit est l'administrateur général (indicateur), l'administrateur technique n'y écrit plus (AC-20). Assertions de comportement inchangées. |
| `training/tests/test_bareme_formation.py` | modifiés : `setUp` | Catalogue commun de formations : le compte qui l'écrit est l'administrateur général (indicateur), l'administrateur technique n'y écrit plus (AC-20). Assertions de comportement inchangées. |
| `training/tests/test_creation_formation.py` | modifiés : `setUp`, `test_commandant_ne_peut_pas_creer_une_formation` | Catalogue commun de formations : le compte qui l'écrit est l'administrateur général (indicateur), l'administrateur technique n'y écrit plus (AC-20). Assertions de comportement inchangées. |
| `training/tests/test_lecture_dossiers.py` | modifiés : `test_administrateur_general_garde_la_flotte_entiere` | AC-15, AC-20 : la validation d'une qualification individuelle relève de l'autorité métier ; l'administrateur général conserve seulement le périmètre « flotte entière ». |
| `training/tests/test_referents.py` | retirés ou renommés : `test_administrateur_general_peut_designer_un_referent_sur_nimporte_quel_navire` ; ajoutés : `test_administrateur_general_ne_designe_pas_un_referent_par_son_seul_statut` | AC-15, AC-20 : la désignation d'un référent de formation relève du commandement de chaque bâtiment ; test renommé et assertion inversée pour l'administrateur général. |
| `training/tests/test_scope_requirements.py` | modifiés : `setUp` | AC-20 : exigences locales = commandement (l'acteur du fichier devient un commandant), exigences communes = administrateur général. |
| `training/tests/test_validation_fichiers_bareme.py` | modifiés : `setUp` | Catalogue commun de formations : le compte qui l'écrit est l'administrateur général (indicateur), l'administrateur technique n'y écrit plus (AC-20). Assertions de comportement inchangées. |

## 17. Procédures d'installation, de réinitialisation et de récupération

**Installation d'un bâtiment (AC-09).** Sur le serveur, par un installateur autorisé, une seule fois par bâtiment : `python manage.py initialiser_autorites_batiment --batiment CODE --commandant ID [--administrateur-technique ID] --autorisation REF [--accepter-cumul]`. Les comptes existent déjà ; aucun mot de passe ni identifiant n'est créé. Refus : bâtiment déjà initialisé (verrou en base), commandant déjà en place, cumul non explicite, administrateur général, bâtiment étranger. Trace : `initialisation_batiment` (opérateur système, référence d'autorisation, comptes).

**Premier administrateur général d'une installation.** Un compte est d'abord créé par la procédure Django habituelle (`createsuperuser`, qui ne confère aucune prérogative applicative ; le README y renvoie). Le statut d'administrateur général est ensuite attribué par la procédure de récupération à deux opérateurs avec l'option `--attribuer`, tant qu'aucun administrateur général applicatif n'existe.

**Habilitation des opérateurs de récupération (installation).** `python manage.py habiliter_operateur_recuperation --nom NOM` : chaque opérateur, depuis son propre compte système, saisit sa phrase secrète personnelle (au moins 12 caractères, saisie masquée, jamais en argument). Deux opérateurs au plus par cette voie ; tout changement ultérieur est une intervention d'exploitation tracée.

**Réinitialisation d'un mot de passe (AC-12, AC-16).** Annuaire → « Réinitialiser le mot de passe » (équipier à chef de service : administrateur technique ; autres comptes : administrateur général). L'autorité reçoit un code, affiché une seule fois ; elle vérifie l'identité du titulaire puis le lui remet. Pour un compte porteur d'une autorité, un **second responsable distinct** (page « Vérifications d'identité ») reçoit un second code après avoir lui-même vérifié l'identité ; le titulaire a besoin des deux. Le titulaire ouvre « Mot de passe oublié » sur la page de connexion, saisit son identifiant, son ou ses codes, puis choisit son mot de passe. Validité 30 minutes, 5 essais ; une nouvelle demande annule la précédente.

**Récupération d'un administrateur général (AC-17).**
1. Opérateur 1, depuis son compte système : `python manage.py recuperer_acces_administrateur ouvrir --identifiant ID --justification "..."` (phrase secrète demandée) ; il reçoit le premier code, la demande vaut 30 minutes.
2. Opérateur 2, depuis **son** compte système distinct : `python manage.py recuperer_acces_administrateur valider --demande N` ; il reçoit le second code.
3. Le titulaire du compte reçoit les deux codes de chacun des opérateurs et définit son mot de passe sur la page de réinitialisation ; les sessions antérieures sont révoquées ; chaque étape est tracée (`recuperation_ouverte`, `recuperation_validee`, `reinitialisation_effectuee`).
Aucun compte de secours, identifiant ou mot de passe prédéfini n'existe. En **développement seulement** (`DJANGO_DEBUG=1`), `recuperer_acces_administrateur simplifie --identifiant ID` fait les deux étapes ; elle est refusée dès que l'application tourne en production. Cette procédure ne protège pas contre un opérateur qui dispose d'un accès système ou base de données illimité (§12).

**Retour arrière et restauration (AC-21).** Les migrations 0024 à 0029 sont réversibles tant que les journaux d'audit correspondants existent ; le retour arrière restaure les rôles d'origine mais **ne reconstitue pas** les modifications faites depuis la migration (rôle changé, fonction confirmée, mot de passe réinitialisé). Il n'est accepté que si une sauvegarde complète a été vérifiée, que sa restauration a été testée (SQLite : copie du fichier ; PostgreSQL : `pg_dump -Fc` puis `pg_restore`), et que la perte éventuelle des modifications postérieures à la sauvegarde est explicitée. Aucun retour arrière sur des données réelles sans autorisation.

## 18. Limitation des connexions : architecture retenue et conséquences

| Exigence AC-18 | Réponse |
|---|---|
| Limitation progressive | Après 5 échecs d'un couple (identifiant, source), blocage de ce couple pendant 15 minutes, puis 30, 60… jusqu'à un plafond (240 minutes par défaut) ; le niveau retombe après une période calme |
| Pas de verrouillage malveillant par un tiers | Le blocage vise le couple, pas l'identifiant seul : un tiers qui s'acharne depuis un autre poste ne prive pas le marin de son poste habituel |
| Attaque répartie sur plusieurs postes | Un compteur global par identifiant (déclenché à 5 fois le seuil) impose l'attente aux seules **sources inconnues** de cet identifiant ; une source qui s'y est déjà connectée avec succès dans les 30 jours n'est jamais bloquée par lui |
| Pas l'adresse seule | L'adresse n'est que la moitié du couple ; deux marins qui partagent un poste ont des identifiants, donc des compteurs, distincts |
| Atomicité SQLite et PostgreSQL | Incrément par `UPDATE … SET essais = essais + 1` ; création concurrente couverte par une contrainte d'unicité ; reprises brèves si SQLite est occupé ; blocage prononcé par une remise à zéro conditionnelle (un seul des accès concurrents le trace) |
| Un échec = un comptage | Le middleware d'authentification de l'API et DRF interrogent chacun le backend : un indicateur sur la requête évite le double comptage |
| Purge | Tâche quotidienne `accounts.tasks.purger_compteurs_connexion` et purge opportuniste ; seuls les compteurs inactifs depuis plus de 30 jours disparaissent, jamais l'`AuditLog` |
| Compteurs techniques ≠ audit | `CompteurConnexion` (temporaire) distinct de `AuditLog` (preuves : `connexion_limitee`, `connexion_limitee_globale`, `reinitialisation_bloquee`, `recuperation_*`) |
| Configurable sans code, bornes non contournables | Variables d'environnement `MATRIX_CODE_REINITIALISATION_VALIDITE_MINUTES` (5 à 120), `MATRIX_TENTATIVES_CODE_MAX` (3 à 10), `MATRIX_TENTATIVES_CONNEXION_MAX` (3 à 10), `MATRIX_VERROUILLAGE_CONNEXION_MINUTES` (5 à 240), `MATRIX_VERROUILLAGE_CONNEXION_PLAFOND_MINUTES` (15 à 1440), `MATRIX_CONSERVATION_COMPTEURS_JOURS` (7 à 365) ; toute valeur hors bornes est ramenée à la borne |
| Code de réinitialisation | Essais erronés comptés par couple (demande, source), atomiques, avec blocage progressif de cette source ; la demande elle-même n'est jamais bloquée par un tiers |

**Conséquences pour les utilisateurs légitimes** : un marin qui se trompe cinq fois depuis un poste est bloqué 15 minutes sur ce poste seulement ; depuis un nouveau poste, pendant une attaque répartie sur son identifiant, il attend le blocage progressif de son identifiant. **Limites résiduelles** : un tiers qui agit depuis le poste même du marin (accès physique) peut le bloquer sur ce poste ; derrière un mandataire qui masque l'adresse d'origine, tous les postes partagent la même source (l'en-tête transmis par le client n'est jamais cru).

## 19. Risques (AC-21)

| Risque | Statut | Protection apportée, limite résiduelle |
|---|---|---|
| Usurpation d'un compte par l'administrateur chargé de sa réinitialisation | **Refusé en l'état — traité** | Le code n'authentifie pas ; pour un compte porteur d'autorité, le second code n'existe qu'après la validation d'un second responsable distinct et compétent, depuis sa session ; le titulaire définit lui-même son mot de passe ; titulaire notifié ; trace d'audit. Résiduel : collusion de deux responsables habilités ; compte sans autorité (équipier) réinitialisable par une seule autorité |
| Verrouillage durable ou répétitif d'un compte légitime par un tiers (connexion et codes de réinitialisation) | **Refusé — traité** | §18 : blocage par couple, exemption des sources connues, retombée du niveau. Résiduel : accès physique au poste du marin |
| Compteur d'échecs non atomique sur SQLite | **Refusé — traité** | `UPDATE` atomique, reprises, test de concurrence sur SQLite (et PostgreSQL via la suite complète) |
| Double comptabilisation des échecs API | **Refusé — traité** | Indicateur par requête ; test |
| Accumulation non maîtrisée des compteurs | **Refusé — traité** | Purge quotidienne + opportuniste, conservation 30 jours (7 à 365 jours bornés) ; aucun compteur pour un identifiant inexistant ; index sur la date d'activité utilisée par la purge |
| Retour arrière partiel des migrations après modification des comptes | **Accepté sous conditions** | §17 : sauvegarde complète vérifiée, restauration testée, conséquences et perte de modifications postérieures explicitées, aucune exécution sur données réelles sans autorisation |
| Opérateur avec accès système ou base illimité, superutilisateur Django | Hors protection applicative | §12 : frontière de confiance, mesures d'exploitation ; la procédure de récupération ne s'en protège pas |
| Habilitation des opérateurs de récupération par qui a la main sur le serveur | Limite documentée | Deux opérateurs au plus par la commande d'installation ; au-delà, intervention d'exploitation tracée |

**Réserves qui bloquent L06** : aucune connue à ce stade. **Réserves qui ne bloquent qu'un futur déploiement** : mise en place des opérateurs de récupération et de leurs comptes système distincts ; revue des superutilisateurs Django ; référentiel local de formations (L38) ; délégations (L08) ; blocages L30, L32, L34 inchangés.

