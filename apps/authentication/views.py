"""
Views for the authentication app.

Registration is a two-step OTP-verified flow:
  Step 1 — POST /api/auth/register      → validates data, sends 6-digit OTP via email
  Step 2 — POST /api/auth/verify-otp    → verifies OTP, creates account, returns tokens

Other endpoints:
  POST /api/auth/login           — Requirement 2
  POST /api/auth/logout          — Requirement 3
  GET  /api/auth/me              — Requirement 4
  POST /api/auth/forgot-password — Requirement 5
  POST /api/auth/reset-password  — Requirement 5

Admin accounts are created exclusively via:
  python manage.py createsuperuser
The /api/auth/register endpoint will reject any attempt to set is_staff=True.
"""

import secrets

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.mail import send_mail
from django.utils import timezone
from rest_framework import status
from rest_framework.exceptions import NotFound, Throttled
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken

from apps.authentication.models import OTPVerification, PasswordResetToken, UserChassis
from apps.authentication.serializers import LoginSerializer, RegistrationRequestSerializer
from core.validators import validate_password_strength

User = get_user_model()

# ---------------------------------------------------------------------------
# Rate-limiting constants (Requirement 2.5)
# ---------------------------------------------------------------------------
_RATE_LIMIT_MAX_ATTEMPTS = 10
_RATE_LIMIT_WINDOW_SECONDS = 15 * 60  # 15 minutes


def _get_client_ip(request) -> str:
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        return x_forwarded_for.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "unknown")


def _check_rate_limit(ip: str) -> None:
    cache_key = f"login_attempts_{ip}"
    attempts = cache.get(cache_key, 0)
    if attempts >= _RATE_LIMIT_MAX_ATTEMPTS:
        ttl = cache.ttl(cache_key) if hasattr(cache, "ttl") else _RATE_LIMIT_WINDOW_SECONDS
        retry_after = ttl if ttl and ttl > 0 else _RATE_LIMIT_WINDOW_SECONDS
        raise Throttled(wait=retry_after)


def _record_failed_attempt(ip: str) -> None:
    cache_key = f"login_attempts_{ip}"
    try:
        cache.incr(cache_key)
    except ValueError:
        cache.set(cache_key, 1, timeout=_RATE_LIMIT_WINDOW_SECONDS)


# ---------------------------------------------------------------------------
# Step 1 — Register (send OTP)
# ---------------------------------------------------------------------------

class RegisterView(APIView):
    """
    POST /api/auth/register

    Validates registration data and sends a 6-digit OTP to the provided
    email address. The account is NOT created yet — call /api/auth/verify-otp
    with the OTP to complete registration.

    Admin accounts cannot be created through this endpoint. Use:
        python manage.py createsuperuser

    Request body:
        {
            "name": "John Doe",
            "email": "john@example.com",
            "password": "SecurePass1",
            "chassis": ["W204", "W212"]
        }

    Response 200:
        {"detail": "OTP sent to john@example.com. It expires in 10 minutes."}
    """

    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = RegistrationRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data["email"]

        # Invalidate any previous unused OTPs for this email
        OTPVerification.objects.filter(email__iexact=email, used=False).update(used=True)

        # Generate and store OTP with the full registration payload
        otp_code = OTPVerification.generate_otp()
        OTPVerification.objects.create(
            email=email,
            otp=otp_code,
            payload={
                "name": serializer.validated_data["name"],
                "email": email,
                "password": serializer.validated_data["password"],  # already validated
                "chassis": serializer.validated_data["chassis"],
            },
        )

        # Send OTP via SMTP
        send_mail(
            subject="Your Automobile Backend Verification Code",
            message=(
                f"Hello {serializer.validated_data['name']},\n\n"
                f"Your one-time verification code is:\n\n"
                f"    {otp_code}\n\n"
                f"This code expires in {OTPVerification.OTP_EXPIRY_MINUTES} minutes "
                f"and can only be used once.\n\n"
                f"If you did not request this, please ignore this email."
            ),
            from_email=None,  # Uses DEFAULT_FROM_EMAIL from settings
            recipient_list=[email],
            fail_silently=True,  # Never block the response on email failure
        )

        return Response(
            {
                "detail": (
                    f"OTP sent to {email}. "
                    f"It expires in {OTPVerification.OTP_EXPIRY_MINUTES} minutes."
                )
            },
            status=status.HTTP_200_OK,
        )


# ---------------------------------------------------------------------------
# Step 2 — Verify OTP (create account)
# ---------------------------------------------------------------------------

