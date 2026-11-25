# Lot L06 — séparation des autorités technique et métier : migration et preuves

> **DOCUMENT PROVISOIRE — DIFFUSION RESTREINTE.** Données fictives uniquement ; aucun secret. Lot livré sur sa branche, **non fusionné** ; clôture soumise à la validation du PO.

Décisions : `docs/DECISIONS_PO.md` ARB-01, ARB-06, AC-01, AC-02. Plan : `docs/PLAN_LOTS_REPRISE.md` fiche L06. Base de travail : `c355310` (L29 validé).

## 1. Ce que fait le lot

- **Deux rôles indépendants.** `UserProfile.administrateur_technique` (droits techniques d'unité) est distinct du rôle métier (`role`). Ils se cumulent explicitement ; un administrateur technique seul a le niveau métier d'un équipier. Le rôle `ADMIN_NAVIRE` (niveau 8 qui franchissait tous les seuils) est retiré de l'échelle métier : conservé uniquement comme valeur obsolète, `UserProfile.save()` le refuse. `RoleLevel.ADMIN_NAVIRE` n'est plus que le palier des droits techniques (`niveau_pour_action`).
- **Aucune déduction.** Un nouvel administrateur ne reçoit aucun droit métier. La migration ne déduit jamais une fonction du statut d'administrateur.
- **Planchers d'autorité (AC-02).** `ActionSeuil.plancher` : structure et administration de l'unité, activation des modules, types de programme exigent au moins le commandant ; le paramétrage peut renforcer, jamais abaisser (`seuil_role`, `seuil_autorise`, refus dans « Sécurité »).
- **Auto-attribution refusée.** Personne ne modifie son propre rôle ni ses droits techniques ; seul un administrateur technique attribue les droits techniques d'un autre compte ; l'administrateur technique ne désigne aucune autorité métier ; l'état-major ne désigne plus les chefs de service (commandant, AC-02).
- **Reprise de compte évitée.** Un administrateur technique sans autorité métier ne réinitialise le mot de passe que d'un compte jusqu'à chef de section et non technique (`accounts/services.py`).
- **Réutilisation du socle L29** : registre d'accès, matrice exécutée (`matrix/tests/habilitation/`), vérifications V01 à V25.

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

## 5. Droits avant / après

| Acte | Administrateur d'unité (avant) | Administrateur technique seul (après) | Commandant (après) |
|---|---|---|---|
| Publier, viser, valider échanges et listes ; déplacer un ticket ; faire avancer un ticket | oui (niveau 8) | non | selon ses droits (inchangés) |
| Lire la passation, le tableau COMANAV, les délais d'activation | oui | non | passation et COMANAV : oui ; délais : modification selon sa fonction |
| Relève d'équipage, onglet Équipage | oui | non | oui |
| Structure de l'unité, archivage, double équipage, fuseau | oui | non | oui (plancher) |
| Types d'événements du programme | oui | non | oui (plancher) |
| Activer ou désactiver un module | oui | non | oui (plancher) ; le commandant en second ne le fait plus |
| Désigner une autorité (rôle) | tous les rôles jusqu'au sien | aucun | adjoints, chefs de service, de secteur, de section, équipiers |
| Se donner un rôle ou des droits | oui | non | non |
| Attribuer les droits techniques d'un autre compte | n/a | oui (API) | non |
| Réinitialiser un mot de passe | tout compte | comptes jusqu'à chef de section, non techniques | non (seuil technique) |
| Créer une formation du catalogue | oui | oui | non |
| Seuils de rôle (« Sécurité ») | tout abaissement | renforcer seulement un seuil métier ; régler les seuils techniques | abaisser dans les planchers (s'il atteint l'onglet) |
| Annuaire | lecture et écriture | lecture et réinitialisation | lecture et écriture |

L'administrateur général (superutilisateur) n'est pas modifié (hors périmètre, à instruire).

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

Suites complètes (`manage.py test --parallel 4`), même machine, mêmes réglages, sur l'état final `326387b` du lot ; référence = `c355310` (L29) exécutée dans les mêmes conditions.

| Exécution | Moteur | Tests | Résultat | Ignorés |
|---|---|---|---|---|
| Référence `c355310` | SQLite | 4021 | OK | 20 |
| Référence `c355310` | PostgreSQL 16 | 4021 | OK | 22 |
| Lot L06 `326387b` | SQLite | 4045 | OK | 20 |
| Lot L06 `326387b` | PostgreSQL 16 | 4045 | OK | 22 |

Écart : +24 tests (nouveaux tests L06 : autorités, API des profils, seuils, migration ; vérifications V26 ajoutée), aucun test supprimé ni ignoré en plus. Les ignorés sont les mêmes que ceux de la référence sur chaque moteur. Un test sensible à l'heure (`test_poste_vacant_visible_sans_relève_interne`, proche de minuit) a échoué une fois sur un essai intermédiaire, sans lien avec le lot ; il passe seul, sur la référence et sur l'exécution finale.

Migration, retour arrière et restauration rejoués sur la migration finale (SQLite et PostgreSQL, données fictives, un doublon de fonction inclus) : 3 comptes convertis en équipier + droits techniques, 3 lignes d'audit, aucune promotion ; retour arrière et restauration depuis sauvegarde identiques à l'état initial sur les deux moteurs.

Journaux : `l06_final_cand_sqlite.log`, `l06_final_cand_pg.log`, `l06_full_base_sqlite.log`, `l06_full_base_pg.log` (hors dépôt).

## 10. Relectures indépendantes

| Relecture | État relu | Verdict | Suites |
|---|---|---|---|
| 1 | `fb51920` | **À corriger** : un technique pouvait désigner une fonction par l'API, élargir son périmètre, retirer son drapeau par un envoi multipart ; droits techniques non tracés ; seuils ; désignations ; migration | corrigées dans `dedb41d` |
| 2 | `dedb41d` | **À corriger** : un technique abaissait des seuils de circuits (auto-élévation) ; désignations incomplètes ; migration promouvant sur simple présence de fonction ; seuil stocké au palier obsolète ; test creux | corrigées dans `24b26b8`, `7621ade` |
| 3 | `7621ade` | **Valide avec réserves**, aucun bloquant, aucune élévation métier trouvée ; une correction demandée avant fusion (comptes d'administration Django réinitialisables) et cinq mineurs | corrigés dans `326387b` (comptes `is_staff`/groupes/droits exclus, fonction retirée de la fiche et restituée au retour arrière, audit avant/après dans l'administration Django, message au lieu d'une page 403, `mot_de_passe_provisoire` en lecture seule) ; suites complètes rejouées sur `326387b` |

Réserve non reprise : un test énumérant toutes les relations du modèle utilisateur pour détecter une désignation oubliée (voir §11). Les corrections de la troisième relecture sont limitées ; l'état final `326387b` est couvert par les suites complètes et par la preuve de migration, mais n'a pas fait l'objet d'une quatrième relecture écrite.

## 11. Anomalies résiduelles et points à arbitrer

- **Administrateur général et superutilisateur Django** : cumulent encore tous les droits ; séparation non traitée.
- **Initialisation des premières autorités** : proposition à valider (`docs/recette/L06_PROPOSITION_INITIALISATION.md`) ; en attendant, seul l'administrateur général désigne le premier commandant.
- **Désignation du commandant en second** : n'apparaît pas dans AC-02 ; proposition à valider.
- **Fonction métier à confirmer** : aucun outil de confirmation par une autorité habilitée n'est livré ; la migration ne promeut aucun administrateur.
- **Abaissement de seuils par un administrateur technique** : sans autorité de commandement il ne peut que renforcer un seuil métier ; à valider par le PO.
- **Navigation** : l'entrée « Annuaire » et l'onglet « Sécurité » ne sont pas proposés à l'administrateur technique dans le menu (accès par adresse) ; à traiter avec L08/L30.
- **Cohérence API / web** : le web masque les comptes techniques aux non-techniques, l'API non ; à aligner.
- **Comptes d'administration Django** : un technique ne réinitialise pas le mot de passe d'un compte `is_staff`, de groupe ou de droits Django.
- **Désignations** : la liste des désignations qui interdisent la réinitialisation d'un mot de passe par un technique est tenue à la main (`accounts/services.py`) ; un registre unique est à prévoir (L08).
- **Commentaires anciens** mentionnant « ADMIN_NAVIRE » dans le code : non réécrits (règle de projet : seules les lignes modifiées sont touchées).
- **Interface** : le drapeau `administrateur_technique` n'a pas d'écran de gestion ; il s'attribue par l'API ou l'administration Django.
