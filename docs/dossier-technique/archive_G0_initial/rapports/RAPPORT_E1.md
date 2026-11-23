# Rapport de livraison — G1 et ensemble 1 (« Fondations »)

> **Diffusion restreinte.** Date : 11/11/2026. Branche documentaire : `claude/fervent-wright-kl6gtx`. État du logiciel décrit : état B, `claude/l03-suppression-sure-v11` @ `6d6d0be`, **non fusionné dans `main`**.
> Aucun code applicatif modifié, aucune fusion dans `main`, aucune PR, aucun nouveau lot. Les décisions du PO n'ont pas été modifiées ni rediscutées.

---

## 1. Ce qui est livré

### 1.1 Chapitres rédigés (ensemble 1)

| Chapitre | Fichier | Diffusion | Lignes |
|---|---|---|---|
| 1 Vision, philosophie, principes | `diffusable/01_vision.md` | Générale | 83 |
| 2 Vue d'ensemble : modules, acteurs, parcours | `diffusable/02_vue_ensemble.md` | Générale | 113 |
| 3 Lire ce dossier | `diffusable/03_lire_ce_dossier.md` | Générale | 103 |
| 4 Organisation (usage) | `diffusable/04_organisation.md` | Générale | 126 |
| 4 Organisation (technique) | `restreint/04_organisation_technique.md` | Restreinte | 116 |
| 5 Comptes, rôles, autorisations (usage) | `diffusable/05_comptes_roles_autorisations.md` | Générale | 168 |
| 5 Comptes et autorisations (technique) | `restreint/05_comptes_autorisations_technique.md` | Restreinte | 105 |
| 18 Architecture technique | `restreint/18_architecture.md` | Restreinte | 158 |
| 19 Modèles de données | `restreint/19_modeles_donnees.md` | Restreinte | 102 |
| 22 Sécurité | `restreint/22_securite.md` | Restreinte | 141 |
| Annexe A Glossaire | `diffusable/annexes/A_glossaire.md` | Générale | 121 |
| Annexe B Matrice rôle × action (générée) | `restreint/annexes/B_matrice_role_action.md` | Restreinte | 65 |

Chaque chapitre suit le gabarit validé : fonctionnement réel 🟢, fonctionnement cible 🔵, limites et éléments non vérifiés ⚪, schémas, sources. Les chapitres sont rédigés pour un lecteur qui ne développe pas ; les références de code servent à vérifier, elles ne remplacent pas l'explication.

### 1.2 Outils et inventaires (G1)

| Élément | Fichier |
|---|---|
| Inventaire du code (modèles, relations, routes, tâches planifiées, commandes, registres, dépendances, signaux) | `outils/inventaire.py` → `couverture/etat_B/INVENTAIRE.md`, `MODELES.md`, `ROUTES.md`, `inventaire.json` |
| Matrice rôle × action | `outils/generer_annexe_b.py` |
| Matrice de couverture | `outils/generer_matrice_couverture.py` → `restreint/annexes/G_matrice_couverture.md` |
| Contrôle des références de code | `outils/verifier_references.py` |
| Contrôle de cohérence documentaire | `outils/controle_coherence.py` |
| Export des schémas | `outils/rendre_schemas.js` |

**Mesures de l'état B** (générées, jamais saisies à la main) : 22 paquets applicatifs (21 applications Django et `matrix.core`), **135 modèles**, 448 relations, 6 relations génériques, **721 routes**, **190 migrations**, **20 tâches planifiées**, **18 commandes de gestion**, **35 actions à seuil de rôle**, 15 signaux, 335 fichiers de tests (3 002 fonctions de test ; les comptes rendus des lots annoncent 3 963 tests exécutés, car l'exécution compte aussi les cas paramétrés et hérités).

## 2. Schémas réalisés (12)

Sources Mermaid dans `schemas/src/`, exports SVG hors ligne dans `schemas/svg/`. Chaque schéma explique un mécanisme ; aucun n'a été ajouté pour le nombre.

