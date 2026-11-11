# Dictionnaire des modèles de l'état B (généré)

## `absences`

### Absence
- Champs : `id`, `created_at`, `updated_at`, `date_debut`, `date_fin`, `statut`, `motif`, `validee_le`
- FK `created_by` → `auth.User`, `SET_NULL` (facultatif)
- FK `updated_by` → `auth.User`, `SET_NULL` (facultatif)
- FK `marin` → `auth.User`, `CASCADE`
- FK `type_absence` → `accounts.TypeAbsence`, `PROTECT`
- FK `validee_par` → `auth.User`, `SET_NULL` (facultatif)

## `accounts`

### AuditLog
- Champs : `id`, `created_at`, `updated_at`, `action`, `details`
- FK `actor` → `auth.User`, `SET_NULL` (facultatif)
- FK `target_user` → `auth.User`, `SET_NULL` (facultatif)

### FonctionQuartChoice
- Champs : `id`, `name`, `active`

### GradeChoice
- Champs : `id`, `name`, `active`

### InstanceDemo
- Champs : `id`, `cree_le`, `commande`, `identifiant`

### ResponsableSpecialite
- Champs : `id`, `created_at`, `updated_at`
- FK `specialite` → `accounts.SpecialityChoice`, `CASCADE`
- FK `user` → `auth.User`, `CASCADE`

### RoleAvailability
- Champs : `id`, `code`, `active`

### ServiceFunctionChoice
- Champs : `id`, `name`, `active`

### SpecialityChoice
- Champs : `id`, `name`, `active`

### TypeAbsence
- Champs : `id`, `name`, `active`

### UserProfile
- Champs : `id`, `created_at`, `updated_at`, `role`, `grade`, `specialite`, `fonction_service`, `matricule`, `equipage`, `fonction_coma`, `date_naissance`, `notification_time`, `notification_time_soir`, `theme`, `barre_laterale_repliee`, `preferences_interface`, `mot_de_passe_provisoire`
- 1-1 `user` → `auth.User`, `CASCADE`
- FK `ship` → `org.Ship`, `PROTECT` (facultatif)
- FK `service` → `org.Service`, `PROTECT` (facultatif)
- FK `sector` → `org.Sector`, `PROTECT` (facultatif)
- FK `section` → `org.Section`, `PROTECT` (facultatif)
- N-N `allowed_sectors` → `org.Sector`

## `annonces`

### Annonce
- Champs : `id`, `created_at`, `updated_at`, `titre`, `corps`, `niveau`, `accuse_requis`, `date_effet`, `date_fin`, `equipage`, `version`, `archivee`, `diffusee_le`
- FK `created_by` → `auth.User`, `SET_NULL` (facultatif)
- FK `updated_by` → `auth.User`, `SET_NULL` (facultatif)
- FK `ship` → `org.Ship`, `PROTECT`
- FK `service` → `org.Service`, `PROTECT` (facultatif)
- FK `sector` → `org.Sector`, `PROTECT` (facultatif)
- FK `section` → `org.Section`, `PROTECT` (facultatif)
- FK `auteur` → `auth.User`, `SET_NULL` (facultatif)

### LectureAnnonce
- Champs : `id`, `created_at`, `updated_at`, `accuse`, `version_lue`
- FK `annonce` → `annonces.Annonce`, `CASCADE`
- FK `user` → `auth.User`, `CASCADE`

### ParametresAnnonces
- Champs : `id`, `created_at`, `updated_at`, `jours_rappel_accuse`

### VersionAnnonce
- Champs : `id`, `created_at`, `updated_at`, `numero`, `titre`, `corps`, `niveau`
- FK `annonce` → `annonces.Annonce`, `CASCADE`
- FK `auteur` → `auth.User`, `SET_NULL` (facultatif)

## `assets`

### ArticleCatalogue
- Champs : `created_at`, `updated_at`, `id`, `designation`, `marque`, `reference`, `nno`, `photo`, `caracteristiques`, `duree_vie_mois`, `actif`
- FK `created_by` → `auth.User`, `SET_NULL` (facultatif)
- FK `updated_by` → `auth.User`, `SET_NULL` (facultatif)
- FK `categorie` → `assets.CategorieCatalogue`, `PROTECT`

### Asset
- Champs : `created_at`, `updated_at`, `id`, `serial_number`, `internal_id`, `designation`, `nno`, `reference`, `marque`, `gisement`, `local`, `photo`, `status`, `criticality`, `date_mise_en_service`, `date_dernier_controle`, `date_peremption`, `position_x`, `position_y`
- FK `created_by` → `auth.User`, `SET_NULL` (facultatif)
- FK `updated_by` → `auth.User`, `SET_NULL` (facultatif)
- FK `asset_type` → `assets.AssetType`, `PROTECT`
- FK `location` → `assets.Location`, `SET_NULL` (facultatif)
- FK `ship` → `org.Ship`, `PROTECT`
- FK `service` → `org.Service`, `PROTECT`
- FK `sector` → `org.Sector`, `PROTECT`
- FK `section` → `org.Section`, `PROTECT` (facultatif)
- FK `folder` → `assets.AssetFolder`, `SET_NULL` (facultatif)
- FK `article_catalogue` → `assets.ArticleCatalogue`, `SET_NULL` (facultatif)
- FK `parent` → `assets.Asset`, `SET_NULL` (facultatif)
- FK `plan_deck` → `assets.Deck`, `SET_NULL` (facultatif)

### AssetChecklistOverride
- Champs : `id`, `created_at`, `updated_at`, `extra_items`, `overrides`
- FK `asset` → `assets.Asset`, `CASCADE`
- FK `template` → `assets.ChecklistTemplate`, `CASCADE`

### AssetDocument
- Champs : `id`, `created_at`, `updated_at`, `file`, `name`
- FK `created_by` → `auth.User`, `SET_NULL` (facultatif)
- FK `updated_by` → `auth.User`, `SET_NULL` (facultatif)
- FK `asset` → `assets.Asset`, `CASCADE`

### AssetFolder
- Champs : `id`, `created_at`, `updated_at`, `name`, `photo`
- FK `created_by` → `auth.User`, `SET_NULL` (facultatif)
- FK `updated_by` → `auth.User`, `SET_NULL` (facultatif)
- FK `parent` → `assets.AssetFolder`, `CASCADE` (facultatif)

### AssetType
- Champs : `id`, `created_at`, `updated_at`, `name`, `category`
- FK `sector` → `org.Sector`, `PROTECT`

### CategorieCatalogue
- Champs : `created_at`, `updated_at`, `id`, `nom`, `ordre`, `icone`, `photo`, `actif`
- FK `created_by` → `auth.User`, `SET_NULL` (facultatif)
- FK `updated_by` → `auth.User`, `SET_NULL` (facultatif)
- FK `parent` → `assets.CategorieCatalogue`, `PROTECT` (facultatif)
- FK `specialite` → `accounts.SpecialityChoice`, `PROTECT`

