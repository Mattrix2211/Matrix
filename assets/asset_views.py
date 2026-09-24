"""Vues du matériel mobile (assets/web_views.py).

Sous-domaine extrait lors du re-découpage du fichier (tâche Notion « [ARCH]
Découper training/web_views.py et re-découper assets/web_views.py »,
assets/web_views.py ayant regrossi au-delà de 800 lignes) : fiche, liste
(avec dossiers, actions groupées) et import en masse du matériel mobile
(Asset) — symétrique à assets/installation_views.py pour les installations
fixes.

Refactor pur : reproduit exactement le comportement d'origine. Les quelques
helpers restés partagés avec les installations (rattachement parent,
périmètre organisationnel, emplacement, actions groupées...) restent définis
dans assets/web_views.py et sont importés ici — voir la docstring de ce
dernier fichier pour l'explication de l'import circulaire volontaire, déjà
en place pour assets/installation_actions.py avant ce découpage."""
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import models
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.views.generic import DetailView, ListView, View

from accounts.models import AuditLog
from logistics.models import CorrectiveTicket, StockPiece
from matrix.core.export import (
    CSV_CONTENT_TYPE,
    XLSX_CONTENT_TYPE,
    construire_url_export,
    rendre_csv,
    rendre_xlsx,
    reponse_fichier,
    xlsx_disponible,
)
from matrix.core.mixins import ScopedQuerySetMixin
from matrix.core.role_thresholds import niveau_requis_pour
from matrix.core.roles import RoleLevel, user_role_level
from matrix.core.scopes import scope_filters_for_user
from matrix.core.validators import message_erreur_fichier, valider_document, valider_photo
from org.models import Section, Sector, Service, Ship

from .import_materiel import generer_modele_xlsx, importer_materiel_depuis_fichier
from .models import Asset, AssetDocument, AssetFolder, AssetType, Location
from .web_views import (
    _afficher_erreur_validation,
    _appliquer_bulk_suppression,
    _appliquer_bulk_update,
    _org_dans_perimetre,
    _perimetre_utilisateur,
    _peut_gerer_rattachement_parent,
    _resoudre_emplacement,
    _resoudre_parent_valide,
)

_ENTETES_EXPORT_ASSETS = [
    'Désignation', 'Type', 'Identifiant interne', 'N° série', 'Statut', 'Criticité',
    'Unité', 'Service', 'Secteur', 'Section', 'Emplacement',
]


def _lignes_export_assets(qs):
    """Construit les lignes de l'export tableur des matériels, à partir d'un
    queryset déjà filtré par périmètre (voir AssetListView.get)."""
    return [
        [
            a.designation,
            a.asset_type.name,
            a.internal_id,
            a.serial_number,
            a.get_status_display(),
            a.criticality,
            a.ship.name if a.ship else '',
            a.service.name if a.service else '',
            a.sector.name if a.sector else '',
            a.section.name if a.section else '',
            a.location.name if a.location else '',
        ]
        for a in qs
    ]


def _peut_gerer_materiel(user):
    """Seuil d'accès à l'import en masse de matériel (AssetImportView,
    AssetImportModeleView) : CHEF_SECTION et au-dessus, en dur — usage isolé et
    volontairement non migré vers le registre configurable ACTION_VERS_SEUIL
    (fonctionnalité annexe, pas une action de création/édition/suppression
    couverte par ce registre). Ne plus utiliser cette fonction pour les actions
    déjà migrées de AssetListView.post()/InstallationListView.post()
    (create_folder, create_asset, create_installation, etc.) : le contrôle en
    tête de post() via ACTION_VERS_SEUIL/niveau_requis_pour suffit désormais et
    rend le seuil configurable par navire (bug corrigé après refus du Tech
    Lead : un doublon avec ce seuil codé en dur rendait la configuration sans
    effet réel sur ces actions)."""
    return user_role_level(user) >= RoleLevel.CHEF_SECTION


