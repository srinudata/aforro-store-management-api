from django.urls import path

from .views import StoreInventoryListAPIView


urlpatterns = [
    path(
        "stores/<int:store_id>/inventory/",
        StoreInventoryListAPIView.as_view(),
        name="store-inventory-list",
    ),
]