### ChecklistItemTemplate
- Champs : `id`, `created_at`, `updated_at`, `cle`, `label`, `field_type`, `required`, `requires_photo`, `unit`, `releve`, `valeur_min`, `valeur_max`, `choices`, `order`
- FK `template` → `assets.ChecklistTemplate`, `CASCADE`

### ChecklistTemplate
- Champs : `id`, `created_at`, `updated_at`, `name`, `numero`, `etat`, `description`, `resume_modifications`, `mode_declenchement`, `intervalle`, `unite_intervalle`, `seuil_heures`, `duree_estimee_min`, `nb_personnes`, `role_redacteur`, `equipage`, `motif_refus`, `valide_le`
- FK `sector` → `org.Sector`, `PROTECT` (facultatif)
- FK `asset_type` → `assets.AssetType`, `SET_NULL` (facultatif)
- FK `fiche` → `assets.InstallationMaintenance`, `CASCADE` (facultatif)
- FK `qualification` → `training.TrainingCourse`, `SET_NULL` (facultatif)
- FK `redacteur` → `auth.User`, `SET_NULL` (facultatif)
- FK `ship_origine` → `org.Ship`, `PROTECT` (facultatif)
- FK `service_origine` → `org.Service`, `PROTECT` (facultatif)
- FK `secteur_origine` → `org.Sector`, `PROTECT` (facultatif)
- FK `verificateur` → `auth.User`, `SET_NULL` (facultatif)

### ChefResponsableSpecialite
- Champs : `id`, `created_at`, `updated_at`
- 1-1 `responsable` → `accounts.ResponsableSpecialite`, `CASCADE`
- FK `chef` → `auth.User`, `CASCADE`

### Deck
- Champs : `id`, `created_at`, `updated_at`, `name`, `order`, `image`
- FK `ship` → `org.Ship`, `PROTECT`

### DocumentInstallation
- Champs : `created_at`, `updated_at`, `id`, `titre`, `type_document`, `fichier`, `notes`
- FK `created_by` → `auth.User`, `SET_NULL` (facultatif)
- FK `updated_by` → `auth.User`, `SET_NULL` (facultatif)
- FK `installation` → `assets.Installation`, `CASCADE`

### EvenementProposition
- Champs : `id`, `created_at`, `updated_at`, `action`, `etape`, `motif`
- FK `proposition` → `assets.PropositionArticle`, `CASCADE` (facultatif)
- FK `version` → `assets.ChecklistTemplate`, `CASCADE` (facultatif)
- FK `user` → `auth.User`, `SET_NULL` (facultatif)

### FicheEtape
- Champs : `id`, `created_at`, `updated_at`, `texte`, `attention`, `ordre`
- FK `version` → `assets.ChecklistTemplate`, `CASCADE`

### FichePreparation
- Champs : `id`, `created_at`, `updated_at`, `type`, `libelle`, `quantite`, `ordre`
- FK `version` → `assets.ChecklistTemplate`, `CASCADE`
- FK `piece` → `logistics.StockPiece`, `SET_NULL` (facultatif)

### Installation
- Champs : `created_at`, `updated_at`, `id`, `designation`, `reference`, `marque`, `gisement`, `local`, `photo`, `vib_days_a`, `vib_days_b`, `vib_days_c`, `iso_periodicity`, `isolation_seuil_ohms`, `critique`
- FK `created_by` → `auth.User`, `SET_NULL` (facultatif)
- FK `updated_by` → `auth.User`, `SET_NULL` (facultatif)
- FK `bigrame` → `assets.InstallationBigrameChoice`, `SET_NULL` (facultatif)
- FK `location` → `assets.Location`, `SET_NULL` (facultatif)
- FK `ship` → `org.Ship`, `PROTECT`
- FK `service` → `org.Service`, `PROTECT`
- FK `sector` → `org.Sector`, `PROTECT`
- FK `section` → `org.Section`, `PROTECT` (facultatif)
- FK `parent` → `assets.Installation`, `SET_NULL` (facultatif)

### InstallationBigrameChoice
- Champs : `id`, `name`, `active`

### InstallationEvent
- Champs : `id`, `created_at`, `updated_at`, `type_evenement`, `date`, `label`, `notes`
- FK `created_by` → `auth.User`, `SET_NULL` (facultatif)
- FK `updated_by` → `auth.User`, `SET_NULL` (facultatif)
- FK `installation` → `assets.Installation`, `CASCADE`

### InstallationEventAttachment
- Champs : `id`, `created_at`, `updated_at`, `file`, `name`
- FK `created_by` → `auth.User`, `SET_NULL` (facultatif)
- FK `updated_by` → `auth.User`, `SET_NULL` (facultatif)
- FK `event` → `assets.InstallationEvent`, `CASCADE`

### InstallationExtraField
- Champs : `id`, `created_at`, `updated_at`, `label`, `value`, `order`
- FK `created_by` → `auth.User`, `SET_NULL` (facultatif)
- FK `updated_by` → `auth.User`, `SET_NULL` (facultatif)
- FK `installation` → `assets.Installation`, `CASCADE`

### InstallationHourReading
- Champs : `id`, `created_at`, `updated_at`, `date`, `hours`, `is_visit`
- FK `created_by` → `auth.User`, `SET_NULL` (facultatif)
- FK `updated_by` → `auth.User`, `SET_NULL` (facultatif)
- FK `installation` → `assets.Installation`, `CASCADE`
- FK `execution` → `maintenance.MaintenanceExecution`, `SET_NULL` (facultatif)

### InstallationIsolationReading
- Champs : `id`, `created_at`, `updated_at`, `date`, `ohms`, `note`
- FK `created_by` → `auth.User`, `SET_NULL` (facultatif)
- FK `updated_by` → `auth.User`, `SET_NULL` (facultatif)
- FK `installation` → `assets.Installation`, `CASCADE`
- FK `execution` → `maintenance.MaintenanceExecution`, `SET_NULL` (facultatif)

### InstallationMaintenance
- Champs : `id`, `created_at`, `updated_at`, `niveau`, `equipement`, `reference_equipement`, `classe_navire`, `origine_numero`, `origine_en_attente`, `periodicity`, `title`, `description`, `planned_duration_min`, `people_count`, `competence`, `mode_declenchement`, `intervalle`, `unite_intervalle`, `seuil_heures`, `derniere_echeance_heures`
- FK `created_by` → `auth.User`, `SET_NULL` (facultatif)
- FK `updated_by` → `auth.User`, `SET_NULL` (facultatif)
- FK `installation` → `assets.Installation`, `CASCADE` (facultatif)
- FK `categorie` → `assets.CategorieCatalogue`, `PROTECT` (facultatif)
- FK `specialite` → `accounts.SpecialityChoice`, `PROTECT` (facultatif)
- FK `origine` → `assets.InstallationMaintenance`, `SET_NULL` (facultatif)

