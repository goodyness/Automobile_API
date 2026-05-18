"""URL patterns for the admin_tools app."""

from django.urls import path

from apps.admin_tools.views import (
    AdminAppointmentStatusView,
    AdminReportAttachView,
    AdminUserListView,
)

urlpatterns = [
    path("users", AdminUserListView.as_view(), name="admin-user-list"),
    path("appointments/<int:pk>/status", AdminAppointmentStatusView.as_view(), name="admin-appointment-status"),
    path("appointments/<int:pk>/report", AdminReportAttachView.as_view(), name="admin-appointment-report"),
]
