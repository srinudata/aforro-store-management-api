from django.urls import path

from .views import OrderCreateAPIView, StoreOrderListAPIView


urlpatterns = [
    path("orders/", OrderCreateAPIView.as_view(), name="order-create"),
    path(
        "stores/<int:store_id>/orders/",
        StoreOrderListAPIView.as_view(),
        name="store-order-list",
    ),
]