### InstallationMaintenanceAttachment
- Champs : `id`, `created_at`, `updated_at`, `file`, `name`
- FK `created_by` → `auth.User`, `SET_NULL` (facultatif)
- FK `updated_by` → `auth.User`, `SET_NULL` (facultatif)
- FK `maintenance` → `assets.InstallationMaintenance`, `CASCADE`

### InstallationPart
- Champs : `id`, `created_at`, `updated_at`, `name`, `nno`, `reference`, `marque`, `photo`
- FK `created_by` → `auth.User`, `SET_NULL` (facultatif)
- FK `updated_by` → `auth.User`, `SET_NULL` (facultatif)
- FK `installation` → `assets.Installation`, `CASCADE`

### InstallationVibrationReading
- Champs : `id`, `created_at`, `updated_at`, `date`, `state`, `note`
- FK `created_by` → `auth.User`, `SET_NULL` (facultatif)
- FK `updated_by` → `auth.User`, `SET_NULL` (facultatif)
- FK `installation` → `assets.Installation`, `CASCADE`
- FK `execution` → `maintenance.MaintenanceExecution`, `SET_NULL` (facultatif)

### Location
- Champs : `id`, `created_at`, `updated_at`, `name`
- FK `ship` → `org.Ship`, `PROTECT`
- FK `parent` → `assets.Location`, `CASCADE` (facultatif)

### PropositionArticle
- Champs : `created_at`, `updated_at`, `id`, `etat`, `role_redacteur`, `equipage`, `designation`, `marque`, `reference`, `nno`, `photo`, `caracteristiques`, `duree_vie_mois`, `motif_refus`
- FK `created_by` → `auth.User`, `SET_NULL` (facultatif)
- FK `updated_by` → `auth.User`, `SET_NULL` (facultatif)
- FK `ship` → `org.Ship`, `PROTECT`
- FK `service` → `org.Service`, `PROTECT`
- FK `secteur` → `org.Sector`, `PROTECT` (facultatif)
- FK `categorie` → `assets.CategorieCatalogue`, `PROTECT`
- FK `verificateur` → `auth.User`, `SET_NULL` (facultatif)
- 1-1 `article` → `assets.ArticleCatalogue`, `SET_NULL` (facultatif)

### SignalementFiche
- Champs : `id`, `created_at`, `updated_at`, `texte`, `traite`
- FK `fiche` → `assets.InstallationMaintenance`, `CASCADE`
- FK `version` → `assets.ChecklistTemplate`, `SET_NULL` (facultatif)
- FK `auteur` → `auth.User`, `SET_NULL` (facultatif)
- FK `version_proposee` → `assets.ChecklistTemplate`, `SET_NULL` (facultatif)

## `calendar_app`

### PersonalEvent
- Champs : `id`, `created_at`, `updated_at`, `title`, `starts_at`, `ends_at`, `note`
- FK `owner` → `auth.User`, `CASCADE`

## `core`

### Brouillon
- Champs : `id`, `created_at`, `updated_at`, `cle`, `contenu`, `libelle`, `url`
- FK `user` → `auth.User`, `CASCADE`

## `dashboard`

### ItemAppareillage
- Champs : `id`, `created_at`, `updated_at`, `categorie`, `libelle`, `object_id`, `verifie_le`
- FK `session` → `dashboard.SessionAppareillage`, `CASCADE`
- FK `content_type` → `contenttypes.ContentType`, `SET_NULL` (facultatif)
- FK `verifie_par` → `auth.User`, `SET_NULL` (facultatif)
- Relation générique `objet_source`

### SessionAppareillage
- Champs : `id`, `created_at`, `updated_at`, `ouverte_le`, `cloturee_le`, `date_validation`
- FK `created_by` → `auth.User`, `SET_NULL` (facultatif)
- FK `updated_by` → `auth.User`, `SET_NULL` (facultatif)
- FK `ship` → `org.Ship`, `PROTECT`
- FK `valide_par` → `auth.User`, `SET_NULL` (facultatif)

## `demandes`

### Demande
- Champs : `id`, `created_at`, `updated_at`, `titre`, `description`, `etat`, `priorite`, `echeance`, `object_id`, `resolue_le`
- FK `created_by` → `auth.User`, `SET_NULL` (facultatif)
- FK `updated_by` → `auth.User`, `SET_NULL` (facultatif)
- FK `declarant` → `auth.User`, `CASCADE`
- FK `responsable` → `auth.User`, `PROTECT`
- FK `content_type` → `contenttypes.ContentType`, `CASCADE`
- FK `ship` → `org.Ship`, `PROTECT` (facultatif)
- FK `service` → `org.Service`, `PROTECT` (facultatif)
- FK `sector` → `org.Sector`, `PROTECT` (facultatif)
- FK `section` → `org.Section`, `PROTECT` (facultatif)
- N-N `interlocuteurs` → `auth.User`
- Relation générique `objet`

## `documentation`

### Document
- Champs : `id`, `created_at`, `updated_at`, `titre`, `domaine`, `origine`, `reference_source`, `prochaine_revision`, `equipage`, `archive`
- FK `created_by` → `auth.User`, `SET_NULL` (facultatif)
- FK `updated_by` → `auth.User`, `SET_NULL` (facultatif)
- FK `ship` → `org.Ship`, `PROTECT`
- FK `service` → `org.Service`, `PROTECT` (facultatif)
- FK `sector` → `org.Sector`, `PROTECT` (facultatif)
- FK `section` → `org.Section`, `PROTECT` (facultatif)

### LienDocument
- Champs : `id`, `created_at`, `updated_at`, `object_id`
- FK `document` → `documentation.Document`, `CASCADE`
- FK `content_type` → `contenttypes.ContentType`, `CASCADE`
- Relation générique `objet`

### VersionDocument
- Champs : `id`, `created_at`, `updated_at`, `numero`, `contenu`, `fichier`, `resume`, `etat`, `valide_le`, `date_effet`, `motif_refus`
- FK `document` → `documentation.Document`, `CASCADE`
- FK `auteur` → `auth.User`, `SET_NULL` (facultatif)
- FK `valide_par` → `auth.User`, `SET_NULL` (facultatif)

## `logistics`

### Anomalie
- Champs : `id`, `created_at`, `updated_at`, `titre`, `description`, `gravite`, `statut`, `localisation`, `photo`
- FK `created_by` → `auth.User`, `SET_NULL` (facultatif)
- FK `updated_by` → `auth.User`, `SET_NULL` (facultatif)
- FK `ship` → `org.Ship`, `PROTECT` (facultatif)
- FK `service` → `org.Service`, `PROTECT` (facultatif)
- FK `sector` → `org.Sector`, `PROTECT` (facultatif)
- FK `section` → `org.Section`, `PROTECT` (facultatif)
- FK `installation` → `assets.Installation`, `SET_NULL` (facultatif)
- FK `asset` → `assets.Asset`, `SET_NULL` (facultatif)
- 1-1 `ticket` → `logistics.CorrectiveTicket`, `SET_NULL` (facultatif)

