from django.views import View
from django.views.generic import ListView
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.shortcuts import render, redirect
from django.http import HttpResponseBadRequest
from django.utils import timezone
from django.db.models import Q
from .models import CorrectiveTicket, PartRequest, PartLineItem, TicketStatusLog, StockPiece
from matrix.core.roles import user_role_level, RoleLevel
from matrix.core.mixins import ScopedQuerySetMixin, build_scope_q
from matrix.core.scopes import scope_filters_for_user
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
from org.models import Sector, Section
from assets.models import Asset

User = get_user_model()


def _secteur_dans_perimetre(user, sector_id):
    """Vérifie qu'un secteur posté dans le formulaire de gestion du stock (T14)
    appartient bien au périmètre de l'appelant, en réutilisant scope_filters_for_user
    (le même système que ScopedQuerySetMixin) plutôt que d'en recréer un nouveau —
    même principe que _org_dans_perimetre dans assets/web_views.py. Un utilisateur
    sans périmètre restreint (ex. administrateur général) peut choisir n'importe
    quel secteur existant ; un utilisateur cantonné à un niveau (navire/service/
    secteur/section) ne peut choisir qu'un secteur qui en descend — pour un chef de
    section, uniquement le secteur contenant sa propre section. Ne fait pas
    confiance au menu déroulant du formulaire, contournable par un POST direct."""
    filters = scope_filters_for_user(user)
    if not filters:
        return Sector.objects.filter(pk=sector_id).exists()
    (key, value), = filters.items()
    if key == "sector_id":
        return str(value) == str(sector_id)
    chemins = {
        "ship_id": "service__ship_id",
        "service_id": "service_id",
        "section_id": "sections__id",
    }
    return Sector.objects.filter(pk=sector_id, **{chemins[key]: value}).exists()


class TicketListView(LoginRequiredMixin, ScopedQuerySetMixin, ListView):
    """Liste des tickets correctifs, scopée par périmètre ET par assignation.

    Par défaut, chaque marin ne voit que « ses » tickets (ceux qui lui sont
    assignés) — même principe que "Mes maintenances" sur le tableau de bord
    (principe fondamental n°3 de CLAUDE.md). Un chef de section et au-dessus
    peut basculer vers "Tout le périmètre" pour voir l'ensemble des tickets
    de son périmètre, pas seulement les siens.
    """
    model = CorrectiveTicket
    template_name = 'logistics/ticket_list.html'
    context_object_name = 'tickets'

    def get_scoped_filters(self):
        # Un ticket correctif porte sur un matériel mobile (asset), qui porte
        # lui-même les 4 champs de périmètre — même logique que
        # CorrectiveTicketViewSet côté API (logistics/views.py).
        return build_scope_q(self.request.user, "asset__")

    def _vue_perimetre_autorisee(self):
        return user_role_level(self.request.user) >= RoleLevel.CHEF_SECTION

    def get_queryset(self):
        qs = super().get_queryset().select_related('asset').order_by('-reported_at')
        self.vue = self.request.GET.get('vue', 'mes')
        if self.vue != 'perimetre' or not self._vue_perimetre_autorisee():
            self.vue = 'mes'
            qs = qs.filter(assignees=self.request.user)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['vue'] = self.vue
        ctx['peut_voir_perimetre'] = self._vue_perimetre_autorisee()
        # Jauge de sévérité (principe n°5 CLAUDE.md) : le chiffre brut 1-5 ne se
        # lit pas aussi vite qu'une barre colorée. Capée à 5 pour l'affichage
        # même si une valeur plus haute était postée directement.
        for ticket in list(ctx.get('tickets', [])):
            ticket.severite_pct = min(ticket.severity, 5) / 5 * 100
        return ctx


def _ship_du_profil_q(ship_id):
    """Filtre les utilisateurs dont le profil appartient au navire donné, quel
    que soit le niveau de périmètre auquel leur profil est réellement scopé
    (ship directement, ou service/sector/section dont on remonte jusqu'au
    navire) — un profil scopé au secteur n'a jamais profile.ship renseigné
    directement, contrairement à profile.service/sector/section."""
    return (
        Q(profile__ship_id=ship_id)
        | Q(profile__service__ship_id=ship_id)
        | Q(profile__sector__service__ship_id=ship_id)
        | Q(profile__section__sector__service__ship_id=ship_id)
    )

