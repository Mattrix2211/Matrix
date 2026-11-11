# Dossier technique intégral de Matrix — Édition G0 : proposition de cadrage

> **Statut : proposition soumise à validation.** Aucune rédaction du dossier n'est commencée. Aucun code applicatif n'est modifié. Ce document ne contient ni audit ni liste d'anomalies : il décrit comment le dossier sera construit, vérifié et relu.

Date : 11/11/2026 · Branche documentaire : `claude/fervent-wright-kl6gtx` (aucune fusion dans `main`, aucune PR).

---

## 0. Points à trancher avant de commencer (décisions demandées)

| # | Question | Pourquoi elle bloque | Recommandation |
|---|---|---|---|
| D1 | **Quelle base de code décrire comme « fonctionnement actuel » ?** | Les branches L01, L05, L02 et L03 sont **empilées** : `l03-suppression-sure-v11` contient les trois autres (vérifié par ancêtre git). Elles ajoutent ~120 commits à `main` (6ef16ad, V1 FANLAB), dont tout le travail V1.1 (UX « Naval Premium », recette, documents `docs/propositions/`, `docs/recette/`), pas seulement L01–L03. | Décrire **deux états étiquetés** : « État A — `main` @ 6ef16ad (publié) » et « État B — `l03` @ 6d6d0be (non fusionné) ». Le texte part de B et marque chaque écart avec A. |
| D2 | Où est le **« dossier V1.2 »** ? | Introuvable dans le dépôt et dans Notion (qui contient V1 FANLAB et V1.1, pas V1.2). | Le transmettre (lien Notion ou fichier). À défaut, G0 le déclare « source absente ». |
| D3 | Où sont les **comptes rendus de lots** L01–L03 (3 963 tests, relecture indépendante) ? | Introuvables par recherche Notion. Seules traces : `docs/recette/L01_recette_windows.md` et l'historique git de `l03`. | Indiquer leur emplacement. Les chiffres de tests ne seront cités que s'ils sont sourcés. |
| D4 | Format de livraison | Mermaid ne se rend pas hors ligne sans bibliothèque ; Matrix interdit les CDN. | Markdown + schémas Mermaid **exportés en SVG** committés, plus un export PDF (WeasyPrint, déjà présent) pour diffusion à bord. |
| D5 | Public et confidentialité | Le dossier détaille la sécurité et le déploiement. | Deux parties distinguées : **Utilisateurs/Responsables** (diffusable) et **Technique/Administration** (diffusion restreinte). |
| D6 | Emplacement de la version de référence | La vision vit dans Notion, pas dans le dépôt. | Le dossier vit dans `docs/dossier-technique/` ; Notion ne contient qu'un lien et le statut d'avancement (une information, un seul endroit). |

---

## 1. Principes éditoriaux (communs à tous les chapitres)

1. **Trois étiquettes obligatoires** sur chaque affirmation structurante :
   - 🟢 **Actuel** — existe dans le code, avec référence `chemin:ligne` (ou migration, test, gabarit) sur l'état A et/ou B.
   - 🔵 **Cible** — décidé par le PO (source citée : page Notion + date), non développé ou partiel. Jamais rédigé au présent.
   - ⚪ **Non vérifié** — information issue d'une seule source (Notion, mémoire) non confrontée au code ; listée dans l'annexe F.
2. **Pas d'audit.** Les anomalies ne sont pas décrites. Une limite connue n'apparaît que comme « périmètre actuel » d'une fonction ; les contrôles à faire avant production (dont les relations génériques des discussions et notifications) figurent dans la checklist du chapitre 23.
3. **Une décision Notion ancienne n'est jamais reprise telle quelle.** Chaque décision citée est confrontée au code ; en cas d'écart, le dossier décrit le code et signale l'écart en annexe F. À confronter d'emblée : génération automatique des tours (abandonnée le 09/10), modèle `org.Equipage` / organisation miroir (historique), double équipage A/B (retenu), QR codes (écartés).
4. **Français partout**, vocabulaire Marine (COMAEQ, COMOPS, COMANAV, COMAVIA, commandant en second…), identifiants de code laissés tels quels.
5. **Quatre lecteurs, quatre entrées** : chaque chapitre ouvre par un encadré « Pour qui / Ce que vous y trouverez » (Marin · Responsable · Développeur · Administrateur).
6. **Données fictives uniquement** dans les exemples et captures.