### AnomalieStatutLog
- Champs : `id`, `created_at`, `updated_at`, `ancien_statut`, `nouveau_statut`, `note`
- FK `anomalie` → `logistics.Anomalie`, `CASCADE`
- FK `user` → `auth.User`, `SET_NULL` (facultatif)

### CorrectiveTicket
- Champs : `created_at`, `updated_at`, `id`, `created_by_text`, `reported_at`, `planned_for`, `description`, `severity`, `status`, `diagnostic_final`, `solution`, `date_validation`
- FK `created_by` → `auth.User`, `SET_NULL` (facultatif)
- FK `updated_by` → `auth.User`, `SET_NULL` (facultatif)
- FK `asset` → `assets.Asset`, `CASCADE` (facultatif)
- FK `installation` → `assets.Installation`, `CASCADE` (facultatif)
- FK `valide_par` → `auth.User`, `SET_NULL` (facultatif)
- N-N `assignees` → `auth.User`

### MouvementStock
- Champs : `id`, `created_at`, `updated_at`, `type`, `quantite`, `solde_apres`, `motif`
- FK `piece` → `logistics.StockPiece`, `PROTECT`
- FK `auteur` → `auth.User`, `SET_NULL` (facultatif)
- FK `ticket` → `logistics.CorrectiveTicket`, `SET_NULL` (facultatif)
- FK `ligne_pieces` → `logistics.PartLineItem`, `SET_NULL` (facultatif)

### PartLineItem
- Champs : `id`, `created_at`, `updated_at`, `reference`, `description`, `qty`, `status`, `vendor`, `order_number`, `estimated_cost`, `actual_cost`, `ordered_at`, `received_at`
- FK `part_request` → `logistics.PartRequest`, `CASCADE`

### PartRequest
- Champs : `id`, `created_at`, `updated_at`, `needed_by_date`, `status`
- FK `created_by` → `auth.User`, `SET_NULL` (facultatif)
- FK `updated_by` → `auth.User`, `SET_NULL` (facultatif)
- FK `ticket` → `logistics.CorrectiveTicket`, `CASCADE`
- FK `requested_by` → `auth.User`, `SET_NULL` (facultatif)

### StockPiece
- Champs : `id`, `created_at`, `updated_at`, `reference`, `designation`, `nno`, `quantite`, `quantite_minimale`, `quantite_critique`, `emplacement`, `note`, `photo`
- FK `created_by` → `auth.User`, `SET_NULL` (facultatif)
- FK `updated_by` → `auth.User`, `SET_NULL` (facultatif)
- FK `ship` → `org.Ship`, `PROTECT`
- FK `service` → `org.Service`, `PROTECT`
- FK `sector` → `org.Sector`, `PROTECT`
- FK `section` → `org.Section`, `PROTECT` (facultatif)
- FK `installation` → `assets.Installation`, `SET_NULL` (facultatif)
- FK `asset` → `assets.Asset`, `SET_NULL` (facultatif)

### TicketStatusLog
- Champs : `id`, `created_at`, `updated_at`, `old_status`, `new_status`, `note`
- FK `ticket` → `logistics.CorrectiveTicket`, `CASCADE`
- FK `user` → `auth.User`, `SET_NULL` (facultatif)

## `maintenance`

### CompteRenduCorrectif
- Champs : `id`, `created_at`, `updated_at`, `jeton`, `started_at`, `completed_at`, `duree_estimee_min`, `constat`, `diagnostic`, `action_realisee`, `notes`, `conformity`, `results`, `measurements`, `pieces`, `saisie_origine`
- FK `created_by` → `auth.User`, `SET_NULL` (facultatif)
- FK `updated_by` → `auth.User`, `SET_NULL` (facultatif)
- 1-1 `ticket` → `logistics.CorrectiveTicket`, `CASCADE`
- FK `executed_by` → `auth.User`, `SET_NULL` (facultatif)
- FK `version_fiche` → `assets.ChecklistTemplate`, `SET_NULL` (facultatif)
- N-N `intervenants` → `auth.User`

### MaintenanceExecution
- Champs : `id`, `created_at`, `updated_at`, `started_at`, `completed_at`, `results`, `measurements`, `saisie_origine`, `conformity`, `notes`, `date_validation`
- FK `created_by` → `auth.User`, `SET_NULL` (facultatif)
- FK `updated_by` → `auth.User`, `SET_NULL` (facultatif)
- 1-1 `occurrence` → `maintenance.MaintenanceOccurrence`, `CASCADE`
- FK `executed_by` → `auth.User`, `SET_NULL` (facultatif)
- FK `valide_par` → `auth.User`, `SET_NULL` (facultatif)
- FK `version_fiche` → `assets.ChecklistTemplate`, `SET_NULL` (facultatif)
- N-N `intervenants` → `auth.User`

### MaintenanceOccurrence
- Champs : `id`, `created_at`, `updated_at`, `scheduled_for`, `status`, `priority`
- FK `created_by` → `auth.User`, `SET_NULL` (facultatif)
- FK `updated_by` → `auth.User`, `SET_NULL` (facultatif)
- FK `plan` → `maintenance.MaintenancePlan`, `CASCADE` (facultatif)
- FK `asset` → `assets.Asset`, `CASCADE` (facultatif)
- FK `installation_maintenance` → `assets.InstallationMaintenance`, `CASCADE` (facultatif)
- N-N `assignees` → `auth.User`

### MaintenancePlan
- Champs : `id`, `created_at`, `updated_at`, `scope`, `name`, `every_n_days`, `expected_duration_min`, `requires_validation`, `validation_role`
- FK `created_by` → `auth.User`, `SET_NULL` (facultatif)
- FK `updated_by` → `auth.User`, `SET_NULL` (facultatif)
- FK `asset_type` → `assets.AssetType`, `CASCADE` (facultatif)
- FK `asset` → `assets.Asset`, `CASCADE` (facultatif)
- FK `checklist_template` → `assets.ChecklistTemplate`, `SET_NULL` (facultatif)
- FK `fiche` → `assets.InstallationMaintenance`, `CASCADE` (facultatif)

### ModificationCompteRendu
- Champs : `id`, `created_at`, `updated_at`, `motif`, `modifications`
- FK `execution` → `maintenance.MaintenanceExecution`, `CASCADE` (facultatif)
- FK `correctif` → `maintenance.CompteRenduCorrectif`, `CASCADE` (facultatif)
- FK `auteur` → `auth.User`, `SET_NULL` (facultatif)

