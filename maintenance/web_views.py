import json
from django.views import View
from django.views.generic import ListView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.shortcuts import render, redirect
from django.http import HttpResponseBadRequest
from django.contrib.contenttypes.models import ContentType
from django.urls import reverse
from django.utils import timezone
from .models import MaintenancePlan, MaintenanceOccurrence, MaintenanceExecution, mettre_a_jour_echeance_installation
from assets.models import Asset, AssetType, ChecklistItemTemplate, ChecklistTemplate
from threads.models import Thread, Message, Attachment
from threads.utils import ajouter_commentaire, commentaires_de
from matrix.core.mixins import ScopedQuerySetMixin, build_scope_q
from matrix.core.roles import user_role_level, RoleLevel


class OccurrenceExecuteView(LoginRequiredMixin, View):
    template_name = 'maintenance/execute.html'

    def get(self, request, pk):
        try:
            occ = MaintenanceOccurrence.objects.select_related(
                'plan', 'asset', 'plan__checklist_template',
                'installation_maintenance', 'installation_maintenance__installation',
            ).get(pk=pk)
        except MaintenanceOccurrence.DoesNotExist:
            return HttpResponseBadRequest('Occurrence introuvable')
        if (request.user not in occ.assignees.all()) and (user_role_level(request.user) < RoleLevel.CHEF_SECTION):
            raise PermissionDenied
        items = []
        if occ.plan and occ.plan.checklist_template:
            items = list(occ.plan.checklist_template.items.order_by('order').all())
        contexte = {
            "occ": occ,
            "items": items,
            "commentaires": commentaires_de(occ),
            "commentaire_action_url": reverse('occurrence-comment-create', args=[occ.pk]),
        }
        return render(request, self.template_name, contexte)

    def post(self, request, pk):
        try:
            occ = MaintenanceOccurrence.objects.select_related(
                'plan', 'asset', 'plan__checklist_template',
                'installation_maintenance', 'installation_maintenance__installation',
            ).get(pk=pk)
        except MaintenanceOccurrence.DoesNotExist:
            return HttpResponseBadRequest('Occurrence introuvable')
        if (request.user not in occ.assignees.all()) and (user_role_level(request.user) < RoleLevel.CHEF_SECTION):
            raise PermissionDenied

        items = []
        if occ.plan and occ.plan.checklist_template:
            items = list(occ.plan.checklist_template.items.order_by('order').all())

        conformity = request.POST.get('conformity', '')

        # Passage en "Terminée" (DONE) d'une installation critique : geste engageant
        # qui exige une ré-authentification légère (mot de passe courant, comme un
        # "sudo" léger). Vérifié avant tout enregistrement, pour ne rien modifier si
        # le mot de passe saisi est incorrect. Une occurrence NON_CONFORME repasse en
        # WAITING_VALIDATION (pas DONE) et n'est donc pas concernée.
        installation = occ.installation_maintenance.installation if occ.installation_maintenance_id else None
        exige_validation = bool(installation and installation.critique) and conformity != 'NON_CONFORME'
        if exige_validation and not request.user.check_password(request.POST.get('mot_de_passe', '')):
            erreur = "Mot de passe incorrect : l'exécution n'a pas été validée."
            if request.headers.get('HX-Request'):
                return render(request, 'maintenance/_execute_erreur.html', {"occ": occ, "erreur": erreur})
            return render(request, self.template_name, {"occ": occ, "items": items, "erreur": erreur})

        # Collecter les résultats des items
        results = {}
        for item in items:
            key = f"item_{item.id}"
            val = request.POST.get(key)
            if item.field_type == 'checkbox':
                results[item.label] = request.POST.get(key) == 'on'
            else:
                results[item.label] = val

        notes = request.POST.get('notes', '')

        exec_obj, _ = MaintenanceExecution.objects.get_or_create(occurrence=occ)
        if not exec_obj.started_at:
            exec_obj.started_at = timezone.now()
        exec_obj.results = results
        exec_obj.conformity = conformity
        exec_obj.notes = notes
        exec_obj.executed_by = request.user
        exec_obj.completed_at = timezone.now()
        if exige_validation:
            exec_obj.valide_par = request.user
            exec_obj.date_validation = timezone.now()
        exec_obj.save()

        # Mettre à jour le statut de l'occurrence (le signal gère le ticket si NON_CONFORME)
        occ.status = 'DONE' if conformity != 'NON_CONFORME' else 'WAITING_VALIDATION'
        occ.save(update_fields=['status'])
        if occ.status == 'DONE':
            # Occurrence liée à une installation fixe : remise à zéro de l'échéance
            # (branche compteur uniquement ici, la branche calendaire est relue
            # directement depuis cette exécution par la génération d'occurrences).
            mettre_a_jour_echeance_installation(occ)

        # Gérer les pièces jointes: créer ou récupérer le thread de l'occurrence
        ct = ContentType.objects.get_for_model(MaintenanceOccurrence)
        thread, _ = Thread.objects.get_or_create(content_type=ct, object_id=str(occ.pk))
        msg = Message.objects.create(thread=thread, author=request.user if request.user.is_authenticated else None, body=f"Exécution: {conformity}", is_system=False)
        for f in request.FILES.getlist('photos'):
            Attachment.objects.create(message=msg, file=f, name=f.name)

        # Réponse HTMX ou redirection
        if request.headers.get('HX-Request'):
            return render(request, 'maintenance/_execute_done.html', {"occ": occ, "exec": exec_obj})
        return redirect('/')