class VerifyOTPView(APIView):
    """
    POST /api/auth/verify-otp

    Verifies the 6-digit OTP and creates the user account.
    Returns JWT tokens on success so the user is immediately logged in.

    Request body:
        {
            "email": "john@example.com",
            "otp": "123456"
        }

    Response 201:
        {
            "name": "John Doe",
            "email": "john@example.com",
            "chassis": ["W204"],
            "access_token": "...",
            "refresh_token": "..."
        }
    """

    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        email = request.data.get("email", "").strip().lower()
        otp_input = request.data.get("otp", "").strip()

        if not email or not otp_input:
            return Response(
                {"detail": "Both 'email' and 'otp' fields are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Find the most recent unused OTP for this email
        try:
            otp_record = OTPVerification.objects.filter(
                email__iexact=email, used=False
            ).latest("created_at")
        except OTPVerification.DoesNotExist:
            return Response(
                {"detail": "No pending OTP found for this email. Please register again."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if otp_record.is_expired():
            return Response(
                {"detail": "OTP has expired. Please register again to receive a new code."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if otp_record.otp != otp_input:
            return Response(
                {"detail": "Invalid OTP. Please check the code and try again."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # OTP is valid — create the user account
        payload = otp_record.payload
        if User.objects.filter(email__iexact=email).exists():
            # Edge case: account was created between OTP send and verify
            otp_record.used = True
            otp_record.save(update_fields=["used"])
            return Response(
                {"detail": "An account with this email already exists."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = User(
            username=email,
            email=email,
            name=payload["name"],
            is_active=True,
            is_staff=False,   # Never allow staff via API
        )
        user.set_password(payload["password"])
        user.save()

        for code in payload.get("chassis", []):
            UserChassis.objects.get_or_create(user=user, chassis=code)

        # Mark OTP as used
        otp_record.used = True
        otp_record.save(update_fields=["used"])

        # Issue tokens so the user is immediately logged in
        refresh = RefreshToken.for_user(user)
        chassis_list = list(user.chassis_set.values_list("chassis", flat=True))

        return Response(
            {
                "name": user.name,
                "email": user.email,
                "chassis": chassis_list,
                "access_token": str(refresh.access_token),
                "refresh_token": str(refresh),
            },
            status=status.HTTP_201_CREATED,
        )


# ---------------------------------------------------------------------------
# Login
# ---------------------------------------------------------------------------

class LoginView(APIView):
    """
    POST /api/auth/login

    Validates credentials and returns a JWT access + refresh token pair.
    Enforces per-IP rate limiting (10 failed attempts / 15 min window).
    Requirements: 2.1–2.5
    """

    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        ip = _get_client_ip(request)
        _check_rate_limit(ip)

        serializer = LoginSerializer(data=request.data)
        if not serializer.is_valid():
            _record_failed_attempt(ip)
            return Response(
                {"detail": "Invalid email or password."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        return Response(serializer.validated_data, status=status.HTTP_200_OK)


# ---------------------------------------------------------------------------
# Logout
# ---------------------------------------------------------------------------

class LogoutView(APIView):
    """
    POST /api/auth/logout

    Blacklists the provided refresh token so it can no longer be used.
    Requirements: 3.1–3.3
    """

    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        refresh_token = request.data.get("refresh_token")
        if not refresh_token:
            return Response(
                {"detail": "refresh_token is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            token = RefreshToken(refresh_token)
            token.blacklist()
        except TokenError:
            return Response(
                {"detail": "Invalid or already invalidated token."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response({"detail": "Successfully logged out."}, status=status.HTTP_200_OK)


# ---------------------------------------------------------------------------
# Me
# ---------------------------------------------------------------------------

class MeView(APIView):
    """
    GET /api/auth/me

    Returns the authenticated user's profile and registered chassis types.
    Requirements: 4.1–4.3
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        try:
            user = User.objects.get(pk=request.user.pk)
        except User.DoesNotExist:
            raise NotFound("User account not found.")

        chassis_list = list(user.chassis_set.values_list("chassis", flat=True))
        return Response(
            {"name": user.name, "email": user.email, "chassis": chassis_list},
            status=status.HTTP_200_OK,
        )


# ---------------------------------------------------------------------------
# Forgot Password
# ---------------------------------------------------------------------------

class ForgotPasswordView(APIView):
    """
    POST /api/auth/forgot-password

    Sends a password recovery email. Always returns 200 to prevent
    user enumeration (Requirement 5.3).
    """

    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        email = request.data.get("email", "").strip()
        _GENERIC_RESPONSE = Response(
            {"detail": "If this email is registered, a recovery link has been sent."},
            status=status.HTTP_200_OK,
        )

        if not email:
            return _GENERIC_RESPONSE

        try:
            user = User.objects.get(email__iexact=email)
        except User.DoesNotExist:
            return _GENERIC_RESPONSE

        raw_token = secrets.token_hex(32)
        PasswordResetToken.objects.create(user=user, token=raw_token)

        send_mail(
            subject="Password Reset Request — Automobile Backend",
            message=(
                f"Hello {user.name},\n\n"
                f"Use the following token to reset your password:\n\n"
                f"  {raw_token}\n\n"
                f"This token expires in 1 hour and can only be used once.\n\n"
                f"If you did not request a password reset, ignore this email."
            ),
            from_email=None,
            recipient_list=[user.email],
            fail_silently=True,
        )

        return _GENERIC_RESPONSE


# ---------------------------------------------------------------------------
# Reset Password
# ---------------------------------------------------------------------------

class ResetPasswordView(APIView):
    """
    POST /api/auth/reset-password

    Validates the recovery token and updates the user's password.
    Requirements: 5.5–5.6
    """

    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        raw_token = request.data.get("token", "").strip()
        new_password = request.data.get("password", "")

        if not raw_token or not new_password:
            return Response(
                {"detail": "Both 'token' and 'password' fields are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            reset_token = PasswordResetToken.objects.select_related("user").get(
                token=raw_token
            )
        except PasswordResetToken.DoesNotExist:
            return Response(
                {"detail": "This token is invalid or has expired."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if reset_token.used or reset_token.is_expired():
            return Response(
                {"detail": "This token is invalid or has expired."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            validate_password_strength(new_password)
        except Exception as exc:
            return Response({"password": list(exc.detail)}, status=status.HTTP_400_BAD_REQUEST)

        user = reset_token.user
        user.set_password(new_password)
        user.save(update_fields=["password"])

        reset_token.used = True
        reset_token.save(update_fields=["used"])

        return Response(
            {"detail": "Password has been reset successfully."},
            status=status.HTTP_200_OK,
        )
