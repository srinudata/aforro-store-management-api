from django.conf import settings
from django.core.cache import cache
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.cache_utils import request_cache_key

from .models import Product
from .serializers import ProductListSerializer


class ProductListAPIView(APIView):
    @extend_schema(
        responses={
            200: ProductListSerializer(many=True),
            400: OpenApiResponse(description="Invalid request."),
        },
        description="List products that customers can use to place orders.",
    )
    def get(self, request):
        cache_key = request_cache_key("products:list", request)
        cached_data = cache.get(cache_key)
        if cached_data is not None:
            return Response(cached_data)

        products = Product.objects.select_related("category").order_by("-created_at", "-id")
        serializer = ProductListSerializer(products, many=True)
        cache.set(cache_key, serializer.data, settings.CACHE_TTL_SECONDS)

        return Response(serializer.data)
