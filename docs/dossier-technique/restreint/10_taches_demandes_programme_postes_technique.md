# Chapitre 10 (technique) — Tâches, demandes, programme, postes : mécanismes

> **Diffusion restreinte.** Complète `diffusable/10_taches_demandes_programme_postes.md` (à lire d'abord). **État décrit :** état B (`6d6d0be`), non fusionné dans `main`.
> **Pour qui :** développeurs, administrateurs. **Ce que vous y trouverez :** les modèles, les règles de droits exactes, la mécanique des transitions, les traces et notifications, les relances planifiées et les points d'entrée de `taches`, `demandes`, `programme` et `postes`.

---

## 10T.1 Les modèles

| Modèle | Rôle | Particularités |
|---|---|---|
| `Tache` (`taches/models.py:25`) | Tâche attribuée | Statuts `A_FAIRE`, `EN_COURS`, `BLOQUEE`, `TERMINEE` (`STATUTS_OUVERTS` : les trois premiers) ; priorités `NORMALE`, `URGENTE` ; `partagee` (vrai par défaut ; une tâche **personnelle** reste privée) ; `assigne` (un seul) ; `participants` (interlocuteurs du fil) ; `motif_blocage`, `compte_rendu`, `terminee_le` ; liens facultatifs `demande`, `annonce`, `lot` |
| `LotTaches` (`:12`) | Regroupement des tâches issues d'une même attribution à une unité | Suivi de l'avancement collectif |
| `ElementChecklistTache` (`:101`), `PieceJointeTache` (`:116`) | Checklist et pièces jointes | Pièces contrôlées par le validateur commun des fichiers ; livrées par le service protégé des médias |
| `ParametresTaches` (`:130`) | Réglages de relance communs à la flotte : jours entre deux relances (1), relancer l'assigné, le chef attributeur, les chefs si blocage, jours d'affichage des tâches terminées (30) | Un seul enregistrement |
| `Demande` (`demandes/models.py:15`) | Difficulté signalée sur un objet | États `OUVERT`, `EN_TRAITEMENT`, `EN_ATTENTE`, `RESOLU`, `CLOS` ; `declarant`, `responsable` (PROTECT, **jamais sans propriétaire**), `interlocuteurs` ; **relation générique** `objet` ; rattachement du déclarant copié à la création (périmètre des chefs) |
| `TypeProgramme` (`programme/models.py:13`), `EvenementProgramme` (`:27`), `DelegationProgramme` (`:55`) | Types propres au bâtiment ; événement ciblé ; délégation du droit de saisie | `annule` (jamais d'effacement), `taches` (M2M vers `Tache`), `equipage` |
| `Poste` (`postes/models.py:13`), `AffectationPoste` (`:36`) | Poste à pourvoir et ses titulaires | `effectif` requis, `formations` exigées ; unicité (poste, utilisateur) |

## 10T.2 Droits : fonctions exactes

### Tâches (`taches/services.py`)

| Question | Fonction | Règle |
|---|---|---|
| Lecture d'équipe | `peut_superviser` (`:37`) | `user_role_level` ≥ seuil `tache_attribution` (chef de section par défaut ; seuil de **portée flotte**) |
| Écriture : attribuer, réaffecter, lever un blocage | `peut_attribuer` (`:42`) | `niveau_ecriture` ≥ même seuil |
| Chef d'un marin | `est_chef_de` (`:51`) | `peut_attribuer` **et** marin dans le périmètre (et l'équipage) du chef |
| Gérer une tâche | `peut_gerer` (`:59`) | Tâche **partagée**, appelant ≠ assigné, `est_chef_de` |
| Consulter | `peut_consulter` (`:67`) | Acteur (assigné, créateur, participant) ou, pour une tâche **partagée**, superviseur du marin |
| Créer | `creer_tache` (`:231`) | Soi-même (tâche personnelle) ou `est_chef_de` ; l'assigné reçoit une notification « à action » |

### Autres modules

| Module | Fonction | Règle |
|---|---|---|
| Demandes | `peut_consulter` (`demandes/services.py:67`), `peut_piloter` (`:71`) | Acteur ou superviseur du périmètre du déclarant ; piloter : dossier ouvert **et** (responsable, ou `peut_attribuer` dans le périmètre) |
| Demandes | `creer_demande` (`:187`) | Refus pour l'équipage à terre ; l'appelant doit avoir accès à l'objet (`lien_objet`) ; responsable choisi parmi `responsables_possibles` (chefs du bâtiment) |
| Programme | `peut_saisir` (`programme/services.py:50`), `peut_deleguer` (`:57`), `peut_configurer_types` (`:61`) | Saisie : niveau ≥ seuil `programme_saisie` (**état-major** par défaut, comparaison au **grade**) ou délégation ; hors équipage à terre ; déléguer : état-major ; types : seuil `programme_types` (administrateur d'unité) |
| Postes | `peut_gerer` (`postes/services.py:20`), `peut_gerer_poste` (`:35`) | `niveau_ecriture` ≥ seuil `poste_gestion` (chef de service) ; cible dans le périmètre de saisie |
| Absences | `peut_gerer_absence_de` (`absences/services.py:53`), `valider_absence` (`:152`) | Soi-même, ou niveau d'écriture chef de section dans le périmètre direct (**sans cascade hiérarchique** : un chef de secteur ne couvre pas automatiquement les sections de son secteur dans ce module) |

## 10T.3 Mécanique des transitions

- **Démarrer** (`demarrer`, `taches/services.py:423`) : l'assigné seulement, depuis `A_FAIRE`. **Bloquer** (`signaler_blocage`, `taches/services.py:432`) : l'assigné, motif obligatoire, tâche ouverte ; notification aux acteurs puis aux chefs qui peuvent lever le blocage ; alerte « à action ». **Reprendre** (`reprendre`, `taches/services.py:474`) : un chef qui `peut_gerer`, tâche bloquée ; solde les alertes. **Rendre compte** (`rendre_compte`, `taches/services.py:487`) : l'assigné, compte rendu non vide, tâche ouverte → `TERMINEE`, `terminee_le` ; informe la demande liée (`action_terminee`).
- **Modifier** (`modifier_tache`, `taches/services.py:389`) : un chef du périmètre, tâche ouverte ; réaffectation, replanification, priorité ; chaque changement tracé dans le fil (message système) et `AuditLog`. **Attribuer à une unité** (`attribuer_a_unite`, `taches/services.py:277`) : une tâche par marin dans le périmètre et l'équipage du chef, liées par un `LotTaches`.
- **Partager** (`partager`, `taches/services.py:377`) : le marin partage sa tâche personnelle avec ses chefs ou la reprend en privé (interlocuteurs retirés).
- **Fil** : un `threads.Thread` générique rattaché à la tâche (`ajouter_commentaire`, `commentaires_de`) ; l'accès au fil suit `peut_consulter` ; les **mentions** `@identifiant` créent une attente de réponse jusqu'à ce que le marin cité réponde.
- **Demandes** : transitions déclarées dans `TRANSITIONS_RESPONSABLE` (`demandes/services.py:33`) et `TRANSITIONS_DECLARANT` (`demandes/services.py:38`) ; `changer_etat` (`demandes/services.py:254`) refuse tout changement non ouvert à l'appelant et exige une note pour « En attente d'information » ; `repondre` (`demandes/services.py:212`) fait repasser le dossier « Ouvert » quand le déclarant fournit l'information ; `creer_action` (`demandes/services.py:317`) crée une `Tache` liée ; `action_terminee` (`demandes/services.py:344`) informe le fil et le responsable.
- **Programme** : `creer_evenement` (`programme/services.py:85`), `annuler_evenement` (`programme/services.py:124`, indicateur `annule`), `evenements_visibles` (`programme/services.py:146`) : événements qui visent l'utilisateur (cibles résolues par `cibles_autorisees` du module annonces, mêmes règles de ciblage), ou saisis par lui ; l'état-major voit tout son bâtiment.
- **Postes** : `affecter` (`postes/services.py:78`) n'est **jamais bloqué** par une qualification manquante ; `tableau_effectifs` (`postes/services.py:95`) calcule titulaires, effectif pourvu et manques.

## 10T.4 Notifications, traces, relances

- Chaque transition appelle `_tracer` (journal `AuditLog`) et `_notifier`, qui crée des `Notification` à cible générique, éventuellement **« à action requise »** (le simple fait de lire ne la solde pas ; `traiter_actions` la solde quand la source est résolue).
- **Relances** : `relancer_echeances_depassees` (`taches/services.py:531`), appelée par la tâche `notify_taches_en_retard_daily` (07:00) ; relance les acteurs tant que la tâche n'est pas traitée, tous les `jours_entre_relances` jours ; destinataires : assigné, chef attributeur ; pour une tâche bloquée, les chefs qui peuvent lever le blocage (`_destinataires_relance`).
- Les tâches du jour et en retard alimentent l'accueil (chapitre 6) et le calendrier (chapitre 7).

## 10T.5 Routes

| Module | Routes (web) |
|---|---|
| Tâches | `/taches/`, `/taches/<id>/`, `/taches/<id>/action/`, `/taches/<id>/fichier/<pièce>/`, `/taches/commentaire/<id>/` |
| Demandes | `/demandes/`, `/demandes/nouvelle/`, `/demandes/<id>/`, `…/action/`, `…/commentaire/` |
| Programme | `/programme/`, `/programme/nouveau/`, `/programme/reglages/`, `/programme/<id>/`, `…/action/` |
| Postes | `/postes/`, `/postes/nouveau/`, `/postes/<id>/` |

Les tâches et les demandes n'ont pas d'API REST dédiée (inventaire généré, `couverture/etat_B/ROUTES.md`).

## 10T.6 Tests

`taches/tests/` (94 fonctions de test), `demandes/tests/` (41), `programme/tests/` (10), `postes/tests/` (7), `absences/tests/` (21).

## 10T.7 Limites et éléments non vérifiés

- ⚪ `programme` et `postes` sont peu couverts par des tests propres ; leur description repose sur le code.
- ⚪ `peut_superviser` compare au **grade**, `peut_attribuer` au **niveau d'écriture** : même schéma de deux comparaisons qu'au chapitre 5 (le commandant en second y est concerné).
- ⚪ Aucune API REST pour les tâches et les demandes : tout passe par les vues web (et HTMX).
- 🔵 L08, L14 à L18 non développés (voir `ECARTS_DECISIONS_CODE.md`, partie C).

---

**Sources (état B).** Références en ligne ; `couverture/etat_B/MODELES.md` ; `matrix/core/role_thresholds.py` (clés `tache_attribution`, `programme_saisie`, `programme_types`, `poste_gestion`).
