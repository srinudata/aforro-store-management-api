from rest_framework import serializers


class ProductSearchResultSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    title = serializers.CharField()
    description = serializers.CharField()
    price = serializers.DecimalField(max_digits=10, decimal_places=2)
    category = serializers.CharField(source="category.name")
    inventory_quantity = serializers.IntegerField(required=False)
