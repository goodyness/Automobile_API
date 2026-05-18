"""
Root URL configuration for the Automobile Backend API.

All API routes are prefixed with /api/.
"""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

# CMS admin URL patterns (imported separately to avoid circular imports)
from apps.cms.urls import admin_urlpatterns as cms_admin_urlpatterns
from apps.products.urls import admin_urlpatterns as products_admin_urlpatterns

urlpatterns = [
    # Django admin panel
    path("django-admin/", admin.site.urls),

    # Authentication endpoints — /api/auth/...
    path("api/auth/", include("apps.authentication.urls")),

    # Services & Appointments — /api/services/..., /api/appointments/...
    path("api/", include("apps.services.urls")),

    # Products catalog — /api/products/...
    path("api/", include("apps.products.urls")),

    # CMS — /api/news/..., /api/media/...
    path("api/", include("apps.cms.urls")),

    # Admin tools — /api/admin/users, /api/admin/appointments/...
    path("api/admin/", include("apps.admin_tools.urls")),

    # Admin-only product endpoints — /api/admin/products/...
    path("api/admin/", include((products_admin_urlpatterns, "admin_products"))),

    # Admin-only CMS endpoints — /api/admin/news, /api/admin/media/upload
    path("api/admin/", include((cms_admin_urlpatterns, "admin_cms"))),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
