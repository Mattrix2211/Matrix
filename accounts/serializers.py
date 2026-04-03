from rest_framework import serializers
from .models import UserProfile, GradeChoice, SpecialityChoice, RoleAvailability
from django.contrib.auth.models import User

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username", "first_name", "last_name", "email"]

class UserProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer()

    class Meta:
        model = UserProfile
        fields = "__all__"


class GradeChoiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = GradeChoice
        fields = "__all__"


class SpecialityChoiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = SpecialityChoice
        fields = "__all__"


class RoleAvailabilitySerializer(serializers.ModelSerializer):
    class Meta:
        model = RoleAvailability
        fields = "__all__"
