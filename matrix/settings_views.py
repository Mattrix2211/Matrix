"""Réglages (/parametre/) : vue SettingsView et ses helpers par onglet.

Extrait de matrix/views.py (tâche Notion « [ARCH] Découper matrix/views.py :
extraire SettingsView et ses actions par onglet »). matrix/views.py réexporte
SettingsView pour que `from .views import SettingsView` (matrix/urls.py)
continue de fonctionner sans changement de comportement."""
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import User
from django.db.models import ProtectedError
from django.shortcuts import render, redirect
from django.views import View

from accounts.models import (
    GradeChoice, SpecialityChoice, ServiceFunctionChoice, FonctionQuartChoice, RoleAvailability, Roles,
    AuditLog, ResponsableSpecialite,
)
from assets.models import InstallationBigrameChoice, Installation
from matrix.core.modules import (
    REGISTRE_MODULES, REGISTRE_PAR_CLE as MODULES_PAR_CLE, module_actif,
    invalidate_cache as invalidate_modules_cache,
)
from matrix.core.role_thresholds import (
    REGISTRE_ACTIONS, REGISTRE_PAR_CLE, PORTEE_GLOBALE, seuil_role, invalidate_cache, niveau_requis_pour,
)
from matrix.core.roles import RoleLevel, user_role_level
from matrix.core.scopes import is_master_admin, ship_id_for_user
from accounts import chefs_responsables
from org import commandant_en_second as en_second
from org import suppleance
from org import commandants_adjoints as coma
from org.miroir import copier_organisation
from org.models import Ship, Service, Sector, Section, RoleThresholdConfig, ResponsableClasseNavire, ModuleActivation, Equipage

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


def _lignes_modules(ship_id):
    """Construit les lignes affichables pour l'onglet Modules des Réglages :
    une ligne par module désactivable du registre, avec son état actuel pour
    ce navire (activé par défaut tant que rien n'est configuré explicitement,
    cf. matrix/core/modules.py)."""
    return [
        {
            "cle": mod.cle,
            "libelle": mod.libelle,
            "description": mod.description,
            "actif": module_actif(mod.cle, ship_id),
        }
        for mod in REGISTRE_MODULES
    ]


