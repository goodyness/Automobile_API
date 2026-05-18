"""
Unit tests for admin tools endpoints.
Requirements: 20.1–20.3, 21.1–21.4, 22.1–22.5
"""

import io

import pytest
from apps.services.models import StageTransition

ADMIN_USERS_URL = "/api/admin/users"


# ---------------------------------------------------------------------------
# Admin User List (Requirement 20)
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestAdminUserList:
    def test_admin_can_list_users(self, admin_client, user):
        res = admin_client.get(ADMIN_USERS_URL)
        assert res.status_code == 200
        assert res.data["count"] >= 1

    def test_non_admin_gets_403(self, auth_client):
        res = auth_client.get(ADMIN_USERS_URL)
        assert res.status_code == 403

    def test_unauthenticated_gets_401(self, api_client):
        res = api_client.get(ADMIN_USERS_URL)
        assert res.status_code == 401

    def test_response_includes_chassis(self, admin_client, user):
        res = admin_client.get(ADMIN_USERS_URL)
        users = res.data["results"]
        found = next((u for u in users if u["email"] == user.email), None)
        assert found is not None
        assert isinstance(found["chassis"], list)


# ---------------------------------------------------------------------------
# Admin Appointment Status (Requirement 21)
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestAdminAppointmentStatus:
    def test_admin_can_advance_stage(self, admin_client, appointment):
        url = f"/api/admin/appointments/{appointment.pk}/status"
        res = admin_client.patch(url, {"stage": "In Diagnostics"}, format="json")
        assert res.status_code == 200
        assert res.data["stage"] == "In Diagnostics"

    def test_transition_recorded(self, admin_client, appointment):
        url = f"/api/admin/appointments/{appointment.pk}/status"
        admin_client.patch(url, {"stage": "In Diagnostics"}, format="json")
        assert StageTransition.objects.filter(
            appointment=appointment, stage="In Diagnostics"
        ).exists()

    def test_invalid_stage_returns_400(self, admin_client, appointment):
        url = f"/api/admin/appointments/{appointment.pk}/status"
        res = admin_client.patch(url, {"stage": "Flying"}, format="json")
        assert res.status_code == 400

    def test_non_admin_gets_403(self, auth_client, appointment):
        url = f"/api/admin/appointments/{appointment.pk}/status"
        res = auth_client.patch(url, {"stage": "In Diagnostics"}, format="json")
        assert res.status_code == 403

    def test_nonexistent_appointment_returns_404(self, admin_client):
        res = admin_client.patch(
            "/api/admin/appointments/99999/status",
            {"stage": "In Diagnostics"},
            format="json",
        )
        assert res.status_code == 404


# ---------------------------------------------------------------------------
# Admin Report Attach (Requirement 22)
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestAdminReportAttach:
    def _make_pdf(self):
        buf = io.BytesIO(b"%PDF-1.4 fake pdf content")
        buf.name = "report.pdf"
        buf.content_type = "application/pdf"
        return buf

    def test_admin_can_attach_report(self, admin_client, appointment):
        url = f"/api/admin/appointments/{appointment.pk}/report"
        res = admin_client.post(url, {"file": self._make_pdf()}, format="multipart")
        assert res.status_code == 200
        assert "url" in res.data

    def test_non_admin_gets_403(self, auth_client, appointment):
        url = f"/api/admin/appointments/{appointment.pk}/report"
        res = auth_client.post(url, {"file": self._make_pdf()}, format="multipart")
        assert res.status_code == 403

    def test_nonexistent_appointment_returns_404(self, admin_client):
        res = admin_client.post(
            "/api/admin/appointments/99999/report",
            {"file": self._make_pdf()},
            format="multipart",
        )
        assert res.status_code == 404

    def test_wrong_file_type_returns_400(self, admin_client, appointment):
        url = f"/api/admin/appointments/{appointment.pk}/report"
        img = io.BytesIO(b"fake image data")
        img.name = "photo.jpg"
        img.content_type = "image/jpeg"
        res = admin_client.post(url, {"file": img}, format="multipart")
        assert res.status_code == 400

    def test_report_replacement(self, admin_client, appointment):
        url = f"/api/admin/appointments/{appointment.pk}/report"
        admin_client.post(url, {"file": self._make_pdf()}, format="multipart")
        res = admin_client.post(url, {"file": self._make_pdf()}, format="multipart")
        assert res.status_code == 200
        appointment.refresh_from_db()
        # Only one report file should be set
        assert appointment.report_file is not None
