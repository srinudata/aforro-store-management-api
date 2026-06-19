from decimal import Decimal
from unittest.mock import patch

import pytest
from rest_framework.test import APIClient

from apps.products.models import Category, Product
from apps.stores.models import Inventory, Store


@pytest.mark.django_db
def test_product_search_filters_by_keyword_store_and_stock():
    category = Category.objects.create(name="Beverages")
    juice = Product.objects.create(
        title="Orange Juice",
        description="Freshly squeezed",
        price=Decimal("3.50"),
        category=category,
    )
    soda = Product.objects.create(
        title="Orange Soda",
        description="Sparkling drink",
        price=Decimal("2.25"),
        category=category,
    )
    store = Store.objects.create(name="Main Store", location="Chennai")
    Inventory.objects.create(store=store, product=juice, quantity=4)
    Inventory.objects.create(store=store, product=soda, quantity=0)

    with patch("apps.search.views.cache") as cache:
        cache.get.return_value = None
        response = APIClient().get(
            "/api/search/products/",
            {"q": "orange", "store_id": store.id, "in_stock": "true"},
        )

    assert response.status_code == 200
    assert response.data["count"] == 1
    assert response.data["results"][0]["id"] == juice.id
    assert response.data["results"][0]["inventory_quantity"] == 4
    cache.set.assert_called_once()


@pytest.mark.django_db
def test_product_search_rejects_invalid_price_filter():
    with patch("apps.search.views.cache") as cache:
        cache.get.return_value = None
        response = APIClient().get(
            "/api/search/products/", {"min_price": "not-a-number"}
        )

    assert response.status_code == 400
    assert response.data["min_price"] == "Must be a valid number."


@pytest.mark.django_db
def test_product_suggestions_return_matching_titles_in_order():
    category = Category.objects.create(name="Beverages")
    for title in ("Orange Soda", "Blood Orange Juice", "Orange Juice"):
        Product.objects.create(
            title=title,
            description="",
            price=Decimal("2.00"),
            category=category,
        )

    with patch("apps.search.views.cache") as cache:
        cache.get.return_value = None
        response = APIClient().get("/api/search/suggest/", {"q": "ora"})

    assert response.status_code == 200
    assert response.data["results"] == [
        "Orange Juice",
        "Orange Soda",
        "Blood Orange Juice",
    ]


@pytest.mark.django_db
def test_product_suggestions_require_three_characters():
    response = APIClient().get("/api/search/suggest/", {"q": "or"})

    assert response.status_code == 400
    assert response.data["q"] == "Minimum 3 characters required."
