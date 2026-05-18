"""Serializers for the admin_tools app."""

from django.contrib.auth import get_user_model
from rest_framework import serializers

from apps.services.models import Appointment, StageTransition
from core.constants import VALID_REPAIR_STAGES

User = get_user_model()


class AdminUserSerializer(serializers.ModelSerializer):
    chassis = serializers.SerializerMethodField()
    registered_at = serializers.DateTimeField(source="date_joined", read_only=True)

    class Meta:
        model = User
        fields = ["id", "name", "email", "registered_at", "chassis"]

    def get_chassis(self, obj):
        return list(obj.chassis_set.values_list("chassis", flat=True))


class StageTransitionSerializer(serializers.ModelSerializer):
    class Meta:
        model = StageTransition
        fields = ["stage", "timestamp"]


class AppointmentStatusSerializer(serializers.Serializer):
    stage = serializers.CharField()

    def validate_stage(self, value):
        if value not in VALID_REPAIR_STAGES:
            raise serializers.ValidationError(
                f"Invalid stage. Valid values are: {', '.join(VALID_REPAIR_STAGES)}."
            )
        return value


class AppointmentWithTransitionsSerializer(serializers.ModelSerializer):
    transitions = StageTransitionSerializer(many=True, read_only=True)

    class Meta:
        model = Appointment
        fields = ["id", "stage", "transitions"]