class OccurrenceCommentCreateView(LoginRequiredMixin, View):
    """Ajoute un commentaire de suivi libre sur une occurrence de maintenance.

    Même contrôle d'accès que OccurrenceExecuteView : assigné à l'occurrence,
    ou CHEF_SECTION et au-dessus — pas de nouveau système de droits, on
    réutilise exactement la règle déjà appliquée à la fiche d'exécution.
    """

    def post(self, request, pk):
        try:
            occ = MaintenanceOccurrence.objects.get(pk=pk)
        except MaintenanceOccurrence.DoesNotExist:
            return HttpResponseBadRequest('Occurrence introuvable')
        if (request.user not in occ.assignees.all()) and (user_role_level(request.user) < RoleLevel.CHEF_SECTION):
            raise PermissionDenied
        corps = request.POST.get('body', '').strip()
        if not corps:
            messages.error(request, "Le commentaire ne peut pas être vide.")
        else:
            ajouter_commentaire(occ, request.user, corps)
            messages.success(request, "Commentaire ajouté.")
        return redirect('occurrence-execute', pk=occ.pk)


# ---------------------------------------------------------------------------
# Page de gestion de la maintenance (plans + occurrences), distincte de la
# vue calendrier (grille datée) : ici, un tableau de pilotage et la gestion
# des plans préventifs. Voir maintenance/views.py pour les ViewSets DRF dont
# le périmètre (build_scope_q) et les seuils de rôle (RoleLevel) sont repris
# à l'identique, sans en dupliquer la logique sous-jacente.
# ---------------------------------------------------------------------------

# Classe de badge Bootstrap par statut d'occurrence — même principe que
# dashboard/web_views.py::_BADGE_STATUT_MAINTENANCE, complété ici pour les 7
# statuts (le tableau de bord n'affichait que les statuts utiles à "mes
# maintenances", ce tableau de pilotage les affiche tous).
_BADGE_STATUT_OCCURRENCE = {
    "PLANNED": "bg-secondary",
    "ASSIGNED": "bg-info",
    "IN_PROGRESS": "bg-primary",
    "WAITING_VALIDATION": "bg-warning",
    "DONE": "badge-conforme",
    "OVERDUE": "bg-danger",
    "CANCELLED": "bg-secondary",
}

# Statuts qui ne comptent jamais comme "en retard" (une occurrence terminée
# ou annulée n'a plus d'échéance à tenir), utilisé à la fois pour le badge
# visuel et pour le filtre "retard" du tableau de pilotage.
_STATUTS_SANS_RETARD = ("DONE", "CANCELLED")


