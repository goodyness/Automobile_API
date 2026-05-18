"""
Views for the admin_tools app.

Endpoints:
  GET   /api/admin/users                        — Requirement 20
  PATCH /api/admin/appointments/:id/status      — Requirement 21
  POST  /api/admin/appointments/:id/report      — Requirement 22
"""

import os

from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import generics, status
from rest_framework.exceptions import NotFound
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.admin_tools.serializers import (
    AdminUserSerializer,
    AppointmentStatusSerializer,
    AppointmentWithTransitionsSerializer,
)
from apps.services.models import Appointment, StageTransition
from core.pagination import StandardPagination
from core.permissions import IsAdminUser
from core.validators import validate_report_file

User = get_user_model()


class AdminUserListView(generics.ListAPIView):
    """GET /api/admin/users — Requirements 20.1–20.3"""

    serializer_class = AdminUserSerializer
    permission_classes = [IsAdminUser]
    pagination_class = StandardPagination

    def get_queryset(self):
        return User.objects.all().order_by("-date_joined")


class AdminAppointmentStatusView(APIView):
    """PATCH /api/admin/appointments/:id/status — Requirements 21.1–21.4"""

    permission_classes = [IsAdminUser]

    def patch(self, request, pk, *args, **kwargs):
        try:
            appointment = Appointment.objects.prefetch_related("transitions").get(pk=pk)
        except Appointment.DoesNotExist:
            raise NotFound(f"Appointment with id {pk} not found.")

        serializer = AppointmentStatusSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        new_stage = serializer.validated_data["stage"]
        appointment.stage = new_stage
        appointment.save(update_fields=["stage"])

        # Record the transition with server-generated UTC timestamp (Req 21.1)
        StageTransition.objects.create(appointment=appointment, stage=new_stage)

        # Refresh to get updated transitions
        appointment.refresh_from_db()
        return Response(
            AppointmentWithTransitionsSerializer(appointment).data,
            status=status.HTTP_200_OK,
        )


class AdminReportAttachView(APIView):
    """POST /api/admin/appointments/:id/report — Requirements 22.1–22.5"""

    permission_classes = [IsAdminUser]

    def post(self, request, pk, *args, **kwargs):
        try:
            appointment = Appointment.objects.get(pk=pk)
        except Appointment.DoesNotExist:
            raise NotFound(f"Appointment with id {pk} not found.")

        file = request.FILES.get("file")
        if not file:
            return Response(
                {"detail": "A file is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Validate file type and size
        try:
            validate_report_file(file)
        except Exception as exc:
            detail = exc.detail if hasattr(exc, "detail") else str(exc)
            if isinstance(detail, list):
                detail = detail[0]
            return Response({"detail": str(detail)}, status=status.HTTP_400_BAD_REQUEST)

        # Delete old report file from storage if one exists (Req 22.5)
        if appointment.report_file:
            try:
                appointment.report_file.delete(save=False)
            except Exception:
                pass  # Don't fail if old file is already gone

        # Save new report
        appointment.report_file = file
        appointment.report_filename = file.name
        appointment.report_file_size = file.size
        appointment.report_mime_type = file.content_type
        appointment.report_uploaded_at = timezone.now()
        appointment.save(update_fields=[
            "report_file", "report_filename", "report_file_size",
            "report_mime_type", "report_uploaded_at",
        ])

        url = request.build_absolute_uri(appointment.report_file.url)
        return Response(
            {
                "url": url,
                "filename": appointment.report_filename,
                "file_size": appointment.report_file_size,
                "mime_type": appointment.report_mime_type,
                "uploaded_at": appointment.report_uploaded_at,
            },
            status=status.HTTP_200_OK,
        )
