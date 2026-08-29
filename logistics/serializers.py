from rest_framework import serializers
from .models import CorrectiveTicket, TicketStatusLog, PartRequest, PartLineItem

class CorrectiveTicketSerializer(serializers.ModelSerializer):
    class Meta:
        model = CorrectiveTicket
        fields = "__all__"
        # Le statut ne se modifie jamais via ce endpoint générique (PATCH/PUT) :
        # il doit obligatoirement passer par l'action dédiée transition() du
        # ViewSet, qui applique les règles métier (REX obligatoire à CLOSED,
        # signature de validation à RETURNED_TO_SERVICE...). Sans ce verrou, un
        # PATCH direct sur "status" contournait totalement le contrôle mot de
        # passe de CorrectiveTicketViewSet.transition() (cf. perform_update
        # ci-contre).
        read_only_fields = ["status"]

class TicketStatusLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = TicketStatusLog
        fields = "__all__"

class PartLineItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = PartLineItem
        fields = "__all__"

class PartRequestSerializer(serializers.ModelSerializer):
    lines = PartLineItemSerializer(many=True, read_only=True)

    class Meta:
        model = PartRequest
        fields = "__all__"
