"""
Models for the services app.

Service       — a technical capability offered by the workshop
Appointment   — a repair/diagnostic job booked by a user
StageTransition — an immutable record of each stage change on an appointment

Requirements: 6.1, 7.1, 8.1, 9.1, 10.1, 21.1
"""

from django.conf import settings
from django.db import models

from core.constants import CHASSIS_CHOICES, REPAIR_STAGES


class Service(models.Model):
    """
    A technical capability offered by the workshop (e.g. ECU programming,
    EIS repair, FBS-4 sync).

    compatible_chassis stores a JSON list of chassis codes, e.g. ["W204", "W212"].
    Only services with is_active=True appear in the public directory (Req 6.1).
    """

    name = models.CharField(max_length=200)
    description = models.TextField()
    turnaround_days = models.PositiveIntegerField(
        help_text="Estimated turnaround time in days."
    )
    is_active = models.BooleanField(default=True)
    compatible_chassis = models.JSONField(
        default=list,
        help_text="List of compatible chassis codes, e.g. ['W204', 'W212'].",
    )

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class Appointment(models.Model):
    """
    A repair or diagnostic job submitted by a user for a specific module.

    The repair progresses through REPAIR_STAGES. Each stage change is
    recorded as an immutable StageTransition entry.

    Report fields store metadata about an attached diagnostic PDF/binary
    file (uploaded by an admin). At most one report per appointment.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="appointments",
    )
    service = models.ForeignKey(
        Service,
        on_delete=models.PROTECT,
        related_name="appointments",
    )
    chassis = models.CharField(max_length=10, choices=CHASSIS_CHOICES)
    stage = models.CharField(
        max_length=20,
        choices=REPAIR_STAGES,
        default="Pending",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    # Diagnostic report fields (populated by admin, Requirement 22)
    report_file = models.FileField(
        upload_to="reports/",
        null=True,
        blank=True,
    )
    report_filename = models.CharField(max_length=255, blank=True)
    report_file_size = models.PositiveIntegerField(null=True, blank=True)
    report_mime_type = models.CharField(max_length=100, blank=True)
    report_uploaded_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"Appointment #{self.pk} — {self.user} — {self.stage}"

    @property
    def report_url(self) -> str | None:
        """Return the absolute URL of the attached report, or None."""
        if self.report_file:
            return self.report_file.url
        return None


class StageTransition(models.Model):
    """
    An immutable record of a single stage change on an Appointment.

    Created automatically when an Appointment is first booked (stage=Pending)
    and each time an admin advances the stage. Never modified or deleted.

    Requirements: 10.1, 21.1, Property 12 (append-only history)
    """

    appointment = models.ForeignKey(
        Appointment,
        on_delete=models.CASCADE,
        related_name="transitions",
    )
    stage = models.CharField(max_length=20, choices=REPAIR_STAGES)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["timestamp"]

    def __str__(self) -> str:
        return f"Appointment #{self.appointment_id} → {self.stage} at {self.timestamp}"
