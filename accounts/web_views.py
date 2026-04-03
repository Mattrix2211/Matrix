from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView
from django.urls import reverse_lazy
from django.contrib.auth import get_user_model
from django.contrib import messages
from .forms import UserProfileForm
from .models import UserProfile, GradeChoice, SpecialityChoice, ServiceFunctionChoice, AuditLog
from bordops.core.roles import user_role_level, RoleLevel


class UserDirectoryView(LoginRequiredMixin, ListView):
    template_name = "accounts/directory.html"
    context_object_name = "users"

    def get_queryset(self):
        User = get_user_model()
        qs = User.objects.select_related("profile", "profile__ship").order_by("profile__ship__name", "username")
        lvl = user_role_level(self.request.user)
        if lvl < RoleLevel.CHEF_SECTION:
            # Les équipiers ne voient que leur propre fiche
            return qs.filter(id=self.request.user.id)
        ship_id = self.request.GET.get("ship")
        if ship_id:
            return qs.filter(profile__ship_id=ship_id)
        # Export Excel
        if self.request.GET.get("export") == "xlsx":
            return qs
        return qs

    def get_context_data(self, **kwargs):
        from accounts.models import Roles, RoleAvailability
        from org.models import Ship, Service, Sector, Section
        ctx = super().get_context_data(**kwargs)
        # Roles disponibles (hors MASTER_ADMIN), filtrés par RoleAvailability
        all_roles = [c for c in Roles.choices if c[0] != 'MASTER_ADMIN']
        opts = {o.code: o.active for o in RoleAvailability.objects.all()}
        ctx["roles"] = [{"code": code, "label": label} for code, label in all_roles if opts.get(code, True)]
        # Hiérarchie pour sélection
        ctx["ships"] = Ship.objects.order_by("name")
        ctx["services"] = Service.objects.select_related("ship").order_by("name")
        ctx["sectors"] = Sector.objects.select_related("service", "service__ship").order_by("name")
        ctx["sections"] = Section.objects.select_related("sector", "sector__service", "sector__service__ship").order_by("name")
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
                    "Navire", "Service", "Secteur", "Section", "Fonction", "Date de naissance", "Âge"
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
        action = request.POST.get("action")
        # Actions groupées
        if action in ("bulk_update_role", "bulk_update_ship", "bulk_update_fonction", "bulk_update_service", "bulk_update_sector", "bulk_update_section", "bulk_update_grade", "bulk_update_specialite", "bulk_delete_users", "bulk_reset_passwords"):
            ids = request.POST.getlist("selected_ids")
            User = get_user_model()
            users = User.objects.filter(id__in=ids)
            count = users.count()
            if action == "bulk_update_role":
                role = request.POST.get("role")
                for user in users:
                    profile, _ = UserProfile.objects.get_or_create(user=user)
                    profile.role = role
                    profile.save(update_fields=["role"])
                    AuditLog.objects.create(actor=request.user, action="bulk_update_role", target_user=user, details=f"role={role}")
                messages.success(request, f"Rôle mis à jour pour {count} utilisateur(s).")
            elif action == "bulk_update_ship":
                ship_id = request.POST.get("ship_id")
                ship = None
                try:
                    ship = Ship.objects.get(pk=ship_id)
                except Ship.DoesNotExist:
                    ship = None
                for user in users:
                    profile, _ = UserProfile.objects.get_or_create(user=user)
                    profile.ship = ship
                    profile.save(update_fields=["ship"])
                    AuditLog.objects.create(actor=request.user, action="bulk_update_ship", target_user=user, details=f"ship_id={ship_id}")
                messages.success(request, f"Navire mis à jour pour {count} utilisateur(s).")
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
                service = None
                try:
                    service = Service.objects.get(pk=service_id)
                except Service.DoesNotExist:
                    service = None
                for user in users:
                    profile, _ = UserProfile.objects.get_or_create(user=user)
                    profile.service = service
                    profile.save(update_fields=["service"])
                    AuditLog.objects.create(actor=request.user, action="bulk_update_service", target_user=user, details=f"service_id={service_id}")
                messages.success(request, f"Service mis à jour pour {count} utilisateur(s).")
            elif action == "bulk_update_sector":
                sector_id = request.POST.get("sector_id")
                sector = None
                try:
                    sector = Sector.objects.get(pk=sector_id)
                except Sector.DoesNotExist:
                    sector = None
                for user in users:
                    profile, _ = UserProfile.objects.get_or_create(user=user)
                    profile.sector = sector
                    profile.save(update_fields=["sector"])
                    AuditLog.objects.create(actor=request.user, action="bulk_update_sector", target_user=user, details=f"sector_id={sector_id}")
                messages.success(request, f"Secteur mis à jour pour {count} utilisateur(s).")
            elif action == "bulk_update_section":
                section_id = request.POST.get("section_id")
                section = None
                try:
                    section = Section.objects.get(pk=section_id)
                except Section.DoesNotExist:
                    section = None
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
                try:
                    if ship_id:
                        profile.ship = Ship.objects.get(pk=ship_id)
                    if service_id:
                        profile.service = Service.objects.get(pk=service_id)
                    if sector_id:
                        profile.sector = Sector.objects.get(pk=sector_id)
                    if section_id:
                        profile.section = Section.objects.get(pk=section_id)
                except (Ship.DoesNotExist, Service.DoesNotExist, Sector.DoesNotExist, Section.DoesNotExist):
                    pass
                profile.save()
                AuditLog.objects.create(actor=request.user, action="create_user", target_user=user, details=f"role={role}; ship_id={ship_id}")
                messages.success(request, f"Utilisateur {user.username} créé avec succès.")
        elif action == "delete_user":
            pk = request.POST.get("pk")
            User = get_user_model()
            try:
                user = User.objects.get(pk=pk)
                AuditLog.objects.create(actor=request.user, action="delete_user", target_user=user, details=f"username={user.username}")
            except User.DoesNotExist:
                pass
            User.objects.filter(pk=pk).delete()
        elif action == "edit_user":
            pk = request.POST.get("pk")
            User = get_user_model()
            try:
                user = User.objects.get(pk=pk)
                user.username = request.POST.get("username", user.username).strip() or user.username
                user.email = request.POST.get("email", user.email).strip()
                user.first_name = request.POST.get("first_name", user.first_name).strip()
                user.last_name = request.POST.get("last_name", user.last_name).strip()
                user.save()
                profile, _ = UserProfile.objects.get_or_create(user=user)
                role = request.POST.get("role")
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
                # Update relations
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
            try:
                user = User.objects.get(pk=pk)
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


# Vue Mon Profil supprimée: les informations sont gérées par l'ADMIN_NAVIRE


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
