from django.views.generic import DetailView, View, ListView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied, ValidationError
from django.shortcuts import redirect, render, get_object_or_404
from django.urls import reverse
from django.utils import timezone
from django.views.generic import TemplateView
from django.http import JsonResponse, HttpResponseBadRequest, HttpResponse
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.db.utils import OperationalError
from django.db.models import Max, Sum
from django.db.models.functions import TruncMonth
from django.db import models
from collections import defaultdict
from .models import Asset, AssetType, Deck, Location, Installation, AssetFolder, InstallationExtraField, AssetDocument, Zone
from .models import InstallationBigrameChoice, InstallationEvent, InstallationPart, InstallationHourReading, InstallationVibrationReading, InstallationIsolationReading
from .models import InstallationMaintenance
from datetime import datetime
from datetime import timedelta
from maintenance.models import MaintenanceOccurrence, MaintenancePlan
from logistics.models import CorrectiveTicket, StockPiece
from .trend import jours_avant_franchissement_seuil
from matrix.core.roles import user_role_level, RoleLevel
from matrix.core.mixins import ScopedQuerySetMixin
from matrix.core.scopes import scope_filters_for_user, is_master_admin, ship_id_for_user
from matrix.core.export import (
    CSV_CONTENT_TYPE,
    XLSX_CONTENT_TYPE,
    construire_url_export,
    rendre_csv,
    rendre_xlsx,
    reponse_fichier,
    xlsx_disponible,
)
from accounts.models import AuditLog
from org.models import Ship, Service, Sector, Section
from .import_materiel import importer_materiel_depuis_fichier, generer_modele_xlsx

# Statuts d'occurrence considérés comme terminés pour le scan QR : une occurrence
# déjà DONE ou CANCELLED ne doit plus être proposée au marin qui scanne
# l'équipement (même logique que dashboard/web_views.py, symbole privé non
# réimporté ici puisqu'il appartient à un autre module).
_STATUTS_OCCURRENCE_TERMINES = ("DONE", "CANCELLED")
import json
import calendar


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


_ENTETES_EXPORT_INSTALLATIONS = [
    'Désignation', 'Référence', 'Marque', 'Gisement', 'Local',
    'Unité', 'Service', 'Secteur', 'Section', 'Emplacement',
]


def _lignes_export_installations(qs):
    """Construit les lignes de l'export tableur des installations, à partir d'un
    queryset déjà filtré par périmètre (voir InstallationListView.get)."""
    return [
        [
            i.designation,
            i.reference,
            i.marque,
            i.gisement,
            i.local,
            i.ship.name if i.ship else '',
            i.service.name if i.service else '',
            i.sector.name if i.sector else '',
            i.section.name if i.section else '',
            i.location.name if i.location else '',
        ]
        for i in qs
    ]


def _peut_gerer_rattachement_parent(user):
    """Seuls les CHEF_SERVICE et rôles supérieurs peuvent créer ou modifier le
    rattachement parent/enfant d'une installation ou d'un matériel (même seuil
    que les tâches d'entretien, cf. MAINTENANCE_WRITE_ACTIONS ci-dessous)."""
    return user_role_level(user) >= RoleLevel.CHEF_SERVICE


def _peut_configurer_plan_navire(user):
    """Seuls les CHEF_SERVICE et rôles supérieurs peuvent configurer les ponts
    et zones du plan visuel du navire (même seuil que la gestion du
    rattachement parent/enfant et des tâches d'entretien ci-dessus : une
    action de configuration structurante, pas une simple consultation)."""
    return user_role_level(user) >= RoleLevel.CHEF_SERVICE


def _dernier_par_installation(queryset, champ_installation='installation_id'):
    """Retourne {installation_id: dernier enregistrement} à partir d'un queryset
    déjà trié du plus récent au plus ancien (ordering par défaut des modèles de
    relevés d'installation) — une seule requête groupée quel que soit le nombre
    d'installations, au lieu d'une requête par installation affichée (même pattern
    que reports/services.py::_dernier_par_installation)."""
    resultat = {}
    for obj in queryset:
        cle = getattr(obj, champ_installation)
        if cle not in resultat:
            resultat[cle] = obj
    return resultat


def _peut_gerer_materiel(user):
    """Seuils d'écriture pour la création/modification/suppression de dossiers,
    matériels et installations : CHEF_SECTION et au-dessus, comme pour l'API DRF
    (RolePermission.min_level_write) — un ÉQUIPIER ne doit pas pouvoir créer un
    dossier, un matériel ou une installation. Attention à ne pas confondre avec
    _peut_gerer_rattachement_parent (CHEF_SERVICE), seuil plus élevé réservé au
    seul rattachement parent/enfant : l'appliquer ici bloquerait à tort un
    CHEF_SECTEUR alors qu'il doit pouvoir créer un dossier ou un matériel."""
    return user_role_level(user) >= RoleLevel.CHEF_SECTION


def _sous_ensembles_ids(equipement):
    """Renvoie l'ensemble des identifiants de tous les sous-ensembles (directs et
    indirects) d'un équipement, afin de les exclure de la liste des parents proposés
    dans le formulaire (évite de présenter un choix qui créerait à coup sûr une boucle)."""
    ids = set()
    a_visiter = list(equipement.sous_ensembles.all())
    while a_visiter:
        enfant = a_visiter.pop()
        if enfant.pk in ids:
            continue
        ids.add(enfant.pk)
        a_visiter.extend(enfant.sous_ensembles.all())
    return ids


def _parent_candidats(model, sector_id, exclure_pks=()):
    """Équipements (Installation ou Asset) du même secteur pouvant être choisis comme
    parent : périmètre de référence utilisé à la fois pour construire les options du
    formulaire (GET) et pour revalider côté serveur le parent_id reçu en POST — empêche
    un rattachement hors périmètre même si le champ est posté directement, en dehors du
    menu déroulant (faille corrigée après refus du Tech Lead sur la T3)."""
    return model.objects.filter(sector_id=sector_id).exclude(pk__in=exclure_pks)


def _resoudre_parent_valide(request, objet, model):
    """Lit parent_id dans les données POST, vérifie le rôle requis (CHEF_SERVICE et
    au-dessus), puis revalide côté serveur que le parent appartient bien au même
    secteur que l'objet, avec la même logique de filtrage que celle utilisée pour
    construire les options du menu déroulant (_parent_candidats). N'exclut ici que
    l'objet lui-même (pas ses sous-ensembles) : la protection anti-cycle reste du
    ressort de full_clean() juste après, avec son propre message d'erreur français.
    Assigne objet.parent si tout est valide et renvoie None ; renvoie un message
    d'erreur français sans rien assigner si le parent_id posté est hors périmètre (ne
    fait pas confiance au menu HTML/JS, qui peut être contourné par un POST direct)."""
    parent_id = request.POST.get('parent_id')
    if parent_id is None:
        return None
    if not _peut_gerer_rattachement_parent(request.user):
        raise PermissionDenied
    if not parent_id:
        objet.parent = None
        return None
    parent = _parent_candidats(model, objet.sector_id, {objet.pk}).filter(pk=parent_id).first()
    if parent is None:
        return "Rattachement invalide : l'équipement sélectionné ne fait pas partie du même secteur."
    objet.parent = parent
    return None


def _resoudre_emplacement(request, ship):
    """Lit location_id (et new_location_name le cas échéant) dans les données POST et
    renvoie l'emplacement (Location) à assigner à un matériel/installation, ou None.

    Permet la création d'un nouvel emplacement à la volée depuis le formulaire de
    matériel/installation (option "+ Ajouter un nouvel emplacement…", location_id
    vaut alors "__new__") sans passer par un écran de gestion séparé. Le nouvel
    emplacement est toujours rattaché au navire déjà validé (ship, résolu et
    contrôlé en périmètre par l'appelant) — jamais à un navire posté séparément,
    pour ne pas pouvoir contourner le contrôle de périmètre déjà effectué sur ship_id.
    get_or_create évite les doublons si le même nom est saisi deux fois pour ce navire."""
    location_id = request.POST.get('location_id')
    if location_id == '__new__':
        nom = request.POST.get('new_location_name', '').strip()
        if not nom or ship is None:
            return None
        emplacement, _cree = Location.objects.get_or_create(ship=ship, name=nom, parent=None)
        return emplacement
    if location_id:
        return Location.objects.filter(pk=location_id).first()
    return None


