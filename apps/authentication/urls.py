"""
URL patterns for the authentication app.

All routes are mounted under /api/auth/ in config/urls.py.

Registration is a two-step flow:
  POST /api/auth/register     → validates data, sends OTP
  POST /api/auth/verify-otp   → verifies OTP, creates account, returns tokens

Admin accounts are created via:
  python manage.py createsuperuser
"""

from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from apps.authentication.views import (
    ForgotPasswordView,
    LoginView,
    LogoutView,
    MeView,
    RegisterView,
    ResetPasswordView,
    VerifyOTPView,
)

urlpatterns = [
    # Step 1: validate + send OTP
    path("register", RegisterView.as_view(), name="auth-register"),
    # Step 2: verify OTP + create account
    path("verify-otp", VerifyOTPView.as_view(), name="auth-verify-otp"),
    path("login", LoginView.as_view(), name="auth-login"),
    path("logout", LogoutView.as_view(), name="auth-logout"),
    path("me", MeView.as_view(), name="auth-me"),
    path("forgot-password", ForgotPasswordView.as_view(), name="auth-forgot-password"),
    path("reset-password", ResetPasswordView.as_view(), name="auth-reset-password"),
    path("token/refresh", TokenRefreshView.as_view(), name="auth-token-refresh"),
]