### OccurrenceStatusLog
- Champs : `id`, `created_at`, `updated_at`, `old_status`, `new_status`, `note`
- FK `occurrence` → `maintenance.MaintenanceOccurrence`, `CASCADE`
- FK `user` → `auth.User`, `SET_NULL` (facultatif)

## `notifications`

### Notification
- Champs : `id`, `created_at`, `updated_at`, `verb`, `level`, `is_read`, `object_id`, `url`, `action_requise`, `traitee_le`, `regime`, `categorie`
- FK `user` → `auth.User`, `CASCADE`
- FK `content_type` → `contenttypes.ContentType`, `CASCADE` (facultatif)
- Relation générique `target`

### PushSubscription
- Champs : `id`, `created_at`, `updated_at`, `endpoint`, `p256dh`, `auth`, `user_agent`
- FK `user` → `auth.User`, `CASCADE`

## `org`

### ModuleActivation
- Champs : `id`, `created_at`, `updated_at`, `module`, `active`
- FK `ship` → `org.Ship`, `PROTECT`

### ParametresPassation
- Champs : `id`, `created_at`, `updated_at`, `active`

### PeriodeEquipage
- Champs : `id`, `created_at`, `updated_at`, `equipage`, `debut`, `fin`, `source`
- FK `ship` → `org.Ship`, `PROTECT`
- 1-1 `releve` → `org.ReleveEquipage`, `SET_NULL` (facultatif)

### ReferenceBatiment
- Champs : `id`, `created_at`, `updated_at`, `nom`, `numero_coque`, `trigramme`, `classe`, `port_base`, `famille`, `statut`, `statut_au`, `avec_equipage`, `source_url`, `source_date`, `commentaire`, `archive`
- FK `type_batiment` → `org.TypeBatiment`, `SET_NULL` (facultatif)
- 1-1 `unite` → `org.Ship`, `SET_NULL` (facultatif)

### ReleveEquipage
- Champs : `id`, `created_at`, `updated_at`, `equipage_propose`, `statut`, `decide_le`, `date_effet`, `appliquee_le`, `annulee_le`, `motif_annulation`
- FK `ship` → `org.Ship`, `PROTECT`
- FK `propose_par` → `auth.User`, `SET_NULL` (facultatif)
- FK `decide_par` → `auth.User`, `SET_NULL` (facultatif)
- FK `annulee_par` → `auth.User`, `SET_NULL` (facultatif)

### ResponsableClasseNavire
- Champs : `id`, `created_at`, `updated_at`, `classe_navire`
- FK `user` → `auth.User`, `CASCADE`

### RoleThresholdConfig
- Champs : `id`, `created_at`, `updated_at`, `thresholds`
- 1-1 `ship` → `org.Ship`, `PROTECT` (facultatif)

### Section
- Champs : `id`, `created_at`, `updated_at`, `name`, `archived`
- FK `sector` → `org.Sector`, `CASCADE`

### Sector
- Champs : `id`, `created_at`, `updated_at`, `name`, `color`, `archived`
- FK `service` → `org.Service`, `CASCADE`

### SectorConfig
- Champs : `id`, `created_at`, `updated_at`, `ui_preferences`, `status_overrides`, `alert_thresholds`, `dashboard_widgets`
- 1-1 `sector` → `org.Sector`, `PROTECT`

### Service
- Champs : `id`, `created_at`, `updated_at`, `name`, `commandant_adjoint`, `archived`
- FK `ship` → `org.Ship`, `CASCADE`

### Ship
- Champs : `id`, `created_at`, `updated_at`, `name`, `code`, `type_unite`, `classe_navire`, `double_equipage`, `equipage_a_bord`, `fuseau_horaire`, `archived`, `numero_coque`, `trigramme`
- FK `type_batiment` → `org.TypeBatiment`, `SET_NULL` (facultatif)

### SynthesePassation
- Champs : `id`, `created_at`, `updated_at`, `equipage_sortant`, `equipage_montant`, `contenu`
- FK `ship` → `org.Ship`, `PROTECT`
- 1-1 `releve` → `org.ReleveEquipage`, `SET_NULL` (facultatif)
- FK `auteur` → `auth.User`, `SET_NULL` (facultatif)

### TypeBatiment
- Champs : `id`, `created_at`, `updated_at`, `code`, `libelle`, `ordre`, `silhouette`, `actif`

### VersionConfiguration
- Champs : `id`, `cle`, `valeur`, `jeton`

## `postes`

### AffectationPoste
- Champs : `id`, `created_at`, `updated_at`
- FK `poste` → `postes.Poste`, `CASCADE`
- FK `user` → `auth.User`, `CASCADE`
- FK `affecte_par` → `auth.User`, `SET_NULL` (facultatif)

### Poste
- Champs : `id`, `created_at`, `updated_at`, `intitule`, `equipage`, `effectif`, `actif`
- FK `created_by` → `auth.User`, `SET_NULL` (facultatif)
- FK `updated_by` → `auth.User`, `SET_NULL` (facultatif)
- FK `ship` → `org.Ship`, `PROTECT`
- FK `service` → `org.Service`, `PROTECT` (facultatif)
- FK `sector` → `org.Sector`, `PROTECT` (facultatif)
- FK `section` → `org.Section`, `PROTECT` (facultatif)
- N-N `formations` → `training.TrainingCourse`

## `programme`

### DelegationProgramme
- Champs : `id`, `created_at`, `updated_at`
- FK `ship` → `org.Ship`, `PROTECT`
- FK `user` → `auth.User`, `CASCADE`
- FK `accordee_par` → `auth.User`, `SET_NULL` (facultatif)

### EvenementProgramme
- Champs : `id`, `created_at`, `updated_at`, `titre`, `description`, `debut`, `fin`, `lieu`, `equipage`, `annule`
- FK `created_by` → `auth.User`, `SET_NULL` (facultatif)
- FK `updated_by` → `auth.User`, `SET_NULL` (facultatif)
- FK `type` → `programme.TypeProgramme`, `PROTECT`
- FK `ship` → `org.Ship`, `PROTECT`
- FK `service` → `org.Service`, `PROTECT` (facultatif)
- FK `sector` → `org.Sector`, `PROTECT` (facultatif)
- FK `section` → `org.Section`, `PROTECT` (facultatif)
- FK `auteur` → `auth.User`, `SET_NULL` (facultatif)
- N-N `taches` → `taches.Tache`

### TypeProgramme
- Champs : `id`, `created_at`, `updated_at`, `nom`, `couleur`, `actif`
- FK `ship` → `org.Ship`, `PROTECT`

## `quarts`

### AlerteAccostage
- Champs : `id`, `created_at`, `updated_at`, `genre`, `fermee_le`, `motif_fermeture`
- FK `mouvement` → `quarts.MouvementBatiment`, `CASCADE`

