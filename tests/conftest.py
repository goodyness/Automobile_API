"""
Shared pytest fixtures for the Automobile Backend API test suite.
"""

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.authentication.models import UserChassis
from apps.services.models import Appointment, Service, StageTransition

User = get_user_model()


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def create_user(db):
    def _create(email="user@example.com", password="SecurePass1", name="Test User",
                chassis=None, is_staff=False):
        user = User.objects.create_user(
            username=email,
            email=email,
            password=password,
            name=name,
            is_staff=is_staff,
        )
        for code in (chassis or []):
            UserChassis.objects.create(user=user, chassis=code)
        return user
    return _create


@pytest.fixture
def user(create_user):
    return create_user(chassis=["W204"])


@pytest.fixture
def admin_user(create_user):
    return create_user(email="admin@example.com", is_staff=True)


@pytest.fixture
def auth_client(api_client, user):
    refresh = RefreshToken.for_user(user)
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
    return api_client


@pytest.fixture
def admin_client(api_client, admin_user):
    refresh = RefreshToken.for_user(admin_user)
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
    return api_client


@pytest.fixture
def service(db):
    return Service.objects.create(
        name="ECU Programming",
        description="Full ECU coding for Mercedes-Benz platforms.",
        turnaround_days=3,
        is_active=True,
        compatible_chassis=["W204", "W212"],
    )


@pytest.fixture
def appointment(db, user, service):
    appt = Appointment.objects.create(
        user=user, service=service, chassis="W204", stage="Pending"
    )
    StageTransition.objects.create(appointment=appt, stage="Pending")
    return appt