_ENTETES_EXPORT_STOCK = [
    'Référence', 'Désignation', 'Quantité', 'Quantité minimale', 'Emplacement',
    'Navire', 'Service', 'Secteur', 'Section',
]


def _lignes_export_stock(qs):
    """Construit les lignes de l'export tableur du stock de pièces, à partir
    d'un queryset déjà filtré par périmètre (ScopedQuerySetMixin)."""
    return [
        [
            p.reference,
            p.designation,
            p.quantite,
            p.quantite_minimale,
            p.emplacement,
            p.ship.name if p.ship else '',
            p.service.name if p.service else '',
            p.sector.name if p.sector else '',
            p.section.name if p.section else '',
        ]
        for p in qs
    ]


class TicketDetailView(LoginRequiredMixin, View):
    template_name = 'logistics/ticket_detail.html'

    def get(self, request, pk):
        try:
            ticket = CorrectiveTicket.objects.select_related('asset').get(pk=pk)
        except CorrectiveTicket.DoesNotExist:
            return HttpResponseBadRequest('Ticket introuvable')
        part_requests = ticket.part_requests.prefetch_related('lines').all()
        contexte = {
            "ticket": ticket,
            "part_requests": part_requests,
            "peut_assigner": user_role_level(request.user) >= RoleLevel.CHEF_SECTION,
        }
        if contexte["peut_assigner"]:
            # Utilisateurs assignables : l'équipage du navire portant l'actif en
            # panne — un chef choisit ensuite librement parmi eux. Le navire de
            # l'utilisateur peut être porté directement par son profil (profile.ship)
            # ou déduit de son périmètre plus fin (service/secteur/section), un
            # profil scopé au secteur n'ayant jamais ship renseigné directement.
            contexte["utilisateurs_assignables"] = User.objects.filter(
                _ship_du_profil_q(ticket.asset.ship_id)
            ).select_related("profile").order_by("username").distinct()
        return render(request, self.template_name, contexte)


class TicketCreateView(LoginRequiredMixin, View):
    """Signalement rapide d'une anomalie sur du matériel mobile : crée un ticket
    correctif à partir de la fiche de l'équipement, en un seul clic (description
    + gravité), sans passer par un formulaire séparé. Accessible à tout marin
    connecté (pas de restriction de rôle) : un équipier doit pouvoir signaler
    une panne constatée sur le terrain sans dépendre d'un chef.
    """

    def post(self, request, asset_pk):
        # Périmètre : un marin ne peut signaler une anomalie que sur un matériel
        # de son propre périmètre — même filtre que ScopedQuerySetMixin/AssetViewSet.
        filtres = scope_filters_for_user(request.user)
        assets = Asset.objects.filter(**filtres) if filtres else Asset.objects.all()
        try:
            asset = assets.get(pk=asset_pk)
        except Asset.DoesNotExist:
            return HttpResponseBadRequest('Matériel introuvable ou hors de votre périmètre.')

        description = request.POST.get('description', '').strip()
        if not description:
            messages.error(request, "Merci de décrire l'anomalie constatée.")
            return redirect('asset-detail', pk=asset.pk)

        try:
            gravite = int(request.POST.get('severity') or 3)
        except ValueError:
            gravite = 3

        ticket = CorrectiveTicket.objects.create(
            asset=asset,
            description=description,
            severity=gravite,
            created_by=request.user,
            updated_by=request.user,
        )
        ticket.assignees.add(request.user)
        TicketStatusLog.objects.create(
            ticket=ticket, old_status='REPORTED', new_status='REPORTED', user=request.user
        )
        messages.success(request, "Anomalie signalée : le ticket correctif a été créé.")
        return redirect('ticket-detail', pk=ticket.pk)


