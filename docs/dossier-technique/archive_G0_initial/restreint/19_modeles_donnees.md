# Chapitre 19 — Modèles de données

> **Diffusion restreinte.** **État décrit :** état B (`6d6d0be`), non fusionné dans `main`.
> **Pour qui :** développeurs, administrateurs. **Ce que vous y trouverez :** comment l'information de Matrix est organisée en base, les conventions que le code respecte, la façon dont les liens entre données protègent ou non l'information, les identifiants, et les liens « génériques » qui rattachent une discussion ou une notification à n'importe quel objet. Le dictionnaire exhaustif (champs et relations de chaque modèle) est **généré** : `couverture/etat_B/MODELES.md`.

---

## 19.1 Comment lire ce chapitre

Une **table** de la base correspond à un **modèle** du code. Une **relation** relie deux tables (« ce marin appartient à cette section »). Le dictionnaire généré liste, pour chaque modèle, ses champs et ses relations avec leur règle de suppression. Ce chapitre explique ce que ce dictionnaire ne dit pas : les familles de modèles, les conventions et les règles d'intégrité.

**Mesures de l'état B** (générées, `couverture/etat_B/INVENTAIRE.md`) : **135 modèles**, 448 relations, 190 migrations.

## 19.2 Les familles de modèles

| Domaine | Modèles (principaux) | Ce qu'ils portent |
|---|---|---|
| **Personnes** (`accounts`, 10) | `UserProfile`, listes de référence (`GradeChoice`, `SpecialityChoice`, `ServiceFunctionChoice`, `FonctionQuartChoice`, `TypeAbsence`, `RoleAvailability`), `ResponsableSpecialite`, `AuditLog`, `InstanceDemo` | Identité métier du marin, listes configurables, journal d'audit, marqueur de base de démonstration |
| **Organisation** (`org`, 15) | `Ship`, `Service`, `Sector`, `Section`, `SectorConfig`, `RoleThresholdConfig`, `ModuleActivation`, `VersionConfiguration`, `ReleveEquipage`, `PeriodeEquipage`, `SynthesePassation`, `ReferenceBatiment`, `TypeBatiment`… | Structure, configuration par bâtiment, double équipage (chapitre 4) |
| **Quarts et services** (`quarts`, 22 ; `absences`, 1) | `ChefDeListe`, `Quart`, `ServiceGarde`, créneaux, versions de liste (`VersionQuart`, `VersionServiceGarde`), `EchangeService` et ses événements, `FeuilleService` et ses versions, alertes d'activation et d'organisation, `MouvementBatiment`, `Absence` | Planification, échanges, feuille de service (chapitre 8) |
| **Tâches et demandes** (`taches`, 5 ; `demandes`, 1 ; `programme`, 3 ; `postes`, 2 ; `calendar_app`, 1) | `Tache`, `LotTaches`, `ElementChecklistTache`, `Demande`, `EvenementProgramme`, `Poste`, `PersonalEvent` | Chapitres 7 et 10 |
| **Matériel** (`assets`, 29) | `Asset` (matériel mobile), `Installation` et ses relevés, `InstallationMaintenance`, `AssetType`, listes de contrôle, `Location`, `Deck`, `ArticleCatalogue`, `CategorieCatalogue`, `PropositionArticle`, fiches | Chapitre 11 |
| **Maintenance et logistique** (`maintenance`, 6 ; `logistics`, 8) | `MaintenancePlan`, `MaintenanceOccurrence`, `MaintenanceExecution`, `CompteRenduCorrectif` ; `CorrectiveTicket`, `Anomalie`, `PartRequest`, `StockPiece`, `MouvementStock` | Chapitres 12 et 13 |
| **Connaissance** (`training`, 11 ; `documentation`, 3 ; `retex`, 2) | `TrainingCourse`, `TrainingRecord`, `TrainingSession`, `ReferentFormation` ; `Document`, `VersionDocument` ; `Retex`, `DomaineRetex` | Chapitres 14 et 15 |
| **Communication** (`threads`, 3 ; `annonces`, 4 ; `notifications`, 2) | `Thread`, `Message`, `Attachment` ; `Annonce`, `VersionAnnonce`, `LectureAnnonce` ; `Notification`, `PushSubscription` | Chapitre 9 |
| **Appareillage** (`dashboard`, 2) | `SessionAppareillage`, `ItemAppareillage` | Chapitre 16 |
| **Transverse** (`core`, 1) | `Brouillon` | Brouillons de formulaires |
| **Rondes** (`rondes`, 4) | `RondeModele`, `PointControle`, `Ronde`, `ResultatPoint` | Module retiré fonctionnellement ; modèles et migrations conservés |

