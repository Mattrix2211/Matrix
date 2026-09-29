from rest_framework import serializers
from .models import CorrectiveTicket, TicketStatusLog, PartRequest, PartLineItem

class CorrectiveTicketSerializer(serializers.ModelSerializer):
    class Meta:
        model = CorrectiveTicket
        fields = (
            "id", "asset", "installation", "created_by_text", "reported_at", "planned_for",
            "description", "severity", "status", "assignees", "diagnostic_final", "solution",
            "valide_par", "date_validation", "created_by", "updated_by", "created_at", "updated_at",
        )
        # Le statut ne se modifie jamais via ce endpoint générique (PATCH/PUT) :
        # il doit obligatoirement passer par l'action dédiée transition() du
        # ViewSet, qui applique les règles métier (REX obligatoire à CLOSED,
        # signature de validation à RETURNED_TO_SERVICE...). Sans ce verrou, un
        # PATCH direct sur "status" contournait totalement le contrôle mot de
        # passe de CorrectiveTicketViewSet.transition() (cf. perform_update
        # ci-contre).
        # `valide_par`/`date_validation` (signature de remise en service) et
        # `created_by`/`updated_by` sont posés côté serveur (transition(),
        # perform_create/perform_update) : jamais forgeables par le client.
        read_only_fields = [
            "id", "status", "valide_par", "date_validation",
            "created_by", "updated_by", "created_at", "updated_at",
        ]

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
        fields = ("id", "ticket", "old_status", "new_status", "user", "note", "created_at", "updated_at")
        # Historique : écrit uniquement par transition() côté serveur.
        read_only_fields = fields

class PartLineItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = PartLineItem
        fields = (
            "id", "part_request", "reference", "description", "qty", "status", "vendor",
            "order_number", "estimated_cost", "actual_cost", "ordered_at", "received_at",
            "created_at", "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")

class PartRequestSerializer(serializers.ModelSerializer):
    lines = PartLineItemSerializer(many=True, read_only=True)

    class Meta:
        model = PartRequest
        fields = (
            "id", "ticket", "requested_by", "needed_by_date", "status", "lines",
            "created_by", "updated_by", "created_at", "updated_at",
        )
        # Le demandeur est toujours l'utilisateur connecté (PartRequestViewSet).
        read_only_fields = ("id", "requested_by", "created_by", "updated_by", "created_at", "updated_at")
