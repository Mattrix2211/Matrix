from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, TemplateView
from django.urls import reverse_lazy
from django.contrib.auth import get_user_model
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from .models import UserProfile, GradeChoice, SpecialityChoice, ServiceFunctionChoice, AuditLog, Roles
from matrix.core.roles import user_role_level, RoleLevel
from matrix.core.permissions import ManageUsersPermission
from matrix.core.scopes import is_master_admin, ship_id_for_user, perimetre_navire_q
from training.models import CandidatureFormation
from training.services import qualifications_validees_de


def _role_attribution_autorisee(acting_user, role_cible):
    """Vérifie que l'utilisateur courant peut attribuer le rôle demandé à un tiers.

    Réutilise la matrice ManageUsersPermission.MANAGE_MAP déjà définie côté API DRF
    (matrix/core/permissions.py) pour que le web et l'API appliquent exactement la
    même règle. Empêche par exemple un COMMANDANT de s'auto-attribuer (ou d'attribuer
    à un tiers) le rôle ADMIN_NAVIRE ou MASTER_ADMIN.
    """
    if getattr(acting_user, "is_superuser", False):
        return True
    profile = getattr(acting_user, "profile", None)
    acting_role = profile.role if profile else None
    if acting_role in (Roles.MASTER_ADMIN, Roles.ADMIN_NAVIRE):
        return True
    allowed = ManageUsersPermission.MANAGE_MAP.get(acting_role, set())
    return role_cible in allowed


def _resoudre_affectation_dans_perimetre(acting_user, ship_id=None, service_id=None, sector_id=None, section_id=None):
    """Résout les valeurs d'affectation (navire/service/secteur/section) demandées
    pour un utilisateur, en s'assurant qu'elles appartiennent au périmètre navire
    de l'appelant : un COMMANDANT ou un ADMIN_NAVIRE ne peut affecter un
    utilisateur qu'à son propre navire (ou à un service/secteur/section qui en
    dépend) ; MASTER_ADMIN (et un superutilisateur) garde une liberté totale sur
    la flotte entière. Réutilise exactement le même filtrage que celui déjà
    appliqué aux listes déroulantes du formulaire (cf.
    UserDirectoryView.get_context_data) plutôt que d'introduire un nouveau
    mécanisme de vérification de périmètre.

    Avant correction, create_user et les actions bulk_update_ship/service/
    sector/section faisaient confiance à l'id transmis par le formulaire sans
    jamais vérifier qu'il appartenait au périmètre de l'appelant : un
    COMMANDANT pouvait ainsi, en forgeant une requête, rattacher un utilisateur
    de son navire à un navire/service/secteur/section d'un AUTRE navire.

    Renvoie (True, ship, service, sector, section) si toutes les valeurs
    demandées (celles non vides) existent et sont dans le périmètre. Renvoie
    (False, None, None, None, None) si l'une d'elles est invalide ou hors
    périmètre : l'appelant ne doit alors procéder à AUCUNE modification, pour
    éviter un état partiellement appliqué."""
    from org.models import Ship, Service, Sector, Section
    if is_master_admin(acting_user):
        ship_qs, service_qs = Ship.objects.all(), Service.objects.all()
        sector_qs, section_qs = Sector.objects.all(), Section.objects.all()
    else:
        mon_navire_id = ship_id_for_user(acting_user)
        ship_qs = Ship.objects.filter(pk=mon_navire_id)
        service_qs = Service.objects.filter(ship_id=mon_navire_id)
        sector_qs = Sector.objects.filter(service__ship_id=mon_navire_id)
        section_qs = Section.objects.filter(sector__service__ship_id=mon_navire_id)
    try:
        ship = ship_qs.get(pk=ship_id) if ship_id else None
        service = service_qs.get(pk=service_id) if service_id else None
        sector = sector_qs.get(pk=sector_id) if sector_id else None
        section = section_qs.get(pk=section_id) if section_id else None
    except (Ship.DoesNotExist, Service.DoesNotExist, Sector.DoesNotExist, Section.DoesNotExist):
        return False, None, None, None, None
    return True, ship, service, sector, section


