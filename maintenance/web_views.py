import json
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.shortcuts import render, redirect
from django.http import HttpResponseBadRequest
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone
from .models import MaintenanceOccurrence, MaintenanceExecution
from assets.models import ChecklistItemTemplate
from threads.models import Thread, Message, Attachment
from bordops.core.roles import user_role_level, RoleLevel


class OccurrenceExecuteView(LoginRequiredMixin, View):
    template_name = 'maintenance/execute.html'

    def get(self, request, pk):
        try:
            occ = MaintenanceOccurrence.objects.select_related('plan', 'asset', 'plan__checklist_template').get(pk=pk)
        except MaintenanceOccurrence.DoesNotExist:
            return HttpResponseBadRequest('Occurrence introuvable')
        if (request.user not in occ.assignees.all()) and (user_role_level(request.user) < RoleLevel.CHEF_SECTION):
            raise PermissionDenied
        items = []
        if occ.plan and occ.plan.checklist_template:
            items = list(occ.plan.checklist_template.items.order_by('order').all())
        return render(request, self.template_name, {"occ": occ, "items": items})

    def post(self, request, pk):
        try:
            occ = MaintenanceOccurrence.objects.select_related('plan', 'asset', 'plan__checklist_template').get(pk=pk)
        except MaintenanceOccurrence.DoesNotExist:
            return HttpResponseBadRequest('Occurrence introuvable')
        if (request.user not in occ.assignees.all()) and (user_role_level(request.user) < RoleLevel.CHEF_SECTION):
            raise PermissionDenied

        # Collecter les résultats des items
        results = {}
        items = []
        if occ.plan and occ.plan.checklist_template:
            items = list(occ.plan.checklist_template.items.order_by('order').all())
        for item in items:
            key = f"item_{item.id}"
            val = request.POST.get(key)
            if item.field_type == 'checkbox':
                results[item.label] = request.POST.get(key) == 'on'
            else:
                results[item.label] = val

        conformity = request.POST.get('conformity', '')
        notes = request.POST.get('notes', '')

        exec_obj, _ = MaintenanceExecution.objects.get_or_create(occurrence=occ)
        if not exec_obj.started_at:
            exec_obj.started_at = timezone.now()
        exec_obj.results = results
        exec_obj.conformity = conformity
        exec_obj.notes = notes
        exec_obj.executed_by = request.user
        exec_obj.completed_at = timezone.now()
        exec_obj.save()

        # Mettre à jour le statut de l'occurrence (le signal gère le ticket si NON_CONFORME)
        occ.status = 'DONE' if conformity != 'NON_CONFORME' else 'WAITING_VALIDATION'
        occ.save(update_fields=['status'])

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
