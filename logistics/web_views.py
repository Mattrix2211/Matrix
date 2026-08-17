from django.views import View
from django.views.generic import ListView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.shortcuts import render, redirect
from django.http import HttpResponseBadRequest
from django.utils import timezone
from django.db.models import Q
from .models import CorrectiveTicket, PartRequest, PartLineItem, TicketStatusLog, StockPiece
from matrix.core.roles import user_role_level, RoleLevel
from matrix.core.mixins import ScopedQuerySetMixin
from matrix.core.scopes import scope_filters_for_user
from org.models import Sector, Section


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


class TicketDetailView(LoginRequiredMixin, View):
    template_name = 'logistics/ticket_detail.html'

    def get(self, request, pk):
        try:
            ticket = CorrectiveTicket.objects.select_related('asset').get(pk=pk)
        except CorrectiveTicket.DoesNotExist:
            return HttpResponseBadRequest('Ticket introuvable')
        part_requests = ticket.part_requests.prefetch_related('lines').all()
        return render(request, self.template_name, {"ticket": ticket, "part_requests": part_requests})


class TicketTransitionView(LoginRequiredMixin, View):
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
        old = ticket.status
        ticket.status = new_status
        ticket.save(update_fields=['status'])
        TicketStatusLog.objects.create(ticket=ticket, old_status=old, new_status=new_status, user=request.user if request.user.is_authenticated else None)
        if request.headers.get('HX-Request'):
            part_requests = ticket.part_requests.prefetch_related('lines').all()
            return render(request, 'logistics/_status.html', {"ticket": ticket, "part_requests": part_requests})
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
        return ctx

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
