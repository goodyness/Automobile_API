"""
Unit tests for authentication endpoints.
Requirements: 1.1–1.6, 2.1–2.5, 3.1–3.3, 4.1–4.3, 5.1–5.6

Registration is a two-step OTP flow:
  POST /api/auth/register    → validates data, sends OTP (mocked in tests)
  POST /api/auth/verify-otp  → verifies OTP, creates account
"""

import pytest
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import RefreshToken

from apps.authentication.models import OTPVerification, PasswordResetToken

User = get_user_model()

REGISTER_URL = "/api/auth/register"
VERIFY_OTP_URL = "/api/auth/verify-otp"
LOGIN_URL = "/api/auth/login"
LOGOUT_URL = "/api/auth/logout"
ME_URL = "/api/auth/me"
FORGOT_URL = "/api/auth/forgot-password"
RESET_URL = "/api/auth/reset-password"

VALID_REGISTER_PAYLOAD = {
    "name": "John Doe",
    "email": "john@example.com",
    "password": "SecurePass1",
    "chassis": ["W204"],
}


def _register_and_verify(api_client, payload=None, email_backend="console"):
    """
    Helper: complete the two-step registration flow.
    Uses the console email backend so no real SMTP is needed.
    Returns the verify-otp response.
    """
    p = payload or VALID_REGISTER_PAYLOAD
    api_client.post(REGISTER_URL, p, format="json")
    otp = OTPVerification.objects.filter(email__iexact=p["email"], used=False).latest("created_at")
    return api_client.post(VERIFY_OTP_URL, {"email": p["email"], "otp": otp.otp}, format="json")


# ---------------------------------------------------------------------------
# Registration Step 1 — /api/auth/register (Requirement 1)
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestRegisterStep1:
    def test_valid_data_returns_200_and_sends_otp(self, api_client):
        res = api_client.post(REGISTER_URL, VALID_REGISTER_PAYLOAD, format="json")
        assert res.status_code == 200
        assert "OTP sent" in res.data["detail"]
        assert OTPVerification.objects.filter(email="john@example.com").exists()

    def test_duplicate_email_returns_400(self, api_client, user):
        payload = {**VALID_REGISTER_PAYLOAD, "email": user.email}
        res = api_client.post(REGISTER_URL, payload, format="json")
        assert res.status_code == 400

    def test_missing_name_returns_400(self, api_client):
        payload = {k: v for k, v in VALID_REGISTER_PAYLOAD.items() if k != "name"}
        res = api_client.post(REGISTER_URL, payload, format="json")
        assert res.status_code == 400

    def test_invalid_email_returns_400(self, api_client):
        res = api_client.post(REGISTER_URL, {**VALID_REGISTER_PAYLOAD, "email": "bad"}, format="json")
        assert res.status_code == 400

    def test_weak_password_too_short_returns_400(self, api_client):
        res = api_client.post(REGISTER_URL, {**VALID_REGISTER_PAYLOAD, "password": "Ab1"}, format="json")
        assert res.status_code == 400

    def test_weak_password_no_uppercase_returns_400(self, api_client):
        res = api_client.post(REGISTER_URL, {**VALID_REGISTER_PAYLOAD, "password": "securepass1"}, format="json")
        assert res.status_code == 400

    def test_weak_password_no_digit_returns_400(self, api_client):
        res = api_client.post(REGISTER_URL, {**VALID_REGISTER_PAYLOAD, "password": "SecurePass"}, format="json")
        assert res.status_code == 400

    def test_invalid_chassis_returns_400(self, api_client):
        res = api_client.post(REGISTER_URL, {**VALID_REGISTER_PAYLOAD, "chassis": ["W999"]}, format="json")
        assert res.status_code == 400


# ---------------------------------------------------------------------------
# Registration Step 2 — /api/auth/verify-otp (Requirement 1)
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestVerifyOTP:
    def test_valid_otp_creates_account_and_returns_tokens(self, api_client):
        res = _register_and_verify(api_client)
        assert res.status_code == 201
        assert "access_token" in res.data
        assert "refresh_token" in res.data
        assert User.objects.filter(email="john@example.com").exists()

    def test_password_not_stored_in_plaintext(self, api_client):
        _register_and_verify(api_client)
        user = User.objects.get(email="john@example.com")
        assert user.password != "SecurePass1"
        assert user.check_password("SecurePass1")

    def test_admin_flag_never_set_via_api(self, api_client):
        _register_and_verify(api_client)
        user = User.objects.get(email="john@example.com")
        assert user.is_staff is False

    def test_wrong_otp_returns_400(self, api_client):
        api_client.post(REGISTER_URL, VALID_REGISTER_PAYLOAD, format="json")
        res = api_client.post(VERIFY_OTP_URL, {"email": "john@example.com", "otp": "000000"}, format="json")
        assert res.status_code == 400

    def test_expired_otp_returns_400(self, api_client):
        from django.utils import timezone
        from datetime import timedelta
        api_client.post(REGISTER_URL, VALID_REGISTER_PAYLOAD, format="json")
        otp = OTPVerification.objects.filter(email="john@example.com", used=False).latest("created_at")
        # Manually expire it
        OTPVerification.objects.filter(pk=otp.pk).update(
            created_at=timezone.now() - timedelta(minutes=11)
        )
        res = api_client.post(VERIFY_OTP_URL, {"email": "john@example.com", "otp": otp.otp}, format="json")
        assert res.status_code == 400

    def test_missing_fields_returns_400(self, api_client):
        res = api_client.post(VERIFY_OTP_URL, {}, format="json")
        assert res.status_code == 400


