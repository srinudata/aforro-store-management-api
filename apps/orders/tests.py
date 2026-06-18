from decimal import Decimal

from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from rest_framework import status
from rest_framework.test import APIClient

from apps.orders.models import Order
from apps.products.models import Category, Product
from apps.stores.models import Inventory, Store


class OrderCreateAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.category = Category.objects.create(name="Groceries")
        self.store = Store.objects.create(name="Main Store", location="Downtown")
        self.product = Product.objects.create(
            title="Rice",
            description="",
            price=Decimal("10.00"),
            category=self.category,
        )
        self.other_product = Product.objects.create(
            title="Beans",
            description="",
            price=Decimal("5.00"),
            category=self.category,
        )
        Inventory.objects.create(
            store=self.store,
            product=self.product,
            quantity=10,
        )

    def test_confirmed_order_deducts_stock(self):
        response = self.client.post(
            "/orders/",
            {
                "store_id": self.store.id,
                "items": [
                    {
                        "product_id": self.product.id,
                        "quantity_requested": 3,
                    },
                ],
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["status"], Order.Status.CONFIRMED)
        self.assertEqual(response.data["order"]["status"], Order.Status.CONFIRMED)
        self.assertEqual(response.data["order"]["store_id"], self.store.id)
        self.assertEqual(len(response.data["order"]["items"]), 1)

        order = Order.objects.get()
        self.assertEqual(order.status, Order.Status.CONFIRMED)
        self.assertEqual(order.items.count(), 1)

        inventory = Inventory.objects.get(store=self.store, product=self.product)
        self.assertEqual(inventory.quantity, 7)

    def test_rejected_order_does_not_deduct_stock(self):
        response = self.client.post(
            "/orders/",
            {
                "store_id": self.store.id,
                "items": [
                    {
                        "product_id": self.product.id,
                        "quantity_requested": 11,
                    },
                    {
                        "product_id": self.other_product.id,
                        "quantity_requested": 1,
                    },
                ],
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["status"], Order.Status.REJECTED)
        self.assertEqual(response.data["order"]["status"], Order.Status.REJECTED)
        self.assertEqual(len(response.data["order"]["items"]), 2)

        order = Order.objects.get()
        self.assertEqual(order.status, Order.Status.REJECTED)
        self.assertEqual(order.items.count(), 2)

        inventory = Inventory.objects.get(store=self.store, product=self.product)
        self.assertEqual(inventory.quantity, 10)


class StoreOrderListAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.category = Category.objects.create(name="Groceries")
        self.store = Store.objects.create(name="Main Store", location="Downtown")
        self.other_store = Store.objects.create(name="Branch Store", location="Uptown")
        self.product = Product.objects.create(
            title="Rice",
            description="",
            price=Decimal("10.00"),
            category=self.category,
        )

    def test_lists_store_orders_newest_first_with_total_items(self):
        older_order = Order.objects.create(
            store=self.store,
            status=Order.Status.CONFIRMED,
        )
        Order.objects.create(
            store=self.other_store,
            status=Order.Status.REJECTED,
        )
        newer_order = Order.objects.create(
            store=self.store,
            status=Order.Status.REJECTED,
        )
        older_order.items.create(
            product=self.product,
            quantity_requested=1,
        )
        newer_order.items.create(
            product=self.product,
            quantity_requested=2,
        )
        newer_order.items.create(
            product=self.product,
            quantity_requested=3,
        )

        response = self.client.get(f"/stores/{self.store.id}/orders/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            [order["id"] for order in response.data],
            [newer_order.id, older_order.id],
        )
        self.assertEqual(response.data[0]["status"], Order.Status.REJECTED)
        self.assertIn("created_at", response.data[0])
        self.assertEqual(response.data[0]["total_items"], 2)
        self.assertEqual(response.data[1]["total_items"], 1)

    def test_list_orders_does_not_query_per_order_for_item_counts(self):
        for _ in range(3):
            order = Order.objects.create(
                store=self.store,
                status=Order.Status.CONFIRMED,
            )
            order.items.create(
                product=self.product,
                quantity_requested=1,
            )

        with CaptureQueriesContext(connection) as queries:
            response = self.client.get(f"/stores/{self.store.id}/orders/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 3)
        self.assertEqual(len(queries), 2)

    def test_returns_404_for_missing_store(self):
        response = self.client.get("/stores/999/orders/")

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
