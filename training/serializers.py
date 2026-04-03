from rest_framework import serializers
from .models import TrainingCourse, TrainingRequirement, TrainingSession, TrainingRecord

class TrainingCourseSerializer(serializers.ModelSerializer):
    class Meta:
        model = TrainingCourse
        fields = "__all__"

class TrainingRequirementSerializer(serializers.ModelSerializer):
    class Meta:
        model = TrainingRequirement
        fields = "__all__"

class TrainingSessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = TrainingSession
        fields = "__all__"

class TrainingRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = TrainingRecord
        fields = "__all__"
