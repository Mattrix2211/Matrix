# Annexe C — Index des routes web et API (généré, état B)

> Diffusion restreinte. Généré par `outils/generer_annexes_e4.py` depuis l'inventaire de l'état B (`6d6d0be`, non fusionné dans `main`). Ne pas éditer à la main.

**721 routes** : 185 pages et fichiers, 171 routes d'API, 365 routes d'administration Django (résumées). Lecture : chemin, nom, vue, gabarit HTML cité dans la vue (quand il y en a un). Chapitres : voir la matrice (annexe G).

## C.1 Pages web, fichiers et recherche

| Chemin | Nom | Vue | Gabarit |
|---|---|---|---|
| `/` | home | `dashboard.web_views.AujourdhuiView` | `matrix/templates/dashboard/aujourdhui.html`, `matrix/templates/dashboard/aujourdhui_terre.html` |
| `absences/` | absences-index | `absences.web_views.MesAbsencesView` | `matrix/templates/absences/index.html` |
| `accounts/login/` | login | `django.contrib.auth.views.LoginView` | — |
| `accounts/password_change/` | password_change | `accounts.web_views.ChangerMotDePasseView` | `matrix/templates/registration/password_change_form.html` |
| `annonces/` | annonces-index | `annonces.web_views.AnnoncesIndexView` | `matrix/templates/annonces/index.html` |
| `annonces/<int:pk>/` | annonce-detail | `annonces.web_views.AnnonceDetailView` | `matrix/templates/annonces/detail.html` |
| `annonces/<int:pk>/action/` | annonce-action | `annonces.web_views.AnnonceActionView` | `matrix/templates/annonces/detail.html` |
| `annonces/nouvelle/` | annonce-nouvelle | `annonces.web_views.AnnonceNouvelleView` | `matrix/templates/annonces/nouvelle.html` |
| `assets/` | asset-list | `assets.asset_views.AssetListView` | `matrix/templates/assets/list.html` |
| `assets/<uuid:pk>/` | asset-detail | `assets.asset_views.AssetDetailView` | `matrix/templates/assets/detail.html` |
| `assets/<uuid:pk>/commentaire/` | asset-comment-create | `assets.asset_views.AssetCommentCreateView` | — |
| `assets/<uuid:pk>/start-visual/` | asset-start-visual | `assets.scan_views.StartVisualCheckView` | — |
| `assets/importer/` | asset-import | `assets.asset_views.AssetImportView` | `matrix/templates/assets/import.html` |
| `assets/importer/modele/` | asset-import-modele | `assets.asset_views.AssetImportModeleView` | — |
| `assets/plan-navire/` | plan-navire-vue | `assets.plan_navire_views.PlanNavireVueView` | `matrix/templates/assets/plan_navire_vue.html` |
| `assets/plan-navire/<int:pk>/` | plan-navire-vue-deck | `assets.plan_navire_views.PlanNavireVueDeckView` | `matrix/templates/assets/plan_navire_vue.html` |
| `assets/plan/` | plan-navire-list | `assets.plan_navire_views.PlanNavireListView` | `matrix/templates/assets/plan_navire_list.html` |
| `assets/plan/<int:pk>/` | plan-navire-deck | `assets.plan_navire_views.PlanNavireDeckView` | `matrix/templates/assets/plan_navire_deck.html` |
| `brouillons/` | brouillon | `matrix.core.brouillons.BrouillonView` | — |
| `calendar/` | calendar-index | `calendar_app.index_views.CalendarView` | `matrix/templates/calendar/index.html` |
| `calendar/detail/<str:type_evenement>/<int:pk>/` | calendar-detail | `calendar_app.detail_views.detail_evenement` | — |
| `calendar/detail/<str:type_evenement>/<int:pk>/commentaire/` | calendar-detail-commentaire | `calendar_app.detail_views.detail_commentaire` | — |
| `calendar/detail/tache/<int:pk>/demarrer/` | calendar-detail-demarrer | `calendar_app.detail_views.detail_tache_demarrer` | — |
| `calendar/events/` | calendar-events | `calendar_app.api_views.calendar_events` | — |
| `calendar/events/move/` | calendar-event-move | `calendar_app.deplacement_views.calendar_event_move` | — |
| `calendar/ical/my/` | calendar-ical-my | `calendar_app.ical_views.user_ical_feed` | — |
| `calendar/personnel/<int:pk>/supprimer/` | calendar-personal-delete | `calendar_app.evenements_personnels_views.personal_event_delete` | — |
| `calendar/personnel/enregistrer/` | calendar-personal-save | `calendar_app.evenements_personnels_views.personal_event_save` | — |
| `catalogue/` | catalogue | `assets.catalogue_web.CatalogueView` | `matrix/templates/assets/catalogue/_contenu.html`, `matrix/templates/assets/catalogue/index.html` |
| `catalogue/articles/<uuid:pk>/` | catalogue-article | `assets.catalogue_web.ArticleCatalogueDetailView` | `matrix/templates/assets/catalogue/fiche.html` |
| `catalogue/articles/<uuid:pk>/archiver/` | catalogue-article-archiver | `assets.catalogue_web.ArticleArchiverView` | — |
| `catalogue/articles/<uuid:pk>/equiper/` | catalogue-article-equiper | `assets.equipement_web.ArticleEquiperView` | `matrix/templates/assets/catalogue/equiper.html` |
| `catalogue/articles/<uuid:pk>/exemplaires/` | catalogue-article-exemplaires | `assets.exemplaires_web.ArticleExemplairesView` | — |
| `catalogue/articles/<uuid:pk>/modifier/` | catalogue-article-modifier | `assets.catalogue_web.ArticleEcritureView` | — |
| `catalogue/articles/nouveau/` | catalogue-article-nouveau | `assets.catalogue_web.ArticleEcritureView` | — |
| `catalogue/categories/<uuid:categorie_pk>/fiches/nouvelle/` | fiche-flotte-nouvelle | `assets.fiche_web.FicheFlotteAssistantView` | — |
| `catalogue/categories/<uuid:pk>/archiver/` | catalogue-categorie-archiver | `assets.catalogue_web.CategorieArchiverView` | — |
| `catalogue/categories/<uuid:pk>/modifier/` | catalogue-categorie-modifier | `assets.catalogue_web.CategorieEcritureView` | — |
| `catalogue/categories/nouvelle/` | catalogue-categorie-nouvelle | `assets.catalogue_web.CategorieEcritureView` | — |
| `catalogue/exemplaires/` | catalogue-exemplaires-incomplets | `assets.exemplaires_web.ExemplairesIncompletsView` | — |
| `catalogue/propositions/` | catalogue-propositions | `assets.proposition_web.PropositionsView` | `matrix/templates/assets/catalogue/propositions.html` |
| `catalogue/propositions/<uuid:pk>/` | catalogue-proposition | `assets.proposition_web.PropositionDetailView` | `matrix/templates/assets/catalogue/proposition.html` |
| `catalogue/propositions/<uuid:pk>/modifier/` | catalogue-proposition-modifier | `assets.proposition_web.PropositionModifierView` | `matrix/templates/assets/catalogue/formulaire.html` |
| `catalogue/propositions/<uuid:pk>/refuser/` | catalogue-proposition-refuser | `assets.proposition_web.PropositionRefuserView` | — |
| `catalogue/propositions/<uuid:pk>/verifier/` | catalogue-proposition-verifier | `assets.proposition_web.PropositionVerifierView` | `matrix/templates/assets/catalogue/formulaire.html` |
| `catalogue/propositions/<uuid:pk>/viser/` | catalogue-proposition-viser | `assets.proposition_web.PropositionViserView` | — |
| `catalogue/propositions/nouvelle/` | catalogue-proposition-nouvelle | `assets.proposition_web.PropositionNouvelleView` | `matrix/templates/assets/catalogue/formulaire.html` |
| `dashboard/classe-navire/` | dashboard-classe-navire-choix | `dashboard.web_views.DashboardClasseNavireChoixView` | `matrix/templates/dashboard/choix_classe_navire.html` |
| `dashboard/classe-navire/<str:classe>/` | dashboard-classe-navire | `dashboard.web_views.DashboardClasseNavireView` | `matrix/templates/dashboard/classe_navire.html` |
| `dashboard/comanav/` | vue-comanav | `dashboard.comanav.VueComanavView` | `matrix/templates/dashboard/comanav.html` |
| `dashboard/flotte/` | vue-flotte | `dashboard.web_views.VueFlotteView` | `matrix/templates/dashboard/flotte.html` |
| `dashboard/passation/<int:pk>/` | passation | `dashboard.passation.PassationView` | `matrix/templates/dashboard/passation.html` |
| `dashboard/passation/<int:pk>/pdf/` | passation-pdf | `dashboard.passation.PassationPdfView` | `matrix/templates/dashboard/passation_pdf.html` |
| `dashboard/pret-appareillage/` | pret-appareillage | `dashboard.web_views.PretAppareillageView` | `matrix/templates/dashboard/pret_appareillage.html` |
| `dashboard/pret-appareillage/historique/` | historique-appareillage | `dashboard.web_views.HistoriqueAppareillageView` | `matrix/templates/dashboard/historique_appareillage.html` |
| `dashboard/pret-appareillage/item/<int:pk>/cocher/` | item-appareillage-cocher | `dashboard.web_views.ItemAppareillageCocherView` | `matrix/templates/dashboard/_checklist_appareillage.html` |
| `dashboard/pret-appareillage/ouvrir/` | session-appareillage-ouvrir | `dashboard.web_views.SessionAppareillageOuvrirView` | — |
| `dashboard/pret-appareillage/session/<int:pk>/` | session-appareillage-detail | `dashboard.web_views.SessionAppareillageDetailView` | `matrix/templates/dashboard/detail_session_appareillage.html` |
| `dashboard/pret-appareillage/session/<int:pk>/signer/` | session-appareillage-signer | `dashboard.web_views.SessionAppareillageSignerView` | — |
| `dashboard/specialite/` | dashboard-specialite-choix | `dashboard.web_views.DashboardSpecialiteChoixView` | `matrix/templates/dashboard/choix_specialite.html` |
| `dashboard/specialite/<int:pk>/` | dashboard-specialite | `dashboard.web_views.DashboardSpecialiteView` | `matrix/templates/dashboard/specialite.html` |
| `demandes/` | demandes-index | `demandes.web_views.DemandesIndexView` | `matrix/templates/demandes/index.html` |
| `demandes/<int:pk>/` | demande-detail | `demandes.web_views.DemandeDetailView` | `matrix/templates/demandes/detail.html` |
| `demandes/<int:pk>/action/` | demande-action | `demandes.web_views.DemandeActionView` | — |
| `demandes/<int:pk>/commentaire/` | demande-commentaire | `demandes.web_views.DemandeCommentaireView` | — |
| `demandes/nouvelle/` | demande-nouvelle | `demandes.web_views.DemandeNouvelleView` | `matrix/templates/demandes/nouvelle.html` |
| `documentation/` | documentation-index | `documentation.web_views.BibliothequeView` | `matrix/templates/documentation/index.html` |
| `documentation/<int:pk>/` | document-detail | `documentation.web_views.DocumentDetailView` | `matrix/templates/documentation/detail.html` |
| `documentation/<int:pk>/action/` | document-action | `documentation.web_views.DocumentActionView` | — |
| `documentation/lier/` | document-lier | `documentation.web_views.DocumentLierView` | — |
| `documentation/nouveau/` | document-nouveau | `documentation.web_views.DocumentNouveauView` | `matrix/templates/documentation/nouveau.html` |
| `fiches/<int:depuis_pk>/proposer-flotte/` | fiche-flotte-depuis-bord | `assets.fiche_web.FicheFlotteAssistantView` | — |
| `fiches/<int:fiche_pk>/modifier-flotte/` | fiche-flotte-modifier | `assets.fiche_web.FicheFlotteAssistantView` | — |
| `fiches/<int:fiche_pk>/modifier/` | fiche-modifier | `assets.fiche_web.FicheAssistantView` | — |
| `fiches/<int:pk>/` | fiche-detail | `assets.fiche_web.FicheDetailView` | `matrix/templates/assets/fiche/detail.html` |
| `fiches/<int:pk>/commentaire/` | fiche-comment-create | `assets.fiche_web.FicheCommentaireView` | — |
| `fiches/<int:pk>/dupliquer/` | fiche-dupliquer | `assets.fiche_web.FicheDupliquerView` | — |
| `fiches/<int:pk>/garder/` | fiche-garder | `assets.fiche_web.FicheOrigineView` | — |
| `fiches/<int:pk>/reprendre/` | fiche-reprendre | `assets.fiche_web.FicheOrigineView` | — |
| `fiches/versions/<int:pk>/refuser/` | fiche-refuser | `assets.fiche_web.FicheRefuserView` | — |
| `fiches/versions/<int:pk>/viser/` | fiche-viser | `assets.fiche_web.FicheViserView` | — |
| `fiches/versions/<int:version_pk>/verifier/` | fiche-flotte-verifier | `assets.fiche_web.FicheFlotteAssistantView` | — |
| `formations/` | formation-list | `training.web_views.TrainingCourseListView` | `matrix/templates/training/formations.html` |
| `formations/<int:pk>/` | formation-detail | `training.web_views.FormationDetailView` | `matrix/templates/training/formation_detail.html` |
| `formations/<int:pk>/commentaire/` | formation-commentaire | `training.web_views.FormationCommentCreateView` | — |
| `formations/arbre-competences/` | formation-arbre-competences | `training.web_views.CompetencyTreeView` | `matrix/templates/training/arbre_competences.html` |
| `formations/valider/` | formation-valider | `training.web_views.ValiderFormationView` | — |
| `installations/` | installation-list | `assets.installation_views.InstallationListView` | `matrix/templates/assets/installations.html` |
| `installations/<uuid:pk>/` | installation-detail | `assets.installation_views.InstallationDetailView` | `matrix/templates/assets/installation_detail.html` |
| `installations/<uuid:pk>/commentaire/` | installation-comment-create | `assets.asset_views.InstallationCommentCreateView` | — |
| `installations/<uuid:pk>/documents/<uuid:document_pk>/supprimer/` | installation-document-supprimer | `assets.documents_installation_web.DocumentInstallationSupprimerView` | — |
| `installations/<uuid:pk>/documents/<uuid:document_pk>/telecharger/` | installation-document-telecharger | `assets.documents_installation_web.DocumentInstallationTelechargerView` | — |
| `installations/<uuid:pk>/documents/ajouter/` | installation-document-ajouter | `assets.documents_installation_web.DocumentInstallationAjouterView` | — |
| `installations/<uuid:pk>/fiches/nouvelle/` | fiche-nouvelle | `assets.fiche_web.FicheAssistantView` | — |
| `login/` | — | `django.contrib.auth.views.LoginView` | — |
| `logistics/anomalies/` | anomalie-list | `logistics.anomalie_views.AnomalieListView` | `matrix/templates/logistics/anomalie_list.html` |
| `logistics/anomalies/<int:pk>/` | anomalie-detail | `logistics.anomalie_views.AnomalieDetailView` | `matrix/templates/logistics/anomalie_detail.html` |
| `logistics/anomalies/<int:pk>/commentaire/` | anomalie-comment | `logistics.anomalie_views.AnomalieCommentView` | — |
| `logistics/anomalies/<int:pk>/convertir/` | anomalie-convertir | `logistics.anomalie_views.AnomalieConvertirView` | — |
| `logistics/anomalies/<int:pk>/statut/` | anomalie-transition | `logistics.anomalie_views.AnomalieTransitionView` | — |
| `logistics/anomalies/signaler/` | anomalie-create | `logistics.anomalie_views.AnomalieCreateView` | `matrix/templates/logistics/anomalie_form.html` |
| `logistics/part-line/<int:line_id>/status/` | part-line-status | `logistics.web_views.PartLineItemUpdateStatusView` | `matrix/templates/logistics/_part_requests.html` |
| `logistics/part-request/<int:pr_id>/line/create/` | part-line-create | `logistics.web_views.PartLineItemCreateView` | `matrix/templates/logistics/_part_requests.html` |
| `logistics/stock/` | stock-piece-list | `logistics.web_views.StockPieceListView` | `matrix/templates/logistics/stock_list.html` |
| `logistics/stock/<int:pk>/mouvements/` | stock-piece-mouvements | `logistics.mouvements_web.StockPieceMouvementsView` | `matrix/templates/logistics/stock_mouvements.html` |
| `logistics/tickets/` | ticket-list | `logistics.web_views.TicketListView` | `matrix/templates/logistics/ticket_list.html` |
| `logistics/tickets/<uuid:pk>/` | ticket-detail | `logistics.web_views.TicketDetailView` | `matrix/templates/logistics/ticket_detail.html` |
| `logistics/tickets/<uuid:pk>/assign/` | ticket-assign | `logistics.web_views.TicketAssignView` | — |
| `logistics/tickets/<uuid:pk>/commentaire/` | ticket-comment-create | `logistics.web_views.TicketCommentCreateView` | — |
| `logistics/tickets/<uuid:pk>/part-request/create/` | part-request-create | `logistics.web_views.PartRequestCreateView` | `matrix/templates/logistics/_part_requests.html` |
| `logistics/tickets/<uuid:pk>/prelever-stock/` | ticket-stock-prelevement | `logistics.web_views.TicketStockPrelevementView` | — |
| `logistics/tickets/<uuid:pk>/transition/` | ticket-transition | `logistics.web_views.TicketTransitionView` | `matrix/templates/logistics/_status.html` |
| `logistics/tickets/creer/<uuid:asset_pk>/` | ticket-create | `logistics.web_views.TicketCreateView` | — |
| `logout/` | logout | `matrix.views.logout_then_login` | — |
| `maintenance/correctifs/<uuid:ticket_pk>/compte-rendu/` | correctif-compte-rendu | `maintenance.correctif_web.CompteRenduCorrectifView` | `matrix/templates/maintenance/correctif.html` |
| `maintenance/correctifs/nouveau/` | correctif-nouveau | `maintenance.correctif_web.CompteRenduCorrectifView` | `matrix/templates/maintenance/correctif.html` |
| `maintenance/gestion/occurrences/` | maintenance-occurrences | `maintenance.web_views.MaintenanceOccurrenceListView` | `matrix/templates/maintenance/occurrence_list.html` |
| `maintenance/gestion/plans/` | maintenance-plans | `maintenance.web_views.MaintenancePlanListView` | `matrix/templates/maintenance/plan_list.html` |
| `maintenance/historique/installation/<uuid:pk>/` | historique-installation | `maintenance.historique_web.HistoriqueEquipementView` | `matrix/templates/maintenance/historique.html` |
| `maintenance/historique/materiel/<uuid:pk>/` | historique-materiel | `maintenance.historique_web.HistoriqueEquipementView` | `matrix/templates/maintenance/historique.html` |
| `maintenance/occurrences/<int:pk>/assigner/` | occurrence-self-assign | `maintenance.web_views.MaintenanceOccurrenceSelfAssignView` | — |
| `maintenance/occurrences/<int:pk>/commentaire/` | occurrence-comment-create | `maintenance.web_views.OccurrenceCommentCreateView` | — |
| `maintenance/occurrences/<int:pk>/execute/` | occurrence-execute | `maintenance.web_views.OccurrenceExecuteView` | `matrix/templates/maintenance/execute.html`, `matrix/templates/maintenance/_execute_done.html`, `matrix/templates/maintenance/_execute_erreur.html` |
| `maintenance/occurrences/<int:pk>/imprimer/` | occurrence-imprimer | `maintenance.web_views.OccurrenceImprimerView` | `matrix/templates/maintenance/fiche_imprimable.html` |
| `maintenance/occurrences/<int:pk>/signaler-fiche/` | occurrence-signaler-fiche | `maintenance.web_views.OccurrenceSignalerFicheView` | — |
| `maintenance/occurrences/imprimer/` | occurrences-imprimer | `maintenance.web_views.OccurrenceImprimerView` | `matrix/templates/maintenance/fiche_imprimable.html` |
| `maintenance/occurrences/tournee/` | tournee-saisie | `maintenance.tournee_web.TourneeSaisieView` | `matrix/templates/maintenance/tournee_saisie.html` |
| `maintenance/occurrences/tournee/imprimer/` | tournee-imprimer | `maintenance.tournee_web.TourneeImprimerView` | `matrix/templates/maintenance/fiche_tournee.html` |
| `media/<path:chemin>` | media | `matrix.core.medias.servir_media` | — |
| `notifications/` | notifications-centre | `notifications.web_views.centre` | — |
| `notifications/<int:pk>/lue/` | notifications-lue | `notifications.web_views.marquer_lue` | — |
| `notifications/centre/<int:pk>/lue/` | notifications-centre-lue | `notifications.web_views.lue_centre` | — |
| `notifications/centre/tout-lu/` | notifications-centre-tout-lu | `notifications.web_views.tout_lu_centre` | — |
| `notifications/compteur/` | notifications-compteur | `notifications.web_views.compteur` | — |
| `notifications/panneau/` | notifications-panneau | `notifications.web_views.panneau` | — |
| `notifications/tout-lu/` | notifications-tout-lu | `notifications.web_views.tout_marquer_lu` | — |
| `parametre/` | settings | `matrix.views.SettingsView` | `matrix/templates/settings/index.html` |
| `postes/` | postes-index | `postes.web_views.PostesIndexView` | `matrix/templates/postes/index.html` |
| `postes/<int:pk>/` | poste-detail | `postes.web_views.PosteDetailView` | `matrix/templates/postes/detail.html` |
| `postes/nouveau/` | poste-nouveau | `postes.web_views.PosteNouveauView` | `matrix/templates/postes/nouveau.html` |
| `programme/` | programme-index | `programme.web_views.ProgrammeIndexView` | `matrix/templates/programme/index.html` |
| `programme/<int:pk>/` | evenement-detail | `programme.web_views.EvenementDetailView` | `matrix/templates/programme/detail.html` |
| `programme/<int:pk>/action/` | evenement-action | `programme.web_views.EvenementActionView` | — |
| `programme/nouveau/` | evenement-nouveau | `programme.web_views.EvenementNouveauView` | `matrix/templates/programme/nouveau.html` |
| `programme/reglages/` | programme-reglages | `programme.web_views.ProgrammeReglagesView` | `matrix/templates/programme/reglages.html` |
| `quarts/` | quarts-index | `quarts.listes_views.ListeIndexView` | `matrix/templates/quarts/liste_index.html` |
| `quarts/creer/` | quarts-creer | `quarts.listes_views.CreerListeView` | `matrix/templates/quarts/liste_creer.html` |
| `quarts/echanges/` | echanges-index | `quarts.echanges_views.EchangesIndexView` | `matrix/templates/quarts/echanges.html` |
| `quarts/echanges/<int:pk>/<str:action>/` | echange-action | `quarts.echanges_views.EchangeActionView` | — |
| `quarts/feuille-service/` | feuille-service-index | `quarts.feuille_service_views.FeuilleServiceIndexView` | — |
| `quarts/feuille-service/<int:ship_id>/<str:date_str>/` | feuille-service-detail | `quarts.feuille_service_views.FeuilleServiceDetailView` | `matrix/templates/quarts/feuille_service_detail.html` |
| `quarts/feuille-service/alertes/` | feuille-service-alertes | `quarts.alertes_views.OrganisationAlerteView` | `matrix/templates/quarts/organisation_alerte.html` |
| `quarts/feuille-service/redacteurs/` | feuille-service-redacteurs | `quarts.feuille_service_views.FeuilleServiceRedacteursView` | `matrix/templates/quarts/feuille_service_redacteurs.html`, `matrix/templates/quarts/_redacteurs_contenu.html` |
| `quarts/feuille-service/reglages/` | feuille-service-reglages | `quarts.feuille_service_views.FeuilleServiceReglagesView` | `matrix/templates/quarts/feuille_service_reglages.html` |
| `quarts/garde/<int:pk>/` | garde-detail | `quarts.listes_views.ServiceGardeDetailView` | — |
| `quarts/garde/<int:pk>/echanges/proposer/` | echange-proposer | `quarts.echanges_views.ProposerEchangeView` | — |
| `quarts/mouvements/` | mouvements-batiment | `quarts.mouvements_views.MouvementsBatimentView` | `matrix/templates/quarts/mouvements.html` |
| `quarts/quart/<int:pk>/` | quart-detail | `quarts.listes_views.QuartDetailView` | — |
| `quarts/reglages/` | quarts-reglages | `quarts.listes_views.ChefDeListeReglagesView` | `matrix/templates/quarts/reglages.html` |
| `quarts/reglages/delais-activation/` | quarts-delais-activation | `quarts.configuration_views.DelaisActivationView` | `matrix/templates/quarts/delais_activation.html` |
| `rapports/bilan/` | rapport-bilan | `reports.web_views.GenererBilanView` | — |
| `retex/` | retex-index | `retex.web_views.RetexIndexView` | `matrix/templates/retex/index.html` |
| `retex/<int:pk>/` | retex-detail | `retex.web_views.RetexDetailView` | `matrix/templates/retex/detail.html` |
| `retex/<int:pk>/action/` | retex-action | `retex.web_views.RetexActionView` | — |
| `retex/domaines/` | retex-domaines | `retex.web_views.DomainesView` | `matrix/templates/retex/domaines.html` |
| `retex/nouveau/` | retex-nouveau | `retex.web_views.RetexNouveauView` | `matrix/templates/retex/nouveau.html` |
| `scan/<uuid:pk>/` | scan-qr | `assets.scan_views.ScanQRView` | — |
| `search/` | global-search | `matrix.views.global_search` | `matrix/templates/search.html` |
| `search/rapide/` | recherche-rapide | `matrix.views.recherche_rapide` | `matrix/templates/components/_recherche_resultats.html` |
| `service-worker.js` | service-worker | `django.views.static.serve` | — |
| `session/` | session-inactivite | `matrix.core.inactivite.SessionInactiviteView` | — |
| `styleguide/` | styleguide | `matrix.styleguide.StyleguideView` | `matrix/templates/styleguide/index.html` |
| `taches/` | taches-index | `taches.web_views.TachesIndexView` | `matrix/templates/taches/index.html` |
| `taches/<int:pk>/` | tache-detail | `taches.web_views.TacheDetailView` | `matrix/templates/taches/detail.html` |
| `taches/<int:pk>/action/` | tache-action | `taches.web_views.TacheActionView` | — |
| `taches/<int:pk>/fichier/<int:piece_pk>/` | tache-piece-jointe | `taches.web_views.TachePieceJointeView` | — |
| `taches/commentaire/<int:pk>/` | tache-commentaire | `taches.web_views.TacheCommentaireView` | — |
| `users/` | user-directory | `accounts.web_views.UserDirectoryView` | `matrix/templates/accounts/directory.html` |
| `users/<int:pk>/modifier/` | user-edit | `accounts.web_views.UserFormView` | `matrix/templates/accounts/utilisateur_form.html` |
| `users/barre-laterale/` | memoriser-barre-laterale | `accounts.web_views.MemoriserBarreLateraleView` | — |
| `users/batiment/` | choisir-batiment | `accounts.web_views.ChoisirBatimentView` | — |
| `users/nouveau/` | user-create | `accounts.web_views.UserFormView` | `matrix/templates/accounts/utilisateur_form.html` |
| `users/preferences/` | enregistrer-preference | `accounts.web_views.EnregistrerPreferenceView` | — |
| `users/profil/` | mon-profil | `accounts.web_views.MonProfilView` | `matrix/templates/accounts/profile.html` |
| `users/theme/` | basculer-theme | `accounts.web_views.BasculerThemeView` | — |

