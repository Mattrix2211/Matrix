# Rapport de livraison — Ensemble 2 (« Vie du bord »)

> **Diffusion restreinte.** Date : 11/11/2026. Branche documentaire : `claude/fervent-wright-kl6gtx`. État du logiciel décrit : état B, `claude/l03-suppression-sure-v11` @ `6d6d0be`, **non fusionné dans `main`**.
> Aucun code applicatif modifié, aucune fusion dans `main`, aucune PR, aucun nouveau lot. Aucune décision du PO rouverte.

---

## 1. Demandes de revue de l'ensemble 1 : traitement

| Demande | Traitement |
|---|---|
| **Chapitre 5 : exemples concrets** (matelot, chef de section, chef de secteur, chef de service, COMAEQ, commandant, administrateur technique) | Ajout de la section **5.4 bis « Sept personnes, sept journées »** : un tableau **généré depuis le registre réel** (`outils/generer_exemples_droits.py`, `couverture/exemples_droits.md`) et un récit par profil (ce qu'il voit, fait, ne peut pas faire). Le tableau précise qu'« oui » signifie « le niveau suffit », non « peut le faire partout » |
| **Différence grade, fonction, rôle, périmètre, qualification** | §5.2 complété par un **exemple filé** (le maître Durand, personnage fictif : ses cinq notions et ce qui change s'il est muté) |
| **Écart avec une décision PO : ne pas le présenter comme règle** | §5.11 réécrit : tableau « Écarts d'implémentation » (règle validée / comportement actuel / lot), avec la mention explicite que le comportement actuel **n'est pas** la règle souhaitée ; renvoi au registre des écarts |
| **Séparation diffusable / restreint** | Appliquée aux chapitres 6 à 10 (fichier d'usage + fichier technique). **Aucune autorisation de diffusion n'est présumée** : la classification et les destinataires restent à valider séparément ; chaque fichier porte la mention de diffusion correspondante |
| **Les 11 écarts** : règle validée, comportement observé, sources, conséquences, lot | Nouveau **`restreint/ECARTS_DECISIONS_CODE.md`** : les quatre écarts désignés (administrateur technique, échanges de tours, publication des listes, commandant en second) en **partie A** ; les autres écarts de l'ensemble 1 en **A bis** ; ceux de l'ensemble 2 en **A ter** ; les **décisions absentes ou ambiguës** séparément en **partie B** ; les décisions validées non encore développées en **partie C** |

**Correction d'un écart du rapport de l'ensemble 1.** L'écart « QR codes » était erroné : `DEC-PRE-04` conserve l'existant (la route QR reste). Retiré du registre, du chapitre 18 et du rapport E1.

## 2. Chapitres rédigés

| Chapitre | Fichiers | Lignes |
|---|---|---|
| 6 Espace personnel, tableaux de bord, pilotage, rapports | `diffusable/06_accueil_pilotage.md`, `restreint/06_accueil_pilotage_technique.md` | 113 + 79 |
| 7 Calendrier central | `diffusable/07_calendrier.md`, `restreint/07_calendrier_technique.md` | 111 + 56 |
| 8 Quarts, services à quai, gardes, feuille de service, échanges, absences | `diffusable/08_quarts_services_feuille.md`, `restreint/08_quarts_services_feuille_technique.md` | 191 + 118 |
| 9 Communication : discussions, annonces, notifications, recherche | `diffusable/09_communication.md`, `restreint/09_communication_technique.md` | 128 + 62 |
| 10 Tâches, difficultés signalées, programme, postes | `diffusable/10_taches_demandes_programme_postes.md`, `restreint/10_taches_demandes_programme_postes_technique.md` | 148 + 80 |
| Registre des écarts | `restreint/ECARTS_DECISIONS_CODE.md` | — |

Chaque chapitre décrit, pour chaque module : **ce que voit et fait le marin**, puis **ce que font les responsables**, les circuits, les droits, les interactions, les cas particuliers, puis le **fonctionnement cible** et les **limites**.

## 3. Échanges de tours et listes de quarts : les deux états, sans confusion

Au chapitre 8 : §8.6 décrit le **fonctionnement actuel** 🟢 (schéma S16) ; §8.7 décrit le **fonctionnement cible** 🔵 `DEC-FDS-07/13/14` (schéma S17), avec un **tableau comparatif** ligne à ligne et un encadré d'écarts. Les deux circuits ont chacun leur schéma, leur section et leur étiquette.

## 4. Schémas ajoutés (9, soit 21 au total)

| N° | Schéma | Chapitre |
|---|---|---|
| S13 | Composition de la page « Aujourd'hui » | 6 |
| S14 | Neuf sources du calendrier | 7 |
| S15 | Cycle des listes de quarts et de services à quai | 8 |
| S16 | Échange de tours : circuit **actuel** | 8 |
| S17 | Échange de tours : circuit **cible** | 8 |
| S18 | Circuit de visa de la feuille de service | 8 |
| S19 | De l'événement à la notification | 9 |
| S20 | États d'une tâche : **actuel** | 10 |
| S21 | États d'une tâche : **cible** | 10 |

Rendus S16, S18, S15 et S21 regardés à l'image ; S18 corrigé (le rectificatif repasse en brouillon).

## 5. Couverture (matrice générée : `restreint/annexes/G_matrice_couverture.md`)

| Élément | Couvert à l'ensemble 2 |
|---|---|
| Modèles de `quarts` (22), `absences`, `taches`, `demandes`, `programme`, `postes`, `annonces`, `threads`, `notifications`, `calendar_app` | **Tous expliqués** dans un chapitre de domaine (`dashboard` : 2 modèles d'appareillage reportés au chapitre 16, ensemble 3) |
| Modèles expliqués au total | 70 sur 135 (contre 26 à l'ensemble 1) |
| Circuits métier de l'ensemble 2 | **14 circuits** rédigés : échange (actuel, cible), publication des listes, activation d'une liste à quai, feuille de service, absences, annonces, notifications et Web Push, recherche, tâches, difficultés signalées, programme, passation, bilans |
| Circuits restants | 7 (ensemble 3 : maintenance, ticket, pièces, fiche flotte, formation, RETEX, appareillage) |
| Paquets | `quarts`, `absences`, `taches`, `demandes`, `programme`, `postes`, `annonces`, `threads`, `notifications`, `calendar_app`, `dashboard`, `reports` décrits |

Notion lue avant rédaction : page « 06 — Service courant, BSC, feuille de service » (en entier) ; décisions `DEC-FDS`, `DEC-TAC`, `DEC-COL`, `DEC-CLO`, `DEC-BLQ`, `DEC-QUA`, `DEC-SUP`, `DEC-UX`, `DEC-PRE` du registre V1.2 ; propositions `mer_quai_*` et `droits_comaeq` de l'état B.

## 6. Contradictions et écarts (détail : `restreint/ECARTS_DECISIONS_CODE.md`)

**Écarts d'implémentation désignés** (A1 à A4) : administrateur technique (L06), échanges de tours (L10), publication des listes (L09), commandant en second (aucun lot identifié).

**Nouveaux écarts de l'ensemble 2**
- **A11** — « Mes tours de **services** » (`DEC-UX-08`) : l'accueil affiche « service » (visuel).
- **A12** — impression A4 et réimpression de la feuille de service (`DEC-FDS-04/06`, L27) : absentes.
- **A13** — trois priorités de tâche (`DEC-TAC-04/05`, L14) : deux seulement.
- **A14 (à confirmer)** — passation : « un chef de section ne consulte que sa section » : aucune borne trouvée dans `dashboard/passation.py`.

**Décisions absentes ou ambiguës, signalées sans réponse inventée** (partie B) : ce qui rend un **suppléant « officiel »** (B1) ; **responsabilités attribuées** du commandant en second (B2) ; les **échanges concernent-ils aussi les quarts à la mer** (B3) ; autorité de déclaration d'accostage et d'appareillage, absente du registre des 125 décisions (B4) ; désignation du chef de liste des quarts (B5) ; « fin de journée » (B6), ordre des grades (B7), conservation des notifications et journaux (B8).

**Constat favorable** : plusieurs décisions sont **conformes au code** — feuille de service rédigée par un rédacteur **désigné** (`DEC-FDS-11`), visa du COMAEQ titulaire avec secours du seul commandant de l'équipage (`DEC-FDS-02`), une feuille par équipage (`DEC-FDS-12`), qualifications non bloquantes pour les postes (`DEC-QUA-01`), activation d'une liste à quai par le seul chef de liste habilité, jamais le COMAEQ.

## 7. Éléments non vérifiés (⚪)

1. Parcours dans un navigateur réel (accueil, calendrier, échanges, feuille de service) ; FullCalendar ; Web Push sur appareil ; export PDF (bibliothèques natives absentes).
2. PostgreSQL (verrous des échanges et de l'activation ; unicités partielles).
3. Relations génériques (fils, notifications, demandes, liens de document) face à la suppression d'une unité.
4. A14 (passation) et B4 (accostage) : à confirmer par le PO ou en exécution.
5. Le détail de chaque indicateur de la Vue flotte et de la Vue COMANAV, de chaque catégorie de notification, de chaque écran de réglage.
6. `programme` et `postes` : très peu de tests propres (10 et 7).
7. Flux iCal : tâches et programme **non trouvés** ; usage réel non confronté.
8. Sources Notion non lues : « 03 — Formation » (avant le chapitre 14), « Recette UX V1.1 » (avant le chapitre 17).
9. Informations à fournir : ordre des grades, durées de conservation, fin de journée.

## 8. Contrôles documentaires

| Contrôle | Résultat |
|---|---|
| Références de code `fichier:ligne` vérifiées sur l'état B (fichier, ligne non vide, symbole annoncé sur la ligne) | **637 références, 0 erreur**, après correction de **46 références imprécises** détectées par le contrôle (rattachement implicite au mauvais fichier, symbole partagé entre deux références) |
| Identifiants `DEC-…` cités | contrôlés contre le registre V1.2 : 0 inconnu |
| Structure des chapitres (état B rappelé, « Pour qui », diffusion, étiquettes, Limites, Sources), liens, images, schémas exportés et référencés | **23 fichiers, 21 schémas, 0 erreur** |
| Chiffres cités conformes à l'inventaire généré | 0 erreur |
| Matrice de couverture régénérée | 14 circuits de l'ensemble 2 « rédigés », chacun prouvé par la présence d'un symbole du code dans les chapitres |
| Tests de l'état B rejoués (paquets de l'ensemble 2) | voir §8.1 |

### 8.1 Tests rejoués

Copie de l'état B (`6d6d0be`), SQLite, `manage.py test quarts absences taches demandes programme postes annonces threads notifications calendar_app dashboard reports --parallel 4` : **1 464 tests, OK, 10 ignorés** (réservés à PostgreSQL), 340 secondes. Les traces d'erreur affichées pendant l'exécution sont des pannes simulées par des tests. La suite complète (3 963 tests) n'a pas été rejouée.

## 9. Pour la revue

1. **Chapitre 8** : le lecteur distingue-t-il sans effort l'actuel du cible pour les échanges et les listes ?
2. **Chapitre 5, section 5.4 bis** : les sept profils sont-ils réalistes ? Faut-il d'autres fonctions (BSC, chef de liste) en exemples ?
3. **Partie B du registre des écarts** : B1 à B5 demandent une précision du PO avant que le chapitre cible puisse être figé.
4. **A14 et B4** : confirmer ou infirmer.

Je ne commence pas l'ensemble 3 (chapitres 11 à 16 : matériel, maintenance, logistique, formations, documentation et RETEX, appareillage) sans votre revue. Les pages Notion « 03 — Formation » sera lue avant le chapitre 14.
