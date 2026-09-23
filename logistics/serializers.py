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

    def validate(self, attrs):
        # Règle « un matériel OU une installation » (CorrectiveTicket.clean) :
        # ModelSerializer n'appelle pas clean(), on la rejoue ici en tenant compte
        # de la valeur existante lors d'une mise à jour partielle.
        instance = self.instance
        asset = attrs["asset"] if "asset" in attrs else getattr(instance, "asset", None)
        installation = attrs["installation"] if "installation" in attrs else getattr(instance, "installation", None)
        if bool(asset) == bool(installation):
            raise serializers.ValidationError(
                "Un ticket doit viser un matériel OU une installation (l'un des deux, pas les deux)."
            )
        return attrs

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
