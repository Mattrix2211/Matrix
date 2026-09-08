from django.db.models import Q
from django.shortcuts import render, redirect
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from assets.models import Asset, AssetDocument
from logistics.models import CorrectiveTicket
from django.contrib.auth.models import User
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views import View
from accounts.models import GradeChoice, SpecialityChoice, ServiceFunctionChoice, RoleAvailability, Roles, AuditLog
from assets.models import InstallationBigrameChoice, Installation
from training.models import TrainingCourse
from org.models import Ship, Service, Sector, Section, RoleThresholdConfig
from django.contrib import messages
from matrix.core.scopes import scope_filters_for_user, is_master_admin, ship_id_for_user
from matrix.core.roles import RoleLevel
from matrix.core.role_thresholds import REGISTRE_ACTIONS, REGISTRE_PAR_CLE, PORTEE_GLOBALE, seuil_role, invalidate_cache

# Options du menu déroulant "nouveau seuil" de l'onglet Sécurité (Réglages) :
# les 8 rôles, du plus bas (Équipier) au plus haut (Administrateur général) —
# ordre ascendant de RoleLevel, libellés français repris de Roles.choices.
_LIBELLE_ROLE = dict(Roles.choices)
ROLES_POUR_SEUILS = [(niveau.name, _LIBELLE_ROLE.get(niveau.name, niveau.name)) for niveau in RoleLevel]


def _lignes_seuils(ship_id, portee_visee):
    """Construit les lignes affichables pour l'onglet Sécurité des Réglages :
    une ligne par action configurable de la portée demandée (SHIP ou
    GLOBALE), avec son seuil actuel (configuré pour ce navire, ou seuil par
    défaut si rien n'est configuré)."""
    return [
        {
            "cle": action.cle,
            "libelle": action.libelle,
            "categorie": action.categorie,
            "niveau_actuel": seuil_role(action.cle, ship_id),
            "niveau_defaut": action.defaut,
        }
        for action in REGISTRE_ACTIONS
        if action.portee == portee_visee
    ]


@login_required
def global_search(request):
    # Recherche globale réservée aux utilisateurs connectés, restreinte à leur
    # périmètre (navire/service/secteur/section) via scope_filters_for_user —
    # pas de nouveau système de scope. Le matériel et les installations portent
    # directement les champs de périmètre ; les tickets, les documents et les
    # personnes n'en ont pas, on traduit donc le périmètre via la relation vers
    # le matériel (asset) ou le profil (profile).
    #
    # Couverture §37 cahier des charges (recherche universelle) — 6 types sur
    # les 9 listés : matériel mobile, installations (équipement fixe), tickets
    # correctifs, personnes, formations, documents. Volontairement hors
    # périmètre de cette itération (cf. commentaire Notion de la tâche) :
    # tâches (aucun modèle "Tâche" unique n'existe — un marin suit ses
    # échéances via son espace personnel, pas via un objet cherchable dédié),
    # événements de calendrier et discussions — pour éviter la sur-ingénierie
    # et prioriser les types les plus utiles au quotidien en premier.
    q = request.GET.get('q', '').strip()
    perimetre = scope_filters_for_user(request.user)
    perimetre_tickets = {f"asset__{cle}": valeur for cle, valeur in perimetre.items()}
    perimetre_documents = {f"asset__{cle}": valeur for cle, valeur in perimetre.items()}
    perimetre_users = {f"profile__{cle}": valeur for cle, valeur in perimetre.items()}
    assets = tickets = users = installations = formations = documents = []
    if q:
        assets = Asset.objects.filter(**perimetre).filter(
            Q(internal_id__icontains=q) | Q(serial_number__icontains=q)
        )[:20]
        tickets = CorrectiveTicket.objects.filter(**perimetre_tickets).filter(
            Q(description__icontains=q) | Q(id__icontains=q)
        )[:20]
        users = User.objects.filter(**perimetre_users).filter(
            Q(username__icontains=q) | Q(email__icontains=q)
        )[:20]
        installations = Installation.objects.select_related('ship', 'service', 'sector').filter(**perimetre).filter(
            Q(designation__icontains=q) | Q(reference__icontains=q)
        )[:20]
        # Formation : fiche UNIQUE et globale (pas de rattachement navire, cf.
        # TrainingCourse et TrainingCourseListView) — même filtre "catalogue
        # actif" que la liste des formations, aucun périmètre supplémentaire à
        # appliquer puisque le référentiel est déjà commun à toute la flotte.
        formations = TrainingCourse.objects.filter(statut_validation="ACTIVE").filter(
            Q(title__icontains=q) | Q(category__icontains=q)
        )[:20]
        documents = AssetDocument.objects.select_related('asset').filter(**perimetre_documents).filter(
            Q(name__icontains=q)
        )[:20]
    return render(request, 'search.html', {
        "q": q, "assets": assets, "tickets": tickets, "users": users,
        "installations": installations, "formations": formations, "documents": documents,
    })


def logout_then_login(request):
    # Déconnexion simple puis redirection immédiate vers la page de connexion
    logout(request)
    return redirect('/login/')


