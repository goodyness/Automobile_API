from rest_framework.permissions import BasePermission


class IsAdminUser(BasePermission):
    """
    Grants access only to authenticated users who are staff members.

    Used by all admin-only endpoints (Requirements 13.2, 14.2, 18.2,
    19.2, 20.2, 21.3, 22.2).  Non-staff authenticated users receive a
    403 response; unauthenticated requests receive a 401 response via
    the standard DRF authentication layer.
    """

    def has_permission(self, request, view) -> bool:
        return bool(request.user and request.user.is_authenticated and request.user.is_staff)