---

## 2. Sommaire exhaustif et hiérarchisé

Lecteurs : **M** marin · **R** responsable · **D** développeur · **A** administrateur.

### Partie I — Comprendre Matrix
| Ch. | Titre | Lecteurs |
|---|---|---|
| 1 | Vision, philosophie et principes non négociables | M R D A |
| 2 | Vue d'ensemble : modules, acteurs, parcours-types | M R D A |
| 3 | Lire ce dossier : méthode, étiquettes, états A/B, glossaire Marine | tous |

### Partie II — Organisation et personnes
| Ch. | Titre | Lecteurs |
|---|---|---|
| 4 | Organisation : bâtiments, équipages (A/B, relève), services, secteurs, sections, classes de navire, modules activables | R D A |
| 5 | Comptes, fonctions, grades, rôles et autorisations (rôle + périmètre + responsabilité), seuils de rôle, comptes désactivés/archivés | R D A |

### Partie III — Vie quotidienne
| Ch. | Titre | Lecteurs |
|---|---|---|
| 6 | Espace personnel, tableaux de bord par niveau, accueil à terre / à bord, passation | M R |
| 7 | Calendrier central, événements sources, déplacements, export iCal | M R D |
| 8 | Quarts, services à quai, gardes, listes et chef de liste, échanges, absences, feuille de service, compteur d'équité | M R D |
| 9 | Communication : discussions contextuelles, annonces, messagerie, mentions, notifications, Web Push, recherche | M R D |

### Partie IV — Activité technique et logistique
| Ch. | Titre | Lecteurs |
|---|---|---|
| 10 | Tâches, demandes, programme, postes | M R D |
| 11 | Matériel et installations : catalogue, équipements, hiérarchie, documents, mesures, dérive | R D |
| 12 | Maintenance : plans préventifs, occurrences, exécutions guidées, comptes rendus, historique ; anomalies et tickets correctifs ; rondes | M R D |
| 13 | Logistique : stocks, pièces, demandes, mouvements, retours | R D |

### Partie V — Connaissance et préparation
| Ch. | Titre | Lecteurs |
|---|---|---|
| 14 | Formations, qualifications, référents habilités, arbre de compétences, sessions | M R D |
| 15 | Documentation et RETEX | M R D |
| 16 | Préparation à l'appareillage, pilotage et rapports | R D |

### Partie VI — Interface
| Ch. | Titre | Lecteurs |
|---|---|---|
| 17 | Ergonomie, navigation, charte graphique, interface mobile, saisie en grille, brouillons | M R D |

### Partie VII — Technique, administration, exploitation
| Ch. | Titre | Lecteurs |
|---|---|---|
| 18 | Architecture technique : couches, applications, dépendances, middlewares, services transverses (`matrix/core`) | D A |
| 19 | Modèles de données : dictionnaire par application, relations, identifiants stables (UUID, NNO), relations génériques | D |
| 20 | API REST et interfaces web : points d'entrée, authentification, filtrage par périmètre | D |
| 21 | Interactions entre modules : signaux, notifications, tâches Celery, flux inter-apps | D |
| 22 | Sécurité : authentification, sessions, périmètres, fichiers, audit, versionnage, proposer → valider → publier | D A |
| 23 | Configuration, déploiement et exploitation : variables, PostgreSQL, Redis/Celery, sauvegardes, migrations, préparation d'instance de test, mise en production, checklist avant production | A D |
| 24 | Qualité : tests, hooks, contrôles, procédure de contribution (agents, Notion) | D |

### Partie VIII — Cible et références
| Ch. | Titre | Lecteurs |
|---|---|---|
| 25 | **Fonctionnement cible** : fonctions validées par le PO non (ou partiellement) développées, avec statut et source | tous |
| 26 | Historique des versions et des lots (V1 FANLAB, V1.1, L01/L05/L02/L03) : effet de chaque lot sur l'état technique | D A |

