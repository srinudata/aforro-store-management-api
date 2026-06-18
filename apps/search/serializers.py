from rest_framework import serializers


class ProductSearchResultSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    title = serializers.CharField()
    description = serializers.CharField()
    price = serializers.DecimalField(max_digits=10, decimal_places=2)
    category = serializers.CharField(source="category.name")
    inventory_quantity = serializers.IntegerField(required=False)


class ProductSearchResponseSerializer(serializers.Serializer):
    count = serializers.IntegerField()
    page = serializers.IntegerField()
    page_size = serializers.IntegerField()
    total_pages = serializers.IntegerField()
    next = serializers.URLField(allow_null=True)
    previous = serializers.URLField(allow_null=True)
    results = ProductSearchResultSerializer(many=True)


class ProductSuggestResponseSerializer(serializers.Serializer):
    results = serializers.ListField(child=serializers.CharField())