class TicketAssignView(LoginRequiredMixin, View):
    """Assigne un ou plusieurs marins à un ticket correctif — réservé à
    CHEF_SECTION et au-dessus, même seuil que les autres actions d'écriture
    de ce module (transitions, demandes de pièces)."""

    def post(self, request, pk):
        if user_role_level(request.user) < RoleLevel.CHEF_SECTION:
            raise PermissionDenied
        try:
            ticket = CorrectiveTicket.objects.select_related('asset').get(pk=pk)
        except CorrectiveTicket.DoesNotExist:
            return HttpResponseBadRequest('Ticket introuvable')
        ids = request.POST.getlist('assignees')
        # On ne retient que des utilisateurs de l'équipage du navire de l'actif
        # concerné, même filtre que le formulaire (contournement d'un POST direct).
        utilisateurs = User.objects.filter(_ship_du_profil_q(ticket.asset.ship_id), pk__in=ids)
        ticket.assignees.set(utilisateurs)
        messages.info(request, "Assignation du ticket mise à jour.")
        return redirect('ticket-detail', pk=ticket.pk)


class TicketTransitionView(LoginRequiredMixin, View):
    """Change le statut d'un ticket correctif.

    Le retour d'expérience (diagnostic final + solution appliquée) est saisi dans
    le même formulaire que le changement de statut — un seul clic, pas un
    formulaire séparé — et enregistré à chaque soumission. Il devient obligatoire
    pour passer au statut CLOSED : validation appliquée ici (pas seulement une
    contrainte de formulaire HTML), pour garantir qu'un ticket fermé porte
    toujours un REX exploitable, retrouvable ensuite via la recherche « pannes
    déjà rencontrées » sur la fiche d'un actif.
    """

    def post(self, request, pk):
        if user_role_level(request.user) < RoleLevel.CHEF_SECTION:
            raise PermissionDenied
        try:
            ticket = CorrectiveTicket.objects.get(pk=pk)
        except CorrectiveTicket.DoesNotExist:
            return HttpResponseBadRequest('Ticket introuvable')
        new_status = request.POST.get('status')
        if not new_status:
            return HttpResponseBadRequest('Statut requis')

        # Remise en service : geste engageant qui exige une ré-authentification légère
        # (mot de passe courant de l'appelant, comme un "sudo" léger) avant toute
        # écriture. Vérifié en tout premier, pour ne strictement rien modifier au
        # ticket si le mot de passe saisi est incorrect.
        if new_status == 'RETURNED_TO_SERVICE' and not request.user.check_password(request.POST.get('mot_de_passe', '')):
            erreur_fermeture = "Mot de passe incorrect : la remise en service n'a pas été validée."
            messages.error(request, erreur_fermeture)
            if request.headers.get('HX-Request'):
                part_requests = ticket.part_requests.prefetch_related('lines').all()
                return render(request, 'logistics/_status.html', {"ticket": ticket, "part_requests": part_requests, "erreur_fermeture": erreur_fermeture})
            return redirect('ticket-detail', pk=ticket.pk)

        diagnostic_final = request.POST.get('diagnostic_final', '').strip()
        solution = request.POST.get('solution', '').strip()
        ticket.diagnostic_final = diagnostic_final
        ticket.solution = solution

        erreur_fermeture = None
        champs = ['status', 'diagnostic_final', 'solution']
        if new_status == 'CLOSED' and not (diagnostic_final and solution):
            erreur_fermeture = "Impossible de fermer le ticket : le diagnostic final et la solution appliquée sont obligatoires (retour d'expérience)."
        else:
            old = ticket.status
            ticket.status = new_status
            if new_status == 'RETURNED_TO_SERVICE':
                # Mot de passe déjà vérifié plus haut : on enregistre la signature de
                # validation en même temps que la transition.
                ticket.valide_par = request.user
                ticket.date_validation = timezone.now()
                champs += ['valide_par', 'date_validation']

        ticket.save(update_fields=champs)

        if erreur_fermeture:
            messages.error(request, erreur_fermeture)
        else:
            TicketStatusLog.objects.create(ticket=ticket, old_status=old, new_status=new_status, user=request.user if request.user.is_authenticated else None)

        if request.headers.get('HX-Request'):
            part_requests = ticket.part_requests.prefetch_related('lines').all()
            return render(request, 'logistics/_status.html', {"ticket": ticket, "part_requests": part_requests, "erreur_fermeture": erreur_fermeture})
        return redirect('ticket-detail', pk=ticket.pk)


