from rest_framework import viewsets, permissions, decorators, response
from .models import CorrectiveTicket, TicketStatusLog, PartRequest, PartLineItem
from .serializers import CorrectiveTicketSerializer, PartRequestSerializer, PartLineItemSerializer
from bordops.core.mixins import ScopedQuerySetMixin
from django.contrib.contenttypes.models import ContentType
from threads.models import Thread, Message
from bordops.core.permissions import RolePermission

class DefaultPermission(permissions.IsAuthenticated):
    pass

class CorrectiveTicketViewSet(ScopedQuerySetMixin, viewsets.ModelViewSet):
    queryset = CorrectiveTicket.objects.select_related("asset").all()
    serializer_class = CorrectiveTicketSerializer
    permission_classes = [RolePermission]

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

class PartLineItemViewSet(ScopedQuerySetMixin, viewsets.ModelViewSet):
    queryset = PartLineItem.objects.select_related("part_request").all()
    serializer_class = PartLineItemSerializer
    permission_classes = [RolePermission]
