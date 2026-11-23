# Dossier technique de Matrix — Édition G0 : sommaire détaillé définitif (pour revue)

> **Statut : sommaire soumis à revue.** Aucune rédaction de chapitre n'est commencée. Aucun code applicatif modifié, aucune fusion dans `main`, aucune PR, aucun nouveau lot. Ce document complète et remplace, pour le sommaire, `G0_PROPOSITION.md`.

Date : 11/11/2026 · Branche : `claude/fervent-wright-kl6gtx`.

---

## 1. Sources V1.2 et comptes rendus : ce qui a été retrouvé

Lecture seule, directement depuis `origin/claude/eager-hopper-2cbcqh` (dernier commit `6cc1557`, 11/11/2026), dossier `docs/dossier-technique-v12/`. **Rien n'a été recopié ni recréé dans cette branche** : le dossier cite ces pièces par leur chemin et leur commit.

### 1.1 Les 10 pièces demandées : toutes retrouvées

| Pièce | Taille | Contenu utile pour le dossier |
|---|---|---|
| `00_SYNTHESE.md` | 5,9 Ko | Résultat de l'analyse, 28 lots, priorités, limites |
| `D_PLAN_CORRECTION.md` | 9,7 Ko | Premier plan par étapes (remplacé pour l'ordre par `M`) |
| `F_QUESTIONS_RESIDUELLES.md` | 10,6 Ko | 14 questions d'origine (statut dans `J`) |
| `I_CONTRADICTIONS_ET_MANQUES.md` | 10,4 Ko | 12 contradictions, 15 informations manquantes (statut dans `J`) |
| `J_TRIAGE_ET_ARBITRAGES.md` | 13,4 Ko | Triage résolu / technique / reportable ; notes Notion remplacées par une décision PO plus récente |
| `K_PRIORITES_JUSTIFIEES.md` | 18,4 Ko | Priorités P0 à P3 |
| `M_PLAN_DEVELOPPEMENT.md` | 27,3 Ko | 28 lots L01 à L28, phases A à E |
| `N_LOT_L01_COMPTE_RENDU.md` | 6,1 Ko | Verrou des commandes de démonstration |
| `P_LOT_L02_COMPTE_RENDU.md` | 8,9 Ko | Archivage effectif (version consolidée) |
| `Q_LOT_L03_COMPTE_RENDU.md` | 4,0 Ko | Suppression sûre des unités |

### 1.2 Autres pièces présentes (11)

`README.md`, `A_REGISTRE_DECISIONS.md` et `A1_DECISIONS_S1_S2.md` (**125 décisions PO** identifiées `DEC-…`), `B_CARTOGRAPHIE.md` (modules, acteurs, 13 circuits), `C_MATRICE_TRACABILITE.md`, `E_STRATEGIE_TESTS.md`, `E2_CATALOGUE_TESTS.md` (117 tests d'acceptation), `G_ECARTS_DOCUMENTAIRES.md` (plan du manuel), `H_ANOMALIES_47.md`, `L_SOURCES_NON_CONSULTEES.md`, **`O_LOT_L05_COMPTE_RENDU.md`** (compte rendu du lot L05, non cité dans votre liste mais présent).

### 1.3 Ce qui n'existe pas (et c'est normal)

Aucun compte rendu **L04** (lot non lancé) ni L06 à L28 (non lancés). Aucune pièce attendue n'est introuvable.

### 1.4 Vérification de votre compte rendu L03

Les comptes rendus confirment : suite complète SQLite **3 963 tests OK, 20 ignorés** (L01 : 3 884 → L05 : 3 895 → L02 : 3 952 → L03 : 3 963), relectures indépendantes validées, migrations avancées/retour vérifiées (L01 `accounts/0021–0022`, L03 `org` 14 `AlterField` sans SQL). Non vérifiés dans tous les lots : **PostgreSQL, Windows, navigateur réel** (versés au chapitre 24 et à la checklist du chapitre 23, sans tonalité d'audit). Le risque des relations génériques (fils de discussion, notifications) figure dans `Q` §5.3.

### 1.5 Trois réserves de méthode, à connaître

1. **Les références de code du dossier V1.2 se lisent sur la V1.1 `1c37f22`**, pas sur l'état B (`6d6d0be`), qui a ensuite reçu L01, L05, L02 et L03. Les numéros de ligne seront donc **tous revérifiés sur B** (étape G1) ; aucun n'est repris tel quel.
2. **La branche V1.2 (`eager-hopper`) n'est ni dans A ni dans B** : elle reste une branche documentaire séparée. Le dossier la cite par commit.
3. **Les sources qu'elle déclare non lues restent non lues** (`L_SOURCES_NON_CONSULTEES.md`) : Organigramme 02 (RH, qualifications, grades), 03 (formations, brevets), 07 (SIC), 11 (modèle de données cible), « Recette UX V1.1 » ; *Guide du marin 2023* jamais disponible. Je les lirai **avant** les chapitres qui en dépendent (voir §10) ; sinon les passages concernés restent ⚪.

---

## 2. Vos décisions, telles qu'appliquées

| Décision | Application |
|---|---|
| État B (`l03` @ `6d6d0be`) = référence principale | Chaque chapitre décrit B. L'état A (`main` @ `6ef16ad`) n'apparaît que dans un encadré « Comparaison avec `main` » en fin de section, uniquement pour ce qui diffère. **Mention permanente** : « État B, non fusionné dans `main` ». |
| Ne pas réutiliser les arbitrages V1.2 | Les décisions `DEC-…` sont **citées**, jamais rediscutées. Les 2 contradictions restantes ont été tranchées par le PO (S4 : `DEC-FDS-14`, `DEC-APP-14`) ; elles sont reprises comme règles cibles. |
| Branches : ne classer que les importantes | §9 : 15 branches classées, les autres en annexe F, sans analyse. |
| Format | Markdown maintenable ; PDF produit **une fois le contenu stabilisé** (étape finale) ; Mermaid conservé en `.mmd` + SVG ; séparation diffusable / restreint ; Notion = décisions et connaissances, lien et statut seulement. |
| Rédaction groupée, pas 8 validations | **4 ensembles** (§4), soit 4 validations de contenu après celle du sommaire. |
| Trois blocs par chapitre | Voir §5. |

### Corrections au cadrage G0 précédent

- **22 paquets applicatifs**, pas 20 : 21 applications Django + `matrix.core` (confirmé par `INSTALLED_APPS` sur B et par `B_CARTOGRAPHIE.md`). `reports` et `matrix.core` n'ont pas la même structure que les autres.
- **Les nombres de modèles du premier cadrage étaient approximatifs** (comptage grossier des classes). Sur B, un comptage plus strict donne par exemple `assets` 29, `quarts` 19, `accounts` 10, `org` 15. **Les chiffres définitifs viendront de l'inventaire G1** ; aucun chiffre non mesuré ne sera publié.
- **`rondes`** : le module est retiré fonctionnellement (code et migrations conservés, `B_CARTOGRAPHIE` « résidu du module retiré », cahier §20 obsolète). Il est décrit comme tel en chapitre 12, pas comme fonction opérationnelle.
- D2 (dossier V1.2) et D3 (comptes rendus) sont **résolues**.

---

## 3. Diffusion : convention

- **[D] Diffusable** : usage, règles métier, rôles et circuits, parcours, ergonomie. Public : marins, responsables, état-major.
- **[R] Restreint** : architecture, modèles de données, API, sécurité, configuration, déploiement, exploitation, résultats de tests, détails de contrôle d'accès.
- Chaque chapitre mixte est livré en **deux fichiers** : `NN_titre.md` ([D]) et `NN_titre_technique.md` ([R]). Les chapitres 18 à 24 sont entièrement [R].
- Arborescence : `docs/dossier-technique/diffusable/` et `docs/dossier-technique/restreint/`. Le PDF « général » ne contient que [D] ; le PDF « complet » contient [D] + [R] et porte la mention de diffusion restreinte.
- Aucune donnée réelle, aucune clé, aucun mot de passe, y compris ceux des instances de démonstration, n'est écrit dans le dossier.

---

## 4. Regroupement de la rédaction : 4 ensembles, 4 validations

| Ensemble | Chapitres et annexes | Validation demandée au PO |
|---|---|---|
| **E1 — Fondations** | 1–5, 18, 19, 22 ; annexes A, B | Vision, organisation, rôles et droits, architecture, données, sécurité |
| **E2 — Vie du bord** | 6–10 | Accueil, calendrier, quarts et feuilles de service, communication, tâches |
| **E3 — Technique, savoir, appareillage** | 11–16 | Matériel, maintenance, logistique, formation, documentation, appareillage |
| **E4 — Interface, exploitation, cible** | 17, 20, 21, 23–26 ; annexes C, D, E, F, G, H | Ergonomie, API, interactions, exploitation, cible, historique ; PDF |

Entre deux ensembles, aucune attente : j'enchaîne. Je ne m'arrête que sur un point métier incertain (jamais deviné). Un point d'étape de 10 lignes est publié à la fin de chaque ensemble, sans exiger de réponse pour continuer.

---

## 5. Gabarit de chaque chapitre

1. **Encadré lecteur** : pour qui, ce que vous y trouverez, prérequis, diffusion [D]/[R].
2. **Fonctionnement réel** 🟢 — vérifié dans B, avec références `fichier:ligne` (B) et, si différent, comparaison avec A.
3. **Fonctionnement cible** 🔵 — validé par le PO, non (ou partiellement) développé : identifiant `DEC-…`, lot `Lnn`, statut. **Jamais au présent.**
4. **Limites et éléments non vérifiés** ⚪ — périmètre actuel, ce qui n'a pas été rejoué, sources non lues. Court, sans inventaire d'anomalies.
5. **Schémas** du chapitre.
6. **Sources** (code, tests, décisions, comptes rendus).

Style : un texte qui explique (pourquoi, comment, qui, quand), avec exemples fictifs et schémas ; pas de fiches d'audit.

---

## 6. Sommaire détaillé : 26 chapitres

Lecteurs : **M** marin · **R** responsable · **D** développeur · **A** administrateur. Diffusion : **[D]** / **[R]**.

### PARTIE I — COMPRENDRE MATRIX

#### 1. Vision, philosophie et principes non négociables — [D] — M R D A
- Ambition (« l'application ouverte chaque jour »), Matrix n'est pas une GMAO, la GMAO en est un module.
- Les cinq questions du marin : où dois-je être, que dois-je faire, que dois-je savoir, avec qui, que dois-je signaler.
- Les 10 principes de `CLAUDE.md` et les 7 du cahier : français, plus rapide qu'Excel, espace personnel, Internet n'existe pas, visuel, configuration > code, proposer → valider → publier, traçabilité, dialogue métier, administration distribuée.
- Ce que Matrix **n'est pas** : n'autorise pas l'appareillage, ne bloque pas par qualification pour les tâches ordinaires, ne remplace pas SIGLe/ODIN/SSF, pas un système officiel ni homologué.
- *Cible* : ambition à terme (système d'exploitation numérique du bord).
- Schémas : carte de la philosophie ; journée type du marin.

#### 2. Vue d'ensemble : modules, acteurs, parcours-types — [D] — M R D A
- Les 22 paquets regroupés en domaines (personnes, vie quotidienne, communication, technique, connaissance, pilotage, transverse).
- Acteurs par **fonction** (équipier, chefs de section/secteur/service, commandants adjoints COMAEQ/COMOPS/COMANAV/COMAVIA, commandant et second, BSC, chef de liste, administrateur technique, équipage à terre/B, suppléant).
- Trois parcours-types : marin, chef, acteur à terre.
- Schémas : carte des modules ; acteurs × modules.

#### 3. Lire ce dossier — [D] — tous
- États A/B, étiquettes 🟢🔵⚪, diffusion, références, historique des révisions du dossier.
- Glossaire d'orientation (le glossaire complet est l'annexe A).
- Ce que le dossier ne contient pas : audit, registre d'anomalies.

### PARTIE II — ORGANISATION ET PERSONNES

#### 4. Organisation : bâtiments, équipages, unités — [D]+[R] — R D A
- Hiérarchie bâtiment → service → secteur → section (facultative ; le secteur est l'échelon responsable sans section).
- Types d'unités (navire, école, centre de formation, bureau), classes de navire.
- **Double équipage A/B**, relève validée, lecture seule à terre, équipage à terre.
- **Archivage et suppression sûre des unités** (L02, L03) : règle d'occupation, règle des références, ce qui reste consultable.
- Modules activables par bâtiment ; contexte de bâtiment ; configuration versionnée.
- *Cible* : structure du bord par fonction habilitée (L12) ; mutation de personnel (L25, reportée, dépendante de l'architecture bord–terre).
- *Limites* : synchronisation bord–terre non développée ; relations génériques non vérifiées (`Q` §5.3).
- Schémas : hiérarchie d'unités ; double équipage et relève ; cycle de vie d'une unité (active → archivée → supprimable).

#### 5. Comptes, fonctions, grades, rôles, autorisations, administration — [D]+[R] — R D A
- Compte, profil, rattachement (bâtiment, équipage, service, secteur, section), grade, fonction exercée, brevets/habilitations : **cinq notions distinctes**.
- Rôles hiérarchiques et niveaux de rôle ; permissions par action ; seuils de rôle configurables ; périmètre (`scope_filters_for_user`).
- **Administration distribuée** : écran Réglages, qui configure quoi ; limites de l'administrateur technique (aucun visa métier).
- Création, édition, action de masse, désactivation de compte, historique.
- Authentification, mot de passe, session, inactivité.
- *Cible* : exclusion de l'administrateur technique des actes métier (L06), rattachement incomplet et validation des rôles (L07), suppléance explicite (L08), désactiver plutôt que supprimer un compte (L04, non lancé), rang des grades configurable (L16), droits par fonction.
- *Limites* : Organigramme 02/03/11 non lus à ce jour ⚪.
- Schémas : de la personne au périmètre ; calcul des droits ; matrice rôle × action (extrait).

### PARTIE III — VIE QUOTIDIENNE

#### 6. Espace personnel, tableaux de bord, pilotage et rapports — [D]+[R] — M R
- Accueil « Aujourd'hui » à bord et à terre, cartes « À faire », Mon quotidien.
- Tableaux de bord par niveau (marin → commandement), vue flotte, vue COMANAV, spécialité/classe.
- Passation (préservation de l'existant, pas de module autonome).
- Rapports : bilans instantané/période, exports PDF/CSV/Excel.
- *Cible* : pilotage SSF, indicateurs de commandement (phase 6).
- Schémas : accueil par rôle ; du fait métier à l'indicateur.

#### 7. Calendrier central — [D]+[R] — M R D
- Sources d'événements (quarts, services, tâches, formations, maintenance, absences), vue personnelle et globale, déplacements, export iCal, accès aux fichiers.
- *Cible* : calendrier intégrateur, échéances.
- Schémas : sources → calendrier ; périmètre de lecture.

#### 8. Quarts, services, gardes, feuilles de service, échanges, absences — [D]+[R] — M R D
- Listes de quarts et de gardes, chef de liste, versions, publication ; planification **manuelle** avec contrôle des contraintes (génération automatique abandonnée le 09/10).
- Feuille de service : BSC, visa COMAEQ ou suppléant, versions, rectificatif, historisation, escalade, suivi.
- Échanges de tours : instruction, décision, effet sur les calendriers, traçabilité ; compteur d'équité ; absences et indisponibilités ; alertes ; fraction, tiers, bordée.
- *Cible* : échanges décidés par le COMAEQ ou son suppléant (L10, `DEC-FDS-07/13`) ; listes préparées par le chef de liste, approuvées et publiées par le COMAEQ (L09, `DEC-FDS-14`) ; réimpression et fraction à quai (L27) ; suppléance (L08).
- Schémas : circuit des échanges ; feuille de service (états, versions) ; publication d'une liste.
- Chapitre le plus dense : il sera livré en deux fichiers (8a listes et services ; 8b feuille de service et échanges) sans changer sa numérotation.

#### 9. Communication : discussions, annonces, notifications, recherche — [D]+[R] — M R D
- Discussions attachées aux objets (principe 9), mentions ; annonces et accusés ; niveaux de diffusion et périmètre.
- Notifications in-app, par régime, Web Push, délai borné, Celery ; recherche globale et rapide.
- *Cible* : espaces de groupe (section, secteur, bâtiment), messagerie contextuelle avec la terre, épinglage et recherche de personnes (L24).
- *Limites* : relations génériques (discussions, notifications) à contrôler avant production ⚪.
- Schémas : discussion attachée à un objet ; de l'événement à la notification.

#### 10. Tâches, demandes, programme, postes — [D]+[R] — M R D
- Cycle de vie d'une tâche, attribution par les chefs, participants, checklist, pièces jointes, blocage, fil contextuel.
- Demandes, programme du bâtiment, postes.
- *Cible* : trois niveaux de priorité (L14), validation facultative et statut « À valider » (L15), coordinateur de tâche collective (L16), « Bloquée » et « Non réalisée — À reprogrammer » (L17).
- Schémas : états d'une tâche (réel puis cible, clairement séparés) ; tâche ↔ maintenance ↔ anomalie.

### PARTIE IV — ACTIVITÉ TECHNIQUE ET LOGISTIQUE

#### 11. Matériel et installations — [D]+[R] — R D
- Installations fixes, matériel mobile, catalogue et reprise, hiérarchie parent/enfant, documents, mesures et détection de dérive, historique d'équipement.
- Fiches et circuits de fiches (installation, matériel flotte).
- *Cible* : transfert de matériel intra/inter-services (L13).
- Schémas : arbre d'un équipement ; circuit de fiche.

#### 12. Maintenance, anomalies, tickets correctifs, rondes — [D]+[R] — M R D
- Plans préventifs, occurrences, exécutions guidées, confirmations explicites, comptes rendus, historique, séries de relevés.
- Anomalies et tickets correctifs (cycle de réparation, retour en service).
- `rondes` : module retiré, résidu conservé.
- *Cible* : périodicités nommées (L19), durée estimée actualisée (L20), anomalies/interventions/ticket (L22), remarques d'outillage (L26).
- Schémas : de l'échéance à la clôture ; ticket correctif.

#### 13. Logistique : stocks, pièces, demandes — [D]+[R] — R D
- Pièces, stocks, mouvements, demandes, retours, alertes de stock bas, périmètre par secteur/section.
- *Cible* : prêts, inventaires, EPI (cahier §21), selon statut réel à vérifier.
- Schémas : flux d'une demande de pièce.

### PARTIE V — CONNAISSANCE ET PRÉPARATION

#### 14. Formations, qualifications, référents — [D]+[R] — M R D
- Formations, prérequis anti-cycle, catégories, arbre de compétences, référents habilités, sessions et réservation, portabilité, fusion de formations.
- Règle : qualifications **informatives** pour les tâches ordinaires ; exigences réglementaires respectées pour visas, fonctions de service, signatures officielles.
- *Cible* : L18 ; référentiel de brevets configurable (BHT, C-CDM…), alimenté par le bord.
- *Limites* : Organigramme 02/03 non lus ⚪.
- Schémas : arbre de compétences ; validation par un référent.

#### 15. Documentation et RETEX — [D]+[R] — M R D
- Bibliothèque documentaire, types, ciblage par unité ; RETEX (déclaration, consultation).
- *Cible* : circuit RETEX hiérarchique (L11 : auteur → chef de section → chef de secteur → chef de service), bibliothèque validée.
- Schémas : circuit RETEX (cible) à côté de l'existant.

#### 16. Préparation à l'appareillage — [D]+[R] — R D
- Session d'appareillage existante (signature simple), points de contrôle.
- *Cible* : fiche de référence proposée par le chef de secteur, examinée par le chef de service, approuvée par le COMANAV ; contrôles obligatoires/critiques, réserves, points non dérogeables (L23, `DEC-APP-*`, dont `DEC-APP-14`).
- *Limites* : compatibilité avec les procédures du bord **non vérifiée** ⚪.
- Schémas : circuit d'appareillage (réel, cible).

### PARTIE VI — INTERFACE

#### 17. Ergonomie, navigation, charte, mobile — [D]+[R] — M R D
- Principes (non-surcharge, aide progressive), navigation par rôle et modules activés, menu repliable, accueil, saisie en grille, brouillons, confirmations, aide.
- Charte « Naval Premium » et design system (submodule `design/`), composants, styleguide, accessibilité, hors-ligne (aucun CDN).
- Interface mobile, tablette, poste de bord.
- *Cible* : ergonomie (plusieurs petits lots, L24).
- *Limites* : submodule `design/` non initialisé ici ⚪ ; recette navigateur non rejouée.
- Schémas : plan de navigation par rôle ; structure de l'accueil ; captures (données fictives).

### PARTIE VII — TECHNIQUE, ADMINISTRATION, EXPLOITATION — tout [R]

#### 18. Architecture technique — D A
- Pile (Django 5, DRF, HTMX, Bootstrap, Celery/Redis, SQLite/PostgreSQL), 22 paquets, dépendances, `matrix.core` (rôles, scopes, middlewares, recherche, modules), gabarits.
- Schémas : contexte (bord / terre / aucun Internet) ; couches ; dépendances entre paquets.

#### 19. Modèles de données — D
- Dictionnaire par domaine, relations, identifiants stables (UUID, NNO), relations génériques, `AuditLog`, protections `PROTECT` (L03), migrations (par lot).
- Schémas : un diagramme entité-relation par domaine.

#### 20. API REST et interfaces web — D
- Routes `/api/…` et pages, authentification, filtrage par périmètre, codes d'erreur (dont 409 L03), conventions.
- Schémas : carte des routes par domaine.

#### 21. Interactions entre modules — D
- Signaux, services partagés, notifications, tâches Celery planifiées, flux inter-paquets (anomalie → ticket, tâche ↔ maintenance, formation → information).
- Schémas : matrice paquet × paquet ; flux asynchrones.

#### 22. Sécurité — D A
- Authentification, sessions, périmètres, accès aux fichiers, audit et traçabilité, versionnage, proposer → valider → publier.
- Mécanismes ajoutés par les lots : verrou des commandes de démonstration (L01), configuration de production (L05), archivage effectif (L02), suppression sûre (L03).
- *Cible* : sécurité d'accès avec les SIC (L21), désactivation de comptes (L04).
- *Limites* : Organigramme 07 non lu ⚪.
- Schémas : chaîne de contrôle d'une requête ; garde de démonstration.

#### 23. Configuration, déploiement, exploitation — A D
- Environnements, variables, SQLite/PostgreSQL, Docker (Postgres/Redis), Celery worker et beat, VAPID, préparation d'instance de démonstration/test, migrations, mise en production, **checklist avant production**.
- *Cible/à définir avec les SIC* : sauvegarde et restauration, supervision Redis/Celery, HTTPS, conservation des journaux (à fournir, non documenté aujourd'hui) ⚪.
- Schémas : déploiement type ; cycle d'une instance de démonstration.

#### 24. Qualité et contribution — D
- Stratégie de tests (suite complète : 3 963 OK, 20 ignorés, sur SQLite), ce qui n'est pas couvert (PostgreSQL, Windows, navigateur), hooks, contrôle des migrations, système PO/Dev/Relecteur, conventions.
- *Cible* : dette documentaire et CI (L28).
- Schémas : chaîne d'un lot (cadrage → développement → relecture → validation).

### PARTIE VIII — CIBLE ET RÉFÉRENCES

#### 25. Fonctionnement cible — [D] — tous
- Regroupement des fonctions validées non développées, par domaine : plan en 28 lots (phases A à E), état de chacun (L01, L02, L03, L05 : livrés sur B ; L04 et les autres : non lancés), `DEC-…` associées, dépendances.
- Dépendance externe : architecture bord–terre (mutation, synchronisation).
- Jamais au présent ; renvoi vers les chapitres concernés.
- Schémas : feuille de route ; dépendances entre lots.

#### 26. Historique des versions et des lots — [D]+[R] — D A
- Chronologie : V1 FANLAB (`main` @ `6ef16ad`), V1.1 (`1c37f22`), L01, L05, L02, L03 (empilés, B), dossier V1.2.
- Ce que chaque lot a changé dans l'état technique (tests, migrations, branches), **branches non fusionnées**.
- Branches importantes (§9) ; reste en annexe F.
- Schémas : généalogie des branches.

---

## 7. Annexes détaillées (8)

| Réf. | Titre | Contenu | Diffusion | Ensemble |
|---|---|---|---|---|
| **A** | Glossaire | Acronymes et vocabulaire Marine (COMAEQ, COMOPS, COMANAV, COMAVIA, BSC, OPN/DDI, OG, OPSC, fraction, tour, bordée, tiers…), distinction rôle / fonction / grade / brevet | [D] | E1 |
| **B** | Matrice rôle × action | Générée depuis la configuration réelle (B) ; périmètres ; ce que l'administrateur technique ne peut pas faire | [R] | E1 |
| **C** | Index des routes web et API | Généré par script ; vue → gabarit | [R] | E4 |
| **D** | Index des modèles | Une ligne par modèle : paquet, chapitre, relation générique ou non | [R] | E4 |
| **E** | Tâches planifiées et commandes de gestion | Celery beat, `management/commands`, variables | [R] | E4 |
| **F** | Sources, branches et éléments non vérifiés | Sources lues / non lues, `DEC-…` utilisées, **liste des branches distantes non analysées**, registre des ⚪ | [R] | E4 |
| **G** | Matrice de couverture | Élément du code → chapitre → statut (rédigé, vérifié, relu) | [R] | E4 |
| **H** | Index des schémas | Titre, fichier `.mmd` / `.svg`, chapitre | [D] | E4 |

---

## 8. Méthode de couverture (rappel et ajustement)

Inchangée dans son principe (cf. `G0_PROPOSITION.md` §4) : inventaire par script en lecture seule sur B (et A pour comparaison) → matrice G → clôture à 0 ligne non affectée → références `fichier:ligne` contrôlées → parcours rejoués sur instance de démonstration. Ajout : **chaque `DEC-…` utilisée est vérifiée contre sa source**, et celles remplacées par une décision plus récente (`J` §2) ne sont pas reprises.

### Contrôle de couverture de votre liste de contenu

| Votre demande | Chapitre(s) |
|---|---|
| Vision et philosophie | 1 |
| Architecture technique complète | 18, 21 (+ 2) |
| Bâtiments et équipages | 4 |
| Comptes, fonctions, grades, autorisations | 5 |
| Tableau de bord et calendrier | 6, 7 |
| Tâches, maintenance, anomalies, interventions | 10, 12 |
| Matériel, installations, stocks, logistique | 11, 13 |
| Quarts, gardes, feuilles de service, échanges | 8 |
| Annonces, messagerie, notifications, recherche | 9 |
| Formations, qualifications, RETEX | 14, 15 |
| Préparation à l'appareillage | 16 |
| Ergonomie, navigation, charte, mobile | 17 |
| Administration, sécurité, déploiement, exploitation | 5, 22, 23, 24 |
| Modèles de données, API, interactions | 19, 20, 21 |
| Schémas, circuits, parcours | tous (annexe H) |

### Domaines que j'ajoute pour qu'aucun ne soit oublié
Absences (8) · postes, programme, demandes (10) · rondes retirées (12) · passation (6) · seuils de rôle (5) · modules activables (4) · instance de démonstration et `seed_demo` (23) · brouillons et inactivité de session (17, 22) · fichiers médias sécurisés (7, 22) · journal d'audit (19, 22) · mutation et suppléance (cible : 4, 5, 25) · SIC et sécurité d'accès (cible : 22, 23).

---

## 9. Branches : seules celles qui expliquent l'évolution

| Branche (suffixe) | Date | Dans A / B | Rôle pour comprendre Matrix |
|---|---|---|---|
| `main` | 28/10 | A | V1 FANLAB (PR #16) : point de comparaison |
| `integration/v1-fanlab-20261021` | 27/10 | A, B | Consolidation de la V1 FANLAB |
| `integration/pr6-et-travail-local` | 10/10 | A, B | Base des PR #6 et #7 (cahier : baseline du 10/10) |
| `paquet-bordops-review-69huab` | 01/10 | A, B | Retrait de la génération automatique des quarts |
| `feuille-service-*` (4), `quarts-regler-echanges-atomique` | 17–22/10 | A, B | Chaîne feuille de service et échanges |
| `securite-*` (4), `fiabilite-*` (3), `validations-critiques-confirmation`, `compat-postgresql`, `fix-ano-001-equipage-postgres` | 10–21/10 | A, B | Sécurité, fiabilité, PostgreSQL |
| `ux9-*` (5), `ergonomie-p2`, `docs/cahier-ux` | 02–27/10 | A, B | Ergonomie et cahier UX |
| `ux-naval-premium-v11` | 31/10 | B seul | Prototype UX V1.1 |
| `recette-metier-ux-v11-20261101` | 01/11 | B seul | Correctifs métier et UX V1.1 |
| `iteration-ux-v11-20261102` | 05/11 | B seul | **V1.1 (`1c37f22`)**, base des lots |
| `matrix-audit-general-9oohvw` / `-rg0ddz` | 05/11 | ni A ni B | Audit général V1.1 (source du V1.2, non repris) |
| `matrix-v1-recette-audit-4olae7`, `recette-v1-passage-b` | 13–20/10 | ni A ni B | Recette V1 (arbitrages D-05/D-06) |
| `eager-hopper-2cbcqh` | 11/11 | ni A ni B | **Dossier V1.2 et comptes rendus** |
| `l01`, `l05`, `l02`, `l03` | 10–11/11 | B (empilés) | Lots livrés, non fusionnés |
| `maquette-carte-a-faire` | 30/10 | ni A ni B | Maquette « ne pas fusionner » |

Les ~25 autres (anciens essais de printemps/été, `economie-tokens`, `sauvegarde/sonnet-…`, `quizzical-curran`, `ux-fondations`, `ux-3-10`, `taches-lot1`, `verif-socle-accounts`, `matrix-project-tasks-…`…) sont **listées en annexe F sans analyse**.

---

## 10. Sources encore à lire, et quand

| Source | Pourquoi | Avant le chapitre |
|---|---|---|
| Notion Organigramme 02, 03, 11 | Qualifications, brevets, grades, modèle de données cible | 5, 14, 19 (E1/E3) |
| Notion Organigramme 07 (SIC) | Exigences sécurité, déploiement | 22, 23 (E1/E4) |
| « Recette UX V1.1 », « [CADRAGE UX] » | Ergonomie | 17 (E4) |
| Tâche « Recette V1 — F4 et F7 » | Droits du commandement à terre | 5 (E1) |
| `docs/propositions/*`, `docs/recette/*` (état B) | Décisions datées, parcours | chapitres concernés |
| Submodule `design/` | Charte graphique | 17 |
| Fournies par l'administrateur / les SIC | Sauvegardes, supervision, durées de conservation | 23 |
| *Guide du marin 2023* | Jamais disponible ; **non utilisé** | — |

Une page non lue au moment de rédiger un chapitre rend ⚪ les passages qui en dépendent, et le dit.

---

## 11. Ce que je vous demande

1. **Revue du sommaire** : ajouts, retraits, changements d'ordre ? Un domaine manque-t-il ? (§8 donne mon contrôle.)
2. **Confirmer le regroupement en 4 ensembles** (§4) et la convention [D]/[R] (§3).
3. **Confirmer le déplacement de « pilotage et rapports »** : ils passent au chapitre 6, ce qui libère le chapitre 16 pour la préparation à l'appareillage, que vous aviez listée à part.

Après votre validation, je commence **G1** (outils d'inventaire, matrice de couverture, mesures définitives sur B), puis E1.
