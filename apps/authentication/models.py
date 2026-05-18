import random
from datetime import timedelta

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone

from core.constants import CHASSIS_CHOICES


class User(AbstractUser):
    """
    Custom user model that uses email as the primary login identifier.
    Chassis associations are stored via the related UserChassis model.
    """

    email = models.EmailField(unique=True)
    name = models.CharField(max_length=150)

    USERNAME_FIELD = "email"
    # username is still required (inherited from AbstractUser) but is not
    # used for authentication — it serves as a display / handle field.
    REQUIRED_FIELDS = ["username"]

    def __str__(self) -> str:
        return self.email


class UserChassis(models.Model):
    """
    Associates a user with one or more supported Mercedes-Benz chassis types.
    The combination of (user, chassis) is unique to prevent duplicates.
    """

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="chassis_set",
    )
    chassis = models.CharField(max_length=10, choices=CHASSIS_CHOICES)

    class Meta:
        unique_together = ("user", "chassis")

    def __str__(self) -> str:
        return f"{self.user.email} — {self.chassis}"


class PasswordResetToken(models.Model):
    """
    Stores a single-use, time-limited token for password recovery.

    Tokens expire 1 hour after creation and are invalidated after first use.
    """

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="password_reset_tokens",
    )
    token = models.CharField(max_length=64, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    used = models.BooleanField(default=False)

    def is_expired(self) -> bool:
        """Return True if the token was issued more than 1 hour ago."""
        return timezone.now() > self.created_at + timedelta(hours=1)

    def __str__(self) -> str:
        status = "used" if self.used else ("expired" if self.is_expired() else "valid")
        return f"PasswordResetToken({self.user.email}, {status})"


class OTPVerification(models.Model):
    """
    Stores a 6-digit OTP sent to an email address during registration.

    Flow:
      1. User submits registration details → OTP generated & emailed.
      2. User submits OTP → account created if OTP is valid & unexpired.

    OTPs expire after 10 minutes and are single-use.
    """

    OTP_EXPIRY_MINUTES = 10

    # Store against email (not a User FK) because the user doesn't exist yet.
    email = models.EmailField()
    otp = models.CharField(max_length=6)
    # Serialised registration payload stored temporarily so we don't ask the
    # user to re-submit all fields on the verify step.
    payload = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
    used = models.BooleanField(default=False)

    class Meta:
        ordering = ["-created_at"]

    @staticmethod
    def generate_otp() -> str:
        """Return a zero-padded 6-digit OTP string."""
        return f"{random.randint(0, 999999):06d}"

    def is_expired(self) -> bool:
        """Return True if the OTP is older than OTP_EXPIRY_MINUTES."""
        return timezone.now() > self.created_at + timedelta(minutes=self.OTP_EXPIRY_MINUTES)

    def __str__(self) -> str:
        state = "used" if self.used else ("expired" if self.is_expired() else "valid")
        return f"OTP({self.email}, {state})"
