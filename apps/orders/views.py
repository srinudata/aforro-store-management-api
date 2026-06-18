from django.db import transaction
from django.db.models import Count, F
from rest_framework import status
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.products.models import Product
from apps.stores.models import Inventory, Store

from .models import Order, OrderItem
from .serializers import (
    OrderCreateSerializer,
    OrderDetailSerializer,
    StoreOrderListSerializer,
)


class OrderCreateAPIView(APIView):
    def post(self, request):
        serializer = OrderCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        order = self._create_order(serializer.validated_data)
        output_serializer = OrderDetailSerializer(self._serialize_order(order))

        return Response(
            {
                "status": order.status,
                "order": output_serializer.data,
            },
            status=status.HTTP_201_CREATED,
        )

    @transaction.atomic
    def _create_order(self, validated_data):
        store_id = validated_data["store_id"]
        requested_items = validated_data["items"]

        try:
            store = Store.objects.select_for_update().get(pk=store_id)
        except Store.DoesNotExist as exc:
            raise ValidationError({"store_id": "Store does not exist."}) from exc

        product_ids = [item["product_id"] for item in requested_items]
        products = Product.objects.filter(pk__in=product_ids)

        if len(products) != len(set(product_ids)):
            existing_product_ids = set(products.values_list("id", flat=True))
            missing_product_ids = sorted(set(product_ids) - existing_product_ids)
            raise ValidationError(
                {
                    "items": (
                        "Products do not exist: "
                        f"{', '.join(map(str, missing_product_ids))}"
                    )
                }
            )

        requested_quantities = {}
        for item in requested_items:
            product_id = item["product_id"]
            requested_quantities[product_id] = (
                requested_quantities.get(product_id, 0) + item["quantity_requested"]
            )

        inventory_rows = {
            inventory.product_id: inventory
            for inventory in Inventory.objects.select_for_update().filter(
                store=store,
                product_id__in=requested_quantities.keys(),
            )
        }

        has_sufficient_stock = all(
            product_id in inventory_rows
            and inventory_rows[product_id].quantity >= quantity_requested
            for product_id, quantity_requested in requested_quantities.items()
        )

        order = Order.objects.create(
            store=store,
            status=(
                Order.Status.CONFIRMED
                if has_sufficient_stock
                else Order.Status.REJECTED
            ),
        )
        OrderItem.objects.bulk_create(
            OrderItem(
                order=order,
                product_id=item["product_id"],
                quantity_requested=item["quantity_requested"],
            )
            for item in requested_items
        )

        if has_sufficient_stock:
            for product_id, quantity_requested in requested_quantities.items():
                Inventory.objects.filter(
                    pk=inventory_rows[product_id].pk,
                ).update(quantity=F("quantity") - quantity_requested)

        return order

    def _serialize_order(self, order):
        order.refresh_from_db()
        return {
            "id": order.id,
            "store_id": order.store_id,
            "status": order.status,
            "created_at": order.created_at,
            "items": [
                {
                    "product_id": item.product_id,
                    "quantity_requested": item.quantity_requested,
                }
                for item in order.items.order_by("id")
            ],
        }


class StoreOrderListAPIView(APIView):
    def get(self, request, store_id):
        if not Store.objects.filter(pk=store_id).exists():
            raise NotFound("Store does not exist.")

        orders = (
            Order.objects.filter(store_id=store_id)
            .annotate(total_items=Count("items"))
            .order_by("-created_at", "-id")
        )
        serializer = StoreOrderListSerializer(orders, many=True)

        return Response(serializer.data)
