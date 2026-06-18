from django.urls import path

from .views import ProductSearchAPIView, ProductSuggestAPIView


urlpatterns = [
    path("api/search/products/", ProductSearchAPIView.as_view(), name="product-search"),
    path("api/search/suggest/", ProductSuggestAPIView.as_view(), name="product-suggest"),
]
