from rest_framework import serializers


class OrderItemInputSerializer(serializers.Serializer):
    product_id = serializers.IntegerField(min_value=1)
    quantity_requested = serializers.IntegerField(min_value=1)


class OrderCreateSerializer(serializers.Serializer):
    store_id = serializers.IntegerField(min_value=1)
    items = OrderItemInputSerializer(many=True, allow_empty=False)


class OrderItemDetailSerializer(serializers.Serializer):
    product_id = serializers.IntegerField()
    quantity_requested = serializers.IntegerField()


class OrderDetailSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    store_id = serializers.IntegerField()
    status = serializers.CharField()
    created_at = serializers.DateTimeField()
    items = OrderItemDetailSerializer(many=True)


class StoreOrderListSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    status = serializers.CharField()
    created_at = serializers.DateTimeField()
    total_items = serializers.IntegerField()