### AlerteActivation
- Champs : `id`, `created_at`, `updated_at`, `etape`, `version_prevision`, `fermee_le`, `motif_fermeture`, `declenchee_le`
- FK `liste` → `quarts.ServiceGarde`, `CASCADE`

### ChefDeListe
- Champs : `id`, `created_at`, `updated_at`, `type_liste`, `qualifiee_le`
- FK `user` → `auth.User`, `CASCADE`
- FK `ship` → `org.Ship`, `PROTECT` (facultatif)
- FK `service` → `org.Service`, `PROTECT` (facultatif)
- FK `sector` → `org.Sector`, `PROTECT` (facultatif)
- FK `section` → `org.Section`, `PROTECT` (facultatif)
- FK `qualifiee_par` → `auth.User`, `SET_NULL` (facultatif)
- FK `origine` → `quarts.ChefDeListe`, `SET_NULL` (facultatif)

### ConfigurationActivation
- Champs : `id`, `created_at`, `updated_at`, `rappel_minutes`, `alerte_minutes`, `escalade_minutes`, `activation_anticipee_minutes`, `remplacement_duree_max_heures`
- 1-1 `ship` → `org.Ship`, `PROTECT`

### CreneauQuart
- Champs : `id`, `created_at`, `updated_at`, `poste`, `debut`, `fin`, `note`, `fin_initiale`
- FK `marin` → `auth.User`, `SET_NULL` (facultatif)
- FK `quart` → `quarts.Quart`, `CASCADE`

### CreneauServiceGarde
- Champs : `id`, `created_at`, `updated_at`, `poste`, `debut`, `fin`, `note`
- FK `marin` → `auth.User`, `SET_NULL` (facultatif)
- FK `service_garde` → `quarts.ServiceGarde`, `CASCADE`

### EchangeService
- Champs : `id`, `created_at`, `updated_at`, `libelle_creneau_demandeur`, `libelle_creneau_cible`, `statut`, `motif`, `motif_decision`, `accepte_le`, `decide_le`, `applique_le`, `blocage_application`
- FK `creneau_demandeur` → `quarts.CreneauServiceGarde`, `SET_NULL` (facultatif)
- FK `creneau_cible` → `quarts.CreneauServiceGarde`, `SET_NULL` (facultatif)
- FK `demandeur` → `auth.User`, `SET_NULL` (facultatif)
- FK `cible` → `auth.User`, `SET_NULL` (facultatif)
- FK `decide_par` → `auth.User`, `SET_NULL` (facultatif)

### EchangeServiceEvenement
- Champs : `id`, `created_at`, `updated_at`, `action`, `detail`
- FK `echange` → `quarts.EchangeService`, `CASCADE`
- FK `acteur` → `auth.User`, `SET_NULL` (facultatif)

### FeuilleService
- Champs : `id`, `created_at`, `updated_at`, `equipage`, `date`, `statut`, `valeurs_entete`, `structure_figee`, `proposee_le`, `visa_secteur_le`, `visa_service_le`, `visa_comaeq_le`, `publiee_le`, `motif_retour`, `empreinte_visee`, `divergence_signalee`
- FK `created_by` → `auth.User`, `SET_NULL` (facultatif)
- FK `updated_by` → `auth.User`, `SET_NULL` (facultatif)
- FK `ship` → `org.Ship`, `PROTECT`
- FK `secteur_redacteur` → `org.Sector`, `PROTECT` (facultatif)
- FK `service_redacteur` → `org.Service`, `PROTECT` (facultatif)
- FK `proposee_par` → `auth.User`, `SET_NULL` (facultatif)
- FK `visa_secteur_par` → `auth.User`, `SET_NULL` (facultatif)
- FK `visa_service_par` → `auth.User`, `SET_NULL` (facultatif)
- FK `visa_comaeq_par` → `auth.User`, `SET_NULL` (facultatif)
- FK `publiee_par` → `auth.User`, `SET_NULL` (facultatif)
- FK `rectificatif_ouvert_par` → `auth.User`, `SET_NULL` (facultatif)

### FonctionFeuilleService
- Champs : `id`, `created_at`, `updated_at`, `uid`, `ordre`, `libelle`, `poste_recherche`, `actif`
- FK `ship` → `org.Ship`, `PROTECT`

### ModificationOrganisationAlerte
- Champs : `id`, `created_at`, `updated_at`, `action`, `statut`, `donnees`, `decidee_le`, `motif_refus`
- FK `ship` → `org.Ship`, `PROTECT`
- FK `scenario` → `quarts.ScenarioAlerte`, `SET_NULL` (facultatif)
- FK `proposee_par` → `auth.User`, `SET_NULL` (facultatif)
- FK `decidee_par` → `auth.User`, `SET_NULL` (facultatif)

### MouvementBatiment
- Champs : `id`, `created_at`, `updated_at`, `type`, `survenu_le`, `fonction_declarante`, `statut`, `annule_le`, `motif_annulation`, `mode_avant`, `mode_apres`, `motif`
- FK `ship` → `org.Ship`, `PROTECT`
- FK `declare_par` → `auth.User`, `SET_NULL` (facultatif)
- FK `annule_par` → `auth.User`, `SET_NULL` (facultatif)
- FK `remplace` → `quarts.MouvementBatiment`, `SET_NULL` (facultatif)

### PosteAlerte
- Champs : `id`, `created_at`, `updated_at`, `ordre`, `libelle`, `obligatoire`
- FK `scenario` → `quarts.ScenarioAlerte`, `CASCADE`
- FK `fonction` → `quarts.FonctionFeuilleService`, `SET_NULL` (facultatif)

### Quart
- Champs : `id`, `created_at`, `updated_at`, `nom`, `equipage`, `date_debut`, `date_fin`, `statut`, `proposee_le`, `publiee_le`, `duree_creneau_heures`
- FK `created_by` → `auth.User`, `SET_NULL` (facultatif)
- FK `updated_by` → `auth.User`, `SET_NULL` (facultatif)
- FK `ship` → `org.Ship`, `PROTECT` (facultatif)
- FK `service` → `org.Service`, `PROTECT` (facultatif)
- FK `sector` → `org.Sector`, `PROTECT` (facultatif)
- FK `section` → `org.Section`, `PROTECT` (facultatif)
- FK `proposee_par` → `auth.User`, `SET_NULL` (facultatif)
- FK `publiee_par` → `auth.User`, `SET_NULL` (facultatif)
- FK `fonction` → `accounts.FonctionQuartChoice`, `PROTECT` (facultatif)

### RedacteurFeuilleService
- Champs : `id`, `created_at`, `updated_at`, `equipage`
- FK `ship` → `org.Ship`, `PROTECT`
- FK `user` → `auth.User`, `CASCADE`
- FK `accordee_par` → `auth.User`, `SET_NULL` (facultatif)