class PartRequestCreateView(LoginRequiredMixin, View):
    def post(self, request, pk):
        if user_role_level(request.user) < RoleLevel.CHEF_SECTION:
            raise PermissionDenied
        try:
            ticket = CorrectiveTicket.objects.get(pk=pk)
        except CorrectiveTicket.DoesNotExist:
            return HttpResponseBadRequest('Ticket introuvable')
        pr = PartRequest.objects.create(ticket=ticket, requested_by=request.user if request.user.is_authenticated else None, needed_by_date=request.POST.get('needed_by_date') or None)
        if request.headers.get('HX-Request'):
            part_requests = ticket.part_requests.prefetch_related('lines').all()
            return render(request, 'logistics/_part_requests.html', {"ticket": ticket, "part_requests": part_requests})
        return redirect('ticket-detail', pk=ticket.pk)


class PartLineItemCreateView(LoginRequiredMixin, View):
    def post(self, request, pr_id):
        if user_role_level(request.user) < RoleLevel.CHEF_SECTION:
            raise PermissionDenied
        try:
            pr = PartRequest.objects.select_related('ticket').get(pk=pr_id)
        except PartRequest.DoesNotExist:
            return HttpResponseBadRequest('Demande introuvable')
        PartLineItem.objects.create(
            part_request=pr,
            reference=request.POST.get('reference', ''),
            description=request.POST.get('description', ''),
            qty=int(request.POST.get('qty', '1') or 1),
        )
        if request.headers.get('HX-Request'):
            part_requests = pr.ticket.part_requests.prefetch_related('lines').all()
            return render(request, 'logistics/_part_requests.html', {"ticket": pr.ticket, "part_requests": part_requests})
        return redirect('ticket-detail', pk=pr.ticket.pk)


class PartLineItemUpdateStatusView(LoginRequiredMixin, View):
    def post(self, request, line_id):
        if user_role_level(request.user) < RoleLevel.CHEF_SECTION:
            raise PermissionDenied
        try:
            line = PartLineItem.objects.select_related('part_request', 'part_request.ticket').get(pk=line_id)
        except PartLineItem.DoesNotExist:
            return HttpResponseBadRequest('Ligne introuvable')
        status = request.POST.get('status')
        if not status:
            return HttpResponseBadRequest('Statut requis')
        line.status = status
        line.save(update_fields=['status'])
        if request.headers.get('HX-Request'):
            part_requests = line.part_request.ticket.part_requests.prefetch_related('lines').all()
            return render(request, 'logistics/_part_requests.html', {"ticket": line.part_request.ticket, "part_requests": part_requests})
        return redirect('ticket-detail', pk=line.part_request.ticket.pk)