def _valider_points_zone(points_json):
    """Décode et valide le contour posté par l'éditeur de plan (Zone.points) :
    une liste d'au moins 3 points {x, y} en pourcentage (0-100). Renvoie None
    si le format est invalide (ex: manipulation du formulaire), plutôt que de
    lever une exception — l'appelant affiche alors un message d'erreur simple
    et ne modifie pas le contour existant."""
    try:
        points = json.loads(points_json or "[]")
    except (TypeError, ValueError):
        return None
    if not isinstance(points, list) or len(points) < 3:
        return None
    contour = []
    for point in points:
        if not isinstance(point, dict):
            return None
        try:
            x, y = float(point.get("x")), float(point.get("y"))
        except (TypeError, ValueError):
            return None
        if not (0 <= x <= 100 and 0 <= y <= 100):
            return None
        contour.append({"x": round(x, 2), "y": round(y, 2)})
    return contour


def _org_dans_perimetre(user, model, cible_id):
    """Vérifie qu'un navire/service/secteur/section posté (à la création, à
    l'édition, ou dans une action groupée bulk_update_ship/service/sector/
    section) appartient bien au périmètre de l'appelant, en réutilisant le
    même système de périmètre que scope_filters_for_user (matrix/core/
    scopes.py, déjà utilisé par ScopedQuerySetMixin côté API) plutôt que
    d'en recréer un nouveau. Un utilisateur sans périmètre restreint (aucun
    ship/service/sector/section assigné à son profil, ex: vue globale) peut
    choisir n'importe quelle cible existante. Un utilisateur cantonné à un
    niveau peut choisir : ce niveau lui-même, un de ses ancêtres qui
    contient effectivement son propre périmètre (ex: un chef de service
    postant le navire auquel appartient déjà son service — cas normal d'un
    formulaire qui poste toute la chaîne ship/service/sector/section), ou
    un de ses descendants (ex: un utilisateur scopé navire choisissant un
    service de ce navire). Ne fait pas confiance aux menus déroulants du
    formulaire, qui peuvent être contournés par un POST direct (même
    principe que _resoudre_parent_valide pour le champ parent_id)."""
    if not cible_id:
        return True
    profil = getattr(user, 'profile', None)
    niveau, valeur = profil.scope if profil else (None, None)
    if niveau is None:
        return model.objects.filter(pk=cible_id).exists()
    # Pour chaque modèle cible, chemin permettant de vérifier que la cible
    # contient (ou est) le périmètre de l'appelant, quel que soit le niveau
    # relatif : ancêtre (ex: Ship pour un appelant scopé "service"), lui-même,
    # ou descendant (ex: Sector pour un appelant scopé "ship").
    chemins = {
        Ship: {
            'ship': 'id',
            'service': 'services__id',
            'sector': 'services__sectors__id',
            'section': 'services__sectors__sections__id',
        },
        Service: {
            'ship': 'ship_id',
            'service': 'id',
            'sector': 'sectors__id',
            'section': 'sectors__sections__id',
        },
        Sector: {
            'ship': 'service__ship_id',
            'service': 'service_id',
            'sector': 'id',
            'section': 'sections__id',
        },
        Section: {
            'ship': 'sector__service__ship_id',
            'service': 'sector__service_id',
            'sector': 'sector_id',
            'section': 'id',
        },
    }
    champ = chemins.get(model, {}).get(niveau)
    if champ is None:
        return False
    return model.objects.filter(pk=cible_id, **{champ: valeur}).exists()


def _afficher_erreur_validation(request, erreur):
    """Affiche en français le message d'une ValidationError levée par full_clean()
    (notamment la protection anti-cycle sur le rattachement parent), plutôt que de
    laisser remonter une erreur serveur non traitée."""
    if hasattr(erreur, "message_dict") and "parent" in erreur.message_dict:
        messages.error(request, erreur.message_dict["parent"][0])
    else:
        messages.error(request, "Rattachement invalide : " + " ".join(erreur.messages))


def _appliquer_bulk_update(request, queryset, champ, valeur, *, action_audit, detail_audit, message_succes,
                            redirect_url_name, org_model=None, org_id=None, libelle_org=None):
    """Applique une valeur à un champ, en masse, sur les objets du queryset fourni
    (déjà filtré par périmètre via ScopedQuerySetMixin ET par les identifiants
    sélectionnés — voir l'appelant). Si org_model est fourni (champs navire/
    service/secteur/section), valide au préalable que org_id appartient au
    périmètre de l'appelant (même contrôle T-SEC que _org_dans_perimetre pour la
    création/édition) et redirige avec un message d'erreur sans rien modifier si
    ce n'est pas le cas. Crée une entrée d'audit par objet modifié, puis un
    message de succès récapitulatif. Factorise le bloc bulk_update_* commun à
    AssetListView.post (matériel mobile) et InstallationListView.post
    (installation fixe) — ~55 lignes quasi identiques avant factorisation."""
    if org_model is not None and not _org_dans_perimetre(request.user, org_model, org_id):
        messages.error(request, f"{libelle_org} hors de votre périmètre.")
        return redirect(redirect_url_name)
    objets = list(queryset)
    for objet in objets:
        setattr(objet, champ, valeur)
        objet.save(update_fields=[champ])
        AuditLog.objects.create(actor=request.user, action=action_audit, details=detail_audit)
    messages.success(request, message_succes.format(count=len(objets)))
    return redirect(redirect_url_name)


def _appliquer_bulk_suppression(request, queryset, *, action_audit, message_succes, redirect_url_name):
    """Supprime en masse les objets du queryset fourni (déjà filtré par périmètre
    et par les identifiants sélectionnés — voir l'appelant), avec une entrée
    d'audit par objet supprimé puis un message de succès récapitulatif.
    Factorise le bloc bulk_delete_* commun à AssetListView.post et
    InstallationListView.post."""
    count = queryset.count()
    for objet in queryset:
        AuditLog.objects.create(actor=request.user, action=action_audit, details=f'id={objet.id}')
    queryset.delete()
    messages.success(request, message_succes.format(count=count))
    return redirect(redirect_url_name)


def _perimetre_utilisateur(user):
    """Navire/service/secteur/section affectés à l'utilisateur connecté (profil),
    utilisés pour pré-remplir automatiquement les formulaires de création de
    matériel et d'installation avec le périmètre du chef connecté, plutôt que de
    lui faire ressaisir à la main une hiérarchie déjà connue (principe « plus
    rapide qu'Excel »). Réutilise le profil existant (accounts.UserProfile),
    sans nouveau système de scope."""
    profile = getattr(user, 'profile', None)
    if not profile:
        return {'user_ship_id': None, 'user_service_id': None, 'user_sector_id': None, 'user_section_id': None}
    return {
        'user_ship_id': profile.ship_id,
        'user_service_id': profile.service_id,
        'user_sector_id': profile.sector_id,
        'user_section_id': profile.section_id,
    }


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

class StartVisualCheckView(LoginRequiredMixin, View):
    def post(self, request, pk):
        if user_role_level(request.user) < RoleLevel.CHEF_SECTION:
            raise PermissionDenied
        # Périmètre : même filtre que ScanQRView (scope_filters_for_user) — sans
        # lui, un chef de section connaissant l'identifiant d'un matériel d'un
        # autre navire pouvait déclencher un contrôle visuel dessus (T-SEC).
        filtres = scope_filters_for_user(request.user)
        assets = Asset.objects.filter(**filtres) if filtres else Asset.objects.all()
        try:
            asset = assets.get(pk=pk)
        except Asset.DoesNotExist:
            return HttpResponseBadRequest('Matériel introuvable ou hors de votre périmètre.')
        plan = MaintenancePlan.objects.filter(scope='ASSET_TYPE', asset_type=asset.asset_type).first()
        name = plan.name if plan else 'Contrôle visuel'
        occ, _ = MaintenanceOccurrence.objects.get_or_create(
            plan=plan if plan else None,
            asset=asset,
            scheduled_for=timezone.localdate(),
            defaults={"status": "ASSIGNED"}
        )
        if request.headers.get('HX-Request'):
            return JsonResponse({"occurrence_id": occ.id, "status": occ.status, "execute_url": f"/maintenance/occurrences/{occ.id}/execute/"})
        return redirect(f"/maintenance/occurrences/{occ.id}/execute/")


