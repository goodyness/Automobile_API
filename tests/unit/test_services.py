"""
Unit tests for services and appointments endpoints.
Requirements: 6.1–6.3, 7.1–7.3, 8.1–8.6, 9.1–9.2, 10.1–10.4
"""

import pytest
from apps.services.models import Appointment, Service, StageTransition

SERVICES_URL = "/api/services"
BOOK_URL = "/api/appointments/book"
USER_APPTS_URL = "/api/appointments/user"


# ---------------------------------------------------------------------------
# Service Directory (Requirement 6 & 7)
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestServiceList:
    def test_returns_active_services(self, api_client, service):
        res = api_client.get(SERVICES_URL)
        assert res.status_code == 200
        assert res.data["count"] >= 1

    def test_inactive_service_excluded(self, api_client, service):
        service.is_active = False
        service.save()
        res = api_client.get(SERVICES_URL)
        ids = [s["id"] for s in res.data["results"]]
        assert service.pk not in ids

    def test_pagination_metadata_present(self, api_client, service):
        res = api_client.get(SERVICES_URL)
        assert "count" in res.data
        assert "next" in res.data
        assert "previous" in res.data


@pytest.mark.django_db
class TestServiceDetail:
    def test_valid_id_returns_200(self, api_client, service):
        res = api_client.get(f"{SERVICES_URL}/{service.pk}")
        assert res.status_code == 200
        assert res.data["turnaround_days"] == service.turnaround_days

    def test_unknown_id_returns_404(self, api_client):
        res = api_client.get(f"{SERVICES_URL}/99999")
        assert res.status_code == 404

    def test_non_integer_id_returns_400(self, api_client):
        res = api_client.get(f"{SERVICES_URL}/abc")
        assert res.status_code == 400


# ---------------------------------------------------------------------------
# Book Appointment (Requirement 8)
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestBookAppointment:
    def test_valid_booking_returns_201(self, auth_client, service):
        res = auth_client.post(BOOK_URL, {
            "service_id": service.pk, "chassis": "W204",
        }, format="json")
        assert res.status_code == 201
        assert res.data["stage"] == "Pending"

    def test_unauthenticated_returns_401(self, api_client, service):
        res = api_client.post(BOOK_URL, {
            "service_id": service.pk, "chassis": "W204",
        }, format="json")
        assert res.status_code == 401

    def test_nonexistent_service_returns_400(self, auth_client):
        res = auth_client.post(BOOK_URL, {
            "service_id": 99999, "chassis": "W204",
        }, format="json")
        assert res.status_code == 400

    def test_missing_fields_returns_400(self, auth_client):
        res = auth_client.post(BOOK_URL, {}, format="json")
        assert res.status_code == 400

    def test_unsupported_chassis_returns_400(self, auth_client, service):
        res = auth_client.post(BOOK_URL, {
            "service_id": service.pk, "chassis": "W999",
        }, format="json")
        assert res.status_code == 400

    def test_incompatible_chassis_returns_400(self, auth_client, service):
        # W463 is valid but not in service.compatible_chassis (W204, W212)
        res = auth_client.post(BOOK_URL, {
            "service_id": service.pk, "chassis": "W463",
        }, format="json")
        assert res.status_code == 400

    def test_initial_stage_transition_created(self, auth_client, service):
        res = auth_client.post(BOOK_URL, {
            "service_id": service.pk, "chassis": "W204",
        }, format="json")
        appt_id = res.data["id"]
        assert StageTransition.objects.filter(
            appointment_id=appt_id, stage="Pending"
        ).exists()


# ---------------------------------------------------------------------------
# User Appointment History (Requirement 9)
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestUserAppointmentList:
    def test_returns_own_appointments(self, auth_client, appointment):
        res = auth_client.get(USER_APPTS_URL)
        assert res.status_code == 200
        assert res.data["count"] >= 1

    def test_unauthenticated_returns_401(self, api_client):
        res = api_client.get(USER_APPTS_URL)
        assert res.status_code == 401


# ---------------------------------------------------------------------------
# Appointment Detail (Requirement 10)
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestAppointmentDetail:
    def test_owner_can_view(self, auth_client, appointment):
        res = auth_client.get(f"/api/appointments/{appointment.pk}")
        assert res.status_code == 200
        assert "transitions" in res.data

    def test_non_owner_gets_403(self, api_client, appointment, create_user):
        other = create_user(email="other@example.com")
        from rest_framework_simplejwt.tokens import RefreshToken
        token = RefreshToken.for_user(other)
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {token.access_token}")
        res = api_client.get(f"/api/appointments/{appointment.pk}")
        assert res.status_code == 403

    def test_nonexistent_returns_404(self, auth_client):
        res = auth_client.get("/api/appointments/99999")
        assert res.status_code == 404

    def test_unauthenticated_returns_401(self, api_client, appointment):
        res = api_client.get(f"/api/appointments/{appointment.pk}")
        assert res.status_code == 401