### Annexes
A glossaire Marine/Matrix · B matrice rôle × action (générée depuis la configuration) · C index des URL web et points d'API · D index des modèles · E tâches Celery et commandes de gestion · F registre des sources et informations non vérifiées · G matrice de couverture · H index des schémas.

---

## 3. Contenu prévu par chapitre

Gabarit commun : **À quoi ça sert → Qui s'en sert → Parcours → Règles métier → Modèle de données → Interfaces (web/API) → Liens avec les autres modules → Cible → Sources**.

| Ch. | Contenu précis | Sources principales |
|---|---|---|
| 1 | Ambition (« l'application ouverte chaque jour »), GMAO = un module, les 10 principes de `CLAUDE.md`, « Internet n'existe pas », configuration > code, administration distribuée. | Cahier des charges §1–5, 26, 33, 41 ; `CLAUDE.md` |
| 2 | Carte des 20 applications Django regroupées en modules fonctionnels ; acteurs ; trois parcours types (marin, chef, acteur à terre). | `matrix/urls.py`, `INSTALLED_APPS`, `matrix/core/navigation.py`, `modules.py` |
| 3 | Méthode, états A/B, étiquettes, lecture des renvois `fichier:ligne`. | ce document |
| 4 | Entités `org` (17 modèles), double équipage A/B, relève validée, lecture seule à terre, activation de modules par bâtiment, contexte de bâtiment. | `org/models.py`, `matrix/core/equipage.py`, `contexte_batiment.py` ; Notion « Organigramme et rôles » |
| 5 | `accounts` (11 modèles), `RoleLevel`, `RolePermission`, `scope_filters_for_user`, seuils, fonctions/grades, désactivation/archivage (L02), création et action de masse. | `accounts/`, `matrix/core/roles.py`, `permissions.py`, `scopes.py`, `role_thresholds.py` ; Notion « Organigramme » et « 13 — Décisions » |
| 6 | `dashboard` (aujourd'hui, à terre, COMANAV, passation), indicateurs par niveau. | `dashboard/` |
| 7 | Sources d'événements, calendrier personnel/global, déplacements, iCal, accès aux fichiers. | `calendar_app/` |
| 8 | `quarts` (22 modèles) : listes, versions, publication, échanges (marin A → marin B → chef), absences, feuille de service (historisation, rectificatif, escalade, suivi), alertes, équité ; planification manuelle (génération automatique abandonnée). | `quarts/`, `absences/`, `docs/propositions/modales_et_quarts.md`, `mer_quai_*.md` |
| 9 | `threads` (3), `annonces` (4), `notifications` (3), Web Push, notifications par régime, recherche globale/rapide, mentions. | `threads/`, `annonces/`, `notifications/`, `matrix/core/recherche.py`, `docs/propositions/notifications_par_regime.md`, `dialogues_integres.md` |
| 10 | `taches` (5), `demandes`, `programme`, `postes`. | apps correspondantes |
| 11 | `assets` (31 modèles) : installations, matériel mobile, catalogue (reprise), documents, mesures, détection de dérive. | `assets/` |
| 12 | `maintenance` (6), `rondes` (4), anomalies (`logistics`), cycle du ticket correctif et confirmations explicites. | `maintenance/`, `rondes/`, `logistics/` |
| 13 | `logistics` (8) : stock, mouvements, périmètre, alertes de stock bas. | `logistics/` |
| 14 | `training` (11) : prérequis anti-cycle, référents, sessions, fusion de formations. | `training/` |
| 15 | `documentation` (3), `retex` (2). | apps correspondantes |
| 16 | Prêt à appareiller, `reports` (bilans, exports PDF/CSV/Excel). | `dashboard/`, `reports/` |
| 17 | Principes UX, design system (submodule `design/`), composants, mobile, saisie en grille, brouillons, styleguide. | `docs/UX.md`, `design/DESIGN_SYSTEM.md`, `matrix/static`, `matrix/templates` (194 gabarits) |
| 18–21 | Architecture, dictionnaire de données, API, flux inter-modules, produits en partie par script d'inventaire (§4). | code |
| 22 | Mécanismes de sécurité, dont verrou démo (L01), configuration de production (L05), archivage effectif (L02), suppression sûre (L03), décrits comme **mécanismes**, pas comme défauts. | branches L01/L05/L02/L03 |
| 23 | Variables d'environnement, Docker (Postgres/Redis), Celery worker/beat, VAPID, sauvegarde, `scripts/preparer_instance_test.py`, checklist avant production. | `README.md`, `settings.py`, `docker-compose.yml`, `docs/recette/05_*` |
| 24 | Tests (`manage.py test`), hooks `.claude/hooks`, contrôle des migrations, agents PO/Dev/Relecteur. | `CLAUDE.md`, `.claude/` |
| 25 | Fonctions cibles avec statut (non commencé / partiel) et source Notion datée (synchronisation bâtiment ↔ terre, chat contextuel avec la terre, bibliothèque validée, échéances…). | Notion |
| 26 | Chronologie et contenu de chaque lot. | git, comptes rendus (D3) |

---

## 4. Méthode de vérification (garantie de couverture)

**Principe : l'inventaire part du code, pas du texte.** Une matrice de couverture (annexe G) est générée, puis chaque ligne doit être « couverte » par un chapitre avant la relecture.

1. **Inventaire automatique en lecture seule**, par scripts rangés dans `docs/dossier-technique/outils/` (aucun import dans le code applicatif), exécutés sur l'état A puis l'état B :
   - applications, modèles, champs, relations, contraintes ;
   - routes (`urls.py` récursif) → vue → gabarit ;
   - tâches Celery (`CELERY_BEAT_SCHEDULE`) et commandes de gestion (9 sur A) ;
   - rôles, actions du registre `REGISTRE_ACTIONS`, modules du registre ;
   - signaux et relations génériques (`GenericForeignKey`) ;
   - migrations (154 fichiers sur A).
2. **Matrice de couverture** : une ligne par élément inventorié → chapitre → statut (rédigé / vérifié / relu). Clôture : **0 ligne non affectée**, 0 ligne « rédigé » sans renvoi source.
3. **Matrice des circuits métier**, liste fermée : échange de service, publication de liste, relève, feuille de service et rectificatif, ticket correctif, validation de maintenance, validation de formation, demande de pièce, annonce, archivage d'unité, désactivation de compte, proposer → valider → publier. Chaque circuit a : schéma, acteurs, états, droits requis, notifications émises, trace d'audit, tests existants.
4. **Triple source pour les affirmations critiques** (droits, périmètres, circuits) : code + test existant + décision PO. Tout écart va en annexe F, jamais d'arbitrage silencieux.
5. **Contrôle des références** : un script vérifie que chaque `chemin:ligne` cité existe sur l'état annoncé ; relancé à chaque relecture.
6. **Rejeu des parcours** : chaque parcours documenté est rejoué sur instance de démonstration (`seed_demo`, `scripts/preparer_instance_test.py`). Un parcours non rejoué reste ⚪.
7. **Marquage des états** : tout élément présent sur B et absent de A est marqué « non fusionné » (chapitre 26 et pied de section).

---

## 5. Structure documentaire et schémas

```
docs/dossier-technique/
├── 00_LISEZ-MOI.md              # mode d'emploi, états A/B, étiquettes
├── chapitres/01_… à 26_…        # un fichier .md par chapitre
├── annexes/A_… à H_…
├── schemas/
│   ├── src/*.mmd                # sources Mermaid
│   └── svg/*.svg                # exports committés (lisibles hors ligne)
├── outils/                      # scripts d'inventaire et de contrôle (hors app)
└── couverture/                  # sorties générées (matrice, index)
```
`DOSSIER_COMPLET.md` et le PDF sont **générés**, jamais édités.

**Schémas prévus (≈ 35)**
- *Architecture* : contexte (bâtiment / terre / aucun Internet), couches applicatives, dépendances entre apps, flux Celery/Redis, déploiement.
- *Données* : un diagramme entité-relation par domaine (org, accounts, quarts, assets, maintenance, logistique, formation, communication) et les relations génériques.
- *Autorisations* : hiérarchie des rôles, calcul de périmètre, matrice rôle × action.
- *Circuits (états/séquences)* : échange de service, publication de liste, feuille de service, relève A/B, ticket correctif, maintenance et confirmation critique, validation de formation, demande de pièce, annonce, archivage/suppression d'unité, proposer → valider → publier.
- *Parcours utilisateurs* : journée du marin, chef de section, chef de liste, acteur à terre, administrateur.
- *Interface* : plan de navigation par rôle, structure de l'accueil, captures mobile/bureau.

---

## 6. Sources disponibles et informations manquantes

### Disponibles
| Source | État | Fiabilité |
|---|---|---|
| Code `main` @ 6ef16ad (état A) | accessible | référence |
| Code `l03` @ 6d6d0be (état B, contient L01, L05, L02) | accessible | référence |
| `CLAUDE.md`, `README.md`, `docs/REFERENCE.md`, `docs/UX.md` | accessible | à confronter au code |
| `docs/propositions/*`, `docs/recette/*`, `docs/TESTS_MARINS.md` (état B uniquement) | accessible | décisions datées, à confronter |
| Notion : Cahier des charges (édition du 10/10), Organigramme et rôles (31/10), « 13 — Décisions Matrix et gouvernance », Cap V1.1, Audit métier × Guide du marin (31/10), Ordre de travail V1.1 (01/11) | accessible | ⚪ jusqu'à confrontation |
| `docs/archive/*` | historique | **jamais** source de vérité |
| Historique git (121 à 127 commits d'avance par lot) | accessible | haute |

### Manquantes ou à confirmer
1. **Dossier V1.2** : non trouvé (D2).
2. **Comptes rendus L01–L03** : non trouvés (D3). Le chiffre de 3 963 tests ne sera pas repris sans source.
3. **Une quarantaine d'autres branches distantes** (ux-*, securite-*, feuille-service-*, fiabilite-*…) : fusionnées dans A, dans B, ou dans aucun des deux ? À classer avant le chapitre 26.
4. **Décisions PO postérieures au 03/11** : à me transmettre ou à désigner.
5. **Synchronisation bâtiment ↔ terre, API d'interopérabilité (phase 7)** : statut réel à confirmer ; traité comme « Cible » par défaut.
6. **Exploitation réelle** (sauvegardes, supervision, rétention) : aucune source trouvée ; à fournir par l'administrateur.
7. **Charte graphique** : le submodule `design/` est vide dans cet environnement ; à initialiser pour documenter la charte.

---

## 7. Plan de rédaction et de relecture par étapes

| Étape | Contenu | Validation |
|---|---|---|
| **G0** | Ce cadrage | **PO** |
| **G1** | Outils d'inventaire, matrice de couverture initiale (états A et B), classement des branches | contrôle automatique |
| **G2** | Socle : ch. 1–5, 18, 19, 22 (organisation, comptes, droits, architecture, données, sécurité) | PO sur droits et circuits |
| **G3** | Vie quotidienne : ch. 6–9 | PO |
| **G4** | Opérationnel : ch. 10–13 | PO |
| **G5** | Connaissance et pilotage : ch. 14–16 | PO |
| **G6** | Interface, API, interactions, exploitation, qualité : ch. 17, 20, 21, 23, 24 | PO + administrateur |
| **G7** | Cible et historique : ch. 25–26, annexes A, B, F, H | PO |
| **G8** | Assemblage, relecture indépendante (agent `relecteur`, lecture par un marin et un administrateur), contrôle des références, PDF | PO |

Passage d'étape : (a) couverture à 100 % des lignes concernées, (b) références valides, (c) aucune fonction cible au présent, (d) relecture par quelqu'un qui n'a pas rédigé. Tout point métier incertain est posé au PO, jamais deviné. Les dettes constatées hors périmètre vont dans la tâche Notion « Dette — <app> », pas dans le dossier.

**Volume estimé** : 26 chapitres, environ 250 à 350 pages en PDF, ~35 schémas.

---

## 8. Après votre validation

1. Je tranche D1–D6 selon vos réponses.
2. Je commence G1 sur cette branche documentaire, sans modifier le code applicatif.
3. Aucune fusion dans `main`, aucune PR, ni L04 ni aucun autre lot.