class ScanQRView(LoginRequiredMixin, View):
    """Point d'entrée du QR code apposé sur un équipement (matériel mobile ou
    installation fixe) — workflow « Scan QR → occurrence du jour → checklist »
    (CLAUDE.md). Résout l'équipement scanné (même identifiant pour Asset et
    Installation, on essaie l'un puis l'autre), puis :
    - s'il existe une occurrence de maintenance planifiée aujourd'hui et
      assignée au marin connecté sur cet équipement, ouvre directement la
      checklist guidée d'exécution (aucune recherche à faire au poste) ;
    - sinon, affiche la fiche de l'équipement, d'où une anomalie peut être
      signalée en un clic.
    """

    def get(self, request, pk):
        # Périmètre : réutilise scope_filters_for_user (même système que
        # ScopedQuerySetMixin côté API) — un équipement hors périmètre est
        # traité comme introuvable, pas de nouveau contrôle d'accès.
        filtres = scope_filters_for_user(request.user)
        assets = Asset.objects.filter(**filtres) if filtres else Asset.objects.all()
        asset = assets.filter(pk=pk).first()
        if asset is not None:
            return self._rediriger(request, asset=asset)
        installations = Installation.objects.filter(**filtres) if filtres else Installation.objects.all()
        installation = installations.filter(pk=pk).first()
        if installation is not None:
            return self._rediriger(request, installation=installation)

        # Ni Asset ni Installation dans le périmètre de l'utilisateur : au
        # lieu de laisser Django renvoyer sa page 404 technique (brute, en
        # anglais en debug), on distingue deux cas et on redirige vers le
        # tableau de bord avec un message clair en français. On ne révèle
        # jamais le nom/navire de l'équipement d'un autre bâtiment : le
        # message reste générique dans le cas « hors périmètre ».
        existe_hors_perimetre = (
            Asset.objects.filter(pk=pk).exists() or Installation.objects.filter(pk=pk).exists()
        )
        if existe_hors_perimetre:
            messages.error(
                request,
                "Cet équipement n'appartient pas à votre navire, vous ne pouvez pas y accéder.",
            )
        else:
            messages.error(request, "QR code invalide ou équipement introuvable.")
        return redirect('home')

    def _rediriger(self, request, asset=None, installation=None):
        occurrences_du_jour = MaintenanceOccurrence.objects.filter(
            scheduled_for=timezone.localdate(), assignees=request.user
        ).exclude(status__in=_STATUTS_OCCURRENCE_TERMINES)
        if asset is not None:
            occurrence = occurrences_du_jour.filter(asset=asset).first()
        else:
            occurrence = occurrences_du_jour.filter(installation_maintenance__installation=installation).first()
        if occurrence is not None:
            return redirect('occurrence-execute', pk=occurrence.pk)
        if asset is not None:
            return redirect('asset-detail', pk=asset.pk)
        return redirect('installation-detail', pk=installation.pk)


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

    # Contrôle de rôle par action (T-SEC) : CHEF_SECTION pour la création/édition
    # simple, CHEF_SERVICE pour les suppressions et les actions groupées — même seuil
    # que MAINTENANCE_WRITE_ACTIONS (InstallationDetailView) et
    # _peut_gerer_rattachement_parent, pour rester cohérent avec le reste du fichier.
    NIVEAU_REQUIS_PAR_ACTION = {
        'create_folder': RoleLevel.CHEF_SECTION,
        'rename_folder': RoleLevel.CHEF_SECTION,
        'delete_folder': RoleLevel.CHEF_SERVICE,
        'move_asset_to_folder': RoleLevel.CHEF_SECTION,
        'create_asset': RoleLevel.CHEF_SECTION,
        'edit_asset': RoleLevel.CHEF_SECTION,
        'delete_asset': RoleLevel.CHEF_SERVICE,
        'delete_asset_document': RoleLevel.CHEF_SERVICE,
        'bulk_update_status': RoleLevel.CHEF_SERVICE,
        'bulk_update_location': RoleLevel.CHEF_SERVICE,
        'bulk_update_ship': RoleLevel.CHEF_SERVICE,
        'bulk_update_service': RoleLevel.CHEF_SERVICE,
        'bulk_update_sector': RoleLevel.CHEF_SERVICE,
        'bulk_update_section': RoleLevel.CHEF_SERVICE,
        'bulk_delete_assets': RoleLevel.CHEF_SERVICE,
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
        niveau_requis = self.NIVEAU_REQUIS_PAR_ACTION.get(action)
        if niveau_requis is not None and user_role_level(request.user) < niveau_requis:
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
            # Création d'un dossier : réservée aux CHEF_SECTION et au-dessus, même
            # seuil que la création de matériel ci-dessous. Un ÉQUIPIER ne doit pas
            # pouvoir ajouter un dossier (bug sécurité corrigé ici) ; attention à ne
            # pas reprendre le seuil CHEF_SERVICE du rattachement parent, plus élevé,
            # qui bloquerait à tort un CHEF_SECTEUR.
            if not _peut_gerer_materiel(request.user):
                raise PermissionDenied
            name = request.POST.get('name', '').strip()
            parent_id = request.POST.get('parent_id')
            parent = AssetFolder.objects.filter(pk=parent_id).first() if parent_id else None
            if name:
                fld = AssetFolder.objects.create(name=name)
                photo = request.FILES.get('photo')
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
            # Création d'un matériel : réservée aux CHEF_SECTION et au-dessus (même
            # seuil que l'API DRF, cf. RolePermission.min_level_write) — un ÉQUIPIER
            # ne doit pas pouvoir ajouter de matériel (bug sécurité corrigé ici).
            # L'édition et la suppression restent volontairement ouvertes à tous les
            # utilisateurs connectés (comportement existant, cf. tests T2/T3).
            if not _peut_gerer_materiel(request.user):
                raise PermissionDenied
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
                try:
                    for f in request.FILES.getlist('documents'):
                        AssetDocument.objects.create(asset=asset, file=f, name=getattr(f, 'name', '') or '')
                except Exception:
                    pass
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
                try:
                    for f in request.FILES.getlist('documents'):
                        AssetDocument.objects.create(asset=asset, file=f, name=getattr(f, 'name', '') or '')
                except Exception:
                    pass
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


class InstallationListView(LoginRequiredMixin, ScopedQuerySetMixin, ListView):
    model = Installation
    template_name = 'assets/installations.html'
    context_object_name = 'installations'

    # Contrôle de rôle par action (T-SEC) : CHEF_SECTION pour la création/édition
    # simple, CHEF_SERVICE pour les suppressions et les actions groupées — même seuil
    # que MAINTENANCE_WRITE_ACTIONS (InstallationDetailView) et AssetListView.
    NIVEAU_REQUIS_PAR_ACTION = {
        'create_installation': RoleLevel.CHEF_SECTION,
        'edit_installation': RoleLevel.CHEF_SECTION,
        'delete_installation': RoleLevel.CHEF_SERVICE,
        'bulk_update_location': RoleLevel.CHEF_SERVICE,
        'bulk_update_ship': RoleLevel.CHEF_SERVICE,
        'bulk_update_service': RoleLevel.CHEF_SERVICE,
        'bulk_update_sector': RoleLevel.CHEF_SERVICE,
        'bulk_update_section': RoleLevel.CHEF_SERVICE,
        'bulk_delete_installations': RoleLevel.CHEF_SERVICE,
    }

    def get_queryset(self):
        # Périmètre appliqué par ScopedQuerySetMixin (même système que l'API) avant les
        # filtres de recherche/tri propres à cette vue.
        qs = super().get_queryset().select_related('ship', 'service', 'sector', 'section', 'location').order_by('ship__name', 'service__name', 'sector__name', 'section__name', 'designation')
        ship_id = self.request.GET.get('ship')
        service_id = self.request.GET.get('service')
        sector_id = self.request.GET.get('sector')
        section_id = self.request.GET.get('section')
        q = self.request.GET.get('q', '').strip()
        if ship_id:
            qs = qs.filter(ship_id=ship_id)
        if service_id:
            qs = qs.filter(service_id=service_id)
        if sector_id:
            qs = qs.filter(sector_id=sector_id)
        if section_id:
            qs = qs.filter(section_id=section_id)
        if q:
            qs = qs.filter(models.Q(designation__icontains=q) | models.Q(reference__icontains=q) | models.Q(marque__icontains=q) | models.Q(gisement__icontains=q))
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['ships'] = Ship.objects.order_by('name')
        ctx['services'] = Service.objects.select_related('ship').order_by('name')
        ctx['sectors'] = Sector.objects.select_related('service', 'service__ship').order_by('name')
        ctx['sections'] = Section.objects.select_related('sector', 'sector__service', 'sector__service__ship').order_by('name')
        ctx['locations'] = Location.objects.select_related('ship').order_by('ship__name', 'name')
        ctx['bigrames'] = InstallationBigrameChoice.objects.filter(active=True).order_by('name')
        # Pré-remplissage du formulaire de création : Navire/Service/Secteur du
        # périmètre de l'utilisateur connecté, pour éviter de ressaisir à la main
        # ce que son profil connaît déjà (principe « plus rapide qu'Excel »).
        # Reste modifiable si l'utilisateur doit créer ailleurs dans son périmètre.
        ctx['export_url_csv'] = construire_url_export(self.request, 'csv')
        ctx['export_url_xlsx'] = construire_url_export(self.request, 'xlsx')
        ctx['xlsx_disponible'] = xlsx_disponible()
        # Rattachement parent (T3) : réservé aux CHEF_SERVICE et au-dessus, filtré
        # côté client par secteur (data-sector) pour éviter un rattachement cross-navire.
        ctx['peut_gerer_parent'] = _peut_gerer_rattachement_parent(self.request.user)
        ctx['installations_pour_parent'] = (
            Installation.objects.select_related('sector').order_by('designation')
            if ctx['peut_gerer_parent'] else Installation.objects.none()
        )
        # Pré-remplissage du périmètre (navire/service/secteur/section) du formulaire
        # de création à partir du profil du chef connecté.
        ctx.update(_perimetre_utilisateur(self.request.user))
        # Prépare les métriques pour affichage sur les cartes (vibration, heures, isolement).
        # Requêtes groupées (installation_id__in=...) plutôt qu'une requête par
        # installation affichée : le nombre de requêtes ne dépend plus de N.
        try:
            installations = list(ctx.get('installations', []))
        except Exception:
            installations = []
        installation_ids = [it.id for it in installations]
        try:
            derniers_vibrations = _dernier_par_installation(
                InstallationVibrationReading.objects.filter(installation_id__in=installation_ids)
            )
        except OperationalError:
            derniers_vibrations = {}
        try:
            derniers_isolements = _dernier_par_installation(
                InstallationIsolationReading.objects.filter(installation_id__in=installation_ids)
            )
        except OperationalError:
            derniers_isolements = {}
        try:
            releves_heures_par_installation = defaultdict(list)
            for releve in InstallationHourReading.objects.filter(installation_id__in=installation_ids):
                releves_heures_par_installation[releve.installation_id].append(releve)
        except OperationalError:
            releves_heures_par_installation = {}
        for it in installations:
            # Vibrations: dernier état et prochaine échéance
            last_vib = derniers_vibrations.get(it.id)
            if last_vib:
                it.vibration_last_state_card = last_vib.state
                a, b, c = getattr(it, 'vib_days_a', 180), getattr(it, 'vib_days_b', 90), getattr(it, 'vib_days_c', 30)
                delta = a if last_vib.state == 'A' else b if last_vib.state == 'B' else c
                try:
                    next_date = last_vib.date + timedelta(days=int(delta))
                    it.vibration_next_date_card = next_date
                    it.vibration_next_days_card = (next_date - timezone.localdate()).days
                except Exception:
                    it.vibration_next_date_card = None
                    it.vibration_next_days_card = None
            else:
                it.vibration_last_state_card = None
                it.vibration_next_date_card = None
                it.vibration_next_days_card = None
            # Heures de marche: total et depuis dernière visite
            hour_logs = releves_heures_par_installation.get(it.id, [])
            total = sum(float(r.hours or 0) for r in hour_logs) if hour_logs else 0.0
            last_visit = next((r for r in hour_logs if getattr(r, 'is_visit', False)), None)
            since_last = sum(float(r.hours or 0) for r in hour_logs if last_visit and r.date > last_visit.date) if hour_logs and last_visit else total
            it.hours_total_card = total
            it.hours_last_visit_card = since_last
            # Isolement: dernière mesure
            last_iso = derniers_isolements.get(it.id)
            if last_iso:
                it.isolation_last_ohms_card = last_iso.ohms
                it.isolation_last_date_card = last_iso.date
                # Prochaine échéance isolement selon périodicité
                try:
                    period = getattr(it, 'iso_periodicity', 'M')
                    months = 1 if period == 'M' else 3 if period == 'T' else 12
                    d = last_iso.date
                    y = d.year + (d.month - 1 + months) // 12
                    m = (d.month - 1 + months) % 12 + 1
                    max_day = calendar.monthrange(y, m)[1]
                    day = d.day if d.day <= max_day else max_day
                    nd = datetime(y, m, day).date()
                    it.isolation_next_date_card = nd
                    it.isolation_next_days_card = (nd - timezone.localdate()).days
                except Exception:
                    it.isolation_next_date_card = None
                    it.isolation_next_days_card = None
            else:
                it.isolation_last_ohms_card = None
                it.isolation_last_date_card = None
                it.isolation_next_date_card = None
                it.isolation_next_days_card = None
        return ctx

    def get(self, request, *args, **kwargs):
        format_export = request.GET.get('export')
        if format_export in ('csv', 'xlsx'):
            # Périmètre : même garde-fou que AssetListView.get — l'export ne doit
            # JAMAIS dépasser le périmètre de l'utilisateur, même si l'affichage
            # de cette liste n'est pas lui-même restreint par périmètre.
            qs = self.get_queryset().filter(**scope_filters_for_user(request.user))
            lignes = _lignes_export_installations(qs)
            if format_export == 'xlsx':
                contenu = rendre_xlsx(
                    _ENTETES_EXPORT_INSTALLATIONS, lignes, titre_feuille='Installations'
                )
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
                contenu = rendre_csv(_ENTETES_EXPORT_INSTALLATIONS, lignes)
                content_type = CSV_CONTENT_TYPE
            AuditLog.objects.create(
                actor=request.user, action=f'export_installations_{format_export}',
                target_user=None, details=f'rows={len(lignes)}',
            )
            return reponse_fichier(contenu, f'installations.{format_export}', content_type)
        return super().get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        action = request.POST.get('action')
        niveau_requis = self.NIVEAU_REQUIS_PAR_ACTION.get(action)
        if niveau_requis is not None and user_role_level(request.user) < niveau_requis:
            raise PermissionDenied
        if action in (
            'bulk_update_location', 'bulk_update_ship', 'bulk_update_service',
            'bulk_update_sector', 'bulk_update_section', 'bulk_delete_installations'
        ):
            ids = request.POST.getlist('selected_ids')
            # Périmètre : seules les installations du périmètre de l'appelant sont
            # chargées (self.get_queryset(), scopé via ScopedQuerySetMixin) — un
            # identifiant posté hors périmètre est simplement ignoré.
            items = self.get_queryset().filter(id__in=ids)
            if action == 'bulk_update_location':
                loc_id = request.POST.get('location_id')
                loc = Location.objects.filter(pk=loc_id).first()
                return _appliquer_bulk_update(
                    request, items, 'location', loc,
                    action_audit='bulk_update_installation_location', detail_audit=f'location_id={loc_id}',
                    message_succes='Emplacement mis à jour pour {count} installation(s).',
                    redirect_url_name='installation-list',
                )
            elif action == 'bulk_update_ship':
                ship_id = request.POST.get('ship_id')
                return _appliquer_bulk_update(
                    request, items, 'ship', Ship.objects.filter(pk=ship_id).first(),
                    action_audit='bulk_update_installation_ship', detail_audit=f'ship_id={ship_id}',
                    message_succes='Unité mise à jour pour {count} installation(s).',
                    redirect_url_name='installation-list',
                    org_model=Ship, org_id=ship_id, libelle_org='Unité',
                )
            elif action == 'bulk_update_service':
                service_id = request.POST.get('service_id')
                return _appliquer_bulk_update(
                    request, items, 'service', Service.objects.filter(pk=service_id).first(),
                    action_audit='bulk_update_installation_service', detail_audit=f'service_id={service_id}',
                    message_succes='Service mis à jour pour {count} installation(s).',
                    redirect_url_name='installation-list',
                    org_model=Service, org_id=service_id, libelle_org='Service',
                )
            elif action == 'bulk_update_sector':
                sector_id = request.POST.get('sector_id')
                return _appliquer_bulk_update(
                    request, items, 'sector', Sector.objects.filter(pk=sector_id).first(),
                    action_audit='bulk_update_installation_sector', detail_audit=f'sector_id={sector_id}',
                    message_succes='Secteur mis à jour pour {count} installation(s).',
                    redirect_url_name='installation-list',
                    org_model=Sector, org_id=sector_id, libelle_org='Secteur',
                )
            elif action == 'bulk_update_section':
                section_id = request.POST.get('section_id')
                return _appliquer_bulk_update(
                    request, items, 'section', Section.objects.filter(pk=section_id).first(),
                    action_audit='bulk_update_installation_section', detail_audit=f'section_id={section_id}',
                    message_succes='Section mise à jour pour {count} installation(s).',
                    redirect_url_name='installation-list',
                    org_model=Section, org_id=section_id, libelle_org='Section',
                )
            elif action == 'bulk_delete_installations':
                return _appliquer_bulk_suppression(
                    request, items,
                    action_audit='bulk_delete_installation',
                    message_succes='{count} installation(s) supprimée(s).',
                    redirect_url_name='installation-list',
                )

        if action == 'create_installation':
            # Création d'une installation : réservée aux CHEF_SECTION et au-dessus,
            # même seuil que la création de matériel — un ÉQUIPIER ne doit pas
            # pouvoir en ajouter une (bug sécurité corrigé ici). L'édition et la
            # suppression restent volontairement ouvertes à tous les utilisateurs
            # connectés (comportement existant, cf. tests T2/T3).
            if not _peut_gerer_materiel(request.user):
                raise PermissionDenied
            designation = request.POST.get('designation', '').strip()
            reference = request.POST.get('reference', '').strip()
            marque = request.POST.get('marque', '').strip()
            gisement = request.POST.get('gisement', '').strip()
            local = request.POST.get('local', '').strip()
            bigrame_id = request.POST.get('bigrame_id')
            ship_id = request.POST.get('ship_id')
            service_id = request.POST.get('service_id')
            sector_id = request.POST.get('sector_id')
            section_id = request.POST.get('section_id')
            iso_period = (request.POST.get('iso_periodicity') or 'M').strip().upper()
            # Périmètre (T-SEC) : le navire/service/secteur/section posté doit appartenir
            # au périmètre de l'appelant — ne fait pas confiance au menu déroulant.
            if ship_id and not _org_dans_perimetre(request.user, Ship, ship_id):
                messages.error(request, "Unité hors de votre périmètre.")
                return redirect('installation-list')
            if service_id and not _org_dans_perimetre(request.user, Service, service_id):
                messages.error(request, "Service hors de votre périmètre.")
                return redirect('installation-list')
            if sector_id and not _org_dans_perimetre(request.user, Sector, sector_id):
                messages.error(request, "Secteur hors de votre périmètre.")
                return redirect('installation-list')
            if section_id and not _org_dans_perimetre(request.user, Section, section_id):
                messages.error(request, "Section hors de votre périmètre.")
                return redirect('installation-list')
            it = Installation(
                designation=designation,
                reference=reference,
                marque=marque,
                gisement=gisement,
                local=local,
                critique=request.POST.get('critique') == 'on',
            )
            photo = request.FILES.get('photo')
            if photo:
                it.photo = photo
            if ship_id:
                it.ship = Ship.objects.filter(pk=ship_id).first()
            if service_id:
                it.service = Service.objects.filter(pk=service_id).first()
            if sector_id:
                it.sector = Sector.objects.filter(pk=sector_id).first()
            if section_id:
                it.section = Section.objects.filter(pk=section_id).first()
            it.location = _resoudre_emplacement(request, it.ship)
            if bigrame_id:
                it.bigrame = InstallationBigrameChoice.objects.filter(pk=bigrame_id).first()
            if iso_period in ('M','T','A'):
                it.iso_periodicity = iso_period
            erreur_parent = _resoudre_parent_valide(request, it, Installation)
            if erreur_parent:
                messages.error(request, erreur_parent)
                return redirect('installation-list')
            try:
                it.full_clean()
            except ValidationError as exc:
                _afficher_erreur_validation(request, exc)
                return redirect('installation-list')
            it.save()
            # Champs personnalisés (JSON array [{label, value, order}])
            try:
                import json
                extras_json = request.POST.get('extra_fields')
                if extras_json:
                    extras = json.loads(extras_json)
                    order = 0
                    for ex in extras:
                        lbl = (ex.get('label') or '').strip()
                        val = (ex.get('value') or '').strip()
                        if not lbl:
                            continue
                        InstallationExtraField.objects.create(
                            installation=it, label=lbl, value=val, order=order, created_by=request.user
                        )
                        order += 1
            except Exception:
                pass
            AuditLog.objects.create(actor=request.user, action='create_installation', details=f'designation={designation}')
            messages.success(request, 'Installation créée.')
        elif action == 'edit_installation':
            pk = request.POST.get('pk')
            ship_id = request.POST.get('ship_id')
            service_id = request.POST.get('service_id')
            sector_id = request.POST.get('sector_id')
            section_id = request.POST.get('section_id')
            # Périmètre (T-SEC) : même contrôle qu'à la création.
            if ship_id and not _org_dans_perimetre(request.user, Ship, ship_id):
                messages.error(request, "Unité hors de votre périmètre.")
                return redirect('installation-list')
            if service_id and not _org_dans_perimetre(request.user, Service, service_id):
                messages.error(request, "Service hors de votre périmètre.")
                return redirect('installation-list')
            if sector_id and not _org_dans_perimetre(request.user, Sector, sector_id):
                messages.error(request, "Secteur hors de votre périmètre.")
                return redirect('installation-list')
            if section_id and not _org_dans_perimetre(request.user, Section, section_id):
                messages.error(request, "Section hors de votre périmètre.")
                return redirect('installation-list')
            try:
                # Périmètre : l'installation visée doit appartenir au périmètre de
                # l'appelant (self.get_queryset(), scopé) — un identifiant hors périmètre
                # est traité comme introuvable plutôt que d'être chargé via le manager brut.
                it = self.get_queryset().get(pk=pk)
                it.designation = request.POST.get('designation', it.designation).strip()
                it.reference = request.POST.get('reference', it.reference).strip()
                it.marque = request.POST.get('marque', it.marque).strip()
                it.gisement = request.POST.get('gisement', it.gisement).strip()
                it.local = request.POST.get('local', it.local).strip()
                it.critique = request.POST.get('critique') == 'on'
                bigrame_id = request.POST.get('bigrame_id')
                photo = request.FILES.get('photo')
                if photo:
                    it.photo = photo
                it.ship = Ship.objects.filter(pk=ship_id).first() if ship_id else None
                it.service = Service.objects.filter(pk=service_id).first() if service_id else None
                it.sector = Sector.objects.filter(pk=sector_id).first() if sector_id else None
                it.section = Section.objects.filter(pk=section_id).first() if section_id else None
                it.location = _resoudre_emplacement(request, it.ship)
                it.bigrame = InstallationBigrameChoice.objects.filter(pk=bigrame_id).first() if bigrame_id else None
                iso_period = (request.POST.get('iso_periodicity') or '').strip().upper()
                if iso_period in ('M','T','A'):
                    it.iso_periodicity = iso_period
                it.save()
                # Met à jour les champs personnalisés si fournis
                try:
                    import json
                    extras_json = request.POST.get('extra_fields')
                    if extras_json is not None:
                        InstallationExtraField.objects.filter(installation=it).delete()
                        extras = json.loads(extras_json) if extras_json else []
                        order = 0
                        for ex in extras:
                            lbl = (ex.get('label') or '').strip()
                            val = (ex.get('value') or '').strip()
                            if not lbl:
                                continue
                            InstallationExtraField.objects.create(
                                installation=it, label=lbl, value=val, order=order, created_by=request.user
                            )
                            order += 1
                except Exception:
                    pass
                AuditLog.objects.create(actor=request.user, action='edit_installation', details=f'id={it.id}')
                messages.success(request, 'Installation mise à jour.')
            except Installation.DoesNotExist:
                messages.error(request, 'Installation introuvable.')
        elif action == 'delete_installation':
            pk = request.POST.get('pk')
            # Périmètre : une installation hors périmètre est traitée comme introuvable.
            supprimees = self.get_queryset().filter(pk=pk).delete()[0]
            if supprimees:
                messages.success(request, 'Installation supprimée.')
            else:
                messages.error(request, 'Installation introuvable.')
        return redirect('installation-list')


# Import placé ici (après les helpers ci-dessus, avant leur premier usage) plutôt
# qu'en tête de fichier : installation_actions.py importe lui-même certains de ces
# helpers (_org_dans_perimetre, _resoudre_parent_valide, _afficher_erreur_validation)
# depuis ce module — les définir avant cet import évite un import circulaire.
from .installation_actions import ACTION_HANDLERS


class InstallationDetailView(LoginRequiredMixin, ScopedQuerySetMixin, DetailView):
    model = Installation
    template_name = 'assets/installation_detail.html'

    # Actions liées aux tâches d'entretien (InstallationMaintenance) : réservées
    # aux CHEF_SERVICE et au-dessus, cf. RolePermission déjà utilisé côté API DRF.
    MAINTENANCE_WRITE_ACTIONS = {
        'add_maintenance',
        'edit_maintenance',
        'delete_maintenance',
        'add_maintenance_attachment',
        'delete_maintenance_attachment',
    }

    # Actions de gestion de la fiche installation elle-même (hors tâches d'entretien) :
    # même seuil que sur la liste (AssetListView/InstallationListView) — CHEF_SECTION
    # pour l'édition simple, CHEF_SERVICE pour la suppression. Corrige le contournement
    # possible via la fiche détail, ces deux actions n'étant pas dans
    # MAINTENANCE_WRITE_ACTIONS (T-SEC).
    INSTALLATION_WRITE_ACTIONS = {'edit_installation'}
    INSTALLATION_DELETE_ACTIONS = {'delete_installation'}

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['ships'] = Ship.objects.order_by('name')
        ctx['services'] = Service.objects.select_related('ship').order_by('name')
        ctx['sectors'] = Sector.objects.select_related('service', 'service__ship').order_by('name')
        ctx['sections'] = Section.objects.select_related('sector', 'sector__service', 'sector__service__ship').order_by('name')
        ctx['bigrames'] = InstallationBigrameChoice.objects.filter(active=True).order_by('name')
        ctx['locations'] = Location.objects.select_related('ship').order_by('ship__name', 'name')
        # Rattachement parent (T3) : réservé aux CHEF_SERVICE et au-dessus, options
        # limitées au même secteur que l'installation courante (même périmètre),
        # en excluant l'installation elle-même et ses sous-ensembles (évite un choix
        # qui créerait forcément une boucle).
        ctx['peut_gerer_parent'] = _peut_gerer_rattachement_parent(self.request.user)
        if ctx['peut_gerer_parent']:
            exclus = _sous_ensembles_ids(self.object) | {self.object.pk}
            ctx['installations_pour_parent'] = (
                _parent_candidats(Installation, self.object.sector_id, exclus)
                .order_by('designation')
            )
        else:
            ctx['installations_pour_parent'] = Installation.objects.none()
        ctx['events'] = (
            InstallationEvent.objects
            .filter(installation=self.object)
            .select_related('created_by')
            .prefetch_related('attachments')
            .order_by('-date')
        )
        ctx['parts'] = InstallationPart.objects.filter(installation=self.object).order_by('name')
        # Pièces de stock affiliées (T-FEAT stock détaillé) : lien optionnel côté
        # StockPiece (logistics), affiché ici en lecture seule dans l'onglet
        # « Pièces », la gestion du stock se faisant depuis /logistics/stock/.
        ctx['pieces_stock'] = StockPiece.objects.filter(installation=self.object).order_by('reference')
        ctx['extra_fields'] = list(self.object.extra_fields.all())
        # Entretien: liste des tâches d'entretien définies sur l'installation
        try:
            maints = list(
                InstallationMaintenance.objects
                .filter(installation=self.object)
                .prefetch_related('attachments')
                .order_by('periodicity', 'title')
            )
        except OperationalError:
            maints = []
        # Annoter la durée HH:MM pour l'affichage
        for m in maints:
            try:
                total = int(getattr(m, 'planned_duration_min', 0) or 0)
            except Exception:
                total = 0
            m.duration_hours = total // 60
            m.duration_minutes = total % 60
        ctx['maintenances'] = maints
        # Vibrations: historique
        try:
            vib_logs = list(
                InstallationVibrationReading.objects
                .filter(installation=self.object)
                .select_related('created_by')
                .order_by('-date')
            )
        except OperationalError:
            vib_logs = []
        ctx['vibration_logs'] = vib_logs
        # Prochaine mesure de vibration (selon dernier état et paramètres installation)
        next_date = None
        next_days = None
        last_state = None
        if vib_logs:
            last = vib_logs[0]
            last_state = last.state
            a, b, c = getattr(self.object, 'vib_days_a', 180), getattr(self.object, 'vib_days_b', 90), getattr(self.object, 'vib_days_c', 30)
            delta = a if last.state == 'A' else b if last.state == 'B' else c
            try:
                next_date = last.date + timedelta(days=int(delta))
                next_days = (next_date - timezone.localdate()).days
            except Exception:
                next_date = None
                next_days = None
        ctx['vibration_next_date'] = next_date
        ctx['vibration_next_days'] = next_days
        ctx['vibration_last_state'] = last_state
        # Frise visuelle de l'évolution des états A/B/C (principe n°5 CLAUDE.md :
        # le tableau brut existant ne donne aucune vue d'ensemble de la tendance).
        # 100% SVG/CSS, même famille que l'arbre de compétences (training) : pas
        # de nouvelle dépendance JS. Limité aux 20 relevés les plus récents, dans
        # l'ordre chronologique (du plus ancien au plus récent, lecture naturelle),
        # pour rester lisible sans défiler indéfiniment.
        ctx['vibration_timeline'] = list(reversed(vib_logs[:20]))
        # Isolement: relevés (Ohm)
        try:
            iso_logs = list(
                InstallationIsolationReading.objects
                .filter(installation=self.object)
                .select_related('created_by')
                .order_by('-date')
            )
        except OperationalError:
            iso_logs = []
        ctx['isolation_logs'] = iso_logs
        # Dernière mesure d'isolement et prochaine échéance selon périodicité
        isolation_last = iso_logs[0] if iso_logs else None
        isolation_next_date = None
        isolation_next_days = None
        if isolation_last:
            period = getattr(self.object, 'iso_periodicity', 'M')
            months = 1 if period == 'M' else 3 if period == 'T' else 12
            try:
                d = isolation_last.date
                y = d.year + (d.month - 1 + months) // 12
                m = (d.month - 1 + months) % 12 + 1
                max_day = calendar.monthrange(y, m)[1]
                day = d.day if d.day <= max_day else max_day
                isolation_next_date = datetime(y, m, day).date()
                isolation_next_days = (isolation_next_date - timezone.localdate()).days
            except Exception:
                isolation_next_date = None
                isolation_next_days = None
        ctx['isolation_last'] = isolation_last
        ctx['isolation_next_date'] = isolation_next_date
        ctx['isolation_next_days'] = isolation_next_days
        # Courbe de tendance (principe n°5 CLAUDE.md) : même pattern Chart.js que
        # hoursPerMonthChart, avec une ligne horizontale au seuil d'alerte. Ordre
        # chronologique (du plus ancien au plus récent) pour une lecture naturelle
        # de gauche à droite.
        iso_logs_asc = list(reversed(iso_logs))
        ctx['isolation_chart_labels_json'] = json.dumps(
            [r.date.strftime('%d/%m/%Y') for r in iso_logs_asc]
        )
        ctx['isolation_chart_values_json'] = json.dumps(
            [float(r.ohms) for r in iso_logs_asc]
        )
        ctx['isolation_seuil_ohms'] = self.object.isolation_seuil_ohms
        # Estimation de dérive : réutilise la régression linéaire déjà utilisée par
        # notifications/tasks.py::detect_installation_drift, affichée ici en clair
        # plutôt que laissée uniquement dans les alertes.
        ctx['isolation_jours_avant_seuil'] = None
        if self.object.isolation_seuil_ohms:
            releves = [(r.date, float(r.ohms)) for r in iso_logs]
            ctx['isolation_jours_avant_seuil'] = jours_avant_franchissement_seuil(
                releves, float(self.object.isolation_seuil_ohms), sens="BAISSE"
            )
        # Heure de marche: relevés et indicateurs (tolère absence de table/colonne avant migration)
        try:
            logs = list(
                InstallationHourReading.objects
                .filter(installation=self.object)
                .select_related('created_by')
                .order_by('-date')
            )
        except OperationalError:
            logs = []
        ctx['hour_logs'] = logs
        # Total = somme de toutes les heures relevées
        ctx['hours_total'] = sum(float(r.hours or 0) for r in logs) if logs else 0
        # Dernière visite = somme des heures après le dernier relevé marqué visite
        last_visit = next((r for r in logs if getattr(r, 'is_visit', False)), None)
        if last_visit:
            ctx['hours_last_visit'] = sum(float(r.hours or 0) for r in logs if r.date > last_visit.date)
        else:
            ctx['hours_last_visit'] = ctx['hours_total']
        # Heures du mois en cours (somme par mois)
        today = timezone.localdate()
        first_day = today.replace(day=1)
        # Fenêtre fixe: 12 derniers mois, indexation déterministe
        def month_add(year, month, delta):
            y = year + (month - 1 + delta) // 12
            m = (month - 1 + delta) % 12 + 1
            return y, m

        start_y, start_m = month_add(today.year, today.month, -11)
        # Prépare labels et tableau de 12 zéros
        labels = []
        values = [0.0] * 12
        for i in range(12):
            y, m = month_add(start_y, start_m, i)
            labels.append(f"{m:02}/{y}")
        # Répartit chaque relevé dans le bon index 0..11
        for r in logs:
            if not getattr(r, 'date', None):
                continue
            idx = (r.date.year - start_y) * 12 + (r.date.month - start_m)
            if 0 <= idx < 12:
                try:
                    values[idx] += float(r.hours or 0.0)
                except Exception:
                    pass
        values = [max(0.0, v) for v in values]
        ctx['hours_month_labels'] = labels
        ctx['hours_month_values'] = values
        ctx['hours_month_labels_json'] = json.dumps(labels)
        ctx['hours_month_values_json'] = json.dumps(values)
        # KPI "Ce mois" = valeur du dernier index (mois courant)
        ctx['hours_month'] = values[-1] if values else 0.0
        # Libellé du mois de la dernière visite (MM/YYYY) pour marquage sur la courbe
        if last_visit:
            visit_label = f"{last_visit.date.month:02}/{last_visit.date.year}"
        else:
            visit_label = ""
        ctx['hours_visit_label'] = visit_label
        return ctx

    def post(self, request, *args, **kwargs):
        action = request.POST.get('action')
        if action in self.MAINTENANCE_WRITE_ACTIONS and user_role_level(request.user) < RoleLevel.CHEF_SERVICE:
            raise PermissionDenied
        if action in self.INSTALLATION_WRITE_ACTIONS and user_role_level(request.user) < RoleLevel.CHEF_SECTION:
            raise PermissionDenied
        if action in self.INSTALLATION_DELETE_ACTIONS and user_role_level(request.user) < RoleLevel.CHEF_SERVICE:
            raise PermissionDenied
        inst = self.get_object()
        tab = (request.POST.get('tab') or '').strip()
        tab = tab if tab in ('infos','histo','parts','hours','vibration','isolement','entretien') else ''
        qs = f"?tab={tab}" if tab else ''
        handler = ACTION_HANDLERS.get(action)
        if handler is None:
            return HttpResponseBadRequest('Action non prise en charge')
        return handler(self, request, inst, qs)


# (Standalone InstallationSettingsView removed; settings are now managed in global Settings > Installations)
# (LocationListView et la page /locations/ ont été retirées : la gestion des
# emplacements se fait désormais directement depuis les formulaires matériel et
# installation, avec création à la volée via _resoudre_emplacement ci-dessus —
# plus besoin d'un écran de gestion séparé.)


def _navire_selectionne(request):
    """Détermine le navire à configurer pour le plan visuel (ponts/zones).

    Un utilisateur rattaché à un navire précis (ship_id_for_user) ne peut
    configurer que celui-ci. Un utilisateur à accès flotte entière
    (is_master_admin, cf. matrix/core/scopes.py) choisit le navire via le
    sélecteur ?navire=, même principe que le sélecteur de navire de
    SettingsView (matrix/views.py). Renvoie (navire, liste_des_navires ou None
    si l'utilisateur n'a pas de sélecteur à afficher)."""
    if is_master_admin(request.user):
        navires = list(Ship.objects.order_by('name'))
        navire_id = request.GET.get('navire') or request.POST.get('navire_id')
        navire = None
        if navire_id:
            navire = next((n for n in navires if str(n.pk) == str(navire_id)), None)
        if navire is None:
            navire = navires[0] if navires else None
        return navire, navires
    navire_id = ship_id_for_user(request.user)
    navire = Ship.objects.filter(pk=navire_id).first() if navire_id else None
    return navire, None


class PlanNavireListView(LoginRequiredMixin, View):
    """Configuration des ponts d'un navire (Deck) : création, renommage,
    réordonnancement, suppression, et accès à l'éditeur de zones de chaque
    pont (voir PlanNavireDeckView ci-dessous).

    Réservée aux CHEF_SERVICE et rôles supérieurs (_peut_configurer_plan_navire),
    restreinte au navire de l'utilisateur — voir _navire_selectionne."""

    template_name = 'assets/plan_navire_list.html'

    def dispatch(self, request, *args, **kwargs):
        if not _peut_configurer_plan_navire(request.user):
            raise PermissionDenied("Réservé aux chefs de service et aux rôles supérieurs.")
        return super().dispatch(request, *args, **kwargs)

    def get(self, request):
        navire, navires = _navire_selectionne(request)
        contexte = {
            'navire': navire,
            'navires': navires,
            'multi_navires': navires is not None,
        }
        if navire is not None:
            contexte['ponts'] = Deck.objects.filter(ship=navire).order_by('order', 'name')
        return render(request, self.template_name, contexte)

    def post(self, request):
        navire, _navires = _navire_selectionne(request)
        if navire is None:
            messages.error(request, "Aucune unité sélectionnée : impossible de configurer un pont.")
            return redirect('plan-navire-list')

        action = request.POST.get('action')
        if action == 'create_deck':
            nom = request.POST.get('name', '').strip()
            if not nom:
                messages.error(request, "Le nom du pont est obligatoire.")
            else:
                ordre_max = Deck.objects.filter(ship=navire).aggregate(m=Max('order'))['m'] or 0
                Deck.objects.create(ship=navire, name=nom, order=ordre_max + 1)
                messages.success(request, "Pont créé.")
        elif action == 'rename_deck':
            pont = Deck.objects.filter(pk=request.POST.get('pk'), ship=navire).first()
            nom = request.POST.get('name', '').strip()
            if pont and nom:
                pont.name = nom
                pont.save(update_fields=['name'])
                messages.success(request, "Pont renommé.")
        elif action == 'delete_deck':
            supprimes, _detail = Deck.objects.filter(pk=request.POST.get('pk'), ship=navire).delete()
            if supprimes:
                messages.success(request, "Pont supprimé.")
        elif action in ('move_up', 'move_down'):
            pont = Deck.objects.filter(pk=request.POST.get('pk'), ship=navire).first()
            if pont:
                ponts = list(Deck.objects.filter(ship=navire).order_by('order', 'name'))
                idx = next((i for i, p in enumerate(ponts) if p.pk == pont.pk), None)
                cible = idx - 1 if action == 'move_up' else idx + 1
                if idx is not None and 0 <= cible < len(ponts):
                    autre = ponts[cible]
                    pont.order, autre.order = autre.order, pont.order
                    Deck.objects.bulk_update([pont, autre], ['order'])

        suffixe = f"?navire={navire.id}" if is_master_admin(request.user) else ""
        return redirect(f"{reverse('plan-navire-list')}{suffixe}")


def _pont_dans_perimetre(request, pk):
    """Renvoie le pont demandé si son navire correspond au périmètre de
    l'utilisateur (ou si celui-ci a un accès flotte entière), sinon lève un
    refus d'accès. Factorisé ici pour être partagé par l'éditeur du plan
    (PlanNavireDeckView, réservé CHEF_SERVICE+) et sa page de consultation
    (PlanNavireVueDeckView, ouverte à tous les rôles) : le contrôle de
    périmètre est identique, seul le seuil de rôle diffère entre les deux."""
    pont = get_object_or_404(Deck.objects.select_related('ship'), pk=pk)
    if not is_master_admin(request.user) and ship_id_for_user(request.user) != pont.ship_id:
        raise PermissionDenied("Ce pont n'appartient pas à votre unité.")
    return pont


class PlanNavireDeckView(LoginRequiredMixin, View):
    """Éditeur du plan d'un pont : téléversement de l'image de fond, et
    positionnement/édition/suppression des zones cliquables (Zone) dessinées
    dessus (rectangle par clic-glisser, coordonnées en pourcentage — voir le
    script de assets/plan_navire_deck.html, en JS natif sans dépendance
    externe). Une zone peut être laissée sans emplacement assigné (brouillon,
    cf. Zone.location) : la page de consultation (PlanNavireVueDeckView plus
    bas) s'appuie sur ce lien pour filtrer le matériel affiché lors d'un clic
    sur la zone.

    Même seuil et même contrôle de périmètre que PlanNavireListView."""

    template_name = 'assets/plan_navire_deck.html'

    def dispatch(self, request, *args, **kwargs):
        if not _peut_configurer_plan_navire(request.user):
            raise PermissionDenied("Réservé aux chefs de service et aux rôles supérieurs.")
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, pk):
        pont = _pont_dans_perimetre(request, pk)
        ponts_navire = list(Deck.objects.filter(ship=pont.ship).order_by('order', 'name'))
        idx = next((i for i, p in enumerate(ponts_navire) if p.pk == pont.pk), 0)
        zones = list(pont.zones.select_related('location').order_by('name'))
        contexte = {
            'pont': pont,
            'zones': zones,
            'zones_json': json.dumps([
                {
                    'id': z.id,
                    'name': z.name,
                    'location_id': z.location_id,
                    'points': z.points,
                }
                for z in zones
            ]),
            'emplacements': Location.objects.filter(ship=pont.ship).order_by('name'),
            'pont_precedent': ponts_navire[idx - 1] if idx > 0 else None,
            'pont_suivant': ponts_navire[idx + 1] if idx < len(ponts_navire) - 1 else None,
        }
        return render(request, self.template_name, contexte)

    def post(self, request, pk):
        pont = _pont_dans_perimetre(request, pk)
        action = request.POST.get('action')

        if action == 'upload_image':
            image = request.FILES.get('image')
            if image:
                pont.image = image
                pont.save(update_fields=['image'])
                messages.success(request, "Image du plan mise à jour.")
            else:
                messages.error(request, "Aucune image sélectionnée.")
        elif action in ('create_zone', 'update_zone'):
            self._enregistrer_zone(request, pont, action)
        elif action == 'delete_zone':
            supprimes, _detail = Zone.objects.filter(pk=request.POST.get('zone_id'), deck=pont).delete()
            if supprimes:
                messages.success(request, "Zone supprimée.")

        return redirect('plan-navire-deck', pk=pont.pk)

    def _enregistrer_zone(self, request, pont, action):
        nom = request.POST.get('zone_name', '').strip()
        if not nom:
            messages.error(request, "Le nom de la zone est obligatoire.")
            return
        contour = _valider_points_zone(request.POST.get('points'))
        if contour is None:
            messages.error(request, "Contour de zone invalide : redessinez la zone sur le plan.")
            return
        emplacement = _resoudre_emplacement(request, pont.ship)

        if action == 'update_zone':
            zone = Zone.objects.filter(pk=request.POST.get('zone_id'), deck=pont).first()
            if zone is None:
                messages.error(request, "Zone introuvable.")
                return
            zone.name = nom
            zone.points = contour
            zone.location = emplacement
            zone.save(update_fields=['name', 'points', 'location'])
            messages.success(request, "Zone mise à jour.")
        else:
            Zone.objects.create(deck=pont, name=nom, points=contour, location=emplacement)
            messages.success(request, "Zone créée.")


