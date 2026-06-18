from rest_framework import serializers


class StoreInventorySerializer(serializers.Serializer):
    product_title = serializers.CharField(source="product.title")
    price = serializers.DecimalField(
        source="product.price",
        max_digits=10,
        decimal_places=2,
    )
    category_name = serializers.CharField(source="product.category.name")
    quantity = serializers.IntegerField()
