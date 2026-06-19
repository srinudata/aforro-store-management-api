from decimal import Decimal
from unittest.mock import patch

import pytest
from rest_framework.test import APIClient

from apps.orders.models import Order
from apps.products.models import Category, Product
from apps.stores.models import Inventory, Store


@pytest.mark.django_db(transaction=True)
def test_create_confirmed_order_reduces_stock_and_queues_confirmation():
    category = Category.objects.create(name="Groceries")
    product = Product.objects.create(
        title="Rice",
        description="1 kg bag",
        price=Decimal("4.99"),
        category=category,
    )
    store = Store.objects.create(name="Main Store", location="Chennai")
    inventory = Inventory.objects.create(
        store=store,
        product=product,
        quantity=10,
    )

    payload = {
        "store_id": store.id,
        "items": [{"product_id": product.id, "quantity_requested": 3}],
    }

    with patch("apps.orders.views.send_order_confirmation.delay") as delay:
        response = APIClient().post("/orders/", payload, format="json")

    assert response.status_code == 201
    assert response.data["status"] == Order.Status.CONFIRMED

    inventory.refresh_from_db()
    assert inventory.quantity == 7

    order = Order.objects.get()
    delay.assert_called_once_with(order.id)
