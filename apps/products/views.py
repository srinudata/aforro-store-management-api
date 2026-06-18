from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework.response import Response
from rest_framework.views import APIView

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
        products = Product.objects.select_related("category").order_by("-created_at", "-id")
        serializer = ProductListSerializer(products, many=True)

        return Response(serializer.data)
