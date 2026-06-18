from rest_framework.exceptions import NotFound
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Inventory, Store
from .serializers import StoreInventorySerializer


class StoreInventoryListAPIView(APIView):
    def get(self, request, store_id):
        if not Store.objects.filter(pk=store_id).exists():
            raise NotFound("Store does not exist.")

        inventory = (
            Inventory.objects.filter(store_id=store_id)
            .select_related("product", "product__category")
            .order_by("product__title", "id")
        )
        serializer = StoreInventorySerializer(inventory, many=True)

        return Response(serializer.data)
