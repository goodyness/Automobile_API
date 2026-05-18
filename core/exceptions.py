"""
Global exception handler for the Automobile Backend API.

Normalises all DRF and bare Python exceptions to one of two JSON shapes:

  Generic error:
      {"detail": "A descriptive error message."}

  Validation error (field-level):
      {"field_name": ["error message 1", ...], ...}

  Throttled (rate-limit) error:
      {"detail": "Request was throttled. ...", "retry_after": <seconds>}
      + Retry-After HTTP header

Requirements: 24.1, 24.2
"""

import logging

from rest_framework import status
from rest_framework.exceptions import (
    AuthenticationFailed,
    NotAuthenticated,
    NotFound,
    PermissionDenied,
    Throttled,
    ValidationError,
)
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_default_handler

logger = logging.getLogger(__name__)


def custom_exception_handler(exc: Exception, context: dict) -> Response:
    """
    Custom DRF exception handler.

    Intercepts every exception raised inside a DRF view and returns a
    normalised JSON response.  The two possible response shapes are:

    1. Generic  → {"detail": "<message>"}
    2. Validation → {"<field>": ["<error>", ...], ...}

    For Throttled exceptions the generic shape is extended with a
    ``retry_after`` key (integer seconds) and a ``Retry-After`` HTTP
    header is added to the response.

    Unhandled bare ``Exception`` instances are caught last and mapped to
    HTTP 500 with a generic message so that internal details are never
    leaked to the client.

    Args:
        exc:     The exception that was raised.
        context: DRF context dict containing ``view`` and ``request``.

    Returns:
        A DRF ``Response`` object with the normalised error payload.
    """

    # ------------------------------------------------------------------ #
    # 1. ValidationError → field-level map  (Requirement 24.2)           #
    # ------------------------------------------------------------------ #
    if isinstance(exc, ValidationError):
        detail = exc.detail

        # DRF may give us a plain list (non-field errors) or a dict
        # (field-level errors).  Normalise both to the field-level shape.
        if isinstance(detail, list):
            # Non-field validation error — wrap under "detail" key so the
            # response still satisfies Requirement 24.1 (always has a key
            # whose value is a non-empty array of strings).
            payload = {"detail": [str(msg) for msg in detail]}
        elif isinstance(detail, dict):
            # Field-level errors: {"field": [ErrorDetail, ...], ...}
            payload = {
                field: [str(msg) for msg in messages]
                for field, messages in detail.items()
            }
        else:
            payload = {"detail": [str(detail)]}

        return Response(payload, status=status.HTTP_400_BAD_REQUEST)

    # ------------------------------------------------------------------ #
    # 2. Throttled → generic shape + retry_after  (Requirement 24.1)     #
    # ------------------------------------------------------------------ #
    if isinstance(exc, Throttled):
        wait = exc.wait  # seconds until the rate-limit window resets (float | None)
        retry_after = int(wait) if wait is not None else 0

        payload = {
            "detail": (
                exc.detail
                if exc.detail
                else "Request was throttled. Please try again later."
            ),
            "retry_after": retry_after,
        }
        response = Response(payload, status=status.HTTP_429_TOO_MANY_REQUESTS)
        response["Retry-After"] = str(retry_after)
        return response

    # ------------------------------------------------------------------ #
    # 3. AuthenticationFailed / NotAuthenticated → 401                   #
    # ------------------------------------------------------------------ #
    if isinstance(exc, (AuthenticationFailed, NotAuthenticated)):
        payload = {"detail": str(exc.detail) if exc.detail else str(exc)}
        return Response(payload, status=status.HTTP_401_UNAUTHORIZED)

    # ------------------------------------------------------------------ #
    # 4. PermissionDenied → 403                                           #
    # ------------------------------------------------------------------ #
    if isinstance(exc, PermissionDenied):
        payload = {"detail": str(exc.detail) if exc.detail else str(exc)}
        return Response(payload, status=status.HTTP_403_FORBIDDEN)

    # ------------------------------------------------------------------ #
    # 5. NotFound → 404                                                   #
    # ------------------------------------------------------------------ #
    if isinstance(exc, NotFound):
        payload = {"detail": str(exc.detail) if exc.detail else str(exc)}
        return Response(payload, status=status.HTTP_404_NOT_FOUND)

    # ------------------------------------------------------------------ #
    # 6. Other DRF APIException subclasses                                #
    # ------------------------------------------------------------------ #
    # Let the default DRF handler attempt to process any remaining DRF
    # exceptions (e.g. MethodNotAllowed, UnsupportedMediaType, etc.).
    response = drf_default_handler(exc, context)
    if response is not None:
        # Normalise whatever DRF returned to {"detail": "..."} if it isn't
        # already in that shape.
        if isinstance(response.data, dict) and "detail" not in response.data:
            # Flatten to a single detail string for non-validation errors.
            response.data = {"detail": str(response.data)}
        elif not isinstance(response.data, dict):
            response.data = {"detail": str(response.data)}
        return response

    # ------------------------------------------------------------------ #
    # 7. Bare / unhandled Exception → 500  (Requirement 24.1)            #
    # ------------------------------------------------------------------ #
    logger.exception(
        "Unhandled exception in view %s: %s",
        context.get("view", "unknown"),
        exc,
    )
    return Response(
        {"detail": "Internal server error."},
        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )
