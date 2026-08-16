from rest_framework import viewsets, permissions, decorators, response
from .models import CorrectiveTicket, TicketStatusLog, PartRequest, PartLineItem
from .serializers import CorrectiveTicketSerializer, PartRequestSerializer, PartLineItemSerializer
from matrix.core.mixins import ScopedQuerySetMixin, build_scope_q
from django.contrib.contenttypes.models import ContentType
from threads.models import Thread, Message
from matrix.core.permissions import RolePermission

class DefaultPermission(permissions.IsAuthenticated):
    pass

class CorrectiveTicketViewSet(ScopedQuerySetMixin, viewsets.ModelViewSet):
    queryset = CorrectiveTicket.objects.select_related("asset").all()
    serializer_class = CorrectiveTicketSerializer
    permission_classes = [RolePermission]

    def get_scoped_filters(self):
        # Un ticket correctif porte sur un matériel mobile (asset), qui
        # porte lui-même les 4 champs de périmètre.
        return build_scope_q(self.request.user, "asset__")

    @decorators.action(detail=True, methods=["post"])
    def transition(self, request, pk=None):
        ticket = self.get_object()
        new_status = request.data.get("status")
        if new_status:
            old = ticket.status
            ticket.status = new_status
            ticket.save(update_fields=["status"])
            TicketStatusLog.objects.create(ticket=ticket, old_status=old, new_status=new_status, user=request.user)
            # system thread message
            ct = ContentType.objects.get_for_model(CorrectiveTicket)
            thread, _ = Thread.objects.get_or_create(content_type=ct, object_id=str(ticket.pk))
            Message.objects.create(thread=thread, author=request.user, body=f"Statut: {old} → {new_status}", is_system=True)
        return response.Response(self.get_serializer(ticket).data)

class PartRequestViewSet(ScopedQuerySetMixin, viewsets.ModelViewSet):
    queryset = PartRequest.objects.select_related("ticket", "requested_by").all()
    serializer_class = PartRequestSerializer
    permission_classes = [RolePermission]

    def get_scoped_filters(self):
        # Une demande de pièces porte sur un ticket, lui-même rattaché à un
        # matériel mobile (asset).
        return build_scope_q(self.request.user, "ticket__asset__")

class PartLineItemViewSet(ScopedQuerySetMixin, viewsets.ModelViewSet):
    queryset = PartLineItem.objects.select_related("part_request").all()
    serializer_class = PartLineItemSerializer
    permission_classes = [RolePermission]

    def get_scoped_filters(self):
        # Une ligne de pièce porte sur une demande, elle-même rattachée à
        # un ticket, lui-même rattaché à un matériel mobile (asset).
        return build_scope_q(self.request.user, "part_request__ticket__asset__")