## 19.3 Les conventions du code

- **Horodatage systématique.** La plupart des modèles héritent de `TimeStampedModel` (`matrix/core/models.py:4`) : date de création et de dernière modification. Un second socle, `OwnedModel`, ajoute auteur et dernier modificateur.
- **Listes de choix en base, pas dans le code.** Grades, spécialités, fonctions, types d'absence, domaines de RETEX, types de programme, catégories du catalogue sont des **tables** modifiables par un utilisateur habilité (principe « configuration plutôt que code »).
- **Configuration en champs JSON.** Les réglages par bâtiment ou par secteur sont des champs JSON (seuils de rôle, préférences de secteur, widgets), avec repli sur une valeur par défaut tant que rien n'est réglé.
- **Statuts et journal de statut.** Les objets à cycle de vie portent un champ de statut et, pour les plus sensibles, un journal dédié : `OccurrenceStatusLog`, `TicketStatusLog`, `AnomalieStatutLog`, `EchangeServiceEvenement`.
- **Versions pour « proposer, valider, publier ».** `VersionQuart`, `VersionServiceGarde`, `VersionFeuilleService`, `VersionAnnonce`, `VersionDocument` conservent chaque version ; la version publiée reste active jusqu'à validation de la suivante.
- **Pas d'écrasement silencieux.** Les modifications importantes écrivent une ligne dans `AuditLog` (acteur, action, cible, détails horodatés) ; un compte rendu corrigé conserve la saisie d'origine (`ModificationCompteRendu`).

## 19.4 L'intégrité : ce qui protège les données

Chaque relation dit ce qui doit arriver quand l'élément visé disparaît. Les trois règles employées, avec leur fréquence dans l'état B :

| Règle | Signification | Nombre de relations |
|---|---|---|
| **PROTECT** | La suppression de l'élément visé est **refusée** tant qu'il est référencé | 115 |
| **SET_NULL** | Le lien est **vidé** (la relation devient facultative), l'enregistrement reste | 216 |
| **CASCADE** | L'enregistrement qui référence est **supprimé avec** l'élément visé | 102 |
| Plusieurs-à-plusieurs | Table de liaison | 15 |

Lecture : par défaut, **rien n'est supprimé en cascade sauf les éléments qui n'ont pas de sens seuls** (une section sans secteur, une ligne de checklist sans sa liste, un message sans sa discussion). Les relations vers les **unités** sont en PROTECT depuis le lot L03 (92 relations, chapitre 4) : un marin, un matériel, une liste ne disparaît pas parce qu'on supprime une unité.

**À connaître.** Une relation **générique** (§19.6) n'est pas vue par la base comme une relation : supprimer l'objet visé ne supprime pas, et ne refuse pas non plus, ce qui le désigne.

## 19.5 Les identifiants

- **Par défaut**, la clé primaire est un entier auto-incrémenté (`BigAutoField`). C'est le cas du compte, du profil, des unités.
- **12 modèles portent un champ UUID** (pas devinable, stable d'une base à l'autre), le plus souvent comme clé primaire : `Asset`, `Installation`, `DocumentInstallation`, `ChecklistItemTemplate`, `CategorieCatalogue`, `ArticleCatalogue`, `PropositionArticle`, `CompteRenduCorrectif`, `CorrectiveTicket`, `RubriqueEnTeteFeuilleService`, `FonctionFeuilleService` ; `VersionConfiguration` n'en porte qu'un comme jeton. ⚪ Le détail « clé primaire ou simple champ » par modèle est à préciser dans l'annexe D.
- **NNO** (voir annexe A) : champ texte porté par `Asset`, `InstallationPart`, `ArticleCatalogue` et `PropositionArticle`.
- **Conséquence.** Les identifiants techniques stables qui permettraient un futur interfaçage avec les outils du SSF existent côté **matériel et catalogue**, pas côté personnes, unités ou tâches. 🔵 Les règles du projet demandent de « garder des identifiants stables (UUID, NNO) pour de futures API » ; leur extension à d'autres objets n'est pas décidée dans ce dossier.

## 19.6 Les relations génériques