# ---------------------------------------------------------------------------
# Login (Requirement 2)
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestLogin:
    def test_valid_login_returns_tokens(self, api_client, user):
        res = api_client.post(LOGIN_URL, {"email": user.email, "password": "SecurePass1"}, format="json")
        assert res.status_code == 200
        assert "access_token" in res.data
        assert "refresh_token" in res.data

    def test_wrong_password_returns_401(self, api_client, user):
        res = api_client.post(LOGIN_URL, {"email": user.email, "password": "WrongPass1"}, format="json")
        assert res.status_code == 401

    def test_unregistered_email_returns_401(self, api_client):
        res = api_client.post(LOGIN_URL, {"email": "nobody@example.com", "password": "SecurePass1"}, format="json")
        assert res.status_code == 401

    def test_missing_fields_returns_400_or_401(self, api_client):
        res = api_client.post(LOGIN_URL, {"email": "x@example.com"}, format="json")
        assert res.status_code in (400, 401)


# ---------------------------------------------------------------------------
# Logout (Requirement 3)
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestLogout:
    def test_valid_logout_returns_200(self, auth_client, user):
        refresh = RefreshToken.for_user(user)
        res = auth_client.post(LOGOUT_URL, {"refresh_token": str(refresh)}, format="json")
        assert res.status_code == 200

    def test_logout_without_jwt_returns_401(self, api_client, user):
        refresh = RefreshToken.for_user(user)
        res = api_client.post(LOGOUT_URL, {"refresh_token": str(refresh)}, format="json")
        assert res.status_code == 401

    def test_blacklisted_token_cannot_be_reused(self, auth_client, user):
        refresh = RefreshToken.for_user(user)
        auth_client.post(LOGOUT_URL, {"refresh_token": str(refresh)}, format="json")
        res = auth_client.post("/api/auth/token/refresh", {"refresh": str(refresh)}, format="json")
        assert res.status_code == 401


# ---------------------------------------------------------------------------
# Me (Requirement 4)
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestMe:
    def test_authenticated_returns_profile(self, auth_client, user):
        res = auth_client.get(ME_URL)
        assert res.status_code == 200
        assert res.data["email"] == user.email
        assert isinstance(res.data["chassis"], list)

    def test_unauthenticated_returns_401(self, api_client):
        res = api_client.get(ME_URL)
        assert res.status_code == 401


# ---------------------------------------------------------------------------
# Forgot / Reset Password (Requirement 5)
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestPasswordRecovery:
    def test_forgot_password_registered_email_returns_200(self, api_client, user):
        res = api_client.post(FORGOT_URL, {"email": user.email}, format="json")
        assert res.status_code == 200

    def test_forgot_password_unregistered_email_returns_200(self, api_client):
        res = api_client.post(FORGOT_URL, {"email": "nobody@example.com"}, format="json")
        assert res.status_code == 200

    def test_reset_with_valid_token_returns_200(self, api_client, user):
        import secrets
        token = secrets.token_hex(32)
        PasswordResetToken.objects.create(user=user, token=token)
        res = api_client.post(RESET_URL, {"token": token, "password": "NewPass1"}, format="json")
        assert res.status_code == 200
        user.refresh_from_db()
        assert user.check_password("NewPass1")

    def test_reset_with_used_token_returns_400(self, api_client, user):
        import secrets
        token = secrets.token_hex(32)
        PasswordResetToken.objects.create(user=user, token=token, used=True)
        res = api_client.post(RESET_URL, {"token": token, "password": "NewPass1"}, format="json")
        assert res.status_code == 400

    def test_reset_with_invalid_token_returns_400(self, api_client):
        res = api_client.post(RESET_URL, {"token": "nonexistent", "password": "NewPass1"}, format="json")
        assert res.status_code == 400