class PlanNavireVueView(LoginRequiredMixin, View):
    """Point d'entrée de la consultation du plan visuel du navire (rendu final
    de la sous-tâche 3/3), ouverte à tous les rôles — contrairement à
    PlanNavireListView (réservée CHEF_SERVICE+), voir la distinction des deux
    entrées de navigation dans base.html. Redirige vers le premier pont du
    navire de l'utilisateur (dans l'ordre Deck.order), ou affiche un message
    clair si aucun pont n'est encore configuré plutôt qu'une page cassée."""

    template_name = 'assets/plan_navire_vue.html'

    def get(self, request):
        navire, navires = _navire_selectionne(request)
        if navire is None:
            return render(request, self.template_name, {
                'navire': None, 'navires': navires, 'multi_navires': navires is not None,
            })
        premier_pont = Deck.objects.filter(ship=navire).order_by('order', 'name').first()
        if premier_pont is None:
            return render(request, self.template_name, {
                'navire': navire, 'navires': navires, 'multi_navires': navires is not None,
                'aucun_pont': True,
            })
        suffixe = f"?navire={navire.id}" if is_master_admin(request.user) else ""
        return redirect(f"{reverse('plan-navire-vue-deck', kwargs={'pk': premier_pont.pk})}{suffixe}")


class PlanNavireVueDeckView(LoginRequiredMixin, View):
    """Consultation en lecture seule du plan d'un pont : navigation par
    onglets entre les ponts du navire (dans l'ordre Deck.order), zones du plan
    affichées en overlay avec un code couleur selon l'état du matériel qu'elles
    contiennent (cf. Zone.etat_materiel : le pire état présent l'emporte), et
    clic sur une zone pour ouvrir la liste du matériel déjà filtrable
    (AssetListView), filtrée sur l'emplacement lié à cette zone.

    Ouverte à tous les rôles (contrairement à PlanNavireDeckView) : seul le
    contrôle de périmètre (navire de l'utilisateur) est conservé, via la même
    fonction _pont_dans_perimetre que l'éditeur."""

    template_name = 'assets/plan_navire_vue.html'

    def get(self, request, pk):
        pont = _pont_dans_perimetre(request, pk)
        ponts_navire = list(Deck.objects.filter(ship=pont.ship).order_by('order', 'name'))
        zones = list(pont.zones.select_related('location').order_by('name'))
        zones_affichees = []
        for zone in zones:
            rectangle = zone.rectangle_pourcent
            if rectangle is None:
                # Zone sans contour valide (ne devrait pas arriver via l'éditeur,
                # qui impose au moins 3 points) : on ne l'affiche simplement pas
                # plutôt que de faire échouer toute la page.
                continue
            zones_affichees.append({
                'zone': zone,
                'rectangle': rectangle,
                'etat': zone.etat_materiel,
                'url_materiel': (
                    f"{reverse('asset-list')}?location={zone.location_id}" if zone.location_id else None
                ),
            })
        contexte = {
            'navire': pont.ship,
            'pont': pont,
            'ponts': ponts_navire,
            'zones': zones_affichees,
            'multi_navires': is_master_admin(request.user),
        }
        return render(request, self.template_name, contexte)
