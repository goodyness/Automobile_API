"""
Serializers for the authentication app.

Requirements: 1.1–1.6, 2.1–2.3
"""

from django.contrib.auth import get_user_model
from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken

from core.validators import validate_chassis, validate_password_strength

User = get_user_model()


# ---------------------------------------------------------------------------
# Registration — Step 1 (validate only, no account creation yet)
# ---------------------------------------------------------------------------

class RegistrationRequestSerializer(serializers.Serializer):
    """
    Validates registration fields before sending the OTP.
    Does NOT create a user — that happens in VerifyOTPView after OTP confirmation.
    """

    name = serializers.CharField(max_length=150)
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)
    chassis = serializers.ListField(
        child=serializers.CharField(),
        min_length=1,
    )

    def validate_password(self, value: str) -> str:
        validate_password_strength(value)
        return value

    def validate_chassis(self, value: list) -> list:
        for code in value:
            validate_chassis(code)
        return value

    def validate_email(self, value: str) -> str:
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value


# ---------------------------------------------------------------------------
# Registration — kept for backward-compat imports (not used directly)
# ---------------------------------------------------------------------------

class UserSerializer(RegistrationRequestSerializer):
    """Alias kept so existing test imports don't break."""
    pass


# ---------------------------------------------------------------------------
# Login
# ---------------------------------------------------------------------------

class LoginSerializer(serializers.Serializer):
    """
    Validates login credentials and returns a JWT token pair.

    On success returns a dict with ``access_token`` and ``refresh_token``.
    On failure raises ValidationError with a generic message that does NOT
    distinguish between wrong password and unregistered email (Requirement 2.2).

    Requirements: 2.1, 2.2, 2.3
    """

    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs: dict) -> dict:
        email = attrs.get("email")
        password = attrs.get("password")

        # Attempt to find the user by email (case-insensitive)
        try:
            user = User.objects.get(email__iexact=email)
        except User.DoesNotExist:
            raise serializers.ValidationError(
                {"non_field_errors": ["Invalid email or password."]}
            )

        if not user.check_password(password):
            raise serializers.ValidationError(
                {"non_field_errors": ["Invalid email or password."]}
            )

        if not user.is_active:
            raise serializers.ValidationError(
                {"non_field_errors": ["Invalid email or password."]}
            )

        # Generate token pair
        refresh = RefreshToken.for_user(user)
        return {
            "access_token": str(refresh.access_token),
            "refresh_token": str(refresh),
        }
