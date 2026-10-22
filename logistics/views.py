from rest_framework import viewsets, permissions, decorators, response
from rest_framework.exceptions import ValidationError
from django.utils import timezone
from .models import CorrectiveTicket, TicketStatusLog, PartRequest, PartLineItem
from .serializers import CorrectiveTicketSerializer, PartRequestSerializer, PartLineItemSerializer
from matrix.core.confirmations import (
    CANAL_API, MESSAGE_REFUS_API, confirmation_api, details_confirmation, texte_confirmation, tracer_refus,
)
from matrix.core.mixins import EcritureDansLePerimetreMixin, ScopedQuerySetMixin, SuppressionInterditeMixin, build_scope_q
from django.contrib.contenttypes.models import ContentType
from threads.models import Thread, Message
from matrix.core.permissions import RolePermission
from accounts.models import AuditLog
from logistics.perimetre import equipage_tickets_q, perimetre_tickets_q

class DefaultPermission(permissions.IsAuthenticated):
    pass

class CorrectiveTicketViewSet(SuppressionInterditeMixin, EcritureDansLePerimetreMixin, ScopedQuerySetMixin, viewsets.ModelViewSet):
    # Suppression interdite (SuppressionInterditeMixin) : un ticket correctif
    # porte tout le cycle de vie de la panne (statuts, REX obligatoire à
    # CLOSED, confirmation de validation à RETURNED_TO_SERVICE) — il ne doit
    # jamais pouvoir disparaître, seulement changer de statut jusqu'à CLOSED.
    # Avant ce correctif, `DELETE /api/logistics/tickets/{id}/` supprimait
    # réellement le ticket dès le seuil générique CHEF_SECTION atteint,
    # contournant tout ce cycle (refus du Tech Lead, tâche Notion « Matrice
    # de tests de permissions »).
    queryset = CorrectiveTicket.objects.select_related("asset").all()
    serializer_class = CorrectiveTicketSerializer
    permission_classes = [RolePermission]
    champs_utilisateurs_perimetre = ("assignees",)

    def champs_serveur_creation(self):
        return {"created_by": self.request.user}

    def champs_serveur_modification(self):
        return {"updated_by": self.request.user}

    def get_scoped_filters(self):
        # Un ticket correctif porte sur un matériel mobile (asset), qui
        # porte lui-même les 4 champs de périmètre.
        return perimetre_tickets_q(self.request.user)

    def perform_update(self, serializer):
        # "status" est en lecture seule côté serializer (CorrectiveTicketSerializer.
        # Meta.read_only_fields) : un PATCH/PUT générique qui tente malgré tout de le
        # changer est explicitement refusé plutôt que silencieusement ignoré, pour
        # guider vers l'action dédiée transition() — seul chemin qui applique le REX
        # obligatoire à CLOSED et la confirmation de validation à RETURNED_TO_SERVICE.
        # Sans ce garde-fou, un PATCH du statut contournerait la confirmation de transition().
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
        super().perform_update(serializer)

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
            # Remise en service : confirmation explicite, comme TicketTransitionView.post
            # (logistics/web_views.py), vérifiée avant toute écriture.
            if new_status == "RETURNED_TO_SERVICE" and not confirmation_api(request.data):
                tracer_refus(request.user, "remise_en_service", CANAL_API, f"ticket={ticket.pk}")
                return response.Response(
                    {"detail": MESSAGE_REFUS_API.format(texte=texte_confirmation("remise_en_service")[1])},
                    status=400,
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
            # Journal transverse (AuditLog) en plus du TicketStatusLog dédié —
            # même principe que TicketTransitionView (logistics/web_views.py),
            # cf. tâche Notion « Unifier les modèles d'historique/audit ».
            AuditLog.objects.create(
                actor=request.user,
                action='ticket_status_change' if new_status != 'RETURNED_TO_SERVICE' else 'ticket_validation_critique',
                details=f'ticket={ticket.pk}; {old} -> {new_status}'
                + (details_confirmation("remise_en_service", CANAL_API) if new_status == "RETURNED_TO_SERVICE" else ""),
            )
            # system thread message
            ct = ContentType.objects.get_for_model(CorrectiveTicket)
            thread, _ = Thread.objects.get_or_create(content_type=ct, object_id=str(ticket.pk))
            Message.objects.create(thread=thread, author=request.user, body=f"Statut: {old} → {new_status}", is_system=True)
        return response.Response(self.get_serializer(ticket).data)

class PartRequestViewSet(EcritureDansLePerimetreMixin, ScopedQuerySetMixin, viewsets.ModelViewSet):
    queryset = PartRequest.objects.select_related("ticket", "requested_by").all()
    serializer_class = PartRequestSerializer
    permission_classes = [RolePermission]

    def get_scoped_filters(self):
        # Une demande de pièces porte sur un ticket, lui-même rattaché à un
        # matériel mobile (asset).
        return build_scope_q(self.request.user, "ticket__asset__", "ticket__installation__") & equipage_tickets_q(
            self.request.user, "ticket__"
        )

    def champs_serveur_creation(self):
        return {"requested_by": self.request.user, "created_by": self.request.user}

    def champs_serveur_modification(self):
        return {"updated_by": self.request.user}

class PartLineItemViewSet(EcritureDansLePerimetreMixin, ScopedQuerySetMixin, viewsets.ModelViewSet):
    queryset = PartLineItem.objects.select_related("part_request").all()
    serializer_class = PartLineItemSerializer
    permission_classes = [RolePermission]

    def get_scoped_filters(self):
        # Une ligne de pièce porte sur une demande, elle-même rattachée à
        # un ticket, lui-même rattaché à un matériel mobile (asset).
        return build_scope_q(
            self.request.user, "part_request__ticket__asset__", "part_request__ticket__installation__"
        ) & equipage_tickets_q(self.request.user, "part_request__ticket__")
