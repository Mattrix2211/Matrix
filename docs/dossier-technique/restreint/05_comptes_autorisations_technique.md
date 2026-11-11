# Chapitre 5 (technique) — Comptes et autorisations : mécanismes

> **Diffusion restreinte.** Complète `diffusable/05_comptes_roles_autorisations.md` (à lire d'abord) et l'annexe B (matrice générée). **État décrit :** état B (`6d6d0be`), non fusionné dans `main`.
> **Pour qui :** développeurs, administrateurs. **Ce que vous y trouverez :** comment les droits sont réellement calculés dans le code, les deux familles de comparaison de seuils, le calcul des périmètres, la gestion des comptes, et les mécanismes de session.

---

## 5T.1 Les briques

| Brique | Où | Rôle |
|---|---|---|
| `Roles` | `accounts/models.py:11` | Les neuf rôles, stockés dans `UserProfile.role` (texte) |
| `RoleLevel` | `matrix/core/roles.py:4` | Niveau numérique : EQUIPIER 1 … MASTER_ADMIN 9 ; correspondance `ROLE_TO_LEVEL` |
| `user_role_level(user)` | `matrix/core/roles.py:40` | **Grade** : superutilisateur = MASTER_ADMIN ; sans profil ou sans rôle = EQUIPIER |
| `niveau_ecriture(user)` | `matrix/core/roles.py:53` | **Niveau d'écriture** : identique au grade, sauf pour le soutien à terre et le commandant en second, ramenés à EQUIPIER (`ROLES_SANS_ECRITURE_HERITEE`) |
| `REGISTRE_ACTIONS` | `matrix/core/role_thresholds.py:45` | 35 actions `{clé, libellé, catégorie, portée, défaut, ouverte_au_second}` |
| `seuil_role(clé, ship_id)` | `matrix/core/role_thresholds.py:242` | Seuil effectif : configuration du bâtiment (ou globale), repli sur le défaut |
| `RolePermission` | `matrix/core/permissions.py:9` | Permission DRF : lecture = authentifié ; écriture = niveau d'écriture ≥ seuil |
| `ManageUsersPermission` | `matrix/core/permissions.py:81` | Qui peut attribuer quel rôle (`MANAGE_MAP`, `:100`) |
| `niveau_ecriture_sur` | `matrix/core/ecriture_service.py:68` | Borne l'état-major aux services de sa fonction |
| `scope_filters_for_user` | `matrix/core/scopes.py:8` | Périmètre de lecture et d'écriture (niveau de rattachement) |
| `build_scope_q` | `matrix/core/mixins.py:16` | Traduction du périmètre en filtre de requête |

## 5T.2 Deux familles de comparaison de seuils

Le seuil d'une action est **un niveau**. Il est comparé de deux manières selon l'endroit du code, et la différence ne concerne en pratique que le **commandant en second** et le **soutien à terre**.

1. **Comparaison au niveau d'écriture** (`niveau_ecriture`) : API des ViewSets via `RolePermission`, et les vues qui l'utilisent. Le second est traité en équipier (sauf action marquée `ouverte_au_second`).
2. **Comparaison au grade** (`user_role_level`) : la plupart des vues web de gestion (par exemple gestion des modules, `matrix/views.py:289` ; saisie du programme, `programme/services.py:47` ; fiches, `assets/fiche_validation.py:130`). Le second y atteint son grade.
3. `niveau_pour_action(user, clé)` (`matrix/core/role_thresholds.py`) fait la synthèse pour les actions explicitement ouvertes au second.

Conséquence pour la lecture de l'annexe B : la colonne « Second » porte « ✱ » quand son grade atteint le seuil mais pas son niveau d'écriture ; l'accès réel dépend de la vue.

## 5T.3 Le chemin d'une écriture par l'API

1. **Authentification** : bloc `REST_FRAMEWORK` (`matrix/settings.py:239`) : `SessionAuthentication` puis `BasicAuthentication`. Permission par défaut : `IsAuthenticated`.
2. **Chaîne de middlewares** (`matrix/settings.py:115`), dans l'ordre : contexte de configuration → sécurité Django → session → commun → CSRF → retrait du caractère NUL → authentification → déconnexion par inactivité → messages → clickjacking → identité de page → habillage des erreurs 400 → bâtiment courant → mot de passe provisoire → modules activables → **lecture seule à terre** → erreurs de saisie.
3. **`RolePermission.has_permission`** (`matrix/core/permissions.py:45`) : lecture = authentifié ; superutilisateur = autorisé ; sinon `niveau_ecriture(user) >= seuil`. Le seuil vient de l'attribut du ViewSet `role_threshold_action_write` (et `role_threshold_action_delete` pour DELETE), clé du registre résolue **au bâtiment de l'appelant** ; à défaut, d'anciens attributs `min_role_level_write`/`min_role_level_delete` (constantes) puis `CHEF_SECTION`.
4. **`has_object_permission`** (`:52`) : `niveau_ecriture_sur(user, objet, strict=False)` : l'état-major ramené au niveau équipier hors des services de sa fonction ; un assigné peut modifier sa propre occurrence de maintenance.
5. **Périmètre** : le queryset du ViewSet est borné par `build_scope_q` ; une cible hors périmètre répond comme si elle n'existait pas.
6. **Trace** dans `AuditLog` pour les actes sensibles.

Pour une vue web, les étapes 3 et 4 sont réalisées dans la vue (ou son `services.py`) avec `niveau_requis_pour(user, clé)`, dans la plupart des cas ; le menu ne fait que masquer.

## 5T.4 Les seuils : stockage, résolution, cohérence

- **Stockage** : `org.RoleThresholdConfig.thresholds` (JSON `{clé: nom de rôle}`), un enregistrement par bâtiment, plus un enregistrement à `ship` vide pour les actions de portée `GLOBALE`.
- **Résolution** : `seuil_role` retourne le défaut si le bâtiment est inconnu, si la clé n'est pas configurée ou si le nom de rôle est illisible. Une clé inconnue du registre lève `ValueError`.
- **Cache et cohérence** : cache local au processus, validé par la version en base (`VersionConfiguration`) ; `incrementer` est appelé par signal après chaque enregistrement ou suppression (`org/models.py`). Les versions sont lues en **une requête** par requête web ou tâche Celery (`ouvrir_contexte` / `fermer_contexte`, branchés dans `matrix/celery.py`).
- **Modification** : onglet Sécurité des Réglages (`matrix/views.py`) ; un administrateur d'unité n'agit que sur son bâtiment.

## 5T.5 Les périmètres

- `UserProfile.scope` (`accounts/models.py:87`) : couple (niveau, id) du rattachement le plus fin. `scope_filters_for_user` (`matrix/core/scopes.py:8`) le traduit en filtre `{ship_id|service_id|sector_id|section_id: id}`.
- `navire_id_effectif` : remonte au bâtiment même si seul le secteur ou la section est renseigné. `navire_q` (`:127`) couvre les quatre chemins de rattachement.
- `perimetre_hierarchique_q` (`:138`) : tous les marins **sous** le niveau de l'utilisateur.
- `build_scope_q` : accepte plusieurs chemins de relation (ou, pour les modèles qui ne couvrent pas les quatre niveaux, un dictionnaire par niveau) ; **sans rattachement**, administrateur général = flotte entière (ou bâtiment choisi) ; personnel à terre = bâtiments suivis (`batiments_du_perimetre`) ; autre = aucun résultat. Si aucun chemin ne couvre le périmètre, filtre vide : « mieux vaut ne rien montrer ».
- `resoudre_affectation_dans_perimetre` (`:158`) : valide l'unité, le service, le secteur et la section demandés contre le périmètre de l'appelant (création et modification de compte).
- Équipage : `equipage_agissant` (`:209`), `equipage_marin_q` (`:235`), `assignes_equipage_q` (`:243`) bornent les listes à l'équipage agissant.
- `commandants_adjoints.py` : `commandant_adjoint_du_service`, `titulaires_commandant_adjoint(navire, code, équipage)` : retrouve le titulaire de COMA d'un service, par équipage ; `message_absence_coma` produit le signalement quand il est vacant.

## 5T.6 La gestion des comptes

**Web** (`accounts/web_views.py`) : `UserDirectoryView` (`:133`) porte les actions POST de l'annuaire (`create_user` `:376`, `edit_user`, `delete_user` `:465`, `set_password`, actions `bulk_*`).

- `_role_attribution_autorisee` (`:33`) réutilise `ManageUsersPermission.MANAGE_MAP` : mêmes règles que l'API.
- `_utilisateurs_gerables_par` (`:62`) borne la **cible** des actions POST au bâtiment de l'appelant, aux rôles gérables (plus lui-même), sans compte maître ni superutilisateur ; une cible hors périmètre se comporte comme absente.
- Création : rôle validé, rattachement résolu et validé avant création, équipage obligatoire sur double équipage, longueurs de champs refusées si excessives, identifiant `prenom.nom` slugifié (140 caractères au plus, suffixe numérique), `set_unusable_password()`.
- Suppression : refus sur soi-même ; cible bornée ; trace `delete_user`. L'action de masse ignore l'appelant s'il est dans la sélection.

**API** (`accounts/views.py`, `accounts/serializers.py`) : `ManageUsersPermission` ; voir `accounts/tests/test_api_champs_proprietaire.py` pour les champs réservés au propriétaire.

**Mot de passe** (`accounts/services.py`) : `generer_mot_de_passe` (14 caractères, minuscule, majuscule, chiffre, symbole, tirage cryptographique) ; `reinitialiser_mot_de_passe` exige le seuil `mot_de_passe_reinitialisation` (administrateur d'unité par défaut), refuse sur soi-même, marque `mot_de_passe_provisoire`, trace sans le mot de passe. `MotDePasseProvisoireMiddleware` (`matrix/core/middleware.py:121`) redirige, répond 204 + `HX-Redirect` (HTMX) ou 403 JSON (`/api/`) tant que le mot de passe n'est pas changé. La page de changement : `ChangerMotDePasseView` (`accounts/web_views.py:775`).

**Signaux** (`accounts/models.py:227`, `accounts/signals.py`) : création automatique du profil (rôle équipier) à la création d'un utilisateur ; trace de connexion et de déconnexion.

## 5T.7 Référentiels et désignations

- `GradeChoice`, `SpecialityChoice`, `ServiceFunctionChoice`, `FonctionQuartChoice`, `TypeAbsence`, `RoleAvailability` : listes `{nom, actif}` ; le profil stocke **des textes** (grade, spécialité, fonction), pas des clés étrangères : désactiver une valeur ne détruit pas l'identité des marins qui la portent.
- `RoleAvailability` : rôles attribuables ; `MASTER_ADMIN` reste réservé aux superutilisateurs.
- `ResponsableSpecialite` (`accounts/models.py:197`), `org.ResponsableClasseNavire` (`org/models.py:378`) : désignations de portée flotte (seuil `responsabilite_transverse_gestion`, administrateur général par défaut). Elles fondent `soutien_a_terre`.
- Aucun identifiant stable (UUID, NNO) n'existe sur le compte ou le profil : le compte est identifié par la clé entière de la table utilisateur. UUID et NNO existent côté matériel (chapitre 19).

## 5T.8 Session et sécurité des postes partagés

- **Inactivité** (`matrix/core/inactivite.py`, middleware `:105`) : le serveur mémorise la dernière activité humaine dans la session (clé `derniere_activite`) et déconnecte au-delà du délai (`INACTIVITE_DELAI_SECONDES`, 900 par défaut, borné de 60 à 28 800) ; avertissement `INACTIVITE_AVERTISSEMENT_SECONDES` (60). Les requêtes marquées `X-Mx-Automatique` ne renouvellent pas l'activité. L'écriture de la session est limitée à une fois toutes les 5 secondes.
- **Identité de page** (`IdentitePageMiddleware`, `matrix/core/middleware.py:165`) : une écriture dont la page a été ouverte pour un autre utilisateur est refusée.
- **Brouillons** (`matrix/core/brouillons.py`, modèle `core.Brouillon`) : conservation `BROUILLONS_CONSERVATION_JOURS` (30), taille `BROUILLONS_TAILLE_MAX` (256 Kio) ; purge quotidienne par tâche planifiée.
- **Cookies** de session et CSRF marqués sécurisés et redirection HTTPS hors mode DEBUG (`matrix/settings.py:422`).

## 5T.9 Tests de référence

`accounts/tests/` : `test_matrice_droits`, `test_rbac_user_directory`, `test_directory_permissions`, `test_scope_leak_*` (API et web), `test_reinitialisation_mot_de_passe`, `test_admin_navire_limites`, `test_formulaire_utilisateur`. Mesure de l'état B : 159 fonctions de test dans `accounts`.

## 5T.10 Limites et éléments non vérifiés

- ⚪ Les deux familles de comparaison (§5T.2) ne sont pas harmonisées : le comportement du commandant en second varie selon la vue. Le détail par vue est établi chapitre par chapitre.
- ⚪ `BasicAuthentication` est acceptée par l'API en plus de la session : utile pour des scripts, à considérer pour l'exploitation (chapitre 23).
- ⚪ Aucune limitation du nombre de tentatives de connexion n'a été trouvée dans le code ; « absent » signifie « non trouvé par recherche », pas preuve d'absence.
- ⚪ PostgreSQL, Windows, navigateur : non rejoués.
- 🔵 Non développé : L04 (désactivation), L06, L07, L08, L09, L16, L21.

---

**Sources (état B).** Voir les références en ligne ; inventaire généré : `couverture/etat_B/INVENTAIRE.md` (35 actions, 159 tests dans `accounts`). Matrice : `restreint/annexes/B_matrice_role_action.md`.