class SettingsView(LoginRequiredMixin, View):
    template_name = 'settings/index.html'

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_superuser:
            # Seules les sections "Notification quotidienne" (réglage personnel
            # de chaque marin) et "Sécurité" (seuils de rôle, réservée aux
            # ADMIN_NAVIRE — configuration de LEUR navire, cf. tâche Notion
            # « Seuils de rôle configurables par navire ») sont accessibles aux
            # non-superusers. Le reste des Réglages (référentiels globaux,
            # navires, hiérarchie, journal...) reste réservé aux comptes
            # techniques superuser Django (MASTER_ADMIN).
            from django.http import HttpResponseForbidden
            profile = getattr(request.user, 'profile', None)
            est_admin_navire = bool(profile and profile.role == 'ADMIN_NAVIRE')
            tab = request.GET.get('tab', 'generale')
            tab_ok = request.method == 'GET' and (
                tab == 'notifications' or (tab == 'seuils_role' and est_admin_navire)
            )
            action = request.POST.get('action')
            action_notif_ok = request.method == 'POST' and action == 'update_notification_time'
            action_seuil_ok = (
                request.method == 'POST'
                and action in ('update_role_threshold', 'reset_role_threshold')
                and est_admin_navire
            )
            if not (tab_ok or action_notif_ok or action_seuil_ok):
                return HttpResponseForbidden()
        return super().dispatch(request, *args, **kwargs)

    def get(self, request):
        tab = request.GET.get('tab', 'generale')

        # Valeur d'heure de notification de l'utilisateur courant (format HH:MM)
        def fmt_time(t):
            try:
                return t.strftime('%H:%M')
            except Exception:
                return '08:00'

        if not request.user.is_superuser:
            # Vue restreinte : réglage personnel des horaires de notification,
            # et (si ADMIN_NAVIRE) l'onglet Sécurité limité à SON navire —
            # sans les autres données réservées aux superusers.
            profile = getattr(request.user, 'profile', None)
            est_admin_navire = bool(profile and profile.role == 'ADMIN_NAVIRE')
            context = {
                'active_tab': tab if tab == 'seuils_role' else 'notifications',
                'user_notification_time': fmt_time(getattr(profile, 'notification_time', None)),
                'user_notification_time_soir': fmt_time(getattr(profile, 'notification_time_soir', None)),
                'peut_gerer_seuils': est_admin_navire,
            }
            if tab == 'seuils_role' and est_admin_navire:
                mon_ship_id = ship_id_for_user(request.user)
                context.update({
                    'seuils_ship': Ship.objects.filter(pk=mon_ship_id).first(),
                    'seuils_lignes': _lignes_seuils(mon_ship_id, 'SHIP'),
                    'seuils_lignes_globales': [],
                    'peut_editer_global': False,
                    'roles_pour_seuils': ROLES_POUR_SEUILS,
                })
            return render(request, self.template_name, context)

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
            'type_unite_choices': Ship.TypeUnite.choices,
            'selected_ship': selected_ship,
            'services': services_qs.order_by('name'),
            'sectors': sectors_qs.order_by('service__name','name'),
            'sections': sections_qs.order_by('sector__name','name'),
            'role_options': role_options,
            'all_roles': all_roles,
            'roles_with_state': roles_with_state,
            'user_notification_time': fmt_time(getattr(getattr(request.user, 'profile', None), 'notification_time', None)),
            'user_notification_time_soir': fmt_time(getattr(getattr(request.user, 'profile', None), 'notification_time_soir', None)),
            'peut_gerer_seuils': True,
        }
        if tab == 'journal':
            context['logs'] = AuditLog.objects.select_related('actor','target_user').order_by('-created_at')[:200]
        if tab == 'seuils_role':
            # MASTER_ADMIN choisit le navire à configurer (même sélecteur que
            # l'onglet Hiérarchie, cf. selected_ship ci-dessus), et peut en plus
            # éditer la configuration GLOBALE (flotte) des référentiels communs.
            context.update({
                'seuils_ship': selected_ship,
                'seuils_lignes': _lignes_seuils(selected_ship.id if selected_ship else None, 'SHIP'),
                'seuils_lignes_globales': _lignes_seuils(None, PORTEE_GLOBALE),
                'peut_editer_global': True,
                'roles_pour_seuils': ROLES_POUR_SEUILS,
            })
        return render(request, self.template_name, context)

    def post(self, request):
        action = request.POST.get('action')
        next_tab = request.POST.get('next_tab') or 'utilisateurs'
        selected_ship_id = request.POST.get('selected_ship') or request.POST.get('ship_id') or request.GET.get('ship')
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
            type_unite = request.POST.get('type_unite') or Ship.TypeUnite.NAVIRE
            classe_navire = request.POST.get('classe_navire', '').strip()
            if code:
                Ship.objects.get_or_create(
                    name=name, code=code,
                    defaults={'type_unite': type_unite, 'classe_navire': classe_navire},
                )
                messages.success(request, "Unité ajoutée.")
                AuditLog.objects.create(actor=request.user, action='add_ship', details=f'name={name}; code={code}')
        elif action == 'delete_ship':
            pk = request.POST.get('pk')
            Ship.objects.filter(pk=pk).delete()
            messages.success(request, "Unité supprimée.")
            AuditLog.objects.create(actor=request.user, action='delete_ship', details=f'pk={pk}')
        elif action == 'edit_ship':
            pk = request.POST.get('pk')
            name = request.POST.get('name', '').strip()
            code = request.POST.get('code', '').strip()
            type_unite = request.POST.get('type_unite')
            # Champ optionnel : contrairement à name/code, on l'écrase avec la valeur
            # postée même vide, pour permettre d'effacer une classe déjà renseignée.
            classe_navire = request.POST.get('classe_navire', '').strip()
            try:
                sh = Ship.objects.get(pk=pk)
                if name:
                    sh.name = name
                if code:
                    sh.code = code
                if type_unite:
                    sh.type_unite = type_unite
                sh.classe_navire = classe_navire
                sh.save()
                messages.success(request, "Unité mise à jour.")
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
                # Crée la nouvelle unité, en reprenant le type et la classe de l'unité
                # source (des unités dupliquées sont généralement des navires « sister-
                # ship » de même classe).
                new_ship = Ship.objects.create(
                    name=name, code=code, type_unite=src_ship.type_unite, classe_navire=src_ship.classe_navire,
                )
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
                messages.success(request, "Unité dupliquée.")
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
        elif action in ('update_role_threshold', 'reset_role_threshold'):
            # Onglet Sécurité : modification (ou réinitialisation à la valeur
            # par défaut) d'un seuil de rôle configurable par navire, cf.
            # matrix/core/role_thresholds.py. Accessible à un ADMIN_NAVIRE
            # (limité à SON navire, ship_id posté ignoré) ou à un MASTER_ADMIN
            # (choisit le navire, ou édite la configuration GLOBALE flotte).
            next_tab = 'seuils_role'
            cle_action = request.POST.get('cle_action')
            action_seuil = REGISTRE_PAR_CLE.get(cle_action)
            if action_seuil is None:
                messages.error(request, "Seuil de rôle inconnu.")
            elif action_seuil.portee == PORTEE_GLOBALE and not is_master_admin(request.user):
                messages.error(request, "Seuls les administrateurs généraux peuvent modifier ce référentiel commun à toute la flotte.")
            else:
                if action_seuil.portee == PORTEE_GLOBALE:
                    ship = None
                elif request.user.is_superuser:
                    ship = Ship.objects.filter(pk=request.POST.get('ship_id')).first()
                else:
                    ship = Ship.objects.filter(pk=ship_id_for_user(request.user)).first()
                if ship is None and action_seuil.portee != PORTEE_GLOBALE:
                    messages.error(request, "Aucune unité sélectionnée.")
                else:
                    config, _ = RoleThresholdConfig.objects.get_or_create(ship=ship)
                    cible = ship.name if ship else "flotte (configuration globale)"
                    if action == 'update_role_threshold':
                        nouveau_role = request.POST.get('nouveau_role')
                        if nouveau_role not in dict(ROLES_POUR_SEUILS):
                            messages.error(request, "Rôle invalide.")
                        else:
                            ancien = config.thresholds.get(cle_action) or action_seuil.defaut.name
                            config.thresholds[cle_action] = nouveau_role
                            config.save(update_fields=['thresholds', 'updated_at'])
                            invalidate_cache(ship.id if ship else None)
                            AuditLog.objects.create(
                                actor=request.user, action='update_role_threshold',
                                details=f"navire={cible}; action={cle_action}; {ancien} -> {nouveau_role}",
                            )
                            messages.success(request, "Seuil de rôle mis à jour.")
                    else:
                        if cle_action in config.thresholds:
                            ancien = config.thresholds.pop(cle_action)
                            config.save(update_fields=['thresholds', 'updated_at'])
                            invalidate_cache(ship.id if ship else None)
                            AuditLog.objects.create(
                                actor=request.user, action='reset_role_threshold',
                                details=f"navire={cible}; action={cle_action}; {ancien} -> défaut ({action_seuil.defaut.name})",
                            )
                        messages.success(request, "Seuil de rôle réinitialisé à sa valeur par défaut.")
        elif action == 'update_notification_time':
            val = (request.POST.get('notification_time') or '').strip()
            val_soir = (request.POST.get('notification_time_soir') or '').strip()
            from datetime import datetime
            try:
                t = datetime.strptime(val, '%H:%M').time()
                t_soir = datetime.strptime(val_soir, '%H:%M').time()
                profile = getattr(request.user, 'profile', None)
                if profile is None:
                    from accounts.models import UserProfile, Roles
                    profile = UserProfile.objects.create(user=request.user, role=Roles.EQUIPIER)
                profile.notification_time = t
                profile.notification_time_soir = t_soir
                profile.save(update_fields=['notification_time', 'notification_time_soir'])
                messages.success(request, "Heures de notification mises à jour.")
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