class SettingsView(LoginRequiredMixin, View):
    template_name = 'settings/index.html'

    @staticmethod
    def _peut_gerer_responsables(user):
        # Seuil configurable (portée GLOBALE, cf. matrix/core/role_thresholds.py)
        # pour désigner/retirer un responsable de spécialité ou de classe de
        # navire (tâche Notion « Dashboards transverses par spécialité et par
        # classe de navire ») : MASTER_ADMIN par défaut, mais un ADMIN_NAVIRE
        # peut abaisser ce seuil pour un rôle inférieur. Factorisé ici pour être
        # utilisé à la fois côté contrôle d'accès (dispatch) et côté contexte
        # (get), sans dupliquer le calcul.
        return user_role_level(user) >= niveau_requis_pour(user, 'responsabilite_transverse_gestion')

    @staticmethod
    def _peut_gerer_modules(user):
        # Seuil configurable (portée SHIP, cf. matrix/core/role_thresholds.py,
        # clé "module_gestion") pour activer/désactiver un module applicatif
        # sur SON navire : COMMANDANT par défaut (et tout rôle supérieur,
        # ADMIN_NAVIRE compris, puisque la comparaison est >=), ajustable par
        # navire comme n'importe quel autre seuil de l'onglet Sécurité.
        return user_role_level(user) >= niveau_requis_pour(user, 'module_gestion')

    @staticmethod
    def _peut_gerer_coma(user):
        # Seuil configurable « commandant_adjoint_gestion » (COMMANDANT par
        # défaut, donc ADMIN_NAVIRE aussi), limité à SON navire.
        return user_role_level(user) >= niveau_requis_pour(user, 'commandant_adjoint_gestion')

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_superuser:
            # Seules les sections "Notification quotidienne" (réglage personnel
            # de chaque marin), "Sécurité" (seuils de rôle, réservée aux
            # ADMIN_NAVIRE — configuration de LEUR navire, cf. tâche Notion
            # « Seuils de rôle configurables par navire »), "Utilisateurs"
            # (uniquement la désignation de responsables transverses, réservée
            # au rôle habilité par le seuil configurable ci-dessous) et
            # "Modules" (activation/désactivation d'un module pour SON navire,
            # réservée au rôle habilité par le seuil "module_gestion") sont
            # accessibles aux non-superusers. Le reste des Réglages
            # (référentiels globaux, navires, hiérarchie, journal...) reste
            # réservé aux comptes techniques superuser Django (MASTER_ADMIN).
            from django.http import HttpResponseForbidden
            profile = getattr(request.user, 'profile', None)
            est_admin_navire = bool(profile and profile.role == 'ADMIN_NAVIRE')
            peut_gerer_responsables = self._peut_gerer_responsables(request.user)
            peut_gerer_modules = self._peut_gerer_modules(request.user)
            peut_gerer_coma = self._peut_gerer_coma(request.user)
            tab = request.GET.get('tab', 'generale')
            tab_ok = request.method == 'GET' and (
                tab == 'notifications'
                or (tab == 'commandants_adjoints' and peut_gerer_coma)
                or (tab == 'seuils_role' and est_admin_navire)
                or (tab == 'utilisateurs' and peut_gerer_responsables)
                or (tab == 'modules' and peut_gerer_modules)
            )
            action = request.POST.get('action')
            action_notif_ok = request.method == 'POST' and action == 'update_notification_time'
            action_seuil_ok = (
                request.method == 'POST'
                and action in ('update_role_threshold', 'reset_role_threshold')
                and est_admin_navire
            )
            action_responsable_ok = (
                request.method == 'POST'
                and action in (
                    'add_responsable_specialite', 'retirer_responsable_specialite',
                    *chefs_responsables.ACTIONS,
                    'add_responsable_classe', 'retirer_responsable_classe',
                )
                and peut_gerer_responsables
            )
            action_module_ok = (
                request.method == 'POST' and action == 'toggle_module' and peut_gerer_modules
            )
            action_coma_ok = (
                request.method == 'POST' and action in (*coma.ACTIONS, *en_second.ACTIONS, *suppleance.ACTIONS) and peut_gerer_coma
            )
            if not (
                tab_ok or action_notif_ok or action_seuil_ok or action_responsable_ok or action_module_ok
                or action_coma_ok
            ):
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
            # (si ADMIN_NAVIRE) l'onglet Sécurité limité à SON navire, et (si
            # habilité par le seuil configurable) l'onglet Utilisateurs limité
            # à la désignation de responsables transverses — sans les autres
            # données/référentiels réservés aux superusers.
            profile = getattr(request.user, 'profile', None)
            est_admin_navire = bool(profile and profile.role == 'ADMIN_NAVIRE')
            peut_gerer_responsables = self._peut_gerer_responsables(request.user)
            peut_gerer_modules = self._peut_gerer_modules(request.user)
            peut_gerer_coma = self._peut_gerer_coma(request.user)
            active_tab = 'notifications'
            if tab == 'seuils_role' and est_admin_navire:
                active_tab = 'seuils_role'
            elif tab == 'utilisateurs' and peut_gerer_responsables:
                active_tab = 'utilisateurs'
            elif tab == 'modules' and peut_gerer_modules:
                active_tab = 'modules'
            elif tab == 'commandants_adjoints' and peut_gerer_coma:
                active_tab = 'commandants_adjoints'
            context = {
                'active_tab': active_tab,
                'user_notification_time': fmt_time(getattr(profile, 'notification_time', None)),
                'user_notification_time_soir': fmt_time(getattr(profile, 'notification_time_soir', None)),
                'peut_gerer_seuils': est_admin_navire,
                'peut_gerer_responsables': peut_gerer_responsables,
                'peut_gerer_modules': peut_gerer_modules,
                'peut_gerer_coma': peut_gerer_coma,
            }
            if active_tab == 'commandants_adjoints':
                mon_ship = Ship.objects.filter(pk=ship_id_for_user(request.user)).first()
                context.update(coma.contexte_onglet(mon_ship))
                context.update(en_second.contexte_onglet(mon_ship))
                context.update(suppleance.contexte_onglet(mon_ship))
            if active_tab == 'seuils_role':
                mon_ship_id = ship_id_for_user(request.user)
                context.update({
                    'seuils_ship': Ship.objects.filter(pk=mon_ship_id).first(),
                    'seuils_lignes': _lignes_seuils(mon_ship_id, 'SHIP'),
                    'seuils_lignes_globales': [],
                    'peut_editer_global': False,
                    'roles_pour_seuils': ROLES_POUR_SEUILS,
                })
            if active_tab == 'modules':
                mon_ship_id = ship_id_for_user(request.user)
                context.update({
                    'modules_ship': Ship.objects.filter(pk=mon_ship_id).first(),
                    'modules_lignes': _lignes_modules(mon_ship_id),
                })
            if active_tab == 'utilisateurs':
                # Seules les données nécessaires à la désignation de
                # responsables transverses sont exposées ici (pas les
                # référentiels Grades/Fonctions/Rôles, qui restent réservés au
                # superuser) : liste des spécialités pour le sélecteur, et les
                # responsables déjà désignés.
                context.update({
                    'specialites': SpecialityChoice.objects.order_by('name'),
                    'responsables_specialite': ResponsableSpecialite.objects.select_related(
                        'specialite', 'user'
                    ).order_by('specialite__name', 'user__last_name', 'user__first_name'),
                    'responsables_classe_navire': ResponsableClasseNavire.objects.select_related('user').order_by(
                        'classe_navire', 'user__last_name', 'user__first_name'
                    ),
                    'classes_navire_disponibles': list(
                        Ship.objects.exclude(classe_navire='').values_list(
                            'classe_navire', flat=True
                        ).distinct().order_by('classe_navire')
                    ),
                    'marins_disponibles': User.objects.order_by('last_name', 'first_name', 'username'),
                    **chefs_responsables.contexte_ecran(),
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

        services_qs = Service.objects.select_related('ship', 'equipage')
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
            'fonctions_quart': FonctionQuartChoice.objects.order_by('name'),
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
            'peut_gerer_responsables': True,
            'peut_gerer_modules': True,
            'peut_gerer_coma': True,
            # Responsables transverses (dashboards par spécialité / par classe de
            # navire, tâche Notion « Dashboards transverses par spécialité et par
            # classe de navire ») : rôle indépendant de la hiérarchie Navire →
            # Service → Secteur → Section, géré ici comme les autres
            # référentiels communs à toute la flotte.
            'responsables_specialite': ResponsableSpecialite.objects.select_related('specialite', 'user').order_by(
                'specialite__name', 'user__last_name', 'user__first_name'
            ),
            'responsables_classe_navire': ResponsableClasseNavire.objects.select_related('user').order_by(
                'classe_navire', 'user__last_name', 'user__first_name'
            ),
            'classes_navire_disponibles': list(
                Ship.objects.exclude(classe_navire='').values_list('classe_navire', flat=True).distinct().order_by('classe_navire')
            ),
            'marins_disponibles': User.objects.order_by('last_name', 'first_name', 'username'),
            **chefs_responsables.contexte_ecran(),
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
        if tab == 'commandants_adjoints':
            context.update(coma.contexte_onglet(selected_ship))
            context.update(en_second.contexte_onglet(selected_ship))
            context.update(suppleance.contexte_onglet(selected_ship))
        if tab == 'modules':
            # MASTER_ADMIN choisit le navire à configurer, même sélecteur que
            # l'onglet Sécurité ci-dessus (selected_ship).
            context.update({
                'modules_ship': selected_ship,
                'modules_lignes': _lignes_modules(selected_ship.id if selected_ship else None),
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
        elif action == 'add_fonction_quart' and name:
            FonctionQuartChoice.objects.get_or_create(name=name, defaults={'active': True})
            messages.success(request, "Fonction de quart ajoutée.")
            AuditLog.objects.create(actor=request.user, action='add_fonction_quart', details=f'name={name}')
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
                    capacite_aviation=src_ship.capacite_aviation, double_equipage=src_ship.double_equipage,
                )
                # Reprend les équipages (double équipage) puis l'organisation de
                # chacun, sans titulaires ni marins ; un navire à équipage unique
                # n'a que l'organisation sans équipage (clé None).
                equipages_copies = {None: None}
                for eq in src_ship.equipages.all():
                    equipages_copies[eq] = Equipage.objects.create(ship=new_ship, nom=eq.nom)
                if src_ship.equipage_a_bord_id:
                    new_ship.equipage_a_bord = equipages_copies[src_ship.equipage_a_bord]
                    new_ship.save(update_fields=["equipage_a_bord", "updated_at"])
                for eq_source, eq_copie in equipages_copies.items():
                    copier_organisation(src_ship, eq_source, new_ship, eq_copie)
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
                    # Double équipage : le service est créé pour l'équipage choisi.
                    equipage = ship.equipages.filter(pk=request.POST.get('equipage_id') or 0).first()
                    if ship.double_equipage and equipage is None:
                        messages.error(request, "Choisissez l'équipage du service.")
                    else:
                        Service.objects.get_or_create(name=name, ship=ship, equipage=equipage)
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
                    Sector.objects.get_or_create(name=name, service=service, defaults={'equipage': service.equipage})
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
                    Section.objects.get_or_create(name=name, sector=sector, defaults={'equipage': sector.equipage})
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
        elif action == 'add_responsable_specialite':
            specialite_id = request.POST.get('specialite_id')
            user_id = request.POST.get('user_id')
            try:
                specialite = SpecialityChoice.objects.get(pk=specialite_id)
                marin = User.objects.get(pk=user_id)
                _, cree = ResponsableSpecialite.objects.get_or_create(specialite=specialite, user=marin)
                if cree:
                    messages.success(
                        request,
                        f"{marin.get_full_name() or marin.username} désigné responsable de « {specialite.name} ».",
                    )
                    AuditLog.objects.create(
                        actor=request.user, action='add_responsable_specialite',
                        details=f'specialite={specialite.name}; user={marin.username}',
                    )
                else:
                    messages.warning(request, "Ce marin est déjà responsable de cette spécialité.")
            except (SpecialityChoice.DoesNotExist, User.DoesNotExist, ValueError):
                messages.error(request, "Spécialité ou marin introuvable.")
        elif action == 'retirer_responsable_specialite':
            pk = request.POST.get('pk')
            chefs_a_corriger = chefs_responsables.chefs_qui_encadreraient_tous(exclus_pk=pk)
            if chefs_a_corriger:
                noms = ', '.join(c.user.get_full_name() or c.user.username for c in chefs_a_corriger)
                messages.error(
                    request,
                    f"Retrait refusé : {noms} encadrerait alors tous les responsables de spécialité restants. "
                    "Modifiez d'abord sa sélection de responsables, puis retirez ce responsable.",
                )
            else:
                ResponsableSpecialite.objects.filter(pk=pk).delete()
                messages.success(request, "Responsable de spécialité retiré.")
                AuditLog.objects.create(actor=request.user, action='retirer_responsable_specialite', details=f'pk={pk}')
        elif action == 'add_responsable_classe' and name:
            user_id = request.POST.get('user_id')
            try:
                marin = User.objects.get(pk=user_id)
                _, cree = ResponsableClasseNavire.objects.get_or_create(classe_navire=name, user=marin)
                if cree:
                    messages.success(
                        request,
                        f"{marin.get_full_name() or marin.username} désigné responsable de la classe « {name} ».",
                    )
                    AuditLog.objects.create(
                        actor=request.user, action='add_responsable_classe',
                        details=f'classe={name}; user={marin.username}',
                    )
                else:
                    messages.warning(request, "Ce marin est déjà responsable de cette classe de navire.")
            except (User.DoesNotExist, ValueError):
                messages.error(request, "Marin introuvable.")
        elif action == 'retirer_responsable_classe':
            pk = request.POST.get('pk')
            ResponsableClasseNavire.objects.filter(pk=pk).delete()
            messages.success(request, "Responsable de classe de navire retiré.")
            AuditLog.objects.create(actor=request.user, action='retirer_responsable_classe', details=f'pk={pk}')
        elif action == 'delete_fonction':
            pk = request.POST.get('pk')
            try:
                ServiceFunctionChoice.objects.filter(pk=pk).delete()
                messages.success(request, "Fonction supprimée.")
                AuditLog.objects.create(actor=request.user, action='delete_fonction', details=f'pk={pk}')
            except ProtectedError:
                # Utilisée par au moins une liste de services de garde
                # (quarts.models.ServiceGarde.fonction, on_delete=PROTECT) —
                # on ne supprime pas silencieusement une fonction déjà en
                # usage, cf. correction de cadrage du 09/09/2026.
                messages.error(request, "Impossible de supprimer : cette fonction est utilisée par au moins une liste de services de garde.")
        elif action == 'delete_fonction_quart':
            pk = request.POST.get('pk')
            try:
                FonctionQuartChoice.objects.filter(pk=pk).delete()
                messages.success(request, "Fonction de quart supprimée.")
                AuditLog.objects.create(actor=request.user, action='delete_fonction_quart', details=f'pk={pk}')
            except ProtectedError:
                messages.error(request, "Impossible de supprimer : cette fonction est utilisée par au moins une liste de quarts.")
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
        elif action in coma.ACTIONS:
            next_tab = 'commandants_adjoints'
            coma.traiter_action(request, action)
        elif action in en_second.ACTIONS:
            next_tab = 'commandants_adjoints'
            en_second.traiter_action(request, action)
        elif action in suppleance.ACTIONS:
            next_tab = 'commandants_adjoints'
            suppleance.traiter_action(request, action)
        elif action in chefs_responsables.ACTIONS:
            chefs_responsables.traiter_action(request, action)
        elif action == 'toggle_module':
            # Onglet Modules : bascule activé/désactivé d'un module applicatif
            # pour un navire. Accessible à un rôle habilité par le seuil
            # configurable "module_gestion" (COMMANDANT par défaut, cf.
            # matrix/core/role_thresholds.py) limité à SON navire, ou à un
            # MASTER_ADMIN qui choisit le navire. Aucune donnée n'est jamais
            # supprimée : seuls le menu et les vues web du module sont masqués
            # tant qu'il reste désactivé (cf. matrix/core/modules.py).
            next_tab = 'modules'
            cle_module = request.POST.get('cle_module')
            module_info = MODULES_PAR_CLE.get(cle_module)
            if module_info is None:
                messages.error(request, "Module inconnu.")
            else:
                if request.user.is_superuser:
                    ship = Ship.objects.filter(pk=request.POST.get('ship_id')).first()
                else:
                    ship = Ship.objects.filter(pk=ship_id_for_user(request.user)).first()
                if ship is None:
                    messages.error(request, "Aucune unité sélectionnée.")
                else:
                    etat, _ = ModuleActivation.objects.get_or_create(
                        ship=ship, module=cle_module, defaults={'active': True},
                    )
                    etat.active = not etat.active
                    etat.save(update_fields=['active', 'updated_at'])
                    invalidate_modules_cache(ship.id)
                    AuditLog.objects.create(
                        actor=request.user, action='toggle_module',
                        details=f"navire={ship.name}; module={cle_module}; actif={etat.active}",
                    )
                    messages.success(
                        request,
                        f"Module « {module_info.libelle} » "
                        f"{'activé' if etat.active else 'désactivé'} pour {ship.name}.",
                    )
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
