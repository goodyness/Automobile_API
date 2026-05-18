"""URL patterns for the products app."""

from django.urls import path

from apps.products.views import (
    AdminProductCreateView,
    AdminProductUpdateView,
    ProductDetailView,
    ProductListView,
)

urlpatterns = [
    path("products", ProductListView.as_view(), name="product-list"),
    path("products/<str:pk>", ProductDetailView.as_view(), name="product-detail"),
]

admin_urlpatterns = [
    path("products", AdminProductCreateView.as_view(), name="admin-product-create"),
    path("products/<int:pk>", AdminProductUpdateView.as_view(), name="admin-product-update"),
]
