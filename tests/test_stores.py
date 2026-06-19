from decimal import Decimal

import pytest
from rest_framework.test import APIClient

from apps.products.models import Category, Product
from apps.stores.models import Inventory, Store


@pytest.mark.django_db
def test_store_inventory_returns_items_sorted_by_product_title():
    category = Category.objects.create(name="Groceries")
    store = Store.objects.create(name="Main Store", location="Chennai")
    rice = Product.objects.create(
        title="Rice",
        description="1 kg bag",
        price=Decimal("4.99"),
        category=category,
    )
    apples = Product.objects.create(
        title="Apples",
        description="Fresh fruit",
        price=Decimal("2.50"),
        category=category,
    )
    Inventory.objects.create(store=store, product=rice, quantity=7)
    Inventory.objects.create(store=store, product=apples, quantity=3)

    response = APIClient().get(f"/stores/{store.id}/inventory/")

    assert response.status_code == 200
    assert response.data == [
        {
            "product_title": "Apples",
            "price": "2.50",
            "category_name": "Groceries",
            "quantity": 3,
        },
        {
            "product_title": "Rice",
            "price": "4.99",
            "category_name": "Groceries",
            "quantity": 7,
        },
    ]


@pytest.mark.django_db
def test_store_inventory_returns_404_for_unknown_store():
    response = APIClient().get("/stores/99999/inventory/")

    assert response.status_code == 404
    assert response.data["detail"] == "Store does not exist."
