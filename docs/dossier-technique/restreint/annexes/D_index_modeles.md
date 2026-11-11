# Annexe D — Index des modèles (généré, état B)

> Diffusion restreinte. Généré par `outils/generer_annexes_e4.py` depuis l'inventaire de l'état B (`6d6d0be`, non fusionné dans `main`). Ne pas éditer à la main.

**135 modèles**. Colonnes : paquet, modèle, nombre de champs, clé primaire (UUID ou entier ; un modèle à clé entière peut porter par ailleurs un champ UUID, voir le dictionnaire), relation générique (`GenericForeignKey`), chapitres où le modèle est expliqué. Dictionnaire des champs : `couverture/etat_B/MODELES.md`.

| Paquet | Modèle | Champs | Clé primaire | Relation générique | Chapitres |
|---|---|---|---|---|---|
| `absences` | `Absence` | 8 | entier | non | 7, 8, 13 |
| `accounts` | `AuditLog` | 5 | entier | non | 4, 5, 8, 10, 13, 16, 22, 23, 24 |
| `accounts` | `FonctionQuartChoice` | 3 | entier | non | 5 |
| `accounts` | `GradeChoice` | 3 | entier | non | 5 |
| `accounts` | `InstanceDemo` | 4 | entier | non | 22 |
| `accounts` | `ResponsableSpecialite` | 3 | entier | non | 2, 5, 6 |
| `accounts` | `RoleAvailability` | 3 | entier | non | 5 |
| `accounts` | `ServiceFunctionChoice` | 3 | entier | non | 5 |
| `accounts` | `SpecialityChoice` | 3 | entier | non | 5 |
| `accounts` | `TypeAbsence` | 3 | entier | non | 5 |
| `accounts` | `UserProfile` | 17 | entier | non | 4, 5 |
| `annonces` | `Annonce` | 13 | entier | non | 9 |
| `annonces` | `LectureAnnonce` | 5 | entier | non | 9 |
| `annonces` | `ParametresAnnonces` | 4 | entier | non | 9 |
| `annonces` | `VersionAnnonce` | 7 | entier | non | 9 |
| `assets` | `ArticleCatalogue` | 11 | UUID | non | 11 |
| `assets` | `Asset` | 19 | UUID | non | 11 |
| `assets` | `AssetChecklistOverride` | 5 | entier | non | 11 |
| `assets` | `AssetDocument` | 5 | entier | non | 11 |
| `assets` | `AssetFolder` | 5 | entier | non | 11 |
| `assets` | `AssetType` | 5 | entier | non | 11 |
| `assets` | `CategorieCatalogue` | 8 | UUID | non | 11 |
| `assets` | `ChecklistItemTemplate` | 14 | entier | non | 11 |
| `assets` | `ChecklistTemplate` | 18 | entier | non | 11 |
| `assets` | `ChefResponsableSpecialite` | 3 | entier | non | 11 |
| `assets` | `Deck` | 6 | entier | non | 11 |
| `assets` | `DocumentInstallation` | 7 | UUID | non | 11 |
| `assets` | `EvenementProposition` | 6 | entier | non | 11 |
| `assets` | `FicheEtape` | 6 | entier | non | 11 |
| `assets` | `FichePreparation` | 7 | entier | non | 11 |
| `assets` | `Installation` | 15 | UUID | non | 11, 12 |
| `assets` | `InstallationBigrameChoice` | 3 | entier | non | 11 |
| `assets` | `InstallationEvent` | 7 | entier | non | 11 |
| `assets` | `InstallationEventAttachment` | 5 | entier | non | 11 |
| `assets` | `InstallationExtraField` | 6 | entier | non | 11 |
| `assets` | `InstallationHourReading` | 6 | entier | non | 11 |
| `assets` | `InstallationIsolationReading` | 6 | entier | non | 11 |
| `assets` | `InstallationMaintenance` | 20 | entier | non | 11 |
| `assets` | `InstallationMaintenanceAttachment` | 5 | entier | non | 11 |
| `assets` | `InstallationPart` | 8 | entier | non | 11 |
| `assets` | `InstallationVibrationReading` | 6 | entier | non | 11 |
| `assets` | `Location` | 4 | entier | non | 11 |
| `assets` | `PropositionArticle` | 14 | UUID | non | 11 |
| `assets` | `SignalementFiche` | 5 | entier | non | 11 |
| `calendar_app` | `PersonalEvent` | 7 | entier | non | 7 |
| `core` | `Brouillon` | 7 | entier | non | 5, 8, 15, 18 |
| `dashboard` | `ItemAppareillage` | 7 | entier | oui | 16 |
| `dashboard` | `SessionAppareillage` | 6 | entier | non | 16 |
| `demandes` | `Demande` | 10 | entier | oui | 8, 10, 12, 13, 15, 21 |
| `documentation` | `Document` | 10 | entier | non | 11, 15, 26 |
| `documentation` | `LienDocument` | 4 | entier | oui | 15 |
| `documentation` | `VersionDocument` | 11 | entier | non | 15 |
| `logistics` | `Anomalie` | 9 | entier | non | 12, 21 |
| `logistics` | `AnomalieStatutLog` | 6 | entier | non | 12 |
| `logistics` | `CorrectiveTicket` | 12 | UUID | non | 12 |
| `logistics` | `MouvementStock` | 7 | entier | non | 13 |
| `logistics` | `PartLineItem` | 13 | entier | non | 12, 13 |
| `logistics` | `PartRequest` | 5 | entier | non | 12, 13 |
| `logistics` | `StockPiece` | 12 | entier | non | 13 |
| `logistics` | `TicketStatusLog` | 6 | entier | non | 12 |
| `maintenance` | `CompteRenduCorrectif` | 16 | entier | non | 12 |
| `maintenance` | `MaintenanceExecution` | 11 | entier | non | 12 |
| `maintenance` | `MaintenanceOccurrence` | 6 | entier | non | 12 |
| `maintenance` | `MaintenancePlan` | 9 | entier | non | 12 |
| `maintenance` | `ModificationCompteRendu` | 5 | entier | non | 12 |
| `maintenance` | `OccurrenceStatusLog` | 6 | entier | non | 12 |
| `notifications` | `Notification` | 12 | entier | oui | 8, 9, 10, 17, 21, 24 |
| `notifications` | `PushSubscription` | 7 | entier | non | 9 |
| `org` | `ModuleActivation` | 5 | entier | non | 4 |
| `org` | `ParametresPassation` | 4 | entier | non | 4, 6 |
| `org` | `PeriodeEquipage` | 7 | entier | non | 4 |
| `org` | `ReferenceBatiment` | 16 | entier | non | 4 |
| `org` | `ReleveEquipage` | 10 | entier | non | 4, 6 |
| `org` | `ResponsableClasseNavire` | 4 | entier | non | 2, 4, 5, 6 |
| `org` | `RoleThresholdConfig` | 4 | entier | non | 4, 5 |
| `org` | `Section` | 5 | entier | non | 4, 16 |
| `org` | `Sector` | 6 | entier | non | 4 |
| `org` | `SectorConfig` | 7 | entier | non | 4 |
| `org` | `Service` | 6 | entier | non | 1, 4, 8, 15, 22 |
| `org` | `Ship` | 13 | entier | non | 4, 14 |
| `org` | `SynthesePassation` | 6 | entier | non | 4, 6 |
| `org` | `TypeBatiment` | 8 | entier | non | 4 |
| `org` | `VersionConfiguration` | 4 | entier | non | 4, 5 |
| `postes` | `AffectationPoste` | 3 | entier | non | 10 |
| `postes` | `Poste` | 7 | entier | non | 8, 10, 11, 17, 23 |
| `programme` | `DelegationProgramme` | 3 | entier | non | 10 |
| `programme` | `EvenementProgramme` | 10 | entier | non | 10 |
| `programme` | `TypeProgramme` | 6 | entier | non | 10 |
| `quarts` | `AlerteAccostage` | 6 | entier | non | 8 |
| `quarts` | `AlerteActivation` | 8 | entier | non | 8 |
| `quarts` | `ChefDeListe` | 5 | entier | non | 8 |
| `quarts` | `ConfigurationActivation` | 8 | entier | non | 8 |
| `quarts` | `CreneauQuart` | 8 | entier | non | 8 |
| `quarts` | `CreneauServiceGarde` | 7 | entier | non | 6, 8 |
| `quarts` | `EchangeService` | 12 | entier | non | 8 |
| `quarts` | `EchangeServiceEvenement` | 5 | entier | non | 8 |
| `quarts` | `FeuilleService` | 16 | entier | non | 8 |
| `quarts` | `FonctionFeuilleService` | 8 | entier | non | 8 |
| `quarts` | `ModificationOrganisationAlerte` | 8 | entier | non | 8 |
| `quarts` | `MouvementBatiment` | 12 | entier | non | 8 |
| `quarts` | `PosteAlerte` | 6 | entier | non | 8 |
| `quarts` | `Quart` | 11 | entier | non | 7, 8 |
| `quarts` | `RedacteurFeuilleService` | 4 | entier | non | 8 |
| `quarts` | `RemplacementChefDeListe` | 11 | entier | non | 8 |
| `quarts` | `RubriqueEnTeteFeuilleService` | 9 | entier | non | 8 |
| `quarts` | `ScenarioAlerte` | 8 | entier | non | 8 |
| `quarts` | `ServiceGarde` | 21 | entier | non | 8 |
| `quarts` | `VersionFeuilleService` | 7 | entier | non | 8 |
| `quarts` | `VersionQuart` | 6 | entier | non | 8 |
| `quarts` | `VersionServiceGarde` | 6 | entier | non | 8 |
| `retex` | `DomaineRetex` | 7 | entier | non | 15 |
| `retex` | `Retex` | 16 | entier | oui | 15 |
| `rondes` | `PointControle` | 9 | entier | non | 12 |
| `rondes` | `ResultatPoint` | 14 | entier | non | 12 |
| `rondes` | `Ronde` | 9 | entier | non | 12 |
| `rondes` | `RondeModele` | 8 | entier | non | 12 |
| `taches` | `ElementChecklistTache` | 6 | entier | non | 10 |
| `taches` | `LotTaches` | 5 | entier | non | 10 |
| `taches` | `ParametresTaches` | 8 | entier | non | 10 |
| `taches` | `PieceJointeTache` | 5 | entier | non | 10 |
| `taches` | `Tache` | 12 | entier | non | 10 |
| `threads` | `Attachment` | 5 | entier | non | 9 |
| `threads` | `Message` | 5 | entier | non | 9, 21 |
| `threads` | `Thread` | 4 | entier | oui | 9, 10 |
| `training` | `CandidatureFormation` | 6 | entier | non | 14 |
| `training` | `DemandePlace` | 7 | entier | non | 14 |
| `training` | `PersonnelBRH` | 3 | entier | non | 14 |
| `training` | `PlaceAffectee` | 3 | entier | non | 14 |
| `training` | `ReferentFormation` | 3 | entier | non | 14 |
| `training` | `ReferentFormationNavire` | 3 | entier | non | 14 |
| `training` | `TrainingCourse` | 10 | entier | non | 14 |
| `training` | `TrainingRecord` | 6 | entier | non | 14 |
| `training` | `TrainingRequirement` | 5 | entier | non | 14 |
| `training` | `TrainingSession` | 7 | entier | non | 14 |
| `training` | `TrainingWaitlistEntry` | 3 | entier | non | 14 |
