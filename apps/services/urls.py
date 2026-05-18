"""URL patterns for the services app."""

from django.urls import path

from apps.services.views import (
    AppointmentDetailView,
    BookAppointmentView,
    ServiceDetailView,
    ServiceListView,
    UserAppointmentListView,
)

urlpatterns = [
    path("services", ServiceListView.as_view(), name="service-list"),
    path("services/<str:pk>", ServiceDetailView.as_view(), name="service-detail"),
    path("appointments/book", BookAppointmentView.as_view(), name="appointment-book"),
    path("appointments/user", UserAppointmentListView.as_view(), name="appointment-user-list"),
    path("appointments/<int:pk>", AppointmentDetailView.as_view(), name="appointment-detail"),
]
