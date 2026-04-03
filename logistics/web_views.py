from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.shortcuts import render, redirect
from django.http import HttpResponseBadRequest
from django.utils import timezone
from .models import CorrectiveTicket, PartRequest, PartLineItem, TicketStatusLog
from matrix.core.roles import user_role_level, RoleLevel


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