def _periodicite_lisible(nombre_de_jours):
    """Traduit une périodicité en jours (champ brut every_n_days) en libellé
    lisible (principe n°5 CLAUDE.md : un nombre brut de jours se lit moins
    vite qu'une unité familière). Ne garde l'unité la plus grande que si elle
    tombe juste, sans arrondi qui fausserait la périodicité réelle."""
    if nombre_de_jours and nombre_de_jours % 365 == 0:
        n = nombre_de_jours // 365
        return "Tous les ans" if n == 1 else f"Tous les {n} ans"
    if nombre_de_jours and nombre_de_jours % 30 == 0:
        n = nombre_de_jours // 30
        return "Tous les mois" if n == 1 else f"Tous les {n} mois"
    if nombre_de_jours and nombre_de_jours % 7 == 0:
        n = nombre_de_jours // 7
        return "Toutes les semaines" if n == 1 else f"Toutes les {n} semaines"
    return "Tous les jours" if nombre_de_jours == 1 else f"Tous les {nombre_de_jours} jours"


def _assets_disponibles(user):
    """Matériels mobiles utilisables comme périmètre d'un plan de maintenance
    (MaintenancePlan.scope=ASSET), limités au périmètre de l'utilisateur. Un
    Asset porte directement les 4 champs de périmètre, d'où le préfixe vide."""
    return Asset.objects.filter(build_scope_q(user, "")).select_related("asset_type", "sector").order_by("designation")


def _asset_types_disponibles(user):
    """Types d'actifs utilisables comme périmètre d'un plan de maintenance
    (MaintenancePlan.scope=ASSET_TYPE). Un type d'actif n'est jamais rattaché
    à une section précise (même règle que MaintenancePlanViewSet.get_scoped_filters,
    maintenance/views.py) : absent du menu pour un utilisateur cantonné à une
    section, volontairement — pas d'équivalent "propre à une section"."""
    return AssetType.objects.filter(build_scope_q(
        user,
        {
            "ship_id": "sector__service__ship_id",
            "service_id": "sector__service_id",
            "sector_id": "sector_id",
        },
    )).select_related("sector").order_by("name")


def _checklists_disponibles(user):
    """Checklists utilisables pour un plan de maintenance — même règle de
    périmètre que _asset_types_disponibles ci-dessus (ChecklistTemplate ne
    porte lui aussi qu'un secteur, jamais une section précise)."""
    return ChecklistTemplate.objects.filter(build_scope_q(
        user,
        {
            "ship_id": "sector__service__ship_id",
            "service_id": "sector__service_id",
            "sector_id": "sector_id",
        },
    )).select_related("sector").order_by("name")


