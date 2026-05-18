"""
Unit tests for products endpoints.
Requirements: 11.1–11.5, 12.1–12.3, 13.1–13.6, 14.1–14.6
"""

import pytest
from apps.products.models import Product

PRODUCTS_URL = "/api/products"
ADMIN_PRODUCTS_URL = "/api/admin/products"


@pytest.fixture
def product(db):
    return Product.objects.create(
        name="EIS Control Unit",
        oem_number="A2095450208",
        description="Original EIS unit.",
        price="249.99",
        stock=5,
        category="Control Units",
        compatible_chassis=["W204", "W212"],
    )


# ---------------------------------------------------------------------------
# Product Catalog (Requirement 11)
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestProductList:
    def test_returns_paginated_list(self, api_client, product):
        res = api_client.get(PRODUCTS_URL)
        assert res.status_code == 200
        assert res.data["count"] >= 1
        assert "results" in res.data

    def test_filter_by_category(self, api_client, product):
        res = api_client.get(f"{PRODUCTS_URL}?category=Control Units")
        assert res.status_code == 200
        for p in res.data["results"]:
            assert p["compatible_chassis"] is not None

    def test_filter_by_chassis(self, api_client, product):
        res = api_client.get(f"{PRODUCTS_URL}?chassis=W204")
        assert res.status_code == 200
        for p in res.data["results"]:
            assert "W204" in p["compatible_chassis"]

    def test_invalid_chassis_filter_returns_400(self, api_client):
        res = api_client.get(f"{PRODUCTS_URL}?chassis=W999")
        assert res.status_code == 400


# ---------------------------------------------------------------------------
# Product Detail (Requirement 12)
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestProductDetail:
    def test_valid_id_returns_200(self, api_client, product):
        res = api_client.get(f"{PRODUCTS_URL}/{product.pk}")
        assert res.status_code == 200
        assert res.data["oem_number"] == product.oem_number

    def test_unknown_id_returns_404(self, api_client):
        res = api_client.get(f"{PRODUCTS_URL}/99999")
        assert res.status_code == 404

    def test_non_integer_id_returns_400(self, api_client):
        res = api_client.get(f"{PRODUCTS_URL}/abc")
        assert res.status_code == 400


# ---------------------------------------------------------------------------
# Admin Create Product (Requirement 13)
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestAdminCreateProduct:
    PAYLOAD = {
        "name": "New Part",
        "oem_number": "NEW123",
        "description": "A new part.",
        "price": "99.99",
        "stock": 10,
        "category": "Sensors",
        "compatible_chassis": ["W204"],
    }

    def test_admin_can_create(self, admin_client):
        res = admin_client.post(ADMIN_PRODUCTS_URL, self.PAYLOAD, format="json")
        assert res.status_code == 201
        assert res.data["oem_number"] == "NEW123"

    def test_non_admin_gets_403(self, auth_client):
        res = auth_client.post(ADMIN_PRODUCTS_URL, self.PAYLOAD, format="json")
        assert res.status_code == 403

    def test_unauthenticated_gets_401(self, api_client):
        res = api_client.post(ADMIN_PRODUCTS_URL, self.PAYLOAD, format="json")
        assert res.status_code == 401

    def test_missing_field_returns_400(self, admin_client):
        res = admin_client.post(ADMIN_PRODUCTS_URL, {"name": "X"}, format="json")
        assert res.status_code == 400

    def test_duplicate_oem_returns_400(self, admin_client, product):
        payload = {**self.PAYLOAD, "oem_number": product.oem_number}
        res = admin_client.post(ADMIN_PRODUCTS_URL, payload, format="json")
        assert res.status_code == 400

    def test_negative_price_returns_400(self, admin_client):
        payload = {**self.PAYLOAD, "price": "-1.00", "oem_number": "UNIQUE999"}
        res = admin_client.post(ADMIN_PRODUCTS_URL, payload, format="json")
        assert res.status_code == 400


# ---------------------------------------------------------------------------
# Admin Update Product (Requirement 14)
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestAdminUpdateProduct:
    def test_admin_can_update_stock(self, admin_client, product):
        res = admin_client.patch(
            f"{ADMIN_PRODUCTS_URL}/{product.pk}", {"stock": 20}, format="json"
        )
        assert res.status_code == 200
        assert res.data["stock"] == 20

    def test_non_admin_gets_403(self, auth_client, product):
        res = auth_client.patch(
            f"{ADMIN_PRODUCTS_URL}/{product.pk}", {"stock": 20}, format="json"
        )
        assert res.status_code == 403

    def test_unauthenticated_gets_401(self, api_client, product):
        res = api_client.patch(
            f"{ADMIN_PRODUCTS_URL}/{product.pk}", {"stock": 20}, format="json"
        )
        assert res.status_code == 401

    def test_unknown_id_returns_404(self, admin_client):
        res = admin_client.patch(
            f"{ADMIN_PRODUCTS_URL}/99999", {"stock": 5}, format="json"
        )
        assert res.status_code == 404

    def test_negative_stock_returns_400(self, admin_client, product):
        res = admin_client.patch(
            f"{ADMIN_PRODUCTS_URL}/{product.pk}", {"stock": -1}, format="json"
        )
        assert res.status_code == 400

    def test_duplicate_oem_on_update_returns_400(self, admin_client, product):
        other = Product.objects.create(
            name="Other", oem_number="OTHER001", price="10.00",
            stock=1, category="X", compatible_chassis=["W204"],
        )
        res = admin_client.patch(
            f"{ADMIN_PRODUCTS_URL}/{other.pk}",
            {"oem_number": product.oem_number},
            format="json",
        )
        assert res.status_code == 400
