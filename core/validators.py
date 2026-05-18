"""
Shared validators for the Automobile Backend API.

Requirements: 1.6, 8.5, 19.4, 19.5, 22.4
"""

import re

from rest_framework.exceptions import ValidationError

from core.constants import (
    ALLOWED_IMAGE_MIME_TYPES,
    ALLOWED_REPORT_MIME_TYPES,
    MAX_IMAGE_SIZE_BYTES,
    MAX_REPORT_SIZE_BYTES,
    VALID_CHASSIS_CODES,
)

# ---------------------------------------------------------------------------
# MIME detection — prefer python-magic (magic bytes), fall back to
# InMemoryUploadedFile.content_type when python-magic is not installed.
# ---------------------------------------------------------------------------
try:
    import magic as _magic  # type: ignore

    def _detect_mime(file) -> str:
        """Read the first 2 KB and detect MIME type via magic bytes."""
        header = file.read(2048)
        file.seek(0)
        return _magic.from_buffer(header, mime=True)

except ImportError:  # pragma: no cover
    def _detect_mime(file) -> str:  # type: ignore[misc]
        """Fallback: trust the Content-Type reported by the upload."""
        return getattr(file, "content_type", "application/octet-stream")


# ---------------------------------------------------------------------------
# Password strength validator
# ---------------------------------------------------------------------------

def validate_password_strength(value: str) -> str:
    """
    Enforce password strength rules:
      - Minimum 8 characters
      - At least one uppercase letter (A-Z)
      - At least one digit (0-9)

    Raises ValidationError on failure.
    Requirement: 1.6
    """
    errors = []

    if len(value) < 8:
        errors.append("Password must be at least 8 characters long.")

    if not re.search(r"[A-Z]", value):
        errors.append("Password must contain at least one uppercase letter.")

    if not re.search(r"\d", value):
        errors.append("Password must contain at least one digit.")

    if errors:
        raise ValidationError(errors)

    return value


# ---------------------------------------------------------------------------
# Chassis validator
# ---------------------------------------------------------------------------

def validate_chassis(value: str) -> str:
    """
    Ensure the chassis code is in the system's supported list.

    Raises ValidationError on failure.
    Requirement: 8.5
    """
    if value not in VALID_CHASSIS_CODES:
        raise ValidationError(
            f"'{value}' is not a recognized chassis type. "
            f"Valid values are: {', '.join(VALID_CHASSIS_CODES)}."
        )
    return value


# ---------------------------------------------------------------------------
# Image file validator
# ---------------------------------------------------------------------------

def validate_image_file(file) -> None:
    """
    Validate that an uploaded file is an acceptable image:
      - MIME type must be image/jpeg, image/png, or image/webp
      - File size must not exceed 10 MB

    Uses python-magic for MIME detection when available; falls back to
    the Content-Type header otherwise.

    Raises ValidationError on failure.
    Requirements: 19.4, 19.5
    """
    # Size check first (cheap)
    file_size = file.size if hasattr(file, "size") else len(file.read())
    if hasattr(file, "seek"):
        file.seek(0)

    if file_size > MAX_IMAGE_SIZE_BYTES:
        raise ValidationError(
            f"File size exceeds the 10 MB limit. "
            f"Uploaded file is {file_size / (1024 * 1024):.1f} MB."
        )

    # MIME type check
    mime_type = _detect_mime(file)
    if mime_type not in ALLOWED_IMAGE_MIME_TYPES:
        raise ValidationError(
            f"Unsupported file type '{mime_type}'. "
            f"Accepted types: {', '.join(sorted(ALLOWED_IMAGE_MIME_TYPES))}."
        )


# ---------------------------------------------------------------------------
# Report file validator
# ---------------------------------------------------------------------------

def validate_report_file(file) -> None:
    """
    Validate that an uploaded file is an acceptable diagnostic report:
      - MIME type must be application/pdf, application/octet-stream,
        or application/x-binary
      - File size must not exceed 20 MB

    Raises ValidationError on failure.
    Requirements: 22.4
    """
    # Size check first (cheap)
    file_size = file.size if hasattr(file, "size") else len(file.read())
    if hasattr(file, "seek"):
        file.seek(0)

    if file_size > MAX_REPORT_SIZE_BYTES:
        raise ValidationError(
            f"File size exceeds the 20 MB limit. "
            f"Uploaded file is {file_size / (1024 * 1024):.1f} MB."
        )

    # MIME type check
    mime_type = _detect_mime(file)
    if mime_type not in ALLOWED_REPORT_MIME_TYPES:
        raise ValidationError(
            f"Unsupported file type '{mime_type}'. "
            f"Accepted types: {', '.join(sorted(ALLOWED_REPORT_MIME_TYPES))}."
        )