def _redirect_liste_materiel(request):
    """Redirige vers la liste des matériels en conservant le dossier actuellement
    parcouru (paramètre ?folder=), qui figure déjà dans l'URL courante puisque les
    formulaires de la page n'ont pas d'attribut action. Sans cela, toute création,
    modification ou suppression ramenait systématiquement l'utilisateur à la racine
    et donnait l'impression qu'un matériel ajouté dans un sous-dossier n'y apparaissait
    jamais (bug d'affichage corrigé ici)."""
    folder_id = request.GET.get('folder') or request.POST.get('folder_id')
    if folder_id:
        return redirect(f"/assets/?folder={folder_id}")
    return redirect('asset-list')


class AssetDetailView(LoginRequiredMixin, ScopedQuerySetMixin, DetailView):
    # Périmètre : même principe que InstallationDetailView (déjà scopée) — sans
    # ScopedQuerySetMixin, un utilisateur connaissant l'UUID d'un matériel hors de
    # son périmètre (ex. deviné, retrouvé dans un lien) pouvait consulter sa fiche
    # complète malgré l'absence de tout lien y menant depuis la liste (déjà
    # filtrée, elle). Un matériel hors périmètre est désormais traité comme
    # introuvable (404), pas de nouveau contrôle d'accès (T-SEC).
    model = Asset
    template_name = 'assets/detail.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        # Recherche « pannes déjà rencontrées » (REX) : volontairement tous navires
        # confondus, sans filtre de périmètre (scope_filters_for_user), contrairement
        # à toutes les autres requêtes de l'application. Choix assumé, cohérent avec
        # la portabilité déjà pratiquée pour les formations entre bâtiments : un
        # même type d'équipement peut tomber en panne de la même façon sur un autre
        # navire, et cet historique de diagnostic/solution est utile à tout le
        # monde, même hors du périmètre habituel de l'utilisateur.
        # On compare par (nom, catégorie) et non par asset_type_id : AssetType est
        # rattaché à un Sector (unique_together sector+name), donc chaque navire a
        # sa propre ligne AssetType même pour un équipement identique — comparer
        # les clés étrangères ne trouverait jamais de correspondance entre navires.
        ctx['pannes_deja_rencontrees'] = (
            CorrectiveTicket.objects.filter(
                status='CLOSED',
                asset__asset_type__name=self.object.asset_type.name,
                asset__asset_type__category=self.object.asset_type.category,
            )
            .exclude(diagnostic_final='', solution='')
            .select_related('asset', 'asset__ship')
            .order_by('-reported_at')[:20]
        )
        # Pièces de stock affiliées (T-FEAT stock détaillé) : lien optionnel côté
        # StockPiece (logistics), affiché ici en lecture seule, la gestion du stock
        # se faisant depuis /logistics/stock/.
        ctx['pieces_stock'] = StockPiece.objects.filter(asset=self.object).order_by('reference')
        return ctx


class AssetImportView(LoginRequiredMixin, View):
    """Import en masse de matériel mobile depuis un fichier Excel (Phase 6) :
    upload direct, création ligne par ligne dans le périmètre de l'utilisateur
    connecté, avec rapport d'erreurs clair si certaines lignes échouent — sans
    bloquer les autres lignes valides du même fichier (import atomique par
    ligne, cf. assets/import_materiel.py). Même seuil de rôle que la création
    manuelle d'un matériel (_peut_gerer_materiel)."""
    template_name = 'assets/import.html'

    def get(self, request):
        if not _peut_gerer_materiel(request.user):
            raise PermissionDenied
        return render(request, self.template_name, {})

    def post(self, request):
        if not _peut_gerer_materiel(request.user):
            raise PermissionDenied
        fichier = request.FILES.get('fichier')
        if not fichier:
            messages.error(request, "Sélectionnez un fichier Excel (.xlsx) à importer.")
            return render(request, self.template_name, {})
        resultat = importer_materiel_depuis_fichier(fichier, request.user)
        if resultat.crees:
            messages.success(request, f"{resultat.crees} matériel(s) importé(s) avec succès.")
        return render(request, self.template_name, {'resultat': resultat})


class AssetImportModeleView(LoginRequiredMixin, View):
    """Téléchargement du modèle Excel documentant les colonnes attendues pour
    l'import en masse de matériel (voir AssetImportView)."""

    def get(self, request):
        if not _peut_gerer_materiel(request.user):
            raise PermissionDenied
        contenu = generer_modele_xlsx()
        if contenu is None:
            messages.error(request, "La génération du modèle Excel n'est pas disponible sur ce serveur.")
            return redirect('asset-import')
        return reponse_fichier(contenu, 'modele_import_materiel.xlsx', XLSX_CONTENT_TYPE)


class AssetListView(LoginRequiredMixin, ScopedQuerySetMixin, ListView):
    model = Asset
    template_name = 'assets/list.html'
    context_object_name = 'assets'

    # Contrôle de rôle par action (T-SEC) : chaque action POST est associée à
    # une clé du registre des seuils configurables par navire
    # (matrix/core/role_thresholds.py), résolue dynamiquement à chaque
    # requête dans post() ci-dessous — asset_ecriture_simple pour la
    # création simple (CHEF_SECTION par défaut ; l'édition passe par la fiche détail), asset_gestion_avancee
    # pour les suppressions et les actions groupées (CHEF_SERVICE par défaut,
    # même seuil que MAINTENANCE_WRITE_ACTIONS d'InstallationDetailView et
    # _peut_gerer_rattachement_parent, pour rester cohérent avec le reste du
    # fichier).
    ACTION_VERS_SEUIL = {
        'create_folder': 'asset_ecriture_simple',
        'rename_folder': 'asset_ecriture_simple',
        'delete_folder': 'asset_gestion_avancee',
        'move_asset_to_folder': 'asset_ecriture_simple',
        'create_asset': 'asset_ecriture_simple',
        'edit_asset': 'asset_ecriture_simple',
        'delete_asset': 'asset_gestion_avancee',
        'delete_asset_document': 'asset_gestion_avancee',
        'bulk_update_status': 'asset_gestion_avancee',
        'bulk_update_location': 'asset_gestion_avancee',
        'bulk_update_ship': 'asset_gestion_avancee',
        'bulk_update_service': 'asset_gestion_avancee',
        'bulk_update_sector': 'asset_gestion_avancee',
        'bulk_update_section': 'asset_gestion_avancee',
        'bulk_delete_assets': 'asset_gestion_avancee',
    }

    def get_queryset(self):
        # Périmètre appliqué par ScopedQuerySetMixin (même système que l'API) avant les
        # filtres de recherche/tri propres à cette vue. prefetch_related('documents') :
        # la liste affiche les pièces jointes de chaque matériel
        # (matrix/templates/assets/list.html) — sans cela, une requête AssetDocument
        # est exécutée par matériel affiché (N+1).
        qs = super().get_queryset().select_related('asset_type', 'ship', 'service', 'sector', 'section', 'location', 'folder').prefetch_related('documents').order_by('ship__name', 'service__name', 'sector__name', 'section__name', 'asset_type__name')
        ship_id = self.request.GET.get('ship')
        service_id = self.request.GET.get('service')
        sector_id = self.request.GET.get('sector')
        section_id = self.request.GET.get('section')
        status = self.request.GET.get('status')
        asset_type_id = self.request.GET.get('type')
        folder_id = self.request.GET.get('folder')
        # Filtre par emplacement (Location) : utilisé notamment par le clic sur
        # une zone du plan visuel du navire (PlanNavireVueDeckView), qui renvoie
        # ici avec ?location=<id> plutôt que d'ouvrir un nouvel écran de liste.
        location_id = self.request.GET.get('location')
        q = self.request.GET.get('q', '').strip()
        if ship_id:
            qs = qs.filter(ship_id=ship_id)
        if service_id:
            qs = qs.filter(service_id=service_id)
        if sector_id:
            qs = qs.filter(sector_id=sector_id)
        if section_id:
            qs = qs.filter(section_id=section_id)
        if status:
            qs = qs.filter(status=status)
        if asset_type_id:
            qs = qs.filter(asset_type_id=asset_type_id)
        if location_id:
            qs = qs.filter(location_id=location_id)
        if folder_id:
            qs = qs.filter(folder_id=folder_id)
        elif not q and not location_id:
            # Vue racine (aucun dossier sélectionné, pas de recherche globale, pas
            # de filtre par emplacement) : n'affiche que les matériels non classés
            # dans un dossier, symétrique au filtrage déjà appliqué aux dossiers
            # eux-mêmes (parent__isnull=True) plus bas. Sans ce filtre, un matériel
            # rangé dans un sous-dossier se retrouvait mélangé à la racine et ne
            # semblait jamais "rangé" dans son dossier. Le filtre par emplacement
            # doit au contraire remonter tout le matériel de la zone, quel que
            # soit le dossier dans lequel il est classé.
            qs = qs.filter(folder__isnull=True)
        if q:
            qs = qs.filter(
                models.Q(serial_number__icontains=q) |
                models.Q(internal_id__icontains=q) |
                models.Q(asset_type__name__icontains=q) |
                models.Q(designation__icontains=q) |
                models.Q(nno__icontains=q) |
                models.Q(reference__icontains=q) |
                models.Q(marque__icontains=q) |
                models.Q(gisement__icontains=q)
            )
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['ships'] = Ship.objects.order_by('name')
        ctx['services'] = Service.objects.select_related('ship').order_by('name')
        ctx['sectors'] = Sector.objects.select_related('service', 'service__ship').order_by('name')
        ctx['sections'] = Section.objects.select_related('sector', 'sector__service', 'sector__service__ship').order_by('name')
        ctx['types'] = AssetType.objects.order_by('name')
        ctx['locations'] = Location.objects.select_related('ship').order_by('ship__name', 'name')
        # Emplacement actif du filtre ?location=, affiché en bandeau (cf. list.html)
        # pour que l'utilisateur venant du plan visuel du navire comprenne pourquoi
        # la liste est restreinte, avec un lien pour revenir à la vue complète.
        location_id = self.request.GET.get('location')
        ctx['filtre_location'] = Location.objects.filter(pk=location_id).first() if location_id else None
        ctx['export_url_csv'] = construire_url_export(self.request, 'csv')
        ctx['export_url_xlsx'] = construire_url_export(self.request, 'xlsx')
        ctx['xlsx_disponible'] = xlsx_disponible()
        # Rattachement parent (T3) : réservé aux CHEF_SERVICE et au-dessus, filtré
        # côté client par secteur (data-sector) pour éviter un rattachement cross-navire.
        ctx['peut_gerer_parent'] = _peut_gerer_rattachement_parent(self.request.user)
        ctx['assets_pour_parent'] = (
            Asset.objects.select_related('sector', 'asset_type').order_by('designation')
            if ctx['peut_gerer_parent'] else Asset.objects.none()
        )
        # Pré-remplissage du périmètre (navire/service/secteur/section) du formulaire
        # de création à partir du profil du chef connecté.
        ctx.update(_perimetre_utilisateur(self.request.user))
        # Navigation par dossiers
        current_folder_id = self.request.GET.get('folder')
        current_folder = AssetFolder.objects.filter(pk=current_folder_id).select_related('parent').first() if current_folder_id else None
        ctx['current_folder'] = current_folder
        if current_folder:
            ctx['folders'] = AssetFolder.objects.filter(parent=current_folder).order_by('name').select_related('parent')
        else:
            ctx['folders'] = AssetFolder.objects.filter(parent__isnull=True).order_by('name').select_related('parent')
        # Fil d'Ariane (du racine vers courant)
        breadcrumbs = []
        f = current_folder
        while f is not None:
            breadcrumbs.append(f)
            f = f.parent
        breadcrumbs.reverse()
        ctx['folder_breadcrumbs'] = breadcrumbs
        return ctx

    def get(self, request, *args, **kwargs):
        format_export = request.GET.get('export')
        if format_export in ('csv', 'xlsx'):
            # Périmètre : l'export ne doit JAMAIS dépasser le périmètre de
            # l'utilisateur, même si l'affichage de cette liste n'est pas
            # lui-même restreint par périmètre (elle propose des filtres
            # navire/service/secteur/section manuels, cf. get_queryset ci-dessus,
            # destinés à un usage de gestion transverse) — sécurité appliquée
            # explicitement ici, indépendamment de get_queryset().
            qs = self.get_queryset().filter(**scope_filters_for_user(request.user))
            lignes = _lignes_export_assets(qs)
            if format_export == 'xlsx':
                contenu = rendre_xlsx(_ENTETES_EXPORT_ASSETS, lignes, titre_feuille='Matériels')
                if contenu is None:
                    messages.error(
                        request,
                        "L'export Excel n'est pas disponible sur ce serveur. Utilisez le CSV.",
                    )
                    parametres = request.GET.copy()
                    parametres.pop('export', None)
                    return redirect(f"{request.path}?{parametres.urlencode()}")
                content_type = XLSX_CONTENT_TYPE
            else:
                contenu = rendre_csv(_ENTETES_EXPORT_ASSETS, lignes)
                content_type = CSV_CONTENT_TYPE
            AuditLog.objects.create(
                actor=request.user, action=f'export_assets_{format_export}',
                target_user=None, details=f'rows={len(lignes)}',
            )
            return reponse_fichier(contenu, f'materiels.{format_export}', content_type)
        return super().get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        action = request.POST.get('action')
        cle_seuil = self.ACTION_VERS_SEUIL.get(action)
        if cle_seuil is not None and user_role_level(request.user) < niveau_requis_pour(request.user, cle_seuil):
            raise PermissionDenied
        # Bulk actions
        if action in (
            'bulk_update_status', 'bulk_update_location', 'bulk_update_ship',
            'bulk_update_service', 'bulk_update_sector', 'bulk_update_section',
            'bulk_delete_assets'
        ):
            ids = request.POST.getlist('selected_ids')
            # Périmètre : seuls les matériels du périmètre de l'appelant sont chargés
            # (self.get_queryset(), scopé via ScopedQuerySetMixin) — un identifiant posté
            # hors périmètre est simplement ignoré, comme s'il n'existait pas.
            assets = self.get_queryset().filter(id__in=ids)
            if action == 'bulk_update_status':
                status = request.POST.get('status')
                return _appliquer_bulk_update(
                    request, assets, 'status', status,
                    action_audit='bulk_update_asset_status', detail_audit=f'status={status}',
                    message_succes='Statut mis à jour pour {count} matériel(s).',
                    redirect_url_name='asset-list',
                )
            elif action == 'bulk_update_location':
                loc_id = request.POST.get('location_id')
                loc = Location.objects.filter(pk=loc_id).first()
                return _appliquer_bulk_update(
                    request, assets, 'location', loc,
                    action_audit='bulk_update_asset_location', detail_audit=f'location_id={loc_id}',
                    message_succes='Emplacement mis à jour pour {count} matériel(s).',
                    redirect_url_name='asset-list',
                )
            elif action == 'bulk_update_ship':
                ship_id = request.POST.get('ship_id')
                return _appliquer_bulk_update(
                    request, assets, 'ship', Ship.objects.filter(pk=ship_id).first(),
                    action_audit='bulk_update_asset_ship', detail_audit=f'ship_id={ship_id}',
                    message_succes='Unité mise à jour pour {count} matériel(s).',
                    redirect_url_name='asset-list',
                    org_model=Ship, org_id=ship_id, libelle_org='Unité',
                )
            elif action == 'bulk_update_service':
                service_id = request.POST.get('service_id')
                return _appliquer_bulk_update(
                    request, assets, 'service', Service.objects.filter(pk=service_id).first(),
                    action_audit='bulk_update_asset_service', detail_audit=f'service_id={service_id}',
                    message_succes='Service mis à jour pour {count} matériel(s).',
                    redirect_url_name='asset-list',
                    org_model=Service, org_id=service_id, libelle_org='Service',
                )
            elif action == 'bulk_update_sector':
                sector_id = request.POST.get('sector_id')
                return _appliquer_bulk_update(
                    request, assets, 'sector', Sector.objects.filter(pk=sector_id).first(),
                    action_audit='bulk_update_asset_sector', detail_audit=f'sector_id={sector_id}',
                    message_succes='Secteur mis à jour pour {count} matériel(s).',
                    redirect_url_name='asset-list',
                    org_model=Sector, org_id=sector_id, libelle_org='Secteur',
                )
            elif action == 'bulk_update_section':
                section_id = request.POST.get('section_id')
                return _appliquer_bulk_update(
                    request, assets, 'section', Section.objects.filter(pk=section_id).first(),
                    action_audit='bulk_update_asset_section', detail_audit=f'section_id={section_id}',
                    message_succes='Section mise à jour pour {count} matériel(s).',
                    redirect_url_name='asset-list',
                    org_model=Section, org_id=section_id, libelle_org='Section',
                )
            elif action == 'bulk_delete_assets':
                return _appliquer_bulk_suppression(
                    request, assets,
                    action_audit='bulk_delete_asset',
                    message_succes='{count} matériel(s) supprimé(s).',
                    redirect_url_name='asset-list',
                )

        # Folder operations
        if action == 'create_folder':
            # Création d'un dossier : seuil déjà vérifié en tête de post() via
            # ACTION_VERS_SEUIL['create_folder'] = 'asset_ecriture_simple'
            # (configurable par navire) — ne pas dupliquer le contrôle avec
            # _peut_gerer_materiel, sous peine de rendre la configuration sans
            # effet réel sur cette action (bug corrigé après refus du Tech Lead).
            name = request.POST.get('name', '').strip()
            parent_id = request.POST.get('parent_id')
            parent = AssetFolder.objects.filter(pk=parent_id).first() if parent_id else None
            if name:
                photo = request.FILES.get('photo')
                erreur_photo = message_erreur_fichier(photo, valider_photo)
                if erreur_photo:
                    messages.error(request, erreur_photo)
                    return _redirect_liste_materiel(request)
                fld = AssetFolder.objects.create(name=name)
                if photo:
                    fld.photo = photo
                    fld.save(update_fields=['photo'])
                if parent:
                    fld.parent = parent
                    fld.save(update_fields=['parent'])
                messages.success(request, 'Dossier créé.')
                AuditLog.objects.create(actor=request.user, action='create_asset_folder', details=f'name={name}')
            return _redirect_liste_materiel(request)
        if action == 'rename_folder':
            pk = request.POST.get('pk')
            name = request.POST.get('name', '').strip()
            try:
                fld = AssetFolder.objects.get(pk=pk)
                if name:
                    fld.name = name
                    fld.save(update_fields=['name'])
                    AuditLog.objects.create(actor=request.user, action='rename_asset_folder', details=f'id={pk}; name={name}')
                    messages.success(request, 'Dossier renommé.')
            except AssetFolder.DoesNotExist:
                messages.error(request, 'Dossier introuvable.')
            return _redirect_liste_materiel(request)
        if action == 'delete_folder':
            pk = request.POST.get('pk')
            AssetFolder.objects.filter(pk=pk).delete()
            AuditLog.objects.create(actor=request.user, action='delete_asset_folder', details=f'id={pk}')
            messages.success(request, 'Dossier supprimé.')
            return _redirect_liste_materiel(request)
        if action == 'move_asset_to_folder':
            asset_id = request.POST.get('asset_id')
            folder_id = request.POST.get('folder_id')
            try:
                a = self.get_queryset().get(pk=asset_id)
                a.folder = AssetFolder.objects.filter(pk=folder_id).first() if folder_id else None
                a.save(update_fields=['folder'])
                return JsonResponse({'ok': True})
            except Asset.DoesNotExist:
                return JsonResponse({'ok': False}, status=400)

        # Single create/edit/delete
        if action == 'create_asset':
            # Création d'un matériel : seuil déjà vérifié en tête de post() via
            # ACTION_VERS_SEUIL['create_asset'] = 'asset_ecriture_simple'
            # (configurable par navire) — ne pas dupliquer le contrôle avec
            # _peut_gerer_materiel, sous peine de rendre la configuration sans
            # effet réel sur cette action (bug corrigé après refus du Tech Lead).
            # L'édition et la suppression restent volontairement ouvertes à tous les
            # utilisateurs connectés (comportement existant, cf. tests T2/T3).
            type_id = request.POST.get('asset_type_id')
            internal_id = request.POST.get('internal_id', '').strip()
            serial = request.POST.get('serial_number', '').strip()
            designation = request.POST.get('designation', '').strip()
            nno = request.POST.get('nno', '').strip()
            reference = request.POST.get('reference', '').strip()
            marque = request.POST.get('marque', '').strip()
            gisement = request.POST.get('gisement', '').strip()
            local = request.POST.get('local', '').strip()
            status = request.POST.get('status') or 'OK'
            criticality = int(request.POST.get('criticality') or 1)
            ship_id = request.POST.get('ship_id')
            service_id = request.POST.get('service_id')
            sector_id = request.POST.get('sector_id')
            section_id = request.POST.get('section_id')
            folder_id = request.POST.get('folder_id') or self.request.GET.get('folder')
            # Périmètre (T-SEC) : le navire/service/secteur/section posté doit appartenir
            # au périmètre de l'appelant, même principe que _resoudre_parent_valide pour
            # le champ parent_id — ne fait pas confiance aux menus déroulants du formulaire.
            if ship_id and not _org_dans_perimetre(request.user, Ship, ship_id):
                messages.error(request, "Unité hors de votre périmètre.")
                return redirect('asset-list')
            if service_id and not _org_dans_perimetre(request.user, Service, service_id):
                messages.error(request, "Service hors de votre périmètre.")
                return redirect('asset-list')
            if sector_id and not _org_dans_perimetre(request.user, Sector, sector_id):
                messages.error(request, "Secteur hors de votre périmètre.")
                return redirect('asset-list')
            if section_id and not _org_dans_perimetre(request.user, Section, section_id):
                messages.error(request, "Section hors de votre périmètre.")
                return redirect('asset-list')
            # Fallback côté serveur pour type si non fourni: premier type du secteur
            if not type_id and sector_id:
                try:
                    at_fb = AssetType.objects.filter(sector_id=sector_id).order_by('name').first()
                    if at_fb:
                        type_id = at_fb.id
                except Exception:
                    pass
            try:
                if not type_id:
                    messages.error(request, "Aucun type disponible pour le secteur sélectionné.")
                    return _redirect_liste_materiel(request)
                at = AssetType.objects.get(pk=type_id)
                asset = Asset(
                    asset_type=at,
                    internal_id=internal_id,
                    serial_number=serial,
                    designation=designation,
                    nno=nno,
                    reference=reference,
                    marque=marque,
                    gisement=gisement,
                    local=local,
                    status=status,
                    criticality=criticality,
                )
                photo = request.FILES.get('photo')
                if photo:
                    asset.photo = photo
                if ship_id:
                    asset.ship = Ship.objects.filter(pk=ship_id).first()
                if service_id:
                    asset.service = Service.objects.filter(pk=service_id).first()
                if sector_id:
                    asset.sector = Sector.objects.filter(pk=sector_id).first()
                if section_id:
                    asset.section = Section.objects.filter(pk=section_id).first()
                asset.location = _resoudre_emplacement(request, asset.ship)
                erreur_parent = _resoudre_parent_valide(request, asset, Asset)
                if erreur_parent:
                    messages.error(request, erreur_parent)
                    return _redirect_liste_materiel(request)
                try:
                    asset.full_clean()
                except ValidationError as exc:
                    _afficher_erreur_validation(request, exc)
                    return _redirect_liste_materiel(request)
                asset.save()
                # Associer au dossier courant si présent
                if folder_id:
                    try:
                        asset.folder = AssetFolder.objects.filter(pk=folder_id).first()
                        asset.save(update_fields=['folder'])
                    except Exception:
                        pass
                # Documents ajoutés lors de la création
                for f in request.FILES.getlist('documents'):
                    erreur_document = message_erreur_fichier(f, valider_document)
                    if erreur_document:
                        messages.error(request, f"{getattr(f, 'name', 'document')} : {erreur_document}")
                        continue
                    AssetDocument.objects.create(asset=asset, file=f, name=getattr(f, 'name', '') or '')
                AuditLog.objects.create(actor=request.user, action='create_asset', details=f'type_id={type_id}; internal_id={internal_id}')
                messages.success(request, 'Matériel créé.')
            except AssetType.DoesNotExist:
                messages.error(request, 'Type de matériel introuvable.')
        elif action == 'edit_asset':
            pk = request.POST.get('pk')
            ship_id = request.POST.get('ship_id')
            service_id = request.POST.get('service_id')
            sector_id = request.POST.get('sector_id')
            section_id = request.POST.get('section_id')
            # Périmètre (T-SEC) : même contrôle qu'à la création, contre un POST direct
            # qui déplacerait le matériel hors du périmètre de l'appelant.
            if ship_id and not _org_dans_perimetre(request.user, Ship, ship_id):
                messages.error(request, "Unité hors de votre périmètre.")
                return redirect('asset-list')
            if service_id and not _org_dans_perimetre(request.user, Service, service_id):
                messages.error(request, "Service hors de votre périmètre.")
                return redirect('asset-list')
            if sector_id and not _org_dans_perimetre(request.user, Sector, sector_id):
                messages.error(request, "Secteur hors de votre périmètre.")
                return redirect('asset-list')
            if section_id and not _org_dans_perimetre(request.user, Section, section_id):
                messages.error(request, "Section hors de votre périmètre.")
                return redirect('asset-list')
            try:
                # Périmètre : le matériel visé doit appartenir au périmètre de l'appelant
                # (self.get_queryset(), scopé) — un identifiant hors périmètre est traité
                # comme introuvable plutôt que d'être chargé via le manager brut.
                asset = self.get_queryset().get(pk=pk)
                asset.internal_id = request.POST.get('internal_id', asset.internal_id).strip()
                asset.serial_number = request.POST.get('serial_number', asset.serial_number).strip()
                asset.designation = request.POST.get('designation', asset.designation).strip()
                asset.nno = request.POST.get('nno', asset.nno).strip()
                asset.reference = request.POST.get('reference', asset.reference).strip()
                asset.marque = request.POST.get('marque', asset.marque).strip()
                asset.gisement = request.POST.get('gisement', asset.gisement).strip()
                asset.local = request.POST.get('local', asset.local).strip()
                asset.status = request.POST.get('status', asset.status)
                asset.criticality = int(request.POST.get('criticality') or asset.criticality)
                type_id = request.POST.get('asset_type_id')
                if type_id:
                    try:
                        asset.asset_type = AssetType.objects.get(pk=type_id)
                    except AssetType.DoesNotExist:
                        pass
                photo = request.FILES.get('photo')
                if photo:
                    asset.photo = photo
                asset.ship = Ship.objects.filter(pk=ship_id).first() if ship_id else None
                asset.service = Service.objects.filter(pk=service_id).first() if service_id else None
                asset.sector = Sector.objects.filter(pk=sector_id).first() if sector_id else None
                asset.section = Section.objects.filter(pk=section_id).first() if section_id else None
                asset.location = _resoudre_emplacement(request, asset.ship)
                erreur_parent = _resoudre_parent_valide(request, asset, Asset)
                if erreur_parent:
                    messages.error(request, erreur_parent)
                    return _redirect_liste_materiel(request)
                try:
                    asset.full_clean()
                except ValidationError as exc:
                    _afficher_erreur_validation(request, exc)
                    return _redirect_liste_materiel(request)
                asset.save()
                # Ajout de nouveaux documents pendant la modification
                for f in request.FILES.getlist('documents'):
                    erreur_document = message_erreur_fichier(f, valider_document)
                    if erreur_document:
                        messages.error(request, f"{getattr(f, 'name', 'document')} : {erreur_document}")
                        continue
                    AssetDocument.objects.create(asset=asset, file=f, name=getattr(f, 'name', '') or '')
                AuditLog.objects.create(actor=request.user, action='edit_asset', details=f'id={asset.id}')
                messages.success(request, 'Matériel mis à jour.')
            except Asset.DoesNotExist:
                messages.error(request, 'Matériel introuvable.')
        elif action == 'delete_asset':
            pk = request.POST.get('pk')
            # Périmètre : un matériel hors périmètre est traité comme introuvable.
            supprimes = self.get_queryset().filter(pk=pk).delete()[0]
            if supprimes:
                messages.success(request, 'Matériel supprimé.')
            else:
                messages.error(request, 'Matériel introuvable.')
        elif action == 'delete_asset_document':
            pk = request.POST.get('pk')
            doc_id = request.POST.get('document_id')
            try:
                asset = self.get_queryset().get(pk=pk)
                AssetDocument.objects.filter(pk=doc_id, asset=asset).delete()
                messages.success(request, 'Document supprimé.')
            except Asset.DoesNotExist:
                messages.error(request, 'Matériel introuvable.')
        return _redirect_liste_materiel(request)
