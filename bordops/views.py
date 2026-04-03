from django.db.models import Q
from django.shortcuts import render, redirect
from django.contrib.auth import logout
from assets.models import Asset
from logistics.models import CorrectiveTicket
from django.contrib.auth.models import User
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views import View
from accounts.models import GradeChoice, SpecialityChoice, ServiceFunctionChoice, RoleAvailability, Roles, AuditLog
from assets.models import InstallationBigrameChoice, Installation
from org.models import Ship, Service, Sector, Section
from django.contrib import messages

def global_search(request):
    q = request.GET.get('q', '').strip()
    assets = tickets = users = []
    if q:
        assets = Asset.objects.filter(Q(internal_id__icontains=q) | Q(serial_number__icontains=q))[:20]
        tickets = CorrectiveTicket.objects.filter(Q(description__icontains=q) | Q(id__icontains=q))[:20]
        users = User.objects.filter(Q(username__icontains=q) | Q(email__icontains=q))[:20]
    return render(request, 'search.html', {"q": q, "assets": assets, "tickets": tickets, "users": users})


def logout_then_login(request):
    # Déconnexion simple puis redirection immédiate vers la page de connexion
    logout(request)
    return redirect('/login/')


class SettingsView(LoginRequiredMixin, View):
    template_name = 'settings/index.html'

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_superuser:
            from django.http import HttpResponseForbidden
            return HttpResponseForbidden()
        return super().dispatch(request, *args, **kwargs)

    def get(self, request):
        tab = request.GET.get('tab', 'generale')
        # Prépare l'état des rôles (actif/inactif) côté serveur pour simplifier le template
        all_roles = [c for c in Roles.choices if c[0] != 'MASTER_ADMIN']
        role_options = list(RoleAvailability.objects.order_by('code'))
        by_code = {o.code: o.active for o in role_options}
        roles_with_state = [
            {"code": code, "label": label, "active": by_code.get(code, True)}
            for code, label in all_roles
        ]

        # Sélecteur de navire pour paramétrer services/secteurs/sections
        ships_qs = Ship.objects.order_by('name')
        selected_ship_id = request.GET.get('ship')
        selected_ship = None
        if selected_ship_id:
            try:
                selected_ship = ships_qs.get(pk=selected_ship_id)
            except Ship.DoesNotExist:
                selected_ship = None
        if not selected_ship:
            selected_ship = ships_qs.first()

        services_qs = Service.objects.select_related('ship')
        sectors_qs = Sector.objects.select_related('service','service__ship')
        sections_qs = Section.objects.select_related('sector','sector__service','sector__service__ship')
        if selected_ship:
            services_qs = services_qs.filter(ship=selected_ship)
            sectors_qs = sectors_qs.filter(service__ship=selected_ship)
            sections_qs = sections_qs.filter(sector__service__ship=selected_ship)

        # Préparer la liste d'installations pour l'onglet "Installations"
        installations_qs = Installation.objects.select_related('ship','service','sector','section').order_by('ship__name','service__name','sector__name','section__name','designation')
        # Valeurs globales à afficher (prend la première installation ou défauts)
        first_it = installations_qs.first()
        global_vib_days_a = getattr(first_it, 'vib_days_a', 180) if first_it else 180
        global_vib_days_b = getattr(first_it, 'vib_days_b', 90) if first_it else 90
        global_vib_days_c = getattr(first_it, 'vib_days_c', 30) if first_it else 30

        # Valeur d'heure de notification de l'utilisateur courant (format HH:MM)
        def fmt_time(t):
            try:
                return t.strftime('%H:%M')
            except Exception:
                return '08:00'

        context = {
            'active_tab': tab,
            'grades': GradeChoice.objects.order_by('name'),
            'specialites': SpecialityChoice.objects.order_by('name'),
            'fonctions': ServiceFunctionChoice.objects.order_by('name'),
            'bigrames': InstallationBigrameChoice.objects.order_by('name'),
            'installations': installations_qs,
            'global_vib_days_a': global_vib_days_a,
            'global_vib_days_b': global_vib_days_b,
            'global_vib_days_c': global_vib_days_c,
            'ships': ships_qs,
            'selected_ship': selected_ship,
            'services': services_qs.order_by('name'),
            'sectors': sectors_qs.order_by('service__name','name'),
            'sections': sections_qs.order_by('sector__name','name'),
            'role_options': role_options,
            'all_roles': all_roles,
            'roles_with_state': roles_with_state,
            'user_notification_time': fmt_time(getattr(getattr(request.user, 'profile', None), 'notification_time', None)),
        }
        if tab == 'journal':
            context['logs'] = AuditLog.objects.select_related('actor','target_user').order_by('-created_at')[:200]
        return render(request, self.template_name, context)

    def post(self, request):
        action = request.POST.get('action')
        next_tab = request.POST.get('next_tab') or 'utilisateurs'
        selected_ship_id = request.POST.get('selected_ship') or request.GET.get('ship')
        selected_installation_id = None
        name = request.POST.get('name', '').strip()
        if action == 'add_grade' and name:
            GradeChoice.objects.get_or_create(name=name, defaults={'active': True})
            messages.success(request, "Grade ajouté.")
            AuditLog.objects.create(actor=request.user, action='add_grade', details=f'name={name}')
        elif action == 'add_specialite' and name:
            SpecialityChoice.objects.get_or_create(name=name, defaults={'active': True})
            messages.success(request, "Spécialité ajoutée.")
            AuditLog.objects.create(actor=request.user, action='add_specialite', details=f'name={name}')
        elif action == 'add_fonction' and name:
            ServiceFunctionChoice.objects.get_or_create(name=name, defaults={'active': True})
            messages.success(request, "Fonction ajoutée.")
            AuditLog.objects.create(actor=request.user, action='add_fonction', details=f'name={name}')
        elif action == 'add_ship' and name:
            code = request.POST.get('code', '').strip()
            if code:
                Ship.objects.get_or_create(name=name, code=code)
                messages.success(request, "Navire ajouté.")
                AuditLog.objects.create(actor=request.user, action='add_ship', details=f'name={name}; code={code}')
        elif action == 'delete_ship':
            pk = request.POST.get('pk')
            Ship.objects.filter(pk=pk).delete()
            messages.success(request, "Navire supprimé.")
            AuditLog.objects.create(actor=request.user, action='delete_ship', details=f'pk={pk}')
        elif action == 'edit_ship':
            pk = request.POST.get('pk')
            name = request.POST.get('name', '').strip()
            code = request.POST.get('code', '').strip()
            try:
                sh = Ship.objects.get(pk=pk)
                if name:
                    sh.name = name
                if code:
                    sh.code = code
                sh.save()
                messages.success(request, "Navire mis à jour.")
                AuditLog.objects.create(actor=request.user, action='edit_ship', details=f'pk={pk}')
            except Ship.DoesNotExist:
                pass
        elif action == 'duplicate_ship':
            src_pk = request.POST.get('source_pk')
            name = request.POST.get('name', '').strip()
            code = request.POST.get('code', '').strip()
            try:
                src_ship = Ship.objects.get(pk=src_pk)
                if not name or not code:
                    raise ValueError("Nom et code requis pour dupliquer.")
                # Crée le nouveau navire
                new_ship = Ship.objects.create(name=name, code=code)
                # Map des services et secteurs pour rattacher correctement
                service_map = {}
                sector_map = {}
                # Duplique les services
                for sv in Service.objects.filter(ship=src_ship).order_by('id'):
                    new_sv = Service.objects.create(ship=new_ship, name=sv.name)
                    service_map[sv.id] = new_sv
                # Duplique les secteurs
                for sc in Sector.objects.filter(service__ship=src_ship).select_related('service').order_by('id'):
                    parent_new_sv = service_map.get(sc.service_id)
                    if parent_new_sv:
                        new_sc = Sector.objects.create(service=parent_new_sv, name=sc.name, color=sc.color)
                        sector_map[sc.id] = new_sc
                # Duplique les sections
                for se in Section.objects.filter(sector__service__ship=src_ship).select_related('sector').order_by('id'):
                    parent_new_sc = sector_map.get(se.sector_id)
                    if parent_new_sc:
                        Section.objects.create(sector=parent_new_sc, name=se.name)
                messages.success(request, "Navire dupliqué.")
                AuditLog.objects.create(actor=request.user, action='duplicate_ship', details=f'source={src_pk}; name={name}; code={code}')
            except (Ship.DoesNotExist, ValueError):
                pass
        elif action == 'add_service':
            name = request.POST.get('name','').strip()
            ship_id = request.POST.get('ship_id') or request.GET.get('ship') or request.POST.get('selected_ship')
            if name and ship_id:
                try:
                    ship = Ship.objects.get(pk=ship_id)
                    Service.objects.get_or_create(name=name, ship=ship)
                    messages.success(request, "Service ajouté.")
                    AuditLog.objects.create(actor=request.user, action='add_service', details=f'name={name}; ship_id={ship_id}')
                except Ship.DoesNotExist:
                    pass
        elif action == 'delete_service':
            pk = request.POST.get('pk')
            Service.objects.filter(pk=pk).delete()
            messages.success(request, "Service supprimé.")
            AuditLog.objects.create(actor=request.user, action='delete_service', details=f'pk={pk}')
        elif action == 'add_sector':
            service_id = request.POST.get('service_id')
            if name and service_id:
                try:
                    service = Service.objects.get(pk=service_id)
                    Sector.objects.get_or_create(name=name, service=service)
                    messages.success(request, "Secteur ajouté.")
                    AuditLog.objects.create(actor=request.user, action='add_sector', details=f'name={name}; service_id={service_id}')
                except Service.DoesNotExist:
                    pass
        elif action == 'delete_sector':
            pk = request.POST.get('pk')
            Sector.objects.filter(pk=pk).delete()
            messages.success(request, "Secteur supprimé.")
            AuditLog.objects.create(actor=request.user, action='delete_sector', details=f'pk={pk}')
        elif action == 'add_section':
            sector_id = request.POST.get('sector_id')
            if name and sector_id:
                try:
                    sector = Sector.objects.get(pk=sector_id)
                    Section.objects.get_or_create(name=name, sector=sector)
                    messages.success(request, "Section ajoutée.")
                    AuditLog.objects.create(actor=request.user, action='add_section', details=f'name={name}; sector_id={sector_id}')
                except Sector.DoesNotExist:
                    pass
        elif action == 'delete_section':
            pk = request.POST.get('pk')
            Section.objects.filter(pk=pk).delete()
            messages.success(request, "Section supprimée.")
            AuditLog.objects.create(actor=request.user, action='delete_section', details=f'pk={pk}')
        elif action == 'toggle_role':
            code = request.POST.get('code')
            if code and code != 'MASTER_ADMIN':
                opt, _ = RoleAvailability.objects.get_or_create(code=code, defaults={'active': True})
                opt.active = not opt.active
                opt.save(update_fields=['active'])
                messages.success(request, "Disponibilité du rôle mise à jour.")
                AuditLog.objects.create(actor=request.user, action='toggle_role', details=f'code={code}; active={opt.active}')
        elif action == 'delete_grade':
            pk = request.POST.get('pk')
            GradeChoice.objects.filter(pk=pk).delete()
            messages.success(request, "Grade supprimé.")
            AuditLog.objects.create(actor=request.user, action='delete_grade', details=f'pk={pk}')
        elif action == 'delete_specialite':
            pk = request.POST.get('pk')
            SpecialityChoice.objects.filter(pk=pk).delete()
            messages.success(request, "Spécialité supprimée.")
            AuditLog.objects.create(actor=request.user, action='delete_specialite', details=f'pk={pk}')
        elif action == 'delete_fonction':
            pk = request.POST.get('pk')
            ServiceFunctionChoice.objects.filter(pk=pk).delete()
            messages.success(request, "Fonction supprimée.")
            AuditLog.objects.create(actor=request.user, action='delete_fonction', details=f'pk={pk}')
        elif action == 'add_bigrame' and name:
            InstallationBigrameChoice.objects.get_or_create(name=name, defaults={'active': True})
            messages.success(request, "Bigrame ajouté.")
            AuditLog.objects.create(actor=request.user, action='add_bigrame', details=f'name={name}')
        elif action == 'delete_bigrame':
            pk = request.POST.get('pk')
            InstallationBigrameChoice.objects.filter(pk=pk).delete()
            messages.success(request, "Bigrame supprimé.")
            AuditLog.objects.create(actor=request.user, action='delete_bigrame', details=f'pk={pk}')
        elif action == 'toggle_bigrame':
            pk = request.POST.get('pk')
            try:
                bg = InstallationBigrameChoice.objects.get(pk=pk)
                bg.active = not bg.active
                bg.save(update_fields=['active'])
                messages.success(request, "Statut du bigrame mis à jour.")
                AuditLog.objects.create(actor=request.user, action='toggle_bigrame', details=f'pk={pk}; active={bg.active}')
            except InstallationBigrameChoice.DoesNotExist:
                pass
        elif action == 'update_all_vibration_params':
            try:
                a = max(1, int(request.POST.get('vib_days_a')))
                b = max(1, int(request.POST.get('vib_days_b')))
                c = max(1, int(request.POST.get('vib_days_c')))
                Installation.objects.all().update(vib_days_a=a, vib_days_b=b, vib_days_c=c)
                messages.success(request, "Paramètres vibratoires globaux mis à jour pour toutes les installations.")
                AuditLog.objects.create(actor=request.user, action='update_all_vibration_params', details=f'a={a}; b={b}; c={c}')
                next_tab = 'installations'
            except Exception:
                messages.error(request, "Valeurs invalides pour les paramètres vibratoires.")
                next_tab = 'installations'
        elif action == 'update_notification_time':
            val = (request.POST.get('notification_time') or '').strip()
            from datetime import datetime
            try:
                t = datetime.strptime(val, '%H:%M').time()
                profile = getattr(request.user, 'profile', None)
                if profile is None:
                    from accounts.models import UserProfile, Roles
                    profile = UserProfile.objects.create(user=request.user, role=Roles.EQUIPIER)
                profile.notification_time = t
                profile.save(update_fields=['notification_time'])
                messages.success(request, "Heure de notification mise à jour.")
                next_tab = 'notifications'
            except Exception:
                messages.error(request, "Heure invalide (format HH:MM).")
                next_tab = 'notifications'
        # Conserve le navire sélectionné lors de la redirection
        suffix_parts = []
        if selected_ship_id:
            suffix_parts.append(f"ship={selected_ship_id}")
        if next_tab == 'installations' and selected_installation_id:
            suffix_parts.append(f"installation={selected_installation_id}")
        suffix = ("&" + "&".join(suffix_parts)) if suffix_parts else ""
        return redirect(f"/parametre/?tab={next_tab}{suffix}")
