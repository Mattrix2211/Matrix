from django.views.generic import DetailView, View, ListView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect
from django.utils import timezone
from django.views.generic import TemplateView
from django.http import JsonResponse, HttpResponseBadRequest, HttpResponse
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.db.utils import OperationalError
from django.db.models import Sum
from django.db.models.functions import TruncMonth
from django.db import models
from .models import Asset, AssetType, Location, Installation, AssetFolder, InstallationExtraField, AssetDocument
from .models import InstallationBigrameChoice, InstallationEvent, InstallationEventAttachment, InstallationPart, InstallationHourReading, InstallationVibrationReading, InstallationIsolationReading
from .models import InstallationMaintenance, InstallationMaintenanceAttachment
from datetime import datetime, time
from datetime import timedelta
from maintenance.models import MaintenanceOccurrence, MaintenancePlan
from matrix.core.roles import user_role_level, RoleLevel
from accounts.models import AuditLog
from org.models import Ship, Service, Sector, Section
import json
import io
import calendar
try:
    from openpyxl import Workbook
except Exception:
    Workbook = None

class AssetDetailView(LoginRequiredMixin, DetailView):
    model = Asset
    template_name = 'assets/detail.html'

class StartVisualCheckView(LoginRequiredMixin, View):
    def post(self, request, pk):
        if user_role_level(request.user) < RoleLevel.CHEF_SECTION:
            raise PermissionDenied
        try:
            asset = Asset.objects.get(pk=pk)
        except Asset.DoesNotExist:
            return HttpResponseBadRequest('Asset not found')
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