def _utilisateurs_gerables_par(acting_user):
    """Périmètre des comptes utilisateurs qu'un COMMANDANT (et au-dessus) peut
    modifier via les actions POST de l'annuaire (édition, suppression,
    réinitialisation de mot de passe, actions groupées).

    Réutilise exactement le même périmètre que la lecture
    (UserDirectoryView.get_queryset() ci-dessous) : seul MASTER_ADMIN (ou un
    superutilisateur) peut agir sur la flotte entière ; un COMMANDANT ou un
    ADMIN_NAVIRE ne peut agir que sur le personnel de SON navire. Avant
    correction, les actions POST (edit_user, delete_user, set_password,
    bulk_*) résolvaient l'utilisateur cible sans aucun filtre de périmètre :
    un COMMANDANT du navire A pouvait éditer, supprimer ou réinitialiser le
    mot de passe d'un utilisateur d'un autre navire en forgeant une requête
    (faille IDOR en écriture)."""
    User = get_user_model()
    qs = User.objects.all()
    if not is_master_admin(acting_user):
        qs = qs.filter(perimetre_navire_q(acting_user, "profile__"))
    return qs


class UserDirectoryView(LoginRequiredMixin, ListView):
    template_name = "accounts/directory.html"
    context_object_name = "users"

    def dispatch(self, request, *args, **kwargs):
        # L'annuaire utilisateurs (consultation ET actions de gestion) est réservé
        # aux administrateurs (COMMANDANT et au-dessus) : gérer les identifiants,
        # rôles et mots de passe des marins n'est pas du ressort d'un chef de
        # secteur/service. Aucun seuil n'était en place auparavant (bug sécurité).
        # Le test d'authentification (redirection vers /login/) reste géré par
        # LoginRequiredMixin ci-dessous ; on ne bloque en 403 qu'un utilisateur
        # déjà connecté mais dont le rôle est insuffisant.
        if request.user.is_authenticated and user_role_level(request.user) < RoleLevel.COMMANDANT:
            from django.http import HttpResponseForbidden
            return HttpResponseForbidden()
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        User = get_user_model()
        qs = User.objects.select_related("profile", "profile__ship").order_by("profile__ship__name", "username")
        # Périmètre par défaut : seul MASTER_ADMIN (ou un superutilisateur) voit
        # la flotte entière. L'accès à cette vue est déjà réservé à COMMANDANT
        # et au-dessus (cf. dispatch() ci-dessus) ; tous les rôles restants
        # (ADMIN_NAVIRE et COMMANDANT) sont rattachés à un navire précis (cf.
        # matrix/core/scopes.py::is_master_admin) et ne doivent voir que le
        # personnel de LEUR navire, à n'importe quel niveau de rattachement
        # (navire/service/secteur/section — perimetre_navire_q, contrairement
        # à build_scope_q, couvre aussi les profils dont seul le secteur ou la
        # section est renseigné, sans le champ "Unité" lui-même). Appliqué
        # avant le filtre ?ship= ci-dessous pour qu'il ne puisse jamais
        # élargir la vue au-delà de ce périmètre (bug sécurité corrigé : un
        # COMMANDANT pouvait consulter le personnel d'un autre navire via ce
        # paramètre d'URL).
        if not is_master_admin(self.request.user):
            qs = qs.filter(perimetre_navire_q(self.request.user, "profile__"))
        ship_id = self.request.GET.get("ship")
        if ship_id:
            qs = qs.filter(profile__ship_id=ship_id)
        return qs

    def get_context_data(self, **kwargs):
        from accounts.models import RoleAvailability
        from org.models import Ship, Service, Sector, Section
        ctx = super().get_context_data(**kwargs)
        # Roles disponibles (hors MASTER_ADMIN), filtrés par RoleAvailability
        all_roles = [c for c in Roles.choices if c[0] != 'MASTER_ADMIN']
        opts = {o.code: o.active for o in RoleAvailability.objects.all()}
        ctx["roles"] = [{"code": code, "label": label} for code, label in all_roles if opts.get(code, True)]
        # Hiérarchie pour sélection (filtre "Unité" et formulaires de création/
        # édition) : un utilisateur limité à son navire (non MASTER_ADMIN) ne
        # doit se voir proposer que son propre navire — lui montrer les autres
        # navires de la flotte n'aurait aucun sens (l'annuaire ne renverra de
        # toute façon aucun résultat pour eux) et fuiterait leurs noms.
        if is_master_admin(self.request.user):
            ctx["ships"] = Ship.objects.order_by("name")
            ctx["services"] = Service.objects.select_related("ship").order_by("name")
            ctx["sectors"] = Sector.objects.select_related("service", "service__ship").order_by("name")
            ctx["sections"] = Section.objects.select_related("sector", "sector__service", "sector__service__ship").order_by("name")
        else:
            mon_navire_id = ship_id_for_user(self.request.user)
            ctx["ships"] = Ship.objects.filter(pk=mon_navire_id).order_by("name")
            ctx["services"] = Service.objects.filter(ship_id=mon_navire_id).select_related("ship").order_by("name")
            ctx["sectors"] = Sector.objects.filter(service__ship_id=mon_navire_id).select_related("service", "service__ship").order_by("name")
            ctx["sections"] = Section.objects.filter(sector__service__ship_id=mon_navire_id).select_related("sector", "sector__service", "sector__service__ship").order_by("name")
        # Choix pour fonction, grade et spécialité
        ctx["fonctions"] = ServiceFunctionChoice.objects.filter(active=True).order_by("name")
        ctx["grades"] = GradeChoice.objects.filter(active=True).order_by("name")
        ctx["specialites"] = SpecialityChoice.objects.filter(active=True).order_by("name")
        ctx["export_url"] = self.request.build_absolute_uri("?" + ("ship=" + str(self.request.GET.get("ship")) + "&" if self.request.GET.get("ship") else "") + "export=xlsx")
        return ctx

    def get(self, request, *args, **kwargs):
        if request.GET.get("export") == "xlsx":
            User = get_user_model()
            qs = self.get_queryset()
            try:
                from openpyxl import Workbook
                wb = Workbook()
                ws = wb.active
                ws.title = "Utilisateurs"
                headers = [
                    "Identifiant", "Prénom", "Nom", "Rôle", "Grade", "Spécialité", "Matricule",
                    "Unité", "Service", "Secteur", "Section", "Fonction", "Date de naissance", "Âge"
                ]
                ws.append(headers)
                for u in qs:
                    prof = getattr(u, "profile", None)
                    date_str = prof.date_naissance.isoformat() if (prof and prof.date_naissance) else ""
                    age_val = prof.age if (prof and prof.age is not None) else ""
                    ws.append([
                        u.username,
                        u.first_name,
                        u.last_name,
                        prof.role if prof else "",
                        prof.grade if prof else "",
                        prof.specialite if prof else "",
                        prof.matricule if prof else "",
                        prof.ship.name if (prof and prof.ship) else "",
                        prof.service.name if (prof and prof.service) else "",
                        prof.sector.name if (prof and prof.sector) else "",
                        prof.section.name if (prof and prof.section) else "",
                        prof.fonction_service if prof else "",
                        date_str,
                        age_val,
                    ])
                from django.http import HttpResponse
                import io
                buf = io.BytesIO()
                wb.save(buf)
                buf.seek(0)
                resp = HttpResponse(buf.read(), content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
                resp["Content-Disposition"] = "attachment; filename=utilisateurs.xlsx"
                AuditLog.objects.create(actor=request.user, action="export_users_xlsx", target_user=None, details=f"rows={qs.count()}")
                return resp
            except Exception:
                from django.contrib import messages
                messages.error(request, "Export Excel indisponible.")
                return super().get(request, *args, **kwargs)
        return super().get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        from django.shortcuts import redirect
        from org.models import Ship, Service, Sector, Section
        from django.utils.text import slugify
        # Seuil minimum pour toute action d'écriture sur l'annuaire des comptes : la
        # gestion des comptes utilisateurs (création, rôle, mot de passe, suppression,
        # rattachement) relève du périmètre COMMANDANT et au-dessus. Corrige la faille
        # permettant à n'importe quel utilisateur connecté (y compris un EQUIPIER) de
        # s'auto-promouvoir ou d'agir sur les comptes d'autrui via un POST direct.
        if user_role_level(request.user) < RoleLevel.COMMANDANT:
            raise PermissionDenied
        action = request.POST.get("action")
        # Actions groupées
        if action in ("bulk_update_role", "bulk_update_ship", "bulk_update_fonction", "bulk_update_service", "bulk_update_sector", "bulk_update_section", "bulk_update_grade", "bulk_update_specialite", "bulk_delete_users", "bulk_reset_passwords"):
            ids = request.POST.getlist("selected_ids")
            # Périmètre navire appliqué avant toute exécution : un id hors du
            # navire de l'appelant (COMMANDANT/ADMIN_NAVIRE) est ignoré, comme
            # s'il n'existait pas (cf. _utilisateurs_gerables_par ci-dessus).
            users = _utilisateurs_gerables_par(request.user).filter(id__in=ids)
            count = users.count()
            if action == "bulk_update_role":
                role = request.POST.get("role")
                if not _role_attribution_autorisee(request.user, role):
                    messages.error(request, "Vous n'avez pas les droits pour attribuer ce rôle.")
                    return redirect("user-directory")
                for user in users:
                    profile, _ = UserProfile.objects.get_or_create(user=user)
                    profile.role = role
                    profile.save(update_fields=["role"])
                    AuditLog.objects.create(actor=request.user, action="bulk_update_role", target_user=user, details=f"role={role}")
                messages.success(request, f"Rôle mis à jour pour {count} utilisateur(s).")
            elif action == "bulk_update_ship":
                ship_id = request.POST.get("ship_id")
                # Valeur de destination validée contre le périmètre de l'appelant :
                # un COMMANDANT/ADMIN_NAVIRE ne peut affecter ses utilisateurs qu'à
                # son propre navire, jamais à un navire tiers (cf.
                # _resoudre_affectation_dans_perimetre).
                ok, ship, _, _, _ = _resoudre_affectation_dans_perimetre(request.user, ship_id=ship_id)
                if not ok:
                    messages.error(request, "Unité invalide ou hors de votre périmètre.")
                    return redirect("user-directory")
                for user in users:
                    profile, _ = UserProfile.objects.get_or_create(user=user)
                    profile.ship = ship
                    profile.save(update_fields=["ship"])
                    AuditLog.objects.create(actor=request.user, action="bulk_update_ship", target_user=user, details=f"ship_id={ship_id}")
                messages.success(request, f"Unité mise à jour pour {count} utilisateur(s).")
            elif action == "bulk_update_fonction":
                fonction = request.POST.get("fonction_service", "")
                for user in users:
                    profile, _ = UserProfile.objects.get_or_create(user=user)
                    profile.fonction_service = fonction
                    profile.save(update_fields=["fonction_service"])
                    AuditLog.objects.create(actor=request.user, action="bulk_update_fonction", target_user=user, details=f"fonction={fonction}")
                messages.success(request, f"Fonction mise à jour pour {count} utilisateur(s).")
            elif action == "bulk_update_service":
                service_id = request.POST.get("service_id")
                # Valeur de destination validée contre le périmètre de l'appelant
                # (cf. _resoudre_affectation_dans_perimetre) : le service ciblé doit
                # dépendre du navire de l'appelant.
                ok, _, service, _, _ = _resoudre_affectation_dans_perimetre(request.user, service_id=service_id)
                if not ok:
                    messages.error(request, "Service invalide ou hors de votre périmètre.")
                    return redirect("user-directory")
                for user in users:
                    profile, _ = UserProfile.objects.get_or_create(user=user)
                    profile.service = service
                    profile.save(update_fields=["service"])
                    AuditLog.objects.create(actor=request.user, action="bulk_update_service", target_user=user, details=f"service_id={service_id}")
                messages.success(request, f"Service mis à jour pour {count} utilisateur(s).")
            elif action == "bulk_update_sector":
                sector_id = request.POST.get("sector_id")
                # Valeur de destination validée contre le périmètre de l'appelant
                # (cf. _resoudre_affectation_dans_perimetre) : le secteur ciblé doit
                # dépendre du navire de l'appelant.
                ok, _, _, sector, _ = _resoudre_affectation_dans_perimetre(request.user, sector_id=sector_id)
                if not ok:
                    messages.error(request, "Secteur invalide ou hors de votre périmètre.")
                    return redirect("user-directory")
                for user in users:
                    profile, _ = UserProfile.objects.get_or_create(user=user)
                    profile.sector = sector
                    profile.save(update_fields=["sector"])
                    AuditLog.objects.create(actor=request.user, action="bulk_update_sector", target_user=user, details=f"sector_id={sector_id}")
                messages.success(request, f"Secteur mis à jour pour {count} utilisateur(s).")
            elif action == "bulk_update_section":
                section_id = request.POST.get("section_id")
                # Valeur de destination validée contre le périmètre de l'appelant
                # (cf. _resoudre_affectation_dans_perimetre) : la section ciblée doit
                # dépendre du navire de l'appelant.
                ok, _, _, _, section = _resoudre_affectation_dans_perimetre(request.user, section_id=section_id)
                if not ok:
                    messages.error(request, "Section invalide ou hors de votre périmètre.")
                    return redirect("user-directory")
                for user in users:
                    profile, _ = UserProfile.objects.get_or_create(user=user)
                    profile.section = section
                    profile.save(update_fields=["section"])
                    AuditLog.objects.create(actor=request.user, action="bulk_update_section", target_user=user, details=f"section_id={section_id}")
                messages.success(request, f"Section mise à jour pour {count} utilisateur(s).")
            elif action == "bulk_update_grade":
                grade = request.POST.get("grade", "").strip()
                for user in users:
                    profile, _ = UserProfile.objects.get_or_create(user=user)
                    profile.grade = grade
                    profile.save(update_fields=["grade"])
                    AuditLog.objects.create(actor=request.user, action="bulk_update_grade", target_user=user, details=f"grade={grade}")
                messages.success(request, f"Grade mis à jour pour {count} utilisateur(s).")
            elif action == "bulk_update_specialite":
                specialite = request.POST.get("specialite", "").strip()
                for user in users:
                    profile, _ = UserProfile.objects.get_or_create(user=user)
                    profile.specialite = specialite
                    profile.save(update_fields=["specialite"])
                    AuditLog.objects.create(actor=request.user, action="bulk_update_specialite", target_user=user, details=f"specialite={specialite}")
                messages.success(request, f"Spécialité mise à jour pour {count} utilisateur(s).")
            elif action == "bulk_delete_users":
                for user in users:
                    AuditLog.objects.create(actor=request.user, action="bulk_delete_user", target_user=user, details=f"username={user.username}")
                users.delete()
                messages.success(request, f"{count} utilisateur(s) supprimé(s).")
            elif action == "bulk_reset_passwords":
                import secrets, string
                def generate_password(length=14):
                    alphabet = string.ascii_letters + string.digits + "!@$%*#?"
                    pw = ''.join(secrets.choice(alphabet) for _ in range(length))
                    if (any(c.islower() for c in pw) and any(c.isupper() for c in pw) and any(c.isdigit() for c in pw) and any(c in "!@$%*#?" for c in pw)):
                        return pw
                    return generate_password(length)
                for user in users:
                    password = generate_password()
                    user.set_password(password)
                    user.save()
                    AuditLog.objects.create(actor=request.user, action="bulk_reset_password", target_user=user, details="password set")
                messages.success(request, f"Mot de passe réinitialisé pour {count} utilisateur(s).")
            return redirect("user-directory")
        if action == "create_user":
            email = request.POST.get("email", "").strip()
            first_name = request.POST.get("first_name", "").strip()
            last_name = request.POST.get("last_name", "").strip()
            role = request.POST.get("role")
            fonction_service = request.POST.get("fonction_service", "").strip()
            grade = request.POST.get("grade", "").strip()
            specialite = request.POST.get("specialite", "").strip()
            matricule = request.POST.get("matricule", "").strip()
            date_naissance = request.POST.get("date_naissance", "").strip()
            ship_id = request.POST.get("ship_id")
            service_id = request.POST.get("service_id")
            sector_id = request.POST.get("sector_id")
            section_id = request.POST.get("section_id")
            if role and not _role_attribution_autorisee(request.user, role):
                messages.error(request, "Vous n'avez pas les droits pour attribuer ce rôle.")
                return redirect("user-directory")
            # Valeurs de destination (navire/service/secteur/section) validées
            # contre le périmètre de l'appelant AVANT toute création de compte
            # (cf. _resoudre_affectation_dans_perimetre), pour ne jamais créer un
            # utilisateur rattaché à un navire hors du périmètre du COMMANDANT/
            # ADMIN_NAVIRE appelant, et pour ne pas laisser un compte créé dans un
            # état partiel si la valeur demandée est refusée.
            ok, ship, service, sector, section = _resoudre_affectation_dans_perimetre(
                request.user, ship_id=ship_id, service_id=service_id, sector_id=sector_id, section_id=section_id
            )
            if not ok:
                messages.error(request, "Unité, service, secteur ou section invalide, ou hors de votre périmètre.")
                return redirect("user-directory")
            if role:
                User = get_user_model()
                # Identifiant = prenom.nom (slugifié), avec suffixe numérique si collision
                from django.utils.text import slugify
                base_parts = []
                if first_name:
                    base_parts.append(slugify(first_name))
                if last_name:
                    base_parts.append(slugify(last_name))
                base = ".".join(base_parts) if base_parts else "utilisateur"
                username = base
                if User.objects.filter(username=username).exists():
                    i = 2
                    while User.objects.filter(username=f"{base}{i}").exists():
                        i += 1
                    username = f"{base}{i}"
                user = User.objects.create(username=username, email=email, first_name=first_name, last_name=last_name)
                # Pas d'email: le mot de passe sera défini via la clé dans l'annuaire
                user.set_unusable_password()
                user.save(update_fields=["password"])  # set_unusable_password fixe le hash
                profile, _ = UserProfile.objects.get_or_create(user=user, defaults={"role": role})
                # Liens hiérarchiques
                if fonction_service:
                    profile.fonction_service = fonction_service
                if grade:
                    profile.grade = grade
                if specialite:
                    profile.specialite = specialite
                if matricule:
                    profile.matricule = matricule
                if date_naissance:
                    try:
                        from datetime import datetime
                        profile.date_naissance = datetime.strptime(date_naissance, "%Y-%m-%d").date()
                    except Exception:
                        profile.date_naissance = None
                # Objets déjà résolus et validés contre le périmètre de l'appelant
                # ci-dessus (cf. _resoudre_affectation_dans_perimetre).
                profile.ship = ship
                profile.service = service
                profile.sector = sector
                profile.section = section
                profile.save()
                AuditLog.objects.create(actor=request.user, action="create_user", target_user=user, details=f"role={role}; ship_id={ship_id}")
                messages.success(request, f"Utilisateur {user.username} créé avec succès.")
        elif action == "delete_user":
            pk = request.POST.get("pk")
            User = get_user_model()
            # Résolution de la cible bornée au périmètre navire de l'appelant
            # (cf. _utilisateurs_gerables_par) : un id hors périmètre lève
            # User.DoesNotExist, exactement comme si le compte n'existait pas.
            try:
                user = _utilisateurs_gerables_par(request.user).get(pk=pk)
                AuditLog.objects.create(actor=request.user, action="delete_user", target_user=user, details=f"username={user.username}")
                user.delete()
            except User.DoesNotExist:
                pass
        elif action == "edit_user":
            pk = request.POST.get("pk")
            role = request.POST.get("role")
            if role and not _role_attribution_autorisee(request.user, role):
                messages.error(request, "Vous n'avez pas les droits pour attribuer ce rôle.")
                return redirect("user-directory")
            User = get_user_model()
            # Résolution de la cible bornée au périmètre navire de l'appelant
            # (cf. _utilisateurs_gerables_par).
            try:
                user = _utilisateurs_gerables_par(request.user).get(pk=pk)
                user.username = request.POST.get("username", user.username).strip() or user.username
                user.email = request.POST.get("email", user.email).strip()
                user.first_name = request.POST.get("first_name", user.first_name).strip()
                user.last_name = request.POST.get("last_name", user.last_name).strip()
                user.save()
                profile, _ = UserProfile.objects.get_or_create(user=user)
                if role:
                    profile.role = role
                fonction_service = request.POST.get("fonction_service", "")
                profile.fonction_service = fonction_service
                # Grade et spécialité
                profile.grade = request.POST.get("grade", "").strip()
                profile.specialite = request.POST.get("specialite", "").strip()
                # Matricule et date de naissance
                profile.matricule = request.POST.get("matricule", "").strip()
                date_naissance = request.POST.get("date_naissance", "").strip()
                if date_naissance:
                    try:
                        from datetime import datetime
                        profile.date_naissance = datetime.strptime(date_naissance, "%Y-%m-%d").date()
                    except Exception:
                        pass
                else:
                    profile.date_naissance = None
                # Mise à jour des relations
                ship_id = request.POST.get("ship_id")
                service_id = request.POST.get("service_id")
                sector_id = request.POST.get("sector_id")
                section_id = request.POST.get("section_id")
                def get_or_none(model, pk):
                    try:
                        return model.objects.get(pk=pk)
                    except model.DoesNotExist:
                        return None
                profile.ship = get_or_none(Ship, ship_id) if ship_id else None
                profile.service = get_or_none(Service, service_id) if service_id else None
                profile.sector = get_or_none(Sector, sector_id) if sector_id else None
                profile.section = get_or_none(Section, section_id) if section_id else None
                profile.save()
                AuditLog.objects.create(actor=request.user, action="edit_user", target_user=user, details="profil mis à jour")
                messages.success(request, f"Utilisateur {user.username} mis à jour.")
            except User.DoesNotExist:
                pass
        elif action == "set_password":
            pk = request.POST.get("pk")
            password = request.POST.get("password", "").strip()
            # pas d'envoi d'email
            User = get_user_model()
            # Résolution de la cible bornée au périmètre navire de l'appelant
            # (cf. _utilisateurs_gerables_par).
            try:
                user = _utilisateurs_gerables_par(request.user).get(pk=pk)
                # Génère un mot de passe si vide
                if not password:
                    import secrets, string
                    def generate_password(length=14):
                        alphabet = string.ascii_letters + string.digits + "!@$%*#?"
                        pw = ''.join(secrets.choice(alphabet) for _ in range(length))
                        if (any(c.islower() for c in pw) and any(c.isupper() for c in pw) and any(c.isdigit() for c in pw) and any(c in "!@$%*#?" for c in pw)):
                            return pw
                        return generate_password(length)
                    password = generate_password()
                user.set_password(password)
                user.save()
                AuditLog.objects.create(actor=request.user, action="set_password", target_user=user, details="password set")
                messages.success(request, "Mot de passe défini.")
            except User.DoesNotExist:
                pass
        return redirect("user-directory")


class MonProfilView(LoginRequiredMixin, TemplateView):
    """« Mon profil » : fiche personnelle du marin connecté, en lecture seule.

    Le rattachement organisationnel (rôle, unité, service, secteur, section,
    grade, spécialité, matricule) n'est pas modifiable ici : sa gestion a été
    volontairement centralisée dans l'annuaire (UserDirectoryView, POST
    /users/), réservé à COMMANDANT et au-dessus depuis la correction de
    sécurité ci-dessus (cf. _role_attribution_autorisee) — rouvrir une
    édition en self-service sur ces champs reviendrait à recréer la faille
    corrigée. Cette page se contente donc d'afficher ces informations, et y
    ajoute la liste des qualifications (formations) déjà validées du marin,
    en réutilisant telle quelle la requête de la carte « Mes qualifications »
    du tableau de bord (training/services.py::qualifications_validees_de),
    ainsi que le suivi de ses candidatures individuelles à un stage (Circuit
    B — training/models.py::CandidatureFormation) en cours de traitement."""

    template_name = "accounts/profile.html"

    def get_context_data(self, **kwargs):
        contexte = super().get_context_data(**kwargs)
        contexte["profil"] = getattr(self.request.user, "profile", None)
        contexte["mes_qualifications"] = qualifications_validees_de(self.request.user)
        contexte["mes_candidatures"] = list(
            CandidatureFormation.objects.filter(marin=self.request.user).select_related("course")
        )
        return contexte


class UserSettingsView(LoginRequiredMixin, ListView):
    template_name = "accounts/settings_users.html"
    context_object_name = "grades"

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_superuser:
            from django.http import HttpResponseForbidden
            return HttpResponseForbidden()
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        return GradeChoice.objects.order_by("name")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["specialites"] = SpecialityChoice.objects.order_by("name")
        return ctx

    def post(self, request, *args, **kwargs):
        from django.contrib import messages
        action = request.POST.get("action")
        name = request.POST.get("name", "").strip()
        if action == "add_grade" and name:
            GradeChoice.objects.get_or_create(name=name, defaults={"active": True})
            messages.success(request, "Grade ajouté.")
        elif action == "add_specialite" and name:
            SpecialityChoice.objects.get_or_create(name=name, defaults={"active": True})
            messages.success(request, "Spécialité ajoutée.")
        elif action == "toggle_grade":
            pk = request.POST.get("pk")
            try:
                g = GradeChoice.objects.get(pk=pk)
                g.active = not g.active
                g.save(update_fields=["active"])
                messages.success(request, "Disponibilité du grade mise à jour.")
            except GradeChoice.DoesNotExist:
                pass
        elif action == "toggle_specialite":
            pk = request.POST.get("pk")
            try:
                s = SpecialityChoice.objects.get(pk=pk)
                s.active = not s.active
                s.save(update_fields=["active"])
                messages.success(request, "Disponibilité de la spécialité mise à jour.")
            except SpecialityChoice.DoesNotExist:
                pass
        from django.shortcuts import redirect
        return redirect("settings-users")
