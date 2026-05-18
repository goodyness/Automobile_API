"""
Views for the products app.

Endpoints:
  GET   /api/products              — Requirement 11
  GET   /api/products/:id          — Requirement 12
  POST  /api/admin/products        — Requirement 13
  PATCH /api/admin/products/:id    — Requirement 14
"""

from rest_framework import generics, status
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from apps.products.models import Product
from apps.products.serializers import (
    ProductListSerializer,
    ProductSerializer,
    ProductWriteSerializer,
)
from core.constants import VALID_CHASSIS_CODES
from core.pagination import StandardPagination
from core.permissions import IsAdminUser


class ProductListView(generics.ListAPIView):
    """GET /api/products — Requirements 11.1–11.5"""

    serializer_class = ProductListSerializer
    permission_classes = [AllowAny]
    pagination_class = StandardPagination

    def get_queryset(self):
        qs = Product.objects.all()
        category = self.request.query_params.get("category")
        chassis = self.request.query_params.get("chassis")

        if chassis:
            if chassis not in VALID_CHASSIS_CODES:
                raise ValidationError(
                    {"chassis": [f"'{chassis}' is not a recognized chassis type."]}
                )
            # SQLite doesn't support JSONField __contains lookup;
            # filter in Python after fetching all products.
            qs = [p for p in qs if chassis in (p.compatible_chassis or [])]
            from django.db.models import QuerySet
            if not isinstance(qs, QuerySet):
                # Re-wrap as a queryset using pk__in for pagination compatibility
                from apps.products.models import Product as _Product
                pks = [p.pk for p in qs]
                qs = _Product.objects.filter(pk__in=pks)

        if category:
            # Validate category exists in DB
            if not Product.objects.filter(category=category).exists():
                raise ValidationError(
                    {"category": [f"'{category}' is not a recognized category."]}
                )
            qs = qs.filter(category=category)

        return qs


class ProductDetailView(generics.RetrieveAPIView):
    """GET /api/products/:id — Requirements 12.1–12.3"""

    serializer_class = ProductSerializer
    permission_classes = [AllowAny]

    def get_object(self):
        pk = self.kwargs.get("pk")
        try:
            pk = int(pk)
        except (TypeError, ValueError):
            raise ValidationError({"detail": "Product ID must be an integer."})

        try:
            return Product.objects.get(pk=pk)
        except Product.DoesNotExist:
            raise NotFound(f"Product with id {pk} not found.")


class AdminProductCreateView(generics.CreateAPIView):
    """POST /api/admin/products — Requirements 13.1–13.6"""

    serializer_class = ProductWriteSerializer
    permission_classes = [IsAdminUser]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        product = serializer.save()
        return Response(
            ProductSerializer(product).data,
            status=status.HTTP_201_CREATED,
        )


class AdminProductUpdateView(generics.UpdateAPIView):
    """PATCH /api/admin/products/:id — Requirements 14.1–14.6"""

    serializer_class = ProductWriteSerializer
    permission_classes = [IsAdminUser]
    http_method_names = ["patch"]

    def get_object(self):
        pk = self.kwargs.get("pk")
        try:
            return Product.objects.get(pk=pk)
        except Product.DoesNotExist:
            raise NotFound(f"Product with id {pk} not found.")

    def partial_update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        product = serializer.save()
        return Response(ProductSerializer(product).data)
