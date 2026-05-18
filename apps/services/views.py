"""
Views for the services app.

Endpoints:
  GET  /api/services              — Requirement 6
  GET  /api/services/:id          — Requirement 7
  POST /api/appointments/book     — Requirement 8
  GET  /api/appointments/user     — Requirement 9
  GET  /api/appointments/:id      — Requirement 10
"""

from rest_framework import generics, status
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from apps.services.models import Appointment, Service, StageTransition
from apps.services.serializers import (
    AppointmentDetailSerializer,
    AppointmentListSerializer,
    BookAppointmentSerializer,
    ServiceDetailSerializer,
    ServiceListSerializer,
)
from core.pagination import StandardPagination


class ServiceListView(generics.ListAPIView):
    """GET /api/services — Requirements 6.1, 6.2, 6.3"""

    serializer_class = ServiceListSerializer
    permission_classes = [AllowAny]
    pagination_class = StandardPagination

    def get_queryset(self):
        return Service.objects.filter(is_active=True)


class ServiceDetailView(generics.RetrieveAPIView):
    """GET /api/services/:id — Requirements 7.1, 7.2, 7.3"""

    serializer_class = ServiceDetailSerializer
    permission_classes = [AllowAny]

    def get_object(self):
        pk = self.kwargs.get("pk")
        # Validate integer ID (Req 7.3)
        try:
            pk = int(pk)
        except (TypeError, ValueError):
            raise ValidationError({"detail": "Service ID must be an integer."})

        try:
            return Service.objects.get(pk=pk)
        except Service.DoesNotExist:
            raise NotFound(f"Service with id {pk} not found.")


class BookAppointmentView(generics.CreateAPIView):
    """POST /api/appointments/book — Requirements 8.1–8.6"""

    serializer_class = BookAppointmentSerializer
    permission_classes = [IsAuthenticated]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        service = serializer.validated_data["service"]
        chassis = serializer.validated_data["chassis"]

        appointment = Appointment.objects.create(
            user=request.user,
            service=service,
            chassis=chassis,
            stage="Pending",
        )
        # Record initial stage transition
        StageTransition.objects.create(appointment=appointment, stage="Pending")

        return Response(
            {
                "id": appointment.pk,
                "service_id": service.pk,
                "chassis": chassis,
                "stage": appointment.stage,
                "created_at": appointment.created_at,
            },
            status=status.HTTP_201_CREATED,
        )


class UserAppointmentListView(generics.ListAPIView):
    """GET /api/appointments/user — Requirements 9.1, 9.2"""

    serializer_class = AppointmentListSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardPagination

    def get_queryset(self):
        return Appointment.objects.filter(user=self.request.user).order_by("-created_at")


class AppointmentDetailView(generics.RetrieveAPIView):
    """GET /api/appointments/:id — Requirements 10.1–10.4"""

    serializer_class = AppointmentDetailSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        pk = self.kwargs.get("pk")
        try:
            appointment = Appointment.objects.prefetch_related("transitions").get(pk=pk)
        except Appointment.DoesNotExist:
            raise NotFound(f"Appointment with id {pk} not found.")

        # Ownership check — return 403 if not the owner (Req 10.2)
        if appointment.user != self.request.user:
            raise PermissionDenied("You do not have permission to view this appointment.")

        return appointment