class StockPieceListView(LoginRequiredMixin, ScopedQuerySetMixin, ListView):
    """Liste et gestion du stock de pièces (T14), scopée sur le périmètre de l'utilisateur.

    Lecture ouverte à tout utilisateur connecté, restreinte à son périmètre via
    scope_filters_for_user (T12) — pas de nouveau système de scope. Création et
    modification réservées à CHEF_SECTION et au-dessus, même seuil que les autres
    actions d'écriture de ce module (transitions de ticket, demandes de pièces).
    """
    model = StockPiece
    template_name = 'logistics/stock_list.html'
    context_object_name = 'pieces'

    def get_queryset(self):
        qs = super().get_queryset().select_related('ship', 'service', 'sector', 'section')
        q = self.request.GET.get('q', '').strip()
        if q:
            qs = qs.filter(
                Q(reference__icontains=q) | Q(designation__icontains=q) | Q(emplacement__icontains=q)
            )
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['peut_gerer'] = user_role_level(self.request.user) >= RoleLevel.CHEF_SECTION
        ctx['sectors'] = Sector.objects.select_related('service', 'service__ship').order_by('service__ship__name', 'service__name', 'name')
        ctx['sections'] = Section.objects.select_related('sector').order_by('sector__name', 'name')
        ctx['export_url_csv'] = construire_url_export(self.request, 'csv')
        ctx['export_url_xlsx'] = construire_url_export(self.request, 'xlsx')
        ctx['xlsx_disponible'] = xlsx_disponible()
        # Jauge de niveau (principe n°5 CLAUDE.md) : proportion de la quantité
        # actuelle par rapport au seuil minimal, pour visualiser le niveau de
        # stock en un coup d'œil plutôt qu'une colonne de deux chiffres à
        # comparer mentalement. Sans seuil renseigné (0), la pièce n'a pas
        # d'exigence minimale : jauge pleine par convention.
        for p in list(ctx.get('pieces', [])):
            p.jauge_pct = min(round(p.quantite / p.quantite_minimale * 100), 100) if p.quantite_minimale else 100
        return ctx

    def get(self, request, *args, **kwargs):
        format_export = request.GET.get('export')
        if format_export in ('csv', 'xlsx'):
            # get_queryset() est déjà filtré par périmètre (ScopedQuerySetMixin) :
            # l'export ne peut donc jamais dépasser le périmètre de l'utilisateur.
            qs = self.get_queryset()
            lignes = _lignes_export_stock(qs)
            if format_export == 'xlsx':
                contenu = rendre_xlsx(_ENTETES_EXPORT_STOCK, lignes, titre_feuille='Stock')
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
                contenu = rendre_csv(_ENTETES_EXPORT_STOCK, lignes)
                content_type = CSV_CONTENT_TYPE
            AuditLog.objects.create(
                actor=request.user, action=f'export_stock_{format_export}',
                target_user=None, details=f'rows={len(lignes)}',
            )
            return reponse_fichier(contenu, f'stock.{format_export}', content_type)
        return super().get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        if user_role_level(request.user) < RoleLevel.CHEF_SECTION:
            raise PermissionDenied
        action = request.POST.get('action')
        if action not in ('create_piece', 'edit_piece'):
            return HttpResponseBadRequest('Action inconnue')

        reference = request.POST.get('reference', '').strip()
        designation = request.POST.get('designation', '').strip()
        if not reference or not designation:
            messages.error(request, "La référence et la désignation sont obligatoires.")
            return redirect('stock-piece-list')

        sector = Sector.objects.select_related('service', 'service__ship').filter(pk=request.POST.get('sector_id')).first()
        if not sector:
            messages.error(request, "Le secteur est obligatoire.")
            return redirect('stock-piece-list')
        # Le secteur posté doit appartenir au périmètre de l'appelant, sans quoi un
        # chef de section pourrait créer ou transférer une pièce vers un secteur (voire
        # un bâtiment) hors de son périmètre en postant directement un sector_id, en
        # dehors du menu déroulant du formulaire.
        if not _secteur_dans_perimetre(request.user, sector.pk):
            messages.error(request, "Ce secteur ne fait pas partie de votre périmètre.")
            return redirect('stock-piece-list')
        # La section doit appartenir au secteur choisi, sinon on l'ignore plutôt que
        # de créer une hiérarchie incohérente (Section -> Sector -> Service -> Ship).
        section = Section.objects.filter(pk=request.POST.get('section_id'), sector=sector).first()

        try:
            quantite = int(request.POST.get('quantite') or 0)
            quantite_minimale = int(request.POST.get('quantite_minimale') or 0)
        except ValueError:
            messages.error(request, "Les quantités doivent être des nombres entiers.")
            return redirect('stock-piece-list')

        champs = {
            "reference": reference,
            "designation": designation,
            "quantite": max(quantite, 0),
            "quantite_minimale": max(quantite_minimale, 0),
            "emplacement": request.POST.get('emplacement', '').strip(),
            "ship": sector.service.ship,
            "service": sector.service,
            "sector": sector,
            "section": section,
        }

        if action == 'create_piece':
            StockPiece.objects.create(created_by=request.user, updated_by=request.user, **champs)
            messages.info(request, "Pièce ajoutée au stock.")
        else:
            pk = request.POST.get('pk')
            # Recharge la pièce ciblée via le queryset déjà scopé (get_queryset(), même
            # filtre que la liste) plutôt qu'un simple StockPiece.objects.filter(pk=pk) :
            # une pièce hors périmètre doit être traitée comme introuvable, pour empêcher
            # un chef de section de modifier une pièce d'un autre bâtiment via un POST direct.
            if not self.get_queryset().filter(pk=pk).exists():
                messages.error(request, "Pièce introuvable.")
                return redirect('stock-piece-list')
            StockPiece.objects.filter(pk=pk).update(updated_by=request.user, **champs)
            messages.info(request, "Pièce mise à jour.")
        return redirect('stock-piece-list')