Six modèles désignent un objet par un couple « type d'objet + identifiant », sans clé étrangère classique. Cela permet à une discussion de s'attacher à n'importe quoi (principe « le dialogue est une fonction métier »), mais le lien n'est pas protégé par la base.

| Modèle | Champ | Sert à |
|---|---|---|
| `threads.Thread` | `content_object` | Attacher une discussion à une tâche, un équipement, un ticket, une formation… |
| `notifications.Notification` | `target` (facultatif) | Désigner l'objet dont parle une notification |
| `demandes.Demande` | `objet` | « Difficulté signalée » sur un objet |
| `documentation.LienDocument` | `objet` | Lier un document à un objet |
| `retex.Retex` | `source` (facultatif) | Origine d'un retour d'expérience |
| `dashboard.ItemAppareillage` | `objet_source` (facultatif) | Origine d'un point de contrôle d'appareillage |

⚪ **Non vérifié.** Ces six liens n'ont pas été contrôlés vis-à-vis de la suppression ou de l'archivage d'une **unité** lors du lot L03 (compte rendu, risque résiduel 3) : un objet désignant une unité par relation générique ne serait pas compté par le contrôle de suppression. À vérifier avant une mise en production (chapitre 23).

## 19.7 Les migrations

Une **migration** est l'historique des changements de structure de la base ; Matrix en compte **190** à l'état B. Répartition : `assets` 46, `quarts` 26, `accounts` 23, `org` 18, `training` 16, `logistics` 15, `maintenance` 9, `taches` 8, `notifications` 5, les autres paquets entre 1 et 3.

Apportées par les lots non fusionnés :

| Lot | Migration | Nature |
|---|---|---|
| L01 | `accounts` 0021 puis 0022 | Table `InstanceDemo` (marqueur de base de démonstration), puis champ `identifiant` ; additives |
| L03 | 14 migrations nommées `…_protection_suppression_unites` : `org` 0018, `accounts` 0023, `assets` 0044, `quarts` 0026, `training` 0016, `logistics` 0015 et huit autres paquets | Passage de relations vers les unités en `PROTECT` ; **sans SQL** (règle appliquée par Django) |

Règle de projet : une migration qui ajoute un champ doit lui donner une valeur par défaut (contrôle par hook) ; les migrations doivent être appliquées avant tout commit (second hook) ; `makemigrations --check` ne signale rien sur l'état B.

## 19.8 Le vocabulaire cible de Notion, et ce qui existe

La page Notion « 11 — Modèle de données cible » décrit des objets (Mission, Capability, Crew, Post, Person, Qualification, WorkOrder, Fault, Waiver…) qui **ne correspondent pas tous** au code. Correspondances observées : `Ship`, `Service`, `Sector`, `Section` (existent), `Person` ≈ `UserProfile`, `Post` ≈ `Poste`, `TrainingCourse`, `TrainingSession`, `MaintenancePlan` (existent). Pas de modèle pour **mission, capacité, exigence de mission, contrôle de conformité, dérogation** ni « profondeur de relève ». Ce vocabulaire est une **cible** 🔵, pas une description.

## 19.9 Limites et éléments non vérifiés

- ⚪ Les nombres sont ceux de l'état B ; ils changeront avec les lots suivants. Les chiffres de ce chapitre sont tous issus de l'inventaire généré et se régénèrent avec `outils/inventaire.py`.
- ⚪ Certains modèles secondaires (`InstallationBigrameChoice`, `ChefResponsableSpecialite`, `ParametresPassation`…) ne sont décrits qu'au dictionnaire ; leur usage fonctionnel est traité dans les chapitres de domaine.
- ⚪ PostgreSQL : l'état B contient des contraintes d'unicité partielle (relève, période d'équipage) dont la référence de comportement est PostgreSQL ; non exécuté ici.
- ⚪ La conservation des journaux, des notifications lues et des estimations n'est pas définie (information manquante IM-10 du dossier V1.2).

---

**Sources (état B).** `couverture/etat_B/MODELES.md` et `INVENTAIRE.md` (générés par `outils/inventaire.py` en chargeant le code de l'état B), `matrix/core/models.py:4`, `org/models.py`, `accounts/models.py`, `assets/models.py:259,496,736,798` (NNO), `org/structure_services.py`. Compte rendu L03 (`Q_LOT_L03_COMPTE_RENDU.md` §2 et §5.3) ; Notion « 11 — Modèle de données cible Matrix : vue système ».