### RemplacementChefDeListe
- Champs : `id`, `created_at`, `updated_at`, `equipage`, `perimetre_navire`, `type_liste`, `debut`, `fin`, `motif`, `revoque_le`, `motif_revocation`
- FK `ship` → `org.Ship`, `PROTECT`
- FK `service` → `org.Service`, `PROTECT` (facultatif)
- FK `sector` → `org.Sector`, `PROTECT` (facultatif)
- FK `section` → `org.Section`, `PROTECT` (facultatif)
- FK `remplacant` → `auth.User`, `CASCADE`
- FK `titulaire` → `auth.User`, `CASCADE`
- FK `designe_par` → `auth.User`, `SET_NULL` (facultatif)
- FK `revoque_par` → `auth.User`, `SET_NULL` (facultatif)

### RubriqueEnTeteFeuilleService
- Champs : `id`, `created_at`, `updated_at`, `uid`, `ordre`, `libelle`, `type_saisie`, `valeur_fixe`, `actif`
- FK `ship` → `org.Ship`, `PROTECT`

### ScenarioAlerte
- Champs : `id`, `created_at`, `updated_at`, `ordre`, `libelle`, `famille`, `adjoint_sigle`, `actif`
- FK `ship` → `org.Ship`, `PROTECT`

### ServiceGarde
- Champs : `id`, `created_at`, `updated_at`, `nom`, `equipage`, `date_debut`, `date_fin`, `statut`, `proposee_le`, `publiee_le`, `type_service`, `duree_creneau_heures`, `delai_minimal_echange_heures`, `application`, `prise_effet_prevue`, `prise_effet`, `active_le`, `active_en_qualite`, `terminee_le`, `version_prevision`, `activation_historique`
- FK `created_by` → `auth.User`, `SET_NULL` (facultatif)
- FK `updated_by` → `auth.User`, `SET_NULL` (facultatif)
- FK `ship` → `org.Ship`, `PROTECT` (facultatif)
- FK `service` → `org.Service`, `PROTECT` (facultatif)
- FK `sector` → `org.Sector`, `PROTECT` (facultatif)
- FK `section` → `org.Section`, `PROTECT` (facultatif)
- FK `proposee_par` → `auth.User`, `SET_NULL` (facultatif)
- FK `publiee_par` → `auth.User`, `SET_NULL` (facultatif)
- FK `fonction` → `accounts.ServiceFunctionChoice`, `PROTECT` (facultatif)
- FK `active_par` → `auth.User`, `SET_NULL` (facultatif)
- FK `terminee_par` → `auth.User`, `SET_NULL` (facultatif)
- N-N `formations_requises` → `training.TrainingCourse`

### VersionFeuilleService
- Champs : `id`, `created_at`, `updated_at`, `numero`, `publiee_le`, `contenu_fige`, `remplace_numero`
- FK `feuille` → `quarts.FeuilleService`, `CASCADE`
- FK `publiee_par` → `auth.User`, `SET_NULL` (facultatif)

### VersionQuart
- Champs : `id`, `created_at`, `updated_at`, `numero`, `publiee_le`, `creneaux_fige`
- FK `publiee_par` → `auth.User`, `SET_NULL` (facultatif)
- FK `quart` → `quarts.Quart`, `CASCADE`

### VersionServiceGarde
- Champs : `id`, `created_at`, `updated_at`, `numero`, `publiee_le`, `creneaux_fige`
- FK `publiee_par` → `auth.User`, `SET_NULL` (facultatif)
- FK `service_garde` → `quarts.ServiceGarde`, `CASCADE`

## `retex`

### DomaineRetex
- Champs : `id`, `created_at`, `updated_at`, `nom`, `coma`, `organisme`, `actif`
- FK `ship` → `org.Ship`, `PROTECT`

### Retex
- Champs : `id`, `created_at`, `updated_at`, `titre`, `constat`, `causes`, `enseignement`, `recommandation`, `portee`, `diffusion`, `organisme`, `etat`, `decide_le`, `motif_decision`, `object_id`, `source_libelle`
- FK `created_by` → `auth.User`, `SET_NULL` (facultatif)
- FK `updated_by` → `auth.User`, `SET_NULL` (facultatif)
- FK `domaine` → `retex.DomaineRetex`, `PROTECT`
- FK `ship` → `org.Ship`, `PROTECT`
- FK `auteur` → `auth.User`, `SET_NULL` (facultatif)
- FK `decide_par` → `auth.User`, `SET_NULL` (facultatif)
- FK `content_type` → `contenttypes.ContentType`, `SET_NULL` (facultatif)
- 1-1 `document` → `documentation.Document`, `SET_NULL` (facultatif)
- N-N `taches` → `taches.Tache`
- Relation générique `source`

## `rondes`

### PointControle
- Champs : `id`, `created_at`, `updated_at`, `ordre`, `libelle`, `consigne`, `avec_mesure`, `unite_mesure`, `gravite`
- FK `modele` → `rondes.RondeModele`, `CASCADE`
- FK `installation` → `assets.Installation`, `SET_NULL` (facultatif)
- FK `asset` → `assets.Asset`, `SET_NULL` (facultatif)

### ResultatPoint
- Champs : `id`, `created_at`, `updated_at`, `ordre`, `libelle`, `consigne`, `equipement_libelle`, `avec_mesure`, `unite_mesure`, `gravite`, `resultat`, `mesure`, `commentaire`, `saisi_le`
- FK `ronde` → `rondes.Ronde`, `CASCADE`
- FK `installation` → `assets.Installation`, `SET_NULL` (facultatif)
- FK `asset` → `assets.Asset`, `SET_NULL` (facultatif)
- FK `saisi_par` → `auth.User`, `SET_NULL` (facultatif)
- FK `anomalie` → `logistics.Anomalie`, `SET_NULL` (facultatif)

### Ronde
- Champs : `id`, `created_at`, `updated_at`, `version_modele`, `nom`, `date_prevue`, `statut`, `debut`, `fin`
- FK `modele` → `rondes.RondeModele`, `SET_NULL` (facultatif)
- FK `ship` → `org.Ship`, `PROTECT` (facultatif)
- FK `service` → `org.Service`, `PROTECT` (facultatif)
- FK `sector` → `org.Sector`, `PROTECT` (facultatif)
- FK `assigne_a` → `auth.User`, `SET_NULL` (facultatif)
- FK `realisee_par` → `auth.User`, `SET_NULL` (facultatif)

### RondeModele
- Champs : `id`, `created_at`, `updated_at`, `nom`, `description`, `periodicite_jours`, `actif`, `version`
- FK `created_by` → `auth.User`, `SET_NULL` (facultatif)
- FK `updated_by` → `auth.User`, `SET_NULL` (facultatif)
- FK `ship` → `org.Ship`, `PROTECT` (facultatif)
- FK `service` → `org.Service`, `PROTECT` (facultatif)
- FK `sector` → `org.Sector`, `PROTECT` (facultatif)
- FK `responsable` → `auth.User`, `SET_NULL` (facultatif)

