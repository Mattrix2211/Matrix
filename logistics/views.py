from rest_framework import viewsets, permissions, decorators, response
from rest_framework.exceptions import ValidationError
from django.utils import timezone
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

    def perform_update(self, serializer):
        # "status" est en lecture seule côté serializer (CorrectiveTicketSerializer.
        # Meta.read_only_fields) : un PATCH/PUT générique qui tente malgré tout de le
        # changer est explicitement refusé plutôt que silencieusement ignoré, pour
        # guider vers l'action dédiée transition() — seul chemin qui applique le REX
        # obligatoire à CLOSED et la signature de validation à RETURNED_TO_SERVICE.
        # Sans ce garde-fou, `PATCH /api/corrective-tickets/{pk}/
        # {"status": "RETURNED_TO_SERVICE"}` contournait totalement le contrôle mot
        # de passe de transition().
        nouveau_statut = self.request.data.get("status")
        if nouveau_statut and nouveau_statut != serializer.instance.status:
            raise ValidationError(
                {
                    "status": (
                        "Le statut d'un ticket correctif ne se modifie pas via cette route : "
                        "utilisez l'action dédiée /transition/."
                    )
                }
            )
        serializer.save()

    @decorators.action(detail=True, methods=["post"])
    def transition(self, request, pk=None):
        ticket = self.get_object()
        new_status = request.data.get("status")
        if new_status:
            # Retour d'expérience (REX) obligatoire pour fermer un ticket : même
            # règle que TicketTransitionView (interface web), reprise ici pour que
            # l'API n'offre pas un moyen de contourner cette exigence métier
            # (CLAUDE.md : « REX obligatoire à CLOSED »). Sans ce contrôle, un
            # ticket pouvait être fermé sans diagnostic ni solution via l'API.
            if new_status == "CLOSED" and not (ticket.diagnostic_final and ticket.solution):
                return response.Response(
                    {
                        "detail": (
                            "Impossible de fermer le ticket : le diagnostic final et "
                            "la solution appliquée sont obligatoires (retour d'expérience)."
                        )
                    },
                    status=400,
                )
            # Remise en service : geste engageant qui exige une ré-authentification
            # légère (mot de passe courant), exactement comme TicketTransitionView.post
            # (logistics/web_views.py) — systématique sur ce statut, pas seulement si
            # l'installation est critique. Vérifié avant toute écriture, pour ne rien
            # modifier au ticket si le mot de passe saisi est incorrect.
            if new_status == "RETURNED_TO_SERVICE" and not request.user.check_password(
                request.data.get("mot_de_passe", "")
            ):
                return response.Response(
                    {"detail": "Mot de passe incorrect : la remise en service n'a pas été validée."},
                    status=403,
                )
            old = ticket.status
            ticket.status = new_status
            champs = ["status"]
            if new_status == "RETURNED_TO_SERVICE":
                ticket.valide_par = request.user
                ticket.date_validation = timezone.now()
                champs += ["valide_par", "date_validation"]
            ticket.save(update_fields=champs)
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
