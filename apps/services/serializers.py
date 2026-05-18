"""
Serializers for the services app.
"""

from rest_framework import serializers

from apps.services.models import Appointment, Service, StageTransition


class ServiceListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Service
        fields = ["id", "name", "description", "compatible_chassis"]


class ServiceDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = Service
        fields = ["id", "name", "description", "compatible_chassis", "turnaround_days"]


class StageTransitionSerializer(serializers.ModelSerializer):
    class Meta:
        model = StageTransition
        fields = ["stage", "timestamp"]


class AppointmentListSerializer(serializers.ModelSerializer):
    service_name = serializers.CharField(source="service.name", read_only=True)

    class Meta:
        model = Appointment
        fields = ["id", "service_name", "chassis", "stage", "created_at"]


class AppointmentDetailSerializer(serializers.ModelSerializer):
    service_name = serializers.CharField(source="service.name", read_only=True)
    transitions = StageTransitionSerializer(many=True, read_only=True)
    report_url = serializers.SerializerMethodField()

    class Meta:
        model = Appointment
        fields = [
            "id", "service_name", "chassis", "created_at",
            "stage", "report_url", "transitions",
        ]

    def get_report_url(self, obj):
        request = self.context.get("request")
        if obj.report_file:
            url = obj.report_file.url
            if request:
                return request.build_absolute_uri(url)
            return url
        return None


class BookAppointmentSerializer(serializers.Serializer):
    service_id = serializers.IntegerField()
    chassis = serializers.CharField(max_length=10)

    def validate(self, attrs):
        from core.constants import VALID_CHASSIS_CODES
        from core.validators import validate_chassis

        service_id = attrs.get("service_id")
        chassis = attrs.get("chassis")

        # Validate chassis is in supported list
        validate_chassis(chassis)

        # Validate service exists
        try:
            service = Service.objects.get(pk=service_id, is_active=True)
        except Service.DoesNotExist:
            raise serializers.ValidationError(
                {"service_id": [f"Service with id {service_id} does not exist."]}
            )

        # Validate chassis is compatible with this service
        if chassis not in service.compatible_chassis:
            raise serializers.ValidationError(
                {
                    "chassis": [
                        f"Chassis {chassis} is not compatible with service '{service.name}'. "
                        f"Compatible chassis: {', '.join(service.compatible_chassis)}."
                    ]
                }
            )

        attrs["service"] = service
        return attrs