class MaintenancePlanListView(LoginRequiredMixin, ScopedQuerySetMixin, ListView):
    """Liste des plans de maintenance préventive, scopée navire/service/secteur.

    Lecture ouverte à tout marin scopé. Création/modification réservées à
    CHEF_SECTION et au-dessus — même seuil que MaintenancePlanViewSet côté API
    (RolePermission.min_level_write par défaut, aucun min_role_level_write
    personnalisé sur ce ViewSet).
    """
    model = MaintenancePlan
    template_name = "maintenance/plan_list.html"
    context_object_name = "plans"

    def get_scoped_filters(self):
        # Un plan porte soit sur un actif précis (asset), soit sur un type
        # d'actif (asset_type) — même chemin que MaintenancePlanViewSet
        # (maintenance/views.py), répété ici plutôt que dupliqué : seul
        # build_scope_q porte la logique de traduction du périmètre.
        return build_scope_q(
            self.request.user,
            "asset__",
            {
                "ship_id": "asset_type__sector__service__ship_id",
                "service_id": "asset_type__sector__service_id",
                "sector_id": "asset_type__sector_id",
            },
        )

    def get_queryset(self):
        return (
            super().get_queryset()
            .select_related("asset", "asset__asset_type", "asset_type", "asset_type__sector", "checklist_template")
            .order_by("name")
        )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["onglet"] = "plans"
        ctx["peut_gerer"] = user_role_level(self.request.user) >= RoleLevel.CHEF_SECTION
        for plan in ctx["plans"]:
            plan.periodicite_affichee = _periodicite_lisible(plan.every_n_days)
            plan.duree_heures = plan.expected_duration_min // 60
            plan.duree_minutes = plan.expected_duration_min % 60
        if ctx["peut_gerer"]:
            ctx["assets_disponibles"] = _assets_disponibles(self.request.user)
            ctx["asset_types_disponibles"] = _asset_types_disponibles(self.request.user)
            ctx["checklists_disponibles"] = _checklists_disponibles(self.request.user)
        return ctx

    def post(self, request, *args, **kwargs):
        if user_role_level(request.user) < RoleLevel.CHEF_SECTION:
            raise PermissionDenied
        action = request.POST.get("action")
        if action not in ("create_plan", "edit_plan"):
            return HttpResponseBadRequest("Action inconnue")

        name = request.POST.get("name", "").strip()
        if not name:
            messages.error(request, "Le nom du plan est obligatoire.")
            return redirect("maintenance-plans")

        scope = request.POST.get("scope")
        asset = asset_type = None
        if scope == "ASSET":
            asset = _assets_disponibles(request.user).filter(pk=request.POST.get("asset_id")).first()
            if not asset:
                messages.error(request, "Le matériel choisi est introuvable ou hors de votre périmètre.")
                return redirect("maintenance-plans")
        elif scope == "ASSET_TYPE":
            asset_type = _asset_types_disponibles(request.user).filter(pk=request.POST.get("asset_type_id")).first()
            if not asset_type:
                messages.error(request, "Le type de matériel choisi est introuvable ou hors de votre périmètre.")
                return redirect("maintenance-plans")
        else:
            messages.error(request, "Le périmètre du plan (matériel ou type de matériel) est obligatoire.")
            return redirect("maintenance-plans")

        try:
            every_n_days = int(request.POST.get("every_n_days") or 0)
            expected_duration_min = int(request.POST.get("expected_duration_min") or 0)
        except ValueError:
            messages.error(request, "La périodicité et la durée doivent être des nombres entiers.")
            return redirect("maintenance-plans")
        if every_n_days <= 0:
            messages.error(request, "La périodicité doit être d'au moins un jour.")
            return redirect("maintenance-plans")

        checklist_id = request.POST.get("checklist_template_id")
        checklist = _checklists_disponibles(request.user).filter(pk=checklist_id).first() if checklist_id else None

        champs = dict(
            scope=scope,
            asset=asset,
            asset_type=asset_type,
            name=name,
            every_n_days=every_n_days,
            expected_duration_min=max(expected_duration_min, 0),
            checklist_template=checklist,
            requires_validation=request.POST.get("requires_validation") == "on",
        )

        if action == "create_plan":
            MaintenancePlan.objects.create(created_by=request.user, updated_by=request.user, **champs)
            messages.success(request, "Plan de maintenance créé.")
        else:
            pk = request.POST.get("pk")
            # Recharge le plan ciblé via le queryset déjà scopé (même principe
            # que StockPieceListView.post) : un plan hors périmètre est traité
            # comme introuvable, pour empêcher un chef de section de modifier
            # un plan d'un autre secteur via un POST direct.
            if not self.get_queryset().filter(pk=pk).exists():
                messages.error(request, "Plan introuvable.")
                return redirect("maintenance-plans")
            MaintenancePlan.objects.filter(pk=pk).update(updated_by=request.user, **champs)
            messages.success(request, "Plan de maintenance mis à jour.")
        return redirect("maintenance-plans")


