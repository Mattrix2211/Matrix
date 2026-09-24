"""Vues des installations fixes (assets/web_views.py).

Sous-domaine extrait lors du re-découpage du fichier (tâche Notion « [ARCH]
Découper training/web_views.py et re-découper assets/web_views.py »,
assets/web_views.py ayant regrossi au-delà de 800 lignes) : liste (avec
métriques vibration/heures/isolement sur les cartes) et fiche détaillée
(mesures techniques, entretien, pièces) des installations fixes — symétrique
à assets/asset_views.py pour le matériel mobile. Les actions POST de la
fiche détaillée restent déléguées à assets/installation_actions.py, déjà
extrait lors d'un précédent découpage.

Refactor pur : reproduit exactement le comportement d'origine. Les quelques
helpers restés partagés avec le matériel mobile (rattachement parent,
périmètre organisationnel, emplacement, actions groupées...) restent
définis dans assets/web_views.py et sont importés ici — voir la docstring
de ce dernier fichier pour l'explication de l'import circulaire volontaire."""
import calendar
import json
from collections import defaultdict
from datetime import datetime, timedelta

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import models
from django.db.utils import OperationalError
from django.http import HttpResponseBadRequest
from django.shortcuts import redirect
from django.utils import timezone
from django.views.generic import DetailView, ListView

from accounts.models import AuditLog
from logistics.models import StockPiece
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
from matrix.core.roles import user_role_level
from matrix.core.scopes import scope_filters_for_user
from org.models import Section, Sector, Service, Ship

from .models import (
    Installation,
    InstallationBigrameChoice,
    InstallationEvent,
    InstallationExtraField,
    InstallationHourReading,
    InstallationIsolationReading,
    InstallationMaintenance,
    InstallationPart,
    InstallationVibrationReading,
    Location,
)
from .trend import jours_avant_franchissement_seuil
from .web_views import (
    _afficher_erreur_validation,
    _appliquer_bulk_suppression,
    _appliquer_bulk_update,
    _org_dans_perimetre,
    _parent_candidats,
    _perimetre_utilisateur,
    _peut_gerer_rattachement_parent,
    _resoudre_emplacement,
    _resoudre_parent_valide,
)

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


class InstallationListView(LoginRequiredMixin, ScopedQuerySetMixin, ListView):
    model = Installation
    template_name = 'assets/installations.html'
    context_object_name = 'installations'

    # Contrôle de rôle par action (T-SEC) : chaque action POST est associée à
    # une clé du registre des seuils configurables par navire
    # (matrix/core/role_thresholds.py) — installation_ecriture_simple pour la
    # création simple (CHEF_SECTION par défaut ; l'édition passe par la fiche détail),
    # installation_gestion_avancee pour les suppressions et les actions
    # groupées (CHEF_SERVICE par défaut), même seuil que
    # MAINTENANCE_WRITE_ACTIONS (InstallationDetailView) et AssetListView.
    ACTION_VERS_SEUIL = {
        'create_installation': 'installation_ecriture_simple',
        'delete_installation': 'installation_gestion_avancee',
        'bulk_update_location': 'installation_gestion_avancee',
        'bulk_update_ship': 'installation_gestion_avancee',
        'bulk_update_service': 'installation_gestion_avancee',
        'bulk_update_sector': 'installation_gestion_avancee',
        'bulk_update_section': 'installation_gestion_avancee',
        'bulk_delete_installations': 'installation_gestion_avancee',
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
        cle_seuil = self.ACTION_VERS_SEUIL.get(action)
        if cle_seuil is not None and user_role_level(request.user) < niveau_requis_pour(request.user, cle_seuil):
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
            # Création d'une installation : seuil déjà vérifié en tête de post() via
            # ACTION_VERS_SEUIL['create_installation'] = 'installation_ecriture_simple'
            # (configurable par navire) — ne pas dupliquer le contrôle avec
            # _peut_gerer_materiel, sous peine de rendre la configuration sans
            # effet réel sur cette action (bug corrigé après refus du Tech Lead).
            # L'édition et la suppression restent volontairement ouvertes à tous les
            # utilisateurs connectés (comportement existant, cf. tests T2/T3).
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
# qu'en tête de fichier : installation_actions.py importe lui-même certains
# helpers (_org_dans_perimetre, _resoudre_parent_valide, _afficher_erreur_validation)
# depuis assets/web_views.py — les définir avant cet import (déjà fait, importés
# ci-dessus depuis web_views.py) évite un import circulaire.
from .installation_actions import ACTION_HANDLERS


class InstallationDetailView(LoginRequiredMixin, ScopedQuerySetMixin, DetailView):
    model = Installation
    template_name = 'assets/installation_detail.html'

    # Actions liées aux tâches d'entretien (InstallationMaintenance) : réservées
    # par défaut aux CHEF_SERVICE et au-dessus, seuil configurable par navire
    # (matrix/core/role_thresholds.py, "installation_entretien_gestion").
    MAINTENANCE_WRITE_ACTIONS = {
        'add_maintenance',
        'edit_maintenance',
        'delete_maintenance',
        'add_maintenance_attachment',
        'delete_maintenance_attachment',
    }

    # Actions de gestion de la fiche installation elle-même (hors tâches d'entretien) :
    # même seuils que sur la liste (AssetListView/InstallationListView) —
    # installation_ecriture_simple pour l'édition simple,
    # installation_gestion_avancee pour la suppression. Corrige le
    # contournement possible via la fiche détail, ces deux actions n'étant pas
    # dans MAINTENANCE_WRITE_ACTIONS (T-SEC).
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
        ctx['vibration_retard_jours'] = -next_days if next_days is not None and next_days < 0 else 0
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
        if action in self.MAINTENANCE_WRITE_ACTIONS and user_role_level(request.user) < niveau_requis_pour(request.user, 'installation_entretien_gestion'):
            raise PermissionDenied
        if action in self.INSTALLATION_WRITE_ACTIONS and user_role_level(request.user) < niveau_requis_pour(request.user, 'installation_ecriture_simple'):
            raise PermissionDenied
        if action in self.INSTALLATION_DELETE_ACTIONS and user_role_level(request.user) < niveau_requis_pour(request.user, 'installation_gestion_avancee'):
            raise PermissionDenied
        inst = self.get_object()
        tab = (request.POST.get('tab') or '').strip()
        tab = tab if tab in ('infos','histo','parts','hours','vibration','isolement','entretien') else ''
        qs = f"?tab={tab}" if tab else ''
        handler = ACTION_HANDLERS.get(action)
        if handler is None:
            return HttpResponseBadRequest('Action non prise en charge')
        return handler(self, request, inst, qs)
