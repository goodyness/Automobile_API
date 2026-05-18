"""Serializers for the products app."""

from decimal import Decimal

from rest_framework import serializers

from apps.products.models import Product
from core.constants import VALID_CHASSIS_CODES


class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = [
            "id", "name", "oem_number", "description",
            "price", "stock", "category", "compatible_chassis",
        ]


class ProductListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = ["id", "name", "oem_number", "price", "stock", "compatible_chassis"]


class ProductWriteSerializer(serializers.ModelSerializer):
    """Used for admin create and update operations."""

    class Meta:
        model = Product
        fields = [
            "name", "oem_number", "description",
            "price", "stock", "category", "compatible_chassis",
        ]

    def validate_price(self, value):
        if value < Decimal("0.01"):
            raise serializers.ValidationError("Price must be at least 0.01.")
        return value

    def validate_stock(self, value):
        if value < 0:
            raise serializers.ValidationError("Stock must be 0 or greater.")
        return value

    def validate_name(self, value):
        if len(value) > 200:
            raise serializers.ValidationError("Name must not exceed 200 characters.")
        return value

    def validate_compatible_chassis(self, value):
        for code in value:
            if code not in VALID_CHASSIS_CODES:
                raise serializers.ValidationError(
                    f"'{code}' is not a recognized chassis type."
                )
        return value

    def validate_oem_number(self, value):
        qs = Product.objects.filter(oem_number=value)
        # On update, exclude the current instance
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError(
                f"A product with OEM number '{value}' already exists."
            )
        return value