## `taches`

### ElementChecklistTache
- Champs : `id`, `created_at`, `updated_at`, `texte`, `fait`, `ordre`
- FK `tache` → `taches.Tache`, `CASCADE`

### LotTaches
- Champs : `id`, `created_at`, `updated_at`, `libelle`, `titre`
- FK `created_by` → `auth.User`, `SET_NULL` (facultatif)
- FK `updated_by` → `auth.User`, `SET_NULL` (facultatif)

### ParametresTaches
- Champs : `id`, `created_at`, `updated_at`, `jours_entre_relances`, `relancer_assigne`, `relancer_chef_attributeur`, `relancer_chefs_si_blocage`, `jours_terminees_affichees`

### PieceJointeTache
- Champs : `id`, `created_at`, `updated_at`, `fichier`, `nom`
- FK `created_by` → `auth.User`, `SET_NULL` (facultatif)
- FK `updated_by` → `auth.User`, `SET_NULL` (facultatif)
- FK `tache` → `taches.Tache`, `CASCADE`

### Tache
- Champs : `id`, `created_at`, `updated_at`, `titre`, `description`, `echeance`, `statut`, `priorite`, `partagee`, `motif_blocage`, `compte_rendu`, `terminee_le`
- FK `created_by` → `auth.User`, `SET_NULL` (facultatif)
- FK `updated_by` → `auth.User`, `SET_NULL` (facultatif)
- FK `assigne` → `auth.User`, `CASCADE`
- FK `demande` → `demandes.Demande`, `SET_NULL` (facultatif)
- FK `annonce` → `annonces.Annonce`, `SET_NULL` (facultatif)
- FK `lot` → `taches.LotTaches`, `SET_NULL` (facultatif)
- N-N `participants` → `auth.User`

## `threads`

### Attachment
- Champs : `id`, `created_at`, `updated_at`, `file`, `name`
- FK `created_by` → `auth.User`, `SET_NULL` (facultatif)
- FK `updated_by` → `auth.User`, `SET_NULL` (facultatif)
- FK `message` → `threads.Message`, `CASCADE`

### Message
- Champs : `id`, `created_at`, `updated_at`, `body`, `is_system`
- FK `created_by` → `auth.User`, `SET_NULL` (facultatif)
- FK `updated_by` → `auth.User`, `SET_NULL` (facultatif)
- FK `thread` → `threads.Thread`, `CASCADE`
- FK `author` → `auth.User`, `SET_NULL` (facultatif)
- N-N `mentions` → `auth.User`

### Thread
- Champs : `id`, `created_at`, `updated_at`, `object_id`
- FK `content_type` → `contenttypes.ContentType`, `CASCADE`
- Relation générique `content_object`

## `training`

### CandidatureFormation
- Champs : `id`, `created_at`, `updated_at`, `statut`, `date_validation_hierarchie`, `date_validation_brh`
- FK `created_by` → `auth.User`, `SET_NULL` (facultatif)
- FK `updated_by` → `auth.User`, `SET_NULL` (facultatif)
- FK `course` → `training.TrainingCourse`, `CASCADE`
- FK `marin` → `auth.User`, `CASCADE`
- FK `hierarchie_validee_par` → `auth.User`, `SET_NULL` (facultatif)
- FK `brh_validee_par` → `auth.User`, `SET_NULL` (facultatif)

### DemandePlace
- Champs : `id`, `created_at`, `updated_at`, `nb_places_demandees`, `nb_places_attribuees`, `statut`, `date_attribution`
- FK `created_by` → `auth.User`, `SET_NULL` (facultatif)
- FK `updated_by` → `auth.User`, `SET_NULL` (facultatif)
- FK `course` → `training.TrainingCourse`, `CASCADE`
- FK `ship` → `org.Ship`, `PROTECT`
- FK `session` → `training.TrainingSession`, `SET_NULL` (facultatif)
- FK `attribue_par` → `auth.User`, `SET_NULL` (facultatif)

### PersonnelBRH
- Champs : `id`, `created_at`, `updated_at`
- FK `ship` → `org.Ship`, `PROTECT`
- FK `user` → `auth.User`, `CASCADE`

### PlaceAffectee
- Champs : `id`, `created_at`, `updated_at`
- FK `demande_place` → `training.DemandePlace`, `CASCADE`
- FK `marin` → `auth.User`, `CASCADE`

### ReferentFormation
- Champs : `id`, `created_at`, `updated_at`
- FK `course` → `training.TrainingCourse`, `CASCADE`
- FK `ship` → `org.Ship`, `PROTECT`
- FK `user` → `auth.User`, `CASCADE`

### ReferentFormationNavire
- Champs : `id`, `created_at`, `updated_at`
- 1-1 `ship` → `org.Ship`, `PROTECT`
- FK `user` → `auth.User`, `CASCADE`

### TrainingCourse
- Champs : `id`, `created_at`, `updated_at`, `title`, `category`, `description`, `validity_days`, `gere_par_le_bord`, `statut_validation`, `bareme`
- FK `created_by` → `auth.User`, `SET_NULL` (facultatif)
- FK `updated_by` → `auth.User`, `SET_NULL` (facultatif)
- N-N `prerequisites` → `training.TrainingCourse`

### TrainingRecord
- Champs : `id`, `created_at`, `updated_at`, `completed_at`, `expires_at`, `attachment`
- FK `created_by` → `auth.User`, `SET_NULL` (facultatif)
- FK `updated_by` → `auth.User`, `SET_NULL` (facultatif)
- FK `user` → `auth.User`, `CASCADE`
- FK `course` → `training.TrainingCourse`, `CASCADE`
- FK `validated_by` → `auth.User`, `SET_NULL` (facultatif)

### TrainingRequirement
- Champs : `id`, `created_at`, `updated_at`, `applies_to_role`, `required`
- FK `applies_to_ship` → `org.Ship`, `PROTECT` (facultatif)
- FK `applies_to_service` → `org.Service`, `PROTECT` (facultatif)
- FK `applies_to_sector` → `org.Sector`, `PROTECT` (facultatif)
- FK `applies_to_section` → `org.Section`, `PROTECT` (facultatif)
- FK `course` → `training.TrainingCourse`, `CASCADE`

### TrainingSession
- Champs : `id`, `created_at`, `updated_at`, `scheduled_at`, `capacite_max`, `location`, `status`
- FK `course` → `training.TrainingCourse`, `CASCADE`
- FK `instructor` → `auth.User`, `SET_NULL` (facultatif)
- N-N `attendees` → `auth.User`
- N-N `reservations` → `auth.User`

### TrainingWaitlistEntry
- Champs : `id`, `created_at`, `updated_at`
- FK `session` → `training.TrainingSession`, `CASCADE`
- FK `user` → `auth.User`, `CASCADE`