| N° | Schéma | Chapitre |
|---|---|---|
| S01 | Matrix sur le réseau du bord (aucun Internet) | 18 |
| S02 | Carte des modules | 2 |
| S03 | Hiérarchie des unités et équipage | 4 |
| S04 | États d'une relève d'équipage | 4 |
| S05 | Cycle de vie d'une unité (active, archivée, supprimée) | 4 |
| S06 | Contrôles successifs d'une demande d'écriture | 5 |
| S07 | Qui gère quel rôle | 5 |
| S08 | Couches de l'application | 18 |
| S09 | Liaisons principales entre paquets (chacune vérifiée contre l'inventaire des imports) | 18 |
| S10 | Organisation et comptes (entités vérifiées contre l'inventaire) | 4 (technique) |
| S11 | Chaîne de contrôles d'une requête | 22 |
| S12 | Conditions du verrou de démonstration | 22 |

Les rendus de S02, S04, S06, S09 et S10 ont été regardés à l'image ; S04, S06 et S12 ont été redessinés (boîtes plutôt que losanges) pour rester lisibles. S09, le plus dense, reste lisible mais chargé : il se limite aux liaisons principales.

## 3. Couverture

Matrice complète : `restreint/annexes/G_matrice_couverture.md` (générée).

| Élément | Périmètre de l'ensemble 1 | Couvert | Reste |
|---|---|---|---|
| Modèles de `accounts`, `org`, `matrix.core` | 26 | **26 expliqués** (chacun nommé et décrit dans un chapitre de domaine) | — |
| Autres modèles | 109 | 70 nommés dans la présentation par familles (ch. 19), 39 au dictionnaire seul | Ensembles 2 à 4 |
| Actions à seuil de rôle | 35 | **35** dans l'annexe B (générée depuis le registre) | — |
| Rôles | 9 | **9** (chapitre 5) | — |
| Circuits métier de l'ensemble 1 | 9 | **9** : relève d'équipage, archivage et suppression d'unité, création de compte, réinitialisation de mot de passe, suppression de compte (réel) et désactivation (cible), proposer → valider → publier, confirmation explicite des validations critiques, verrou de démonstration | 12 circuits des ensembles 2 et 3 |
| Middlewares (13) | 13 | **13** décrits (chapitre 22) | — |
| Tâches planifiées | 20 | 20 listées par domaine (ch. 18) ; relève nommée | Détail au chapitre 21 (ensemble 4) |
| Commandes de gestion | 18 | Celles du verrou et de la préparation citées | Annexe E (ensemble 4) |
| Paquets | 22 | 22 présentés (ch. 2) ; `accounts`, `org`, `matrix.core` détaillés | 19 des domaines métier détaillés aux ensembles 2 à 4 |

Les sources Notion de l'ensemble 1 ont été **toutes lues avant rédaction** : « Organigramme et rôles », « 02 — RH, postes, qualifications », « 06 — Service courant, BSC… » (aussi utile à l'ensemble 2), « 07 — SIC, cyber… », « 11 — Modèle de données cible », « 12 — Glossaire », « 13 — Décisions », « Cahier des charges ».

## 4. Informations non vérifiées (⚪)

**Non rejoué ou non accessible**
1. Parcours utilisateur dans un navigateur réel (chapitre 2) ; recette visuelle de l'écran Réglages.
2. PostgreSQL (20 tests réservés à ce moteur ignorés sur SQLite ; unicités partielles et verrous de ligne de la relève).
3. Windows (`lancer_demo.bat`, droits du fichier d'identifiants).
4. Les 3 963 tests des comptes rendus n'ont pas été rejoués dans leur ensemble pour ce rapport ; un sous-ensemble a été exécuté (§5).
5. Sous-module `design/` (charte graphique) vide dans cet environnement.

**Sources non lues à ce jour**
6. Notion « 03 — Formation, stages, CFPES, FPS » (à lire avant le chapitre 14), pages 01, 04, 05, 08, 09, 10 de l'organigramme (contexte), « Recette UX V1.1 » et « [CADRAGE UX] » (avant le chapitre 17), tâche « Recette V1 — F4 et F7 ».
7. *Guide du marin 2023* : jamais disponible ; aucune règle ne s'y appuie.

**Points de code à confirmer**
8. Relations génériques (discussions, notifications, demandes, liens de document, RETEX, appareillage) vis-à-vis de la suppression ou de l'archivage d'une unité (risque résiduel déclaré de L03).
9. Quelles vues comparent un seuil au **grade** et lesquelles au **niveau d'écriture** (commandant en second) : établi chapitre par chapitre.
10. Bouton de désactivation d'un compte : non trouvé dans l'annuaire ; la désactivation passerait par l'administration Django (non vérifié).
11. Limitation des tentatives de connexion, en-têtes de sécurité avancés (CSP, HSTS) : non trouvés ; « absent » signifie « non trouvé par recherche ».
12. `CSRF_TRUSTED_ORIGINS` est une liste fixe (localhost) ; comportement d'un déploiement sous un autre nom d'hôte non éprouvé.
13. Clé primaire ou simple champ pour chacun des 12 modèles à champ UUID ; signification développée de « NNO ».
14. Les tâches nommées « daily » qui s'exécutent chaque minute (décision par marin selon son heure de notification) : documenté d'après les commentaires du code, non observé en exécution.

**Informations à fournir par le PO ou l'administrateur**
15. Ordre des grades et liste des brevets (IM-01, IM-02 du dossier V1.2).
16. Sauvegarde, restauration, supervision, durée de conservation des journaux et des notifications (IM-10).
17. Exigences des SIC pour l'hébergement et la sécurité (page 07 : principes seulement).
18. Circuits exacts PÉPIN, CRAT, RAV/c : non validés.

## 5. Résultats des contrôles de cohérence documentaire

| Contrôle | Résultat |
|---|---|
| Références de code (`fichier:ligne`) vérifiées **sur l'état B** : fichier existant, ligne existante et non vide, symbole annoncé présent sur la ligne citée | **238 références, 0 erreur** (après correction de 20 références imprécises détectées par le contrôle : bornes, symbole partagé entre deux références, fichier de rattachement implicite) |
| Identifiants de décision `DEC-…` cités | contrôlés contre le registre V1.2 (branche `claude/eager-hopper-2cbcqh`) : 0 inconnu |
| Structure de chaque chapitre : état B non fusionné rappelé, bloc « Pour qui », diffusion, étiquettes, section Limites, sources | **0 erreur** (1 écart initial corrigé : section Limites manquante au chapitre 3) |
| Liens et images résolus ; schémas sources exportés ; schémas référencés | 12 sur 12, 0 erreur |
| Chiffres cités (modèles, routes, tâches, migrations, actions, paquets) conformes à l'inventaire généré | 0 erreur (4 chiffres de dépendances validés après ajustement du contrôle) |
| Liaisons du schéma S09 et entités du schéma S10 présentes dans l'inventaire | 0 erreur |
| Motifs sensibles (adresse personnelle, mot de passe en clair) | aucun |
| Sous-ensemble de tests de l'état B rejoué | voir §5.1 |

### 5.1 Tests rejoués sur l'état B (sous-ensemble)

Exécution sur une copie de l'état B (`6d6d0be`, extraite par `git archive`), SQLite, `manage.py test org accounts matrix.tests.test_securite_terre_second --parallel 4` : **360 tests, OK, 8 ignorés** (tests réservés à PostgreSQL), 153 secondes. Ce sont les tests des paquets décrits par l'ensemble 1 (organisation, comptes, lecture seule à terre). La trace affichée au cours de l'exécution (`RuntimeError: panne`) est une panne simulée volontairement par un test de relève, non une erreur. **Les 3 963 tests de la suite complète n'ont pas été rejoués** : leur résultat est celui des comptes rendus des lots.

## 6. Contradictions et écarts découverts (sans modifier les décisions PO)

Ces points sont **signalés**, pas arbitrés. Les décisions du PO restent la référence ; il s'agit d'écarts entre une décision et le code actuel, ou entre deux documents.

| # | Écart | Nature | Où c'est traité |
|---|---|---|---|
| 1 | Décision : l'administrateur technique n'a **aucun visa métier**. Code : le niveau de l'administrateur d'unité (8) dépasse tous les seuils par défaut des actions métier ; seules des règles propres à certains circuits l'en écartent. | Décision non encore appliquée (lot L06) | Ch. 5 §5.11 |
| 2 | Décision `DEC-FDS-07/13` : les échanges sont décidés par le COMAEQ ou son suppléant. Code : `peut_valider_echange` donne la validation à qui gère la liste (`quarts/echanges.py:205`). | Décision non encore appliquée (L10) | Ch. 2 §2.4, ch. 8 (ensemble 2) |
| 3 | Décision `DEC-FDS-14` : le COMAEQ approuve et publie les listes. Code : le seuil `liste_service_publication` est « chef de service » (`matrix/core/role_thresholds.py`). | Décision non encore appliquée (L09) | Annexe B, ch. 8 |
| 4 | Décision : les droits d'écriture du commandant en second découlent de ses responsabilités, pas d'un seuil. Code : l'écriture héritée du grade lui est retirée, mais **certaines vues comparent le seuil à son grade** et d'autres à son niveau d'écriture : le comportement varie selon la vue. | Écart d'application à arbitrer | Annexe B (colonne ✱), ch. 5T §5T.2 |
| 5 | Règles du projet : « garder des identifiants stables (UUID, NNO) ». Code : UUID et NNO n'existent que côté matériel, catalogue, ticket et quelques objets de la feuille de service ; ni le compte, ni l'unité, ni la tâche. | Écart documentaire / périmètre non décidé | Ch. 19 §19.5 |
| 6 | `docs/REFERENCE.md` §4 intitulé « Les 14 apps Django » ; l'état B compte 21 applications et `matrix.core`. | Documentation du dépôt à jour à faire (déjà relevée au dossier V1.2, G2) | Ch. 2, 18 |
| 7 | ~~Décision : QR codes « hors V1 »~~ — **retiré après vérification** : `DEC-PRE-04` conserve l'existant (la route QR reste) ; le code est conforme. Voir `restreint/ECARTS_DECISIONS_CODE.md`. | Non-écart | Ch. 18 §18.10 |
| 8 | Cahier des charges §35 : modèle « RBAC + ABAC + périmètre + responsabilité ». Réalisé : rôle, périmètre, attributs ciblés (équipage, fonction de commandant adjoint), désignations ; pas de moteur d'attributs général. | Ambition décrite plus large que l'existant | Ch. 5 §5.2 |
| 9 | Cahier des charges §8, §10, §11 (génération automatique des tours) : **abandonnée** ; §20 (Rondes) : module retiré ; ancienne organisation « miroir » : retirée. | Cahier partiellement obsolète (déjà signalé par la décision du 09/10 et le dossier V1.2) | Ch. 1 §1.6, ch. 4 §4.3 |
| 10 | Principe « Internet n'existe pas » tenu par le code ; mais `boto3`, `requests` (et `django-storages` déclaré) figurent dans les dépendances sans usage constaté. | Observation d'exploitation, pas une contradiction | Ch. 18 §18.2 |
| 11 | Le vocabulaire cible de la page Notion 11 (mission, capacité, dérogation, profondeur de relève) n'a pas d'équivalent dans le code. | Cible, non développé | Ch. 19 §19.8 |

## 7. Pour la revue du PO

Points à examiner en priorité :
1. **Ton et niveau de détail** des chapitres 1 à 5 : un responsable comprend-il le modèle de droits (chapitre 5) sans lire le code ?
2. **Séparation diffusable / restreint** : la matrice rôle × action et les mécanismes de sécurité sont en restreint ; le chapitre 5 diffusable décrit les règles sans la table complète. Convient-il ?
3. **Les 11 écarts du §6** : lesquels demandent une décision, une précision ou un simple suivi ?
4. **Le périmètre de l'ensemble 2** (chapitres 6 à 10) : je lirai avant de rédiger la page Notion « 06 — Service courant » (déjà lue pour l'annexe A) ; confirmation que le circuit des échanges et des listes doit être décrit en réel (code actuel) puis en cible (`DEC-FDS-07/13/14`).

Je ne commence pas l'ensemble 2 sans votre revue.