class AssetListView(LoginRequiredMixin, ListView):
    model = Asset
    template_name = 'assets/list.html'
    context_object_name = 'assets'

    def get_queryset(self):
        qs = Asset.objects.select_related('asset_type', 'ship', 'service', 'sector', 'section', 'location', 'folder').order_by('ship__name', 'service__name', 'sector__name', 'section__name', 'asset_type__name')
        ship_id = self.request.GET.get('ship')
        service_id = self.request.GET.get('service')
        sector_id = self.request.GET.get('sector')
        section_id = self.request.GET.get('section')
        status = self.request.GET.get('status')
        asset_type_id = self.request.GET.get('type')
        folder_id = self.request.GET.get('folder')
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
        if folder_id:
            qs = qs.filter(folder_id=folder_id)
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
        ctx['export_url'] = self.request.build_absolute_uri('?' + (self.request.META.get('QUERY_STRING') or '') + ('&' if self.request.META.get('QUERY_STRING') else '') + 'export=xlsx')
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
        if request.GET.get('export') == 'xlsx' and Workbook is not None:
            qs = self.get_queryset()
            wb = Workbook(); ws = wb.active; ws.title = 'Matériels'
            ws.append(['Type', 'Identifiant interne', 'N° série', 'Statut', 'Criticité', 'Navire', 'Service', 'Secteur', 'Section', 'Emplacement'])
            for a in qs:
                ws.append([
                    a.asset_type.name,
                    a.internal_id,
                    a.serial_number,
                    a.status,
                    a.criticality,
                    a.ship.name if a.ship else '',
                    a.service.name if a.service else '',
                    a.sector.name if a.sector else '',
                    a.section.name if a.section else '',
                    a.location.name if a.location else '',
                ])
            buf = io.BytesIO(); wb.save(buf); buf.seek(0)
            resp = HttpResponse(buf.read(), content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
            resp['Content-Disposition'] = 'attachment; filename=materiels.xlsx'
            AuditLog.objects.create(actor=request.user, action='export_assets_xlsx', target_user=None, details=f'rows={qs.count()}')
            return resp
        return super().get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        action = request.POST.get('action')
        # Bulk actions
        if action in (
            'bulk_update_status', 'bulk_update_location', 'bulk_update_ship',
            'bulk_update_service', 'bulk_update_sector', 'bulk_update_section',
            'bulk_delete_assets'
        ):
            ids = request.POST.getlist('selected_ids')
            assets = Asset.objects.filter(id__in=ids)
            count = assets.count()
            if action == 'bulk_update_status':
                status = request.POST.get('status')
                for a in assets:
                    a.status = status
                    a.save(update_fields=['status'])
                    AuditLog.objects.create(actor=request.user, action='bulk_update_asset_status', details=f'status={status}')
                messages.success(request, f'Statut mis à jour pour {count} matériel(s).')
            elif action == 'bulk_update_location':
                loc_id = request.POST.get('location_id')
                loc = Location.objects.filter(pk=loc_id).first()
                for a in assets:
                    a.location = loc
                    a.save(update_fields=['location'])
                    AuditLog.objects.create(actor=request.user, action='bulk_update_asset_location', details=f'location_id={loc_id}')
                messages.success(request, f'Emplacement mis à jour pour {count} matériel(s).')
            elif action == 'bulk_update_ship':
                ship_id = request.POST.get('ship_id')
                ship = Ship.objects.filter(pk=ship_id).first()
                for a in assets:
                    a.ship = ship
                    a.save(update_fields=['ship'])
                    AuditLog.objects.create(actor=request.user, action='bulk_update_asset_ship', details=f'ship_id={ship_id}')
                messages.success(request, f'Navire mis à jour pour {count} matériel(s).')
            elif action == 'bulk_update_service':
                service_id = request.POST.get('service_id')
                sv = Service.objects.filter(pk=service_id).first()
                for a in assets:
                    a.service = sv
                    a.save(update_fields=['service'])
                    AuditLog.objects.create(actor=request.user, action='bulk_update_asset_service', details=f'service_id={service_id}')
                messages.success(request, f'Service mis à jour pour {count} matériel(s).')
            elif action == 'bulk_update_sector':
                sector_id = request.POST.get('sector_id')
                sc = Sector.objects.filter(pk=sector_id).first()
                for a in assets:
                    a.sector = sc
                    a.save(update_fields=['sector'])
                    AuditLog.objects.create(actor=request.user, action='bulk_update_asset_sector', details=f'sector_id={sector_id}')
                messages.success(request, f'Secteur mis à jour pour {count} matériel(s).')
            elif action == 'bulk_update_section':
                section_id = request.POST.get('section_id')
                se = Section.objects.filter(pk=section_id).first()
                for a in assets:
                    a.section = se
                    a.save(update_fields=['section'])
                    AuditLog.objects.create(actor=request.user, action='bulk_update_asset_section', details=f'section_id={section_id}')
                messages.success(request, f'Section mise à jour pour {count} matériel(s).')
            elif action == 'bulk_delete_assets':
                for a in assets:
                    AuditLog.objects.create(actor=request.user, action='bulk_delete_asset', details=f'id={a.id}')
                assets.delete()
                messages.success(request, f'{count} matériel(s) supprimé(s).')
            return redirect('asset-list')

        # Folder operations
        if action == 'create_folder':
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
            return redirect('asset-list')
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
            return redirect('asset-list')
        if action == 'delete_folder':
            pk = request.POST.get('pk')
            AssetFolder.objects.filter(pk=pk).delete()
            AuditLog.objects.create(actor=request.user, action='delete_asset_folder', details=f'id={pk}')
            messages.success(request, 'Dossier supprimé.')
            return redirect('asset-list')
        if action == 'move_asset_to_folder':
            asset_id = request.POST.get('asset_id')
            folder_id = request.POST.get('folder_id')
            try:
                a = Asset.objects.get(pk=asset_id)
                a.folder = AssetFolder.objects.filter(pk=folder_id).first() if folder_id else None
                a.save(update_fields=['folder'])
                return JsonResponse({'ok': True})
            except Asset.DoesNotExist:
                return JsonResponse({'ok': False}, status=400)

        # Single create/edit/delete
        if action == 'create_asset':
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
            location_id = request.POST.get('location_id')
            folder_id = request.POST.get('folder_id') or self.request.GET.get('folder')
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
                    return redirect('asset-list')
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
                if location_id:
                    asset.location = Location.objects.filter(pk=location_id).first()
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
            try:
                asset = Asset.objects.get(pk=pk)
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
                asset.ship = Ship.objects.filter(pk=request.POST.get('ship_id')).first() if request.POST.get('ship_id') else None
                asset.service = Service.objects.filter(pk=request.POST.get('service_id')).first() if request.POST.get('service_id') else None
                asset.sector = Sector.objects.filter(pk=request.POST.get('sector_id')).first() if request.POST.get('sector_id') else None
                asset.section = Section.objects.filter(pk=request.POST.get('section_id')).first() if request.POST.get('section_id') else None
                asset.location = Location.objects.filter(pk=request.POST.get('location_id')).first() if request.POST.get('location_id') else None
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
                pass
        elif action == 'delete_asset':
            pk = request.POST.get('pk')
            Asset.objects.filter(pk=pk).delete()
            messages.success(request, 'Matériel supprimé.')
        elif action == 'delete_asset_document':
            pk = request.POST.get('pk')
            doc_id = request.POST.get('document_id')
            try:
                asset = Asset.objects.get(pk=pk)
                AssetDocument.objects.filter(pk=doc_id, asset=asset).delete()
                messages.success(request, 'Document supprimé.')
            except Asset.DoesNotExist:
                messages.error(request, 'Matériel introuvable.')
        return redirect('asset-list')


class InstallationListView(LoginRequiredMixin, ListView):
    model = Installation
    template_name = 'assets/installations.html'
    context_object_name = 'installations'

    def get_queryset(self):
        qs = Installation.objects.select_related('ship', 'service', 'sector', 'section', 'location').order_by('ship__name', 'service__name', 'sector__name', 'section__name', 'designation')
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
        # Prépare les métriques pour affichage sur les cartes (vibration, heures, isolement)
        try:
            installations = list(ctx.get('installations', []))
        except Exception:
            installations = []
        for it in installations:
            # Vibrations: dernier état et prochaine échéance
            try:
                last_vib = (
                    InstallationVibrationReading.objects
                    .filter(installation=it)
                    .order_by('-date')
                    .first()
                )
            except OperationalError:
                last_vib = None
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
            try:
                hour_logs = list(
                    InstallationHourReading.objects
                    .filter(installation=it)
                    .order_by('-date')
                )
            except OperationalError:
                hour_logs = []
            total = sum(float(r.hours or 0) for r in hour_logs) if hour_logs else 0.0
            last_visit = next((r for r in hour_logs if getattr(r, 'is_visit', False)), None)
            since_last = sum(float(r.hours or 0) for r in hour_logs if last_visit and r.date > last_visit.date) if hour_logs and last_visit else total
            it.hours_total_card = total
            it.hours_last_visit_card = since_last
            # Isolement: dernière mesure
            try:
                last_iso = (
                    InstallationIsolationReading.objects
                    .filter(installation=it)
                    .order_by('-date')
                    .first()
                )
            except OperationalError:
                last_iso = None
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

    def post(self, request, *args, **kwargs):
        action = request.POST.get('action')
        if action in (
            'bulk_update_location', 'bulk_update_ship', 'bulk_update_service',
            'bulk_update_sector', 'bulk_update_section', 'bulk_delete_installations'
        ):
            ids = request.POST.getlist('selected_ids')
            items = Installation.objects.filter(id__in=ids)
            count = items.count()
            if action == 'bulk_update_location':
                loc_id = request.POST.get('location_id')
                loc = Location.objects.filter(pk=loc_id).first()
                for it in items:
                    it.location = loc
                    it.save(update_fields=['location'])
                    AuditLog.objects.create(actor=request.user, action='bulk_update_installation_location', details=f'location_id={loc_id}')
                messages.success(request, f'Emplacement mis à jour pour {count} installation(s).')
            elif action == 'bulk_update_ship':
                ship_id = request.POST.get('ship_id')
                ship = Ship.objects.filter(pk=ship_id).first()
                for it in items:
                    it.ship = ship
                    it.save(update_fields=['ship'])
                    AuditLog.objects.create(actor=request.user, action='bulk_update_installation_ship', details=f'ship_id={ship_id}')
                messages.success(request, f'Navire mis à jour pour {count} installation(s).')
            elif action == 'bulk_update_service':
                service_id = request.POST.get('service_id')
                sv = Service.objects.filter(pk=service_id).first()
                for it in items:
                    it.service = sv
                    it.save(update_fields=['service'])
                    AuditLog.objects.create(actor=request.user, action='bulk_update_installation_service', details=f'service_id={service_id}')
                messages.success(request, f'Service mis à jour pour {count} installation(s).')
            elif action == 'bulk_update_sector':
                sector_id = request.POST.get('sector_id')
                sc = Sector.objects.filter(pk=sector_id).first()
                for it in items:
                    it.sector = sc
                    it.save(update_fields=['sector'])
                    AuditLog.objects.create(actor=request.user, action='bulk_update_installation_sector', details=f'sector_id={sector_id}')
                messages.success(request, f'Secteur mis à jour pour {count} installation(s).')
            elif action == 'bulk_update_section':
                section_id = request.POST.get('section_id')
                se = Section.objects.filter(pk=section_id).first()
                for it in items:
                    it.section = se
                    it.save(update_fields=['section'])
                    AuditLog.objects.create(actor=request.user, action='bulk_update_installation_section', details=f'section_id={section_id}')
                messages.success(request, f'Section mise à jour pour {count} installation(s).')
            elif action == 'bulk_delete_installations':
                for it in items:
                    AuditLog.objects.create(actor=request.user, action='bulk_delete_installation', details=f'id={it.id}')
                items.delete()
                messages.success(request, f'{count} installation(s) supprimée(s).')
            return redirect('installation-list')

        if action == 'create_installation':
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
            location_id = request.POST.get('location_id')
            iso_period = (request.POST.get('iso_periodicity') or 'M').strip().upper()
            it = Installation(
                designation=designation,
                reference=reference,
                marque=marque,
                gisement=gisement,
                local=local,
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
            if location_id:
                it.location = Location.objects.filter(pk=location_id).first()
            if bigrame_id:
                it.bigrame = InstallationBigrameChoice.objects.filter(pk=bigrame_id).first()
            if iso_period in ('M','T','A'):
                it.iso_periodicity = iso_period
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
            try:
                it = Installation.objects.get(pk=pk)
                it.designation = request.POST.get('designation', it.designation).strip()
                it.reference = request.POST.get('reference', it.reference).strip()
                it.marque = request.POST.get('marque', it.marque).strip()
                it.gisement = request.POST.get('gisement', it.gisement).strip()
                it.local = request.POST.get('local', it.local).strip()
                bigrame_id = request.POST.get('bigrame_id')
                photo = request.FILES.get('photo')
                if photo:
                    it.photo = photo
                it.ship = Ship.objects.filter(pk=request.POST.get('ship_id')).first() if request.POST.get('ship_id') else None
                it.service = Service.objects.filter(pk=request.POST.get('service_id')).first() if request.POST.get('service_id') else None
                it.sector = Sector.objects.filter(pk=request.POST.get('sector_id')).first() if request.POST.get('sector_id') else None
                it.section = Section.objects.filter(pk=request.POST.get('section_id')).first() if request.POST.get('section_id') else None
                it.location = Location.objects.filter(pk=request.POST.get('location_id')).first() if request.POST.get('location_id') else None
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
                pass
        elif action == 'delete_installation':
            pk = request.POST.get('pk')
            Installation.objects.filter(pk=pk).delete()
            messages.success(request, 'Installation supprimée.')
        return redirect('installation-list')


class InstallationDetailView(LoginRequiredMixin, DetailView):
    model = Installation
    template_name = 'assets/installation_detail.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['ships'] = Ship.objects.order_by('name')
        ctx['services'] = Service.objects.select_related('ship').order_by('name')
        ctx['sectors'] = Sector.objects.select_related('service', 'service__ship').order_by('name')
        ctx['sections'] = Section.objects.select_related('sector', 'sector__service', 'sector__service__ship').order_by('name')
        ctx['bigrames'] = InstallationBigrameChoice.objects.filter(active=True).order_by('name')
        ctx['events'] = (
            InstallationEvent.objects
            .filter(installation=self.object)
            .select_related('created_by')
            .prefetch_related('attachments')
            .order_by('-date')
        )
        ctx['parts'] = InstallationPart.objects.filter(installation=self.object).order_by('name')
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
        inst = self.get_object()
        tab = (request.POST.get('tab') or '').strip()
        tab = tab if tab in ('infos','histo','parts','hours','vibration','isolement','entretien') else ''
        qs = f"?tab={tab}" if tab else ''
        if action == 'edit_installation':
            pk = request.POST.get('pk')
            try:
                it = Installation.objects.get(pk=pk)
                it.designation = request.POST.get('designation', it.designation).strip()
                it.reference = request.POST.get('reference', it.reference).strip()
                it.marque = request.POST.get('marque', it.marque).strip()
                it.gisement = request.POST.get('gisement', it.gisement).strip()
                it.local = request.POST.get('local', it.local).strip()
                bigrame_id = request.POST.get('bigrame_id')
                photo = request.FILES.get('photo')
                if photo:
                    it.photo = photo
                it.ship = Ship.objects.filter(pk=request.POST.get('ship_id')).first() if request.POST.get('ship_id') else None
                it.service = Service.objects.filter(pk=request.POST.get('service_id')).first() if request.POST.get('service_id') else None
                it.sector = Sector.objects.filter(pk=request.POST.get('sector_id')).first() if request.POST.get('sector_id') else None
                it.section = Section.objects.filter(pk=request.POST.get('section_id')).first() if request.POST.get('section_id') else None
                it.bigrame = InstallationBigrameChoice.objects.filter(pk=bigrame_id).first() if bigrame_id else None
                # Périodicité isolement
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
                messages.error(request, "Installation introuvable")
            return redirect(f"/installations/{pk}/{qs}")
        elif action == 'delete_installation':
            pk = request.POST.get('pk')
            Installation.objects.filter(pk=pk).delete()
            messages.success(request, 'Installation supprimée.')
            return redirect('installation-list')
        elif action == 'add_event':
            label = request.POST.get('label', '').strip()
            notes = request.POST.get('notes', '').strip()
            date_str = request.POST.get('date', '').strip()
            if not label:
                messages.error(request, "Le champ 'Événement' est requis.")
                return redirect(f"/installations/{inst.id}/{qs}")
            # Parse date JJ/MM/AAAA
            ev_date = None
            if date_str:
                try:
                    dt = datetime.strptime(date_str, '%d/%m/%Y')
                    ev_date = timezone.make_aware(datetime.combine(dt.date(), time(0, 0)), timezone.get_current_timezone())
                except Exception:
                    ev_date = None
            ev = InstallationEvent.objects.create(
                installation=inst,
                label=label,
                notes=notes,
                date=ev_date or timezone.now(),
                created_by=request.user,
                updated_by=request.user,
            )
            for f in request.FILES.getlist('attachments'):
                InstallationEventAttachment.objects.create(event=ev, file=f, created_by=request.user, updated_by=request.user)
            AuditLog.objects.create(actor=request.user, action='add_installation_event', details=f'installation_id={inst.id}, event_id={ev.id}')
            messages.success(request, 'Événement ajouté.')
            return redirect(f"/installations/{inst.id}/{qs}")
        elif action == 'edit_event':
            event_id = request.POST.get('event_id')
            try:
                ev = InstallationEvent.objects.get(pk=event_id, installation=inst)
            except InstallationEvent.DoesNotExist:
                messages.error(request, "Événement introuvable")
                return redirect(f"/installations/{inst.id}/{qs}")
            ev.label = request.POST.get('label', ev.label).strip()
            ev.notes = request.POST.get('notes', ev.notes or '').strip()
            date_str = request.POST.get('date', '').strip()
            if date_str:
                try:
                    dt = datetime.strptime(date_str, '%d/%m/%Y')
                    new_dt = timezone.make_aware(datetime.combine(dt.date(), time(0, 0)), timezone.get_current_timezone())
                    ev.date = new_dt
                except Exception:
                    pass
            ev.updated_by = request.user
            ev.save()
            for f in request.FILES.getlist('attachments'):
                InstallationEventAttachment.objects.create(event=ev, file=f, created_by=request.user, updated_by=request.user)
            AuditLog.objects.create(actor=request.user, action='edit_installation_event', details=f'event_id={ev.id}')
            messages.success(request, "Événement mis à jour.")
            return redirect(f"/installations/{inst.id}/{qs}")
        elif action == 'delete_event_attachment':
            event_id = request.POST.get('event_id')
            att_id = request.POST.get('attachment_id')
            try:
                ev = InstallationEvent.objects.get(pk=event_id, installation=inst)
            except InstallationEvent.DoesNotExist:
                messages.error(request, "Événement introuvable")
                return redirect(f"/installations/{inst.id}/")
            deleted = InstallationEventAttachment.objects.filter(event=ev, pk=att_id).delete()[0]
            if deleted:
                AuditLog.objects.create(actor=request.user, action='delete_installation_event_attachment', details=f'attachment_id={att_id}')
                messages.success(request, 'Pièce jointe supprimée.')
            else:
                messages.error(request, "Pièce jointe introuvable")
            return redirect(f"/installations/{inst.id}/{qs}")
        elif action == 'delete_event':
            event_id = request.POST.get('event_id')
            InstallationEvent.objects.filter(pk=event_id, installation=inst).delete()
            AuditLog.objects.create(actor=request.user, action='delete_installation_event', details=f'event_id={event_id}')
            messages.success(request, 'Événement supprimé.')
            return redirect(f"/installations/{inst.id}/{qs}")
        # Entretien: création d'une tâche
        elif action == 'add_maintenance':
            periodicity = (request.POST.get('periodicity') or '').strip()
            title = (request.POST.get('title') or '').strip()
            description = (request.POST.get('description') or '').strip()
            # Parse durée HH:MM -> minutes
            try:
                hours = int((request.POST.get('planned_duration_hours') or '0') or 0)
            except Exception:
                hours = 0
            try:
                minutes = int((request.POST.get('planned_duration_minutes') or '0') or 0)
            except Exception:
                minutes = 0
            minutes = max(0, min(59, minutes))
            duration = max(0, hours * 60 + minutes)
            people = int((request.POST.get('people_count') or '1') or 1)
            competence = (request.POST.get('competence') or 'BORD').strip().upper()
            if competence not in ('BORD','SLM','INDUSTRIEL'):
                competence = 'BORD'
            if not title:
                messages.error(request, "Le titre est requis.")
                return redirect(f"/installations/{inst.id}/{qs}")
            m = InstallationMaintenance.objects.create(
                installation=inst,
                periodicity=periodicity or '—',
                title=title,
                description=description,
                planned_duration_min=max(0, duration),
                people_count=max(1, people),
                competence=competence,
                created_by=request.user,
                updated_by=request.user,
            )
            for f in request.FILES.getlist('attachments'):
                InstallationMaintenanceAttachment.objects.create(maintenance=m, file=f, created_by=request.user, updated_by=request.user)
            AuditLog.objects.create(actor=request.user, action='add_installation_maintenance', details=f'maintenance_id={m.id}')
            messages.success(request, "Entretien ajouté.")
            return redirect(f"/installations/{inst.id}/{qs}")
            for f in request.FILES.getlist('attachments'):
                InstallationMaintenanceAttachment.objects.create(maintenance=m, file=f, created_by=request.user, updated_by=request.user)
            AuditLog.objects.create(actor=request.user, action='add_installation_maintenance', details=f'maintenance_id={m.id}')
            messages.success(request, "Entretien ajouté.")
            return redirect(f"/installations/{inst.id}/{qs}")
        # Entretien: ajout de PJ sur une tâche existante
        elif action == 'add_maintenance_attachment':
            mid = request.POST.get('maintenance_id')
            try:
                m = InstallationMaintenance.objects.get(pk=mid, installation=inst)
            except InstallationMaintenance.DoesNotExist:
                messages.error(request, "Tâche d'entretien introuvable")
                return redirect(f"/installations/{inst.id}/{qs}")
            count = 0
            for f in request.FILES.getlist('attachments'):
                InstallationMaintenanceAttachment.objects.create(maintenance=m, file=f, created_by=request.user, updated_by=request.user)
                count += 1
            AuditLog.objects.create(actor=request.user, action='add_installation_maintenance_attachment', details=f'maintenance_id={m.id}; files={count}')
            messages.success(request, f"{count} pièce(s) jointe(s) ajoutée(s).")
            return redirect(f"/installations/{inst.id}/{qs}")
        # Entretien: suppression d'une PJ
        elif action == 'delete_maintenance_attachment':
            mid = request.POST.get('maintenance_id')
            att_id = request.POST.get('attachment_id')
            try:
                m = InstallationMaintenance.objects.get(pk=mid, installation=inst)
            except InstallationMaintenance.DoesNotExist:
                messages.error(request, "Tâche d'entretien introuvable")
                return redirect(f"/installations/{inst.id}/{qs}")
            deleted = InstallationMaintenanceAttachment.objects.filter(maintenance=m, pk=att_id).delete()[0]
            if deleted:
                AuditLog.objects.create(actor=request.user, action='delete_installation_maintenance_attachment', details=f'attachment_id={att_id}')
                messages.success(request, 'Pièce jointe supprimée.')
            else:
                messages.error(request, "Pièce jointe introuvable")
            return redirect(f"/installations/{inst.id}/{qs}")
        # Entretien: suppression de la tâche
        elif action == 'delete_maintenance':
            mid = request.POST.get('maintenance_id')
            InstallationMaintenance.objects.filter(pk=mid, installation=inst).delete()
            AuditLog.objects.create(actor=request.user, action='delete_installation_maintenance', details=f'maintenance_id={mid}')
            messages.success(request, "Entretien supprimé.")
            return redirect(f"/installations/{inst.id}/{qs}")
        elif action == 'edit_maintenance':
            mid = request.POST.get('maintenance_id')
            try:
                m = InstallationMaintenance.objects.get(pk=mid, installation=inst)
            except InstallationMaintenance.DoesNotExist:
                messages.error(request, "Tâche d'entretien introuvable")
                return redirect(f"/installations/{inst.id}/{qs}")
            m.periodicity = (request.POST.get('periodicity') or m.periodicity or '').strip()
            m.title = (request.POST.get('title') or m.title or '').strip()
            m.description = (request.POST.get('description') or m.description or '').strip()
            try:
                hours = int((request.POST.get('planned_duration_hours') or '') or 0)
            except Exception:
                hours = m.planned_duration_min // 60
            try:
                minutes = int((request.POST.get('planned_duration_minutes') or '') or 0)
            except Exception:
                minutes = m.planned_duration_min % 60
            minutes = max(0, min(59, minutes))
            m.planned_duration_min = max(0, hours * 60 + minutes)
            try:
                people = int((request.POST.get('people_count') or '') or m.people_count)
            except Exception:
                people = m.people_count
            m.people_count = max(1, people)
            comp = (request.POST.get('competence') or m.competence or '').strip().upper()
            m.competence = comp if comp in ('BORD','SLM','INDUSTRIEL') else m.competence
            m.updated_by = request.user
            m.save()
            # Ajout de nouvelles pièces jointes lors de la modification
            for f in request.FILES.getlist('attachments'):
                InstallationMaintenanceAttachment.objects.create(maintenance=m, file=f, created_by=request.user, updated_by=request.user)
            AuditLog.objects.create(actor=request.user, action='edit_installation_maintenance', details=f'maintenance_id={m.id}')
            messages.success(request, "Entretien mis à jour.")
            return redirect(f"/installations/{inst.id}/{qs}")
        elif action == 'add_part':
            name = request.POST.get('designation', '').strip()
            nno = request.POST.get('nno', '').strip()
            reference = request.POST.get('reference', '').strip()
            marque = request.POST.get('marque', '').strip()
            if not name:
                messages.error(request, "La désignation de la pièce est requise.")
                return redirect(f"/installations/{inst.id}/{qs}")
            p = InstallationPart.objects.create(
                installation=inst,
                name=name,
                nno=nno,
                reference=reference,
                marque=marque,
                created_by=request.user,
                updated_by=request.user,
            )
            photo = request.FILES.get('photo')
            if photo:
                p.photo = photo
                p.save(update_fields=['photo'])
            AuditLog.objects.create(actor=request.user, action='add_installation_part', details=f'part_id={p.id}')
            messages.success(request, 'Pièce ajoutée.')
            return redirect(f"/installations/{inst.id}/{qs}")
        elif action == 'edit_part':
            part_id = request.POST.get('part_id')
            try:
                p = InstallationPart.objects.get(pk=part_id, installation=inst)
            except InstallationPart.DoesNotExist:
                messages.error(request, "Pièce introuvable")
                return redirect(f"/installations/{inst.id}/")
            p.name = request.POST.get('designation', p.name).strip()
            p.nno = request.POST.get('nno', p.nno or '').strip()
            p.reference = request.POST.get('reference', p.reference or '').strip()
            p.marque = request.POST.get('marque', p.marque or '').strip()
            photo = request.FILES.get('photo')
            if photo:
                p.photo = photo
            p.updated_by = request.user
            p.save()
            AuditLog.objects.create(actor=request.user, action='edit_installation_part', details=f'part_id={p.id}')
            messages.success(request, 'Pièce mise à jour.')
            
        elif action == 'delete_part':
            part_id = request.POST.get('part_id')
            InstallationPart.objects.filter(pk=part_id, installation=inst).delete()
            AuditLog.objects.create(actor=request.user, action='delete_installation_part', details=f'part_id={part_id}')
            messages.success(request, 'Pièce supprimée.')
            return redirect(f"/installations/{inst.id}/{qs}")
        elif action == 'add_hour_reading':
            date_str = request.POST.get('date', '').strip()
            hours_str = request.POST.get('hours', '').strip()
            is_visit = bool(request.POST.get('is_visit'))
            if not hours_str:
                messages.error(request, "Le champ 'Heures' est requis.")
                return redirect(f"/installations/{inst.id}/{qs}")
            # Parse date JJ/MM/AAAA -> DateField
            rd_date = None
            if date_str:
                try:
                    dt = datetime.strptime(date_str, '%d/%m/%Y').date()
                    rd_date = dt
                except Exception:
                    rd_date = None
            try:
                val = float(hours_str.replace(',', '.'))
                if val < 0:
                    val = 0.0
            except Exception:
                messages.error(request, "Valeur d'heures invalide.")
                return redirect(f"/installations/{inst.id}/{qs}")
            try:
                reading = InstallationHourReading.objects.create(
                    installation=inst,
                    date=rd_date or timezone.localdate(),
                    hours=val,
                    is_visit=is_visit,
                    created_by=request.user,
                    updated_by=request.user,
                )
            except OperationalError:
                messages.error(request, "Base non à jour: appliquez les migrations (assets).")
                return redirect(f"/installations/{inst.id}/{qs}")
            AuditLog.objects.create(actor=request.user, action='add_installation_hour_reading', details=f'reading_id={reading.id}')
            messages.success(request, "Relevé d'heures ajouté.")
            return redirect(f"/installations/{inst.id}/{qs}")
        elif action == 'edit_hour_reading':
            rid = request.POST.get('reading_id')
            try:
                reading = InstallationHourReading.objects.get(pk=rid, installation=inst)
            except InstallationHourReading.DoesNotExist:
                messages.error(request, "Relevé introuvable")
                return redirect(f"/installations/{inst.id}/{qs}")
            date_str = request.POST.get('date', '').strip()
            hours_str = request.POST.get('hours', '').strip()
            is_visit = bool(request.POST.get('is_visit'))
            if date_str:
                try:
                    reading.date = datetime.strptime(date_str, '%d/%m/%Y').date()
                except Exception:
                    pass
            if hours_str:
                try:
                    val = float(hours_str.replace(',', '.'))
                    reading.hours = val if val >= 0 else 0.0
                except Exception:
                    pass
            try:
                reading.is_visit = is_visit
                reading.updated_by = request.user
                reading.save()
            except OperationalError:
                messages.error(request, "Base non à jour: appliquez les migrations (assets).")
                return redirect(f"/installations/{inst.id}/{qs}")
            AuditLog.objects.create(actor=request.user, action='edit_installation_hour_reading', details=f'reading_id={reading.id}')
            messages.success(request, "Relevé mis à jour.")
            return redirect(f"/installations/{inst.id}/{qs}")
        elif action == 'delete_hour_reading':
            rid = request.POST.get('reading_id')
            InstallationHourReading.objects.filter(pk=rid, installation=inst).delete()
            AuditLog.objects.create(actor=request.user, action='delete_installation_hour_reading', details=f'reading_id={rid}')
            messages.success(request, "Relevé supprimé.")
            return redirect(f"/installations/{inst.id}/{qs}")
        elif action == 'edit_vibration':
            rid = request.POST.get('reading_id')
            try:
                vb = InstallationVibrationReading.objects.get(pk=rid, installation=inst)
            except InstallationVibrationReading.DoesNotExist:
                messages.error(request, "Mesure introuvable")
                return redirect(f"/installations/{inst.id}/{qs}")
            date_str = request.POST.get('date', '').strip()
            state = (request.POST.get('state') or '').strip().upper()
            note = request.POST.get('note', '').strip()
            if date_str:
                try:
                    vb.date = datetime.strptime(date_str, '%d/%m/%Y').date()
                except Exception:
                    pass
            if state in ('A','B','C'):
                vb.state = state
            vb.note = note
            try:
                vb.updated_by = request.user
                vb.save()
            except OperationalError:
                messages.error(request, "Base non à jour: appliquez les migrations (assets).")
                return redirect(f"/installations/{inst.id}/{qs}")
            AuditLog.objects.create(actor=request.user, action='edit_installation_vibration', details=f'reading_id={vb.id}')
            messages.success(request, "Mesure de vibration mise à jour.")
            return redirect(f"/installations/{inst.id}/{qs}")
        elif action == 'delete_vibration':
            rid = request.POST.get('reading_id')
            InstallationVibrationReading.objects.filter(pk=rid, installation=inst).delete()
            AuditLog.objects.create(actor=request.user, action='delete_installation_vibration', details=f'reading_id={rid}')
            messages.success(request, "Mesure supprimée.")
            return redirect(f"/installations/{inst.id}/{qs}")
        elif action == 'add_vibration':
            date_str = request.POST.get('date', '').strip()
            state = (request.POST.get('state') or '').strip().upper()
            note = request.POST.get('note', '').strip()
            if state not in ('A','B','C'):
                messages.error(request, "État vibratoire invalide (A/B/C).")
                return redirect(f"/installations/{inst.id}/{qs}")
            vb_date = timezone.localdate()
            if date_str:
                try:
                    vb_date = datetime.strptime(date_str, '%d/%m/%Y').date()
                except Exception:
                    pass
            try:
                reading = InstallationVibrationReading.objects.create(
                    installation=inst,
                    date=vb_date,
                    state=state,
                    note=note,
                    created_by=request.user,
                    updated_by=request.user,
                )
            except OperationalError:
                messages.error(request, "Base non à jour: appliquez les migrations (assets).")
                return redirect(f"/installations/{inst.id}/{qs}")
            AuditLog.objects.create(actor=request.user, action='add_installation_vibration', details=f'reading_id={reading.id}')
            messages.success(request, "Mesure de vibration ajoutée.")
            return redirect(f"/installations/{inst.id}/{qs}")
        elif action == 'add_isolation':
            date_str = request.POST.get('date', '').strip()
            ohm_str = request.POST.get('ohms', '').strip()
            note = request.POST.get('note', '').strip()
            if not ohm_str:
                messages.error(request, "La mesure (Ohm) est requise.")
                return redirect(f"/installations/{inst.id}/{qs}")
            iso_date = timezone.localdate()
            if date_str:
                try:
                    iso_date = datetime.strptime(date_str, '%d/%m/%Y').date()
                except Exception:
                    pass
            try:
                val = float(ohm_str.replace(',', '.'))
            except Exception:
                messages.error(request, "Valeur de mesure invalide.")
                return redirect(f"/installations/{inst.id}/{qs}")
            try:
                rd = InstallationIsolationReading.objects.create(
                    installation=inst,
                    date=iso_date,
                    ohms=val,
                    note=note,
                    created_by=request.user,
                    updated_by=request.user,
                )
            except OperationalError:
                messages.error(request, "Base non à jour: appliquez les migrations (assets).")
                return redirect(f"/installations/{inst.id}/{qs}")
            AuditLog.objects.create(actor=request.user, action='add_installation_isolation', details=f'reading_id={rd.id}')
            messages.success(request, "Mesure d'isolement ajoutée.")
            return redirect(f"/installations/{inst.id}/{qs}")
        elif action == 'edit_isolation':
            rid = request.POST.get('reading_id')
            try:
                rd = InstallationIsolationReading.objects.get(pk=rid, installation=inst)
            except InstallationIsolationReading.DoesNotExist:
                messages.error(request, "Mesure d'isolement introuvable")
                return redirect(f"/installations/{inst.id}/{qs}")
            date_str = request.POST.get('date', '').strip()
            ohm_str = request.POST.get('ohms', '').strip()
            note = request.POST.get('note', '').strip()
            if date_str:
                try:
                    rd.date = datetime.strptime(date_str, '%d/%m/%Y').date()
                except Exception:
                    pass
            if ohm_str:
                try:
                    val = float(ohm_str.replace(',', '.'))
                    rd.ohms = val
                except Exception:
                    pass
            rd.note = note
            try:
                rd.updated_by = request.user
                rd.save()
            except OperationalError:
                messages.error(request, "Base non à jour: appliquez les migrations (assets).")
                return redirect(f"/installations/{inst.id}/{qs}")
            AuditLog.objects.create(actor=request.user, action='edit_installation_isolation', details=f'reading_id={rd.id}')
            messages.success(request, "Mesure d'isolement mise à jour.")
            return redirect(f"/installations/{inst.id}/{qs}")
        elif action == 'delete_isolation':
            rid = request.POST.get('reading_id')
            InstallationIsolationReading.objects.filter(pk=rid, installation=inst).delete()
            AuditLog.objects.create(actor=request.user, action='delete_installation_isolation', details=f'reading_id={rid}')
            messages.success(request, "Mesure d'isolement supprimée.")
            return redirect(f"/installations/{inst.id}/{qs}")
        return HttpResponseBadRequest('Action non prise en charge')


class LocationListView(LoginRequiredMixin, ListView):
    model = Location
    template_name = 'assets/locations.html'
    context_object_name = 'locations'

    def get_queryset(self):
        qs = Location.objects.select_related('ship', 'parent').order_by('ship__name', 'name')
        ship_id = self.request.GET.get('ship')
        if ship_id:
            qs = qs.filter(ship_id=ship_id)
        q = self.request.GET.get('q', '').strip()
        if q:
            qs = qs.filter(name__icontains=q)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['ships'] = Ship.objects.order_by('name')
        ctx['parents'] = Location.objects.select_related('ship').order_by('ship__name', 'name')
        return ctx

    def post(self, request, *args, **kwargs):
        action = request.POST.get('action')
        if action == 'create_location':
            name = request.POST.get('name', '').strip()
            ship_id = request.POST.get('ship_id')
            parent_id = request.POST.get('parent_id')
            if name and ship_id:
                loc = Location.objects.create(name=name, ship=Ship.objects.get(pk=ship_id))
                if parent_id:
                    loc.parent = Location.objects.filter(pk=parent_id).first()
                    loc.save()
                AuditLog.objects.create(actor=request.user, action='create_location', details=f'name={name}')
                messages.success(request, 'Emplacement créé.')
        elif action == 'edit_location':
            pk = request.POST.get('pk')
            try:
                loc = Location.objects.get(pk=pk)
                loc.name = request.POST.get('name', loc.name).strip()
                ship_id = request.POST.get('ship_id')
                if ship_id:
                    try:
                        loc.ship = Ship.objects.get(pk=ship_id)
                    except Ship.DoesNotExist:
                        pass
                parent_id = request.POST.get('parent_id')
                loc.parent = Location.objects.filter(pk=parent_id).first() if parent_id else None
                loc.save()
                AuditLog.objects.create(actor=request.user, action='edit_location', details=f'id={loc.id}')
                messages.success(request, 'Emplacement mis à jour.')
            except Location.DoesNotExist:
                pass
        elif action == 'delete_location':
            pk = request.POST.get('pk'); Location.objects.filter(pk=pk).delete(); messages.success(request, 'Emplacement supprimé.')
        return redirect('location-list')

# (Standalone InstallationSettingsView removed; settings are now managed in global Settings > Installations)
