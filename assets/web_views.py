"""Fonctions partagées par les vues web de l'app assets, et point d'entrée
unique pour les URLs (assets/web_urls.py) et pour test_performance_n_plus_1.py.

Fichier re-découpé par sous-domaine fonctionnel (tâche Notion « [ARCH]
Découper training/web_views.py et re-découper assets/web_views.py + règle de
taille pour le Tech Lead »), suivant le même principe que le premier
découpage (assets/installation_actions.py) : un module par sous-domaine,
regroupés ici :
- assets/asset_views.py — matériel mobile (Asset) : fiche, liste, import Excel
- assets/installation_views.py — installations fixes : liste, fiche détaillée
- assets/scan_views.py — scan QR et contrôle visuel (Asset ET Installation)
- assets/plan_navire_views.py — plan visuel du navire (ponts, positionnement)

Ce fichier ne contient plus que les helpers RÉELLEMENT partagés entre
plusieurs de ces sous-domaines (rattachement parent, périmètre
organisationnel, emplacement, actions groupées) — les helpers propres à un
seul sous-domaine ont été déplacés avec lui. Les classes de vues sont
réimportées ci-dessous pour que `from .web_views import AssetListView` (ou
`from assets.web_views import ...`, cf. web_urls.py et
assets/tests/test_performance_n_plus_1.py) continue de fonctionner sans
changement de comportement. L'import a lieu APRÈS la définition des helpers
ci-dessous, car asset_views.py et installation_views.py les réimportent en
retour (`from .web_views import ...`) — même import circulaire volontaire,
déjà en place pour assets/installation_actions.py avant ce découpage."""
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect

from accounts.models import AuditLog
from matrix.core.role_thresholds import niveau_requis_pour
from matrix.core.roles import user_role_level
from org.models import Section, Sector, Service, Ship

from .models import Location


def _peut_gerer_rattachement_parent(user):
    """Seuls les CHEF_SERVICE et rôles supérieurs (par défaut, seuil
    configurable par navire : matrix/core/role_thresholds.py,
    "rattachement_parent_gestion") peuvent créer ou modifier le rattachement
    parent/enfant d'une installation ou d'un matériel (même seuil que les
    tâches d'entretien, cf. MAINTENANCE_WRITE_ACTIONS d'InstallationDetailView)."""
    return user_role_level(user) >= niveau_requis_pour(user, "rattachement_parent_gestion")


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
    """Affiche en français le(s) message(s) d'une ValidationError levée par
    full_clean() : protection anti-cycle sur le rattachement parent, fichier
    téléversé invalide (validators.py)... plutôt que de laisser remonter une
    erreur serveur non traitée."""
    if hasattr(erreur, "message_dict"):
        if "parent" in erreur.message_dict:
            messages.error(request, erreur.message_dict["parent"][0])
        else:
            for messages_champ in erreur.message_dict.values():
                for message in messages_champ:
                    messages.error(request, message)
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


# Réimports pour compatibilité (voir docstring de ce fichier ci-dessus) : placés
# après les helpers ci-dessus, jamais en tête de fichier, car asset_views.py et
# installation_views.py réimportent certains de ces helpers depuis CE module.
from .asset_views import (  # noqa: E402,F401
    AssetDetailView,
    AssetImportModeleView,
    AssetImportView,
    AssetListView,
)
from .installation_views import InstallationDetailView, InstallationListView  # noqa: E402,F401
from .plan_navire_views import (  # noqa: E402,F401
    PlanNavireDeckView,
    PlanNavireListView,
    PlanNavireVueDeckView,
    PlanNavireVueView,
)
from .scan_views import ScanQRView, StartVisualCheckView  # noqa: E402,F401