class MaintenanceOccurrenceListView(LoginRequiredMixin, ScopedQuerySetMixin, ListView):
    """Tableau de pilotage des occurrences de maintenance : liste filtrable par
    statut et par retard, distincte de la vue calendrier (grille datée) qui
    reste disponible par ailleurs pour une lecture chronologique.

    Les occurrences sont générées uniquement par la tâche Celery quotidienne
    generate_occurrences (maintenance/tasks.py) : aucune création manuelle
    n'est proposée ici, volontairement. Lecture ouverte à tout marin scopé ;
    les actions d'écriture (auto-assignation) sont ouvertes à EQUIPIER et
    au-dessus — même seuil que MaintenanceOccurrenceViewSet côté API.
    """
    model = MaintenanceOccurrence
    template_name = "maintenance/occurrence_list.html"
    context_object_name = "occurrences"

    def get_scoped_filters(self):
        # Même chemin que MaintenanceOccurrenceViewSet (maintenance/views.py) :
        # une occurrence porte soit sur du matériel mobile, soit sur une
        # installation fixe, jamais les deux à la fois.
        return build_scope_q(self.request.user, "asset__", "installation_maintenance__installation__")

    def get_queryset(self):
        qs = (
            super().get_queryset()
            .select_related("plan", "asset", "asset__asset_type", "installation_maintenance", "installation_maintenance__installation")
            .prefetch_related("assignees")
            .order_by("scheduled_for")
        )
        statuts_valides = {code for code, _ in MaintenanceOccurrence.STATUS}
        self.statut = self.request.GET.get("statut", "")
        if self.statut in statuts_valides:
            qs = qs.filter(status=self.statut)
        self.retard = self.request.GET.get("retard") == "1"
        if self.retard:
            # Filtre calculé sur la date d'échéance plutôt que sur le seul
            # statut OVERDUE : ce dernier n'est mis à jour qu'une fois par
            # heure par compute_overdue (Celery), le filtre "retard" doit
            # rester exact même entre deux passages de la tâche.
            qs = qs.filter(scheduled_for__lt=timezone.localdate()).exclude(status__in=_STATUTS_SANS_RETARD)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["onglet"] = "occurrences"
        ctx["statuts"] = MaintenanceOccurrence.STATUS
        ctx["statut_actif"] = self.statut
        ctx["retard_actif"] = self.retard
        aujourdhui = timezone.localdate()
        for occ in ctx["occurrences"]:
            occ.badge_classe = _BADGE_STATUT_OCCURRENCE.get(occ.status, "bg-secondary")
            occ.en_retard = occ.scheduled_for < aujourdhui and occ.status not in _STATUTS_SANS_RETARD
            occ.suis_assigne = self.request.user in occ.assignees.all()
        return ctx


class MaintenanceOccurrenceSelfAssignView(LoginRequiredMixin, View):
    """Auto-assignation en un clic sur une occurrence, depuis le tableau de
    pilotage — plus rapide qu'un formulaire d'assignation séparé (principe
    n°2 CLAUDE.md). Ouvert à EQUIPIER et au-dessus (même seuil que
    min_role_level_write=EQUIPIER sur MaintenanceOccurrenceViewSet) : tout
    marin scopé peut se déclarer preneur d'une occurrence, un second clic le
    retire. Un clic ré-assigne/désassigne uniquement l'auteur du clic, jamais
    un tiers — pas de sélection multi-utilisateurs ici, pour rester aussi
    rapide qu'un tableur (contrairement à l'assignation de tickets correctifs,
    qui reste réservée aux chefs)."""

    def post(self, request, pk):
        filtres = build_scope_q(request.user, "asset__", "installation_maintenance__installation__")
        try:
            occ = MaintenanceOccurrence.objects.filter(filtres).get(pk=pk)
        except MaintenanceOccurrence.DoesNotExist:
            return HttpResponseBadRequest("Occurrence introuvable ou hors de votre périmètre.")

        if request.user in occ.assignees.all():
            occ.assignees.remove(request.user)
            messages.info(request, "Vous n'êtes plus assigné à cette occurrence.")
        else:
            occ.assignees.add(request.user)
            if occ.status == "PLANNED":
                occ.status = "ASSIGNED"
                occ.save(update_fields=["status"])
            messages.success(request, "Vous êtes désormais assigné à cette occurrence.")

        return redirect("maintenance-occurrences")
