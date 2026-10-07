from django.urls import path
from .catalogue_web import (
    CatalogueView, ArticleCatalogueDetailView, CategorieEcritureView, ArticleEcritureView,
    CategorieArchiverView, ArticleArchiverView,
)
from .equipement_web import ArticleEquiperView
from .proposition_web import (
    PropositionsView, PropositionNouvelleView, PropositionDetailView, PropositionModifierView,
    PropositionViserView, PropositionRefuserView, PropositionVerifierView,
)
from .exemplaires_web import ArticleExemplairesView, ExemplairesIncompletsView
from .web_views import (
    AssetDetailView, StartVisualCheckView, AssetListView, InstallationListView,
    InstallationDetailView, ScanQRView, AssetImportView, AssetImportModeleView,
    PlanNavireListView, PlanNavireDeckView, PlanNavireVueView, PlanNavireVueDeckView,
    AssetCommentCreateView, InstallationCommentCreateView,
)

urlpatterns = [
    path('catalogue/', CatalogueView.as_view(), name='catalogue'),
    path('catalogue/categories/nouvelle/', CategorieEcritureView.as_view(), name='catalogue-categorie-nouvelle'),
    path('catalogue/categories/<uuid:pk>/modifier/', CategorieEcritureView.as_view(), name='catalogue-categorie-modifier'),
    path('catalogue/categories/<uuid:pk>/archiver/', CategorieArchiverView.as_view(), name='catalogue-categorie-archiver'),
    path('catalogue/articles/nouveau/', ArticleEcritureView.as_view(), name='catalogue-article-nouveau'),
    path('catalogue/articles/<uuid:pk>/', ArticleCatalogueDetailView.as_view(), name='catalogue-article'),
    path('catalogue/articles/<uuid:pk>/equiper/', ArticleEquiperView.as_view(), name='catalogue-article-equiper'),
    path('catalogue/articles/<uuid:pk>/exemplaires/', ArticleExemplairesView.as_view(), name='catalogue-article-exemplaires'),
    path('catalogue/exemplaires/', ExemplairesIncompletsView.as_view(), name='catalogue-exemplaires-incomplets'),
    path('catalogue/articles/<uuid:pk>/modifier/', ArticleEcritureView.as_view(), name='catalogue-article-modifier'),
    path('catalogue/articles/<uuid:pk>/archiver/', ArticleArchiverView.as_view(), name='catalogue-article-archiver'),
    path('catalogue/propositions/', PropositionsView.as_view(), name='catalogue-propositions'),
    path('catalogue/propositions/nouvelle/', PropositionNouvelleView.as_view(), name='catalogue-proposition-nouvelle'),
    path('catalogue/propositions/<uuid:pk>/', PropositionDetailView.as_view(), name='catalogue-proposition'),
    path('catalogue/propositions/<uuid:pk>/modifier/', PropositionModifierView.as_view(), name='catalogue-proposition-modifier'),
    path('catalogue/propositions/<uuid:pk>/viser/', PropositionViserView.as_view(), name='catalogue-proposition-viser'),
    path('catalogue/propositions/<uuid:pk>/refuser/', PropositionRefuserView.as_view(), name='catalogue-proposition-refuser'),
    path('catalogue/propositions/<uuid:pk>/verifier/', PropositionVerifierView.as_view(), name='catalogue-proposition-verifier'),
    path('assets/', AssetListView.as_view(), name='asset-list'),
    path('assets/importer/', AssetImportView.as_view(), name='asset-import'),
    path('assets/importer/modele/', AssetImportModeleView.as_view(), name='asset-import-modele'),
    path('assets/<uuid:pk>/', AssetDetailView.as_view(), name='asset-detail'),
    path('assets/<uuid:pk>/commentaire/', AssetCommentCreateView.as_view(), name='asset-comment-create'),
    path('assets/<uuid:pk>/start-visual/', StartVisualCheckView.as_view(), name='asset-start-visual'),
    path('installations/', InstallationListView.as_view(), name='installation-list'),
    path('installations/<uuid:pk>/', InstallationDetailView.as_view(), name='installation-detail'),
    path('installations/<uuid:pk>/commentaire/', InstallationCommentCreateView.as_view(), name='installation-comment-create'),
    # Scan QR : point d'entrée unique pour matériel mobile ET installation fixe
    # (même UUID, ScanQRView résout le bon modèle).
    path('scan/<uuid:pk>/', ScanQRView.as_view(), name='scan-qr'),
    # Plan visuel du navire : configuration des ponts et du positionnement
    # précis du matériel dessus (réservée CHEF_SERVICE+, cf.
    # PlanNavireListView/PlanNavireDeckView).
    path('assets/plan/', PlanNavireListView.as_view(), name='plan-navire-list'),
    path('assets/plan/<int:pk>/', PlanNavireDeckView.as_view(), name='plan-navire-deck'),
    # Plan visuel du navire : consultation en lecture seule, ouverte à tous les
    # rôles (cf. PlanNavireVueView/PlanNavireVueDeckView) — sous-tâche 3/3.
    path('assets/plan-navire/', PlanNavireVueView.as_view(), name='plan-navire-vue'),
    path('assets/plan-navire/<int:pk>/', PlanNavireVueDeckView.as_view(), name='plan-navire-vue-deck'),
]
