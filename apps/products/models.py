"""
Models for the products app.

Product — a spare part in the inventory catalog.

Requirements: 11.1, 13.1
"""

from django.db import models

from core.constants import CHASSIS_CHOICES


class Product(models.Model):
    """
    A spare part identified by OEM part number and chassis compatibility.
    """

    name = models.CharField(max_length=200)
    oem_number = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    stock = models.PositiveIntegerField(default=0)
    category = models.CharField(max_length=100)
    compatible_chassis = models.JSONField(
        default=list,
        help_text="List of compatible chassis codes, e.g. ['W204', 'W212'].",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return f"{self.name} ({self.oem_number})"
