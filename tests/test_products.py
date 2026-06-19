from decimal import Decimal
from unittest.mock import patch

import pytest
from rest_framework.test import APIClient

from apps.products.models import Category, Product


@pytest.mark.django_db
def test_product_list_returns_products():
    category = Category.objects.create(name="Beverages")
    product = Product.objects.create(
        title="Orange Juice",
        description="Fresh orange juice",
        price=Decimal("3.50"),
        category=category,
    )

    with patch("apps.products.views.cache") as cache:
        cache.get.return_value = None
        response = APIClient().get("/api/products/")

    assert response.status_code == 200
    assert len(response.data) == 1
    assert response.data[0]["id"] == product.id
    assert response.data[0]["title"] == "Orange Juice"
    assert response.data[0]["description"] == "Fresh orange juice"
    assert response.data[0]["price"] == "3.50"
    assert response.data[0]["category"] == "Beverages"
    assert "created_at" in response.data[0]
    cache.set.assert_called_once()