## C.2 API REST (`/api/…`)

Les routes avec suffixe de format (`.json`) et les racines d'API sont omises ; chaque ressource expose liste, détail, création, modification, suppression selon ses droits (chapitre 20).

| Chemin | Nom | Vue |
|---|---|---|
| `api/accounts/^grades/$` | gradechoice-list | `accounts.views.GradeChoiceViewSet` |
| `api/accounts/^grades/(?P<pk>[^/.]+)/$` | gradechoice-detail | `accounts.views.GradeChoiceViewSet` |
| `api/accounts/^profiles/$` | userprofile-list | `accounts.views.UserProfileViewSet` |
| `api/accounts/^profiles/(?P<pk>[^/.]+)/$` | userprofile-detail | `accounts.views.UserProfileViewSet` |
| `api/accounts/^role-availability/$` | roleavailability-list | `accounts.views.RoleAvailabilityViewSet` |
| `api/accounts/^role-availability/(?P<pk>[^/.]+)/$` | roleavailability-detail | `accounts.views.RoleAvailabilityViewSet` |
| `api/accounts/^specialities/$` | specialitychoice-list | `accounts.views.SpecialityChoiceViewSet` |
| `api/accounts/^specialities/(?P<pk>[^/.]+)/$` | specialitychoice-detail | `accounts.views.SpecialityChoiceViewSet` |
| `api/accounts/^users/$` | user-list | `accounts.views.UserViewSet` |
| `api/accounts/^users/(?P<pk>[^/.]+)/$` | user-detail | `accounts.views.UserViewSet` |
| `api/assets/^asset-checklist-overrides/$` | assetchecklistoverride-list | `assets.views.AssetChecklistOverrideViewSet` |
| `api/assets/^asset-checklist-overrides/(?P<pk>[^/.]+)/$` | assetchecklistoverride-detail | `assets.views.AssetChecklistOverrideViewSet` |
| `api/assets/^asset-docs/$` | assetdocument-list | `assets.views.AssetDocumentViewSet` |
| `api/assets/^asset-docs/(?P<pk>[^/.]+)/$` | assetdocument-detail | `assets.views.AssetDocumentViewSet` |
| `api/assets/^assets/$` | asset-list | `assets.views.AssetViewSet` |
| `api/assets/^assets/(?P<pk>[^/.]+)/$` | asset-detail | `assets.views.AssetViewSet` |
| `api/assets/^assets/(?P<pk>[^/.]+)/qr/$` | asset-qr-code | `assets.views.AssetViewSet` |
| `api/assets/^assets/(?P<pk>[^/.]+)/qr_png/$` | asset-qr-png | `assets.views.AssetViewSet` |
| `api/assets/^catalogue-articles/$` | articlecatalogue-list | `assets.views.ArticleCatalogueViewSet` |
| `api/assets/^catalogue-articles/(?P<pk>[^/.]+)/$` | articlecatalogue-detail | `assets.views.ArticleCatalogueViewSet` |
| `api/assets/^catalogue-categories/$` | categoriecatalogue-list | `assets.views.CategorieCatalogueViewSet` |
| `api/assets/^catalogue-categories/(?P<pk>[^/.]+)/$` | categoriecatalogue-detail | `assets.views.CategorieCatalogueViewSet` |
| `api/assets/^checklist-items/$` | checklistitemtemplate-list | `assets.views.ChecklistItemTemplateViewSet` |
| `api/assets/^checklist-items/(?P<pk>[^/.]+)/$` | checklistitemtemplate-detail | `assets.views.ChecklistItemTemplateViewSet` |
| `api/assets/^checklist-templates/$` | checklisttemplate-list | `assets.views.ChecklistTemplateViewSet` |
| `api/assets/^checklist-templates/(?P<pk>[^/.]+)/$` | checklisttemplate-detail | `assets.views.ChecklistTemplateViewSet` |
| `api/assets/^locations/$` | location-list | `assets.views.LocationViewSet` |
| `api/assets/^locations/(?P<pk>[^/.]+)/$` | location-detail | `assets.views.LocationViewSet` |
| `api/assets/^types/$` | assettype-list | `assets.views.AssetTypeViewSet` |
| `api/assets/^types/(?P<pk>[^/.]+)/$` | assettype-detail | `assets.views.AssetTypeViewSet` |
| `api/assets/installations/<uuid:pk>/qr/` | installation-qr | `assets.views.installation_qr_code` |
| `api/assets/installations/<uuid:pk>/qr_png/` | installation-qr-png | `assets.views.installation_qr_png` |
| `api/dashboard/corrective_open/` | — | `dashboard.views.CorrectiveOpenChartView` |
| `api/dashboard/preventive_week/` | — | `dashboard.views.PreventiveWeekChartView` |
| `api/logistics/^part-lines/$` | partlineitem-list | `logistics.views.PartLineItemViewSet` |
| `api/logistics/^part-lines/(?P<pk>[^/.]+)/$` | partlineitem-detail | `logistics.views.PartLineItemViewSet` |
| `api/logistics/^part-requests/$` | partrequest-list | `logistics.views.PartRequestViewSet` |
| `api/logistics/^part-requests/(?P<pk>[^/.]+)/$` | partrequest-detail | `logistics.views.PartRequestViewSet` |
| `api/logistics/^tickets/$` | correctiveticket-list | `logistics.views.CorrectiveTicketViewSet` |
| `api/logistics/^tickets/(?P<pk>[^/.]+)/$` | correctiveticket-detail | `logistics.views.CorrectiveTicketViewSet` |
| `api/logistics/^tickets/(?P<pk>[^/.]+)/transition/$` | correctiveticket-transition | `logistics.views.CorrectiveTicketViewSet` |
| `api/maintenance/^executions/$` | maintenanceexecution-list | `maintenance.views.MaintenanceExecutionViewSet` |
| `api/maintenance/^executions/(?P<pk>[^/.]+)/$` | maintenanceexecution-detail | `maintenance.views.MaintenanceExecutionViewSet` |
| `api/maintenance/^occurrences/$` | maintenanceoccurrence-list | `maintenance.views.MaintenanceOccurrenceViewSet` |
| `api/maintenance/^occurrences/(?P<pk>[^/.]+)/$` | maintenanceoccurrence-detail | `maintenance.views.MaintenanceOccurrenceViewSet` |
| `api/maintenance/^occurrences/(?P<pk>[^/.]+)/complete/$` | maintenanceoccurrence-complete | `maintenance.views.MaintenanceOccurrenceViewSet` |
| `api/maintenance/^occurrences/(?P<pk>[^/.]+)/start/$` | maintenanceoccurrence-start | `maintenance.views.MaintenanceOccurrenceViewSet` |
| `api/maintenance/^plans/$` | maintenanceplan-list | `maintenance.views.MaintenancePlanViewSet` |
| `api/maintenance/^plans/(?P<pk>[^/.]+)/$` | maintenanceplan-detail | `maintenance.views.MaintenancePlanViewSet` |
| `api/notifications/^notifications/$` | notification-list | `notifications.views.NotificationViewSet` |
| `api/notifications/^notifications/(?P<pk>[^/.]+)/$` | notification-detail | `notifications.views.NotificationViewSet` |
| `api/notifications/^notifications/mark_all_read/$` | notification-mark-all-read | `notifications.views.NotificationViewSet` |
| `api/notifications/push/public-key/` | push-public-key | `notifications.views.PushPublicKeyView` |
| `api/notifications/push/subscribe/` | push-subscribe | `notifications.views.PushSubscribeView` |
| `api/notifications/push/unsubscribe/` | push-unsubscribe | `notifications.views.PushUnsubscribeView` |
| `api/org/^sections/$` | section-list | `org.views.SectionViewSet` |
| `api/org/^sections/(?P<pk>[^/.]+)/$` | section-detail | `org.views.SectionViewSet` |
| `api/org/^sector-configs/$` | sectorconfig-list | `org.views.SectorConfigViewSet` |
| `api/org/^sector-configs/(?P<pk>[^/.]+)/$` | sectorconfig-detail | `org.views.SectorConfigViewSet` |
| `api/org/^sectors/$` | sector-list | `org.views.SectorViewSet` |
| `api/org/^sectors/(?P<pk>[^/.]+)/$` | sector-detail | `org.views.SectorViewSet` |
| `api/org/^services/$` | service-list | `org.views.ServiceViewSet` |
| `api/org/^services/(?P<pk>[^/.]+)/$` | service-detail | `org.views.ServiceViewSet` |
| `api/org/^ships/$` | ship-list | `org.views.ShipViewSet` |
| `api/org/^ships/(?P<pk>[^/.]+)/$` | ship-detail | `org.views.ShipViewSet` |
| `api/threads/^attachments/$` | attachment-list | `threads.views.AttachmentViewSet` |
| `api/threads/^attachments/(?P<pk>[^/.]+)/$` | attachment-detail | `threads.views.AttachmentViewSet` |
| `api/threads/^messages/$` | message-list | `threads.views.MessageViewSet` |
| `api/threads/^messages/(?P<pk>[^/.]+)/$` | message-detail | `threads.views.MessageViewSet` |
| `api/threads/^threads/$` | thread-list | `threads.views.ThreadViewSet` |
| `api/threads/^threads/(?P<pk>[^/.]+)/$` | thread-detail | `threads.views.ThreadViewSet` |
| `api/training/^courses/$` | trainingcourse-list | `training.views.TrainingCourseViewSet` |
| `api/training/^courses/(?P<pk>[^/.]+)/$` | trainingcourse-detail | `training.views.TrainingCourseViewSet` |
| `api/training/^records/$` | trainingrecord-list | `training.views.TrainingRecordViewSet` |
| `api/training/^records/(?P<pk>[^/.]+)/$` | trainingrecord-detail | `training.views.TrainingRecordViewSet` |
| `api/training/^referents/$` | referentformation-list | `training.views.ReferentFormationViewSet` |
| `api/training/^referents/(?P<pk>[^/.]+)/$` | referentformation-detail | `training.views.ReferentFormationViewSet` |
| `api/training/^requirements/$` | trainingrequirement-list | `training.views.TrainingRequirementViewSet` |
| `api/training/^requirements/(?P<pk>[^/.]+)/$` | trainingrequirement-detail | `training.views.TrainingRequirementViewSet` |
| `api/training/^sessions/$` | trainingsession-list | `training.views.TrainingSessionViewSet` |
| `api/training/^sessions/(?P<pk>[^/.]+)/$` | trainingsession-detail | `training.views.TrainingSessionViewSet` |

## C.3 Administration Django (résumé)

| Application | Routes |
|---|---|
| `(racine)` | 2 |
| `^(?P<app_label>auth|accounts|org|assets|maintenance|logistics|training|quarts|absences|taches|threads|notifications)` | 1 |
| `absences` | 6 |
| `accounts` | 12 |
| `assets` | 66 |
| `auth` | 13 |
| `autocomplete` | 1 |
| `jsi18n` | 1 |
| `login` | 1 |
| `logistics` | 30 |
| `logout` | 1 |
| `maintenance` | 24 |
| `notifications` | 12 |
| `org` | 54 |
| `password_change` | 2 |
| `quarts` | 42 |
| `r` | 1 |
| `taches` | 12 |
| `threads` | 18 |
| `training` | 66 |

Ces routes servent aux comptes techniques ; elles ne sont pas un parcours métier (chapitre 20).
