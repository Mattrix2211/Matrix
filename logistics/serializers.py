from rest_framework import serializers
from .models import CorrectiveTicket, TicketStatusLog, PartRequest, PartLineItem

class CorrectiveTicketSerializer(serializers.ModelSerializer):
    class Meta:
        model = CorrectiveTicket
        fields = "__all__"

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
