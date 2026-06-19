from decimal import Decimal, InvalidOperation

from django.conf import settings
from django.core.cache import cache
from django.core.paginator import EmptyPage, Paginator
from django.db.models import Case, Exists, IntegerField, OuterRef, Q, Subquery, Value, When
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.cache_utils import request_cache_key
from apps.products.models import Product
from apps.stores.models import Inventory

from .serializers import (
    ProductSearchResponseSerializer,
    ProductSearchResultSerializer,
    ProductSuggestResponseSerializer,
)


class ProductSearchAPIView(APIView):
    default_page_size = 10
    max_page_size = 100

    @extend_schema(
        parameters=[
            OpenApiParameter("q", str, description="Keyword search term."),
            OpenApiParameter("keyword", str, description="Alternative keyword parameter."),
            OpenApiParameter("category", str, description="Category id or category name."),
            OpenApiParameter("min_price", str, description="Minimum product price."),
            OpenApiParameter("max_price", str, description="Maximum product price."),
            OpenApiParameter("store_id", int, description="Filter products by store inventory."),
            OpenApiParameter("in_stock", bool, description="Filter products by stock availability."),
            OpenApiParameter(
                "sort",
                str,
                enum=["price", "-price", "newest", "relevance"],
                description="Sort by price, newest, or relevance.",
            ),
            OpenApiParameter("page", int, description="Page number."),
            OpenApiParameter("page_size", int, description="Results per page, max 100."),
        ],
        responses={
            200: ProductSearchResponseSerializer,
            400: OpenApiResponse(description="Invalid filter, sort, or pagination value."),
        },
        description="Search products with keyword matching, filters, sorting, and pagination.",
    )
    def get(self, request):
        cache_key = request_cache_key("products:search", request)
        cached_data = cache.get(cache_key)
        if cached_data is not None:
            return Response(cached_data)

        queryset = Product.objects.select_related("category")
        keyword = request.query_params.get("q") or request.query_params.get("keyword")
        category = request.query_params.get("category")
        min_price = request.query_params.get("min_price")
        max_price = request.query_params.get("max_price")
        store_id = request.query_params.get("store_id")
        in_stock = request.query_params.get("in_stock")
        sort = request.query_params.get("sort", "relevance" if keyword else "newest")

        if keyword:
            queryset = queryset.filter(
                Q(title__icontains=keyword)
                | Q(description__icontains=keyword)
                | Q(category__name__icontains=keyword)
            ).annotate(
                relevance=Case(
                    When(title__icontains=keyword, then=Value(3)),
                    When(category__name__icontains=keyword, then=Value(2)),
                    When(description__icontains=keyword, then=Value(1)),
                    default=Value(0),
                    output_field=IntegerField(),
                )
            )
        else:
            queryset = queryset.annotate(relevance=Value(0, output_field=IntegerField()))

        if category:
            queryset = self._filter_category(queryset, category)

        if min_price:
            queryset = queryset.filter(price__gte=self._decimal_filter("min_price", min_price))

        if max_price:
            queryset = queryset.filter(price__lte=self._decimal_filter("max_price", max_price))

        if store_id:
            store_id = self._integer_filter("store_id", store_id)
            store_inventory = Inventory.objects.filter(
                store_id=store_id,
                product_id=OuterRef("pk"),
            )
            queryset = queryset.filter(Exists(store_inventory)).annotate(
                inventory_quantity=Subquery(store_inventory.values("quantity")[:1])
            )
        elif in_stock is not None:
            in_stock_value = self._boolean_filter("in_stock", in_stock)
            any_stock = Inventory.objects.filter(product_id=OuterRef("pk"), quantity__gt=0)
            if in_stock_value:
                queryset = queryset.filter(Exists(any_stock))
            else:
                queryset = queryset.filter(~Exists(any_stock))

        if in_stock is not None and store_id:
            in_stock_value = self._boolean_filter("in_stock", in_stock)
            if in_stock_value:
                queryset = queryset.filter(inventory_quantity__gt=0)
            else:
                queryset = queryset.filter(inventory_quantity=0)

        queryset = self._sort_queryset(queryset, sort)
        response_data = self._paginated_response(request, queryset)
        cache.set(cache_key, response_data, settings.CACHE_TTL_SECONDS)
        return Response(response_data)

    def _filter_category(self, queryset, category):
        if category.isdigit():
            return queryset.filter(category_id=int(category))
        return queryset.filter(category__name__icontains=category)

    def _decimal_filter(self, name, value):
        try:
            return Decimal(value)
        except (InvalidOperation, ValueError) as exc:
            raise ValidationError({name: "Must be a valid number."}) from exc

    def _integer_filter(self, name, value):
        try:
            return int(value)
        except ValueError as exc:
            raise ValidationError({name: "Must be a valid integer."}) from exc

    def _boolean_filter(self, name, value):
        normalized = value.lower()
        if normalized in {"true", "1", "yes"}:
            return True
        if normalized in {"false", "0", "no"}:
            return False
        raise ValidationError({name: "Must be true or false."})

    def _sort_queryset(self, queryset, sort):
        sort_options = {
            "price": ("price", "id"),
            "-price": ("-price", "id"),
            "newest": ("-created_at", "-id"),
            "relevance": ("-relevance", "-created_at", "-id"),
        }
        if sort not in sort_options:
            raise ValidationError(
                {"sort": "Must be one of: price, -price, newest, relevance."}
            )
        return queryset.order_by(*sort_options[sort])

    def _paginated_response(self, request, queryset):
        page_number = self._integer_filter("page", request.query_params.get("page", "1"))
        page_size = self._integer_filter(
            "page_size",
            request.query_params.get("page_size", str(self.default_page_size)),
        )
        page_size = min(page_size, self.max_page_size)

        if page_number < 1:
            raise ValidationError({"page": "Must be greater than 0."})
        if page_size < 1:
            raise ValidationError({"page_size": "Must be greater than 0."})

        paginator = Paginator(queryset, page_size)
        try:
            page = paginator.page(page_number)
        except EmptyPage:
            page = paginator.page(paginator.num_pages or 1)

        return {
            "count": paginator.count,
            "page": page.number,
            "page_size": page_size,
            "total_pages": paginator.num_pages,
            "next": self._page_url(request, page.next_page_number())
            if page.has_next()
            else None,
            "previous": self._page_url(request, page.previous_page_number())
            if page.has_previous()
            else None,
            "results": ProductSearchResultSerializer(page.object_list, many=True).data,
        }

    def _page_url(self, request, page_number):
        query_params = request.query_params.copy()
        query_params["page"] = page_number
        return request.build_absolute_uri(f"{request.path}?{query_params.urlencode()}")


class ProductSuggestAPIView(APIView):
    @extend_schema(
        parameters=[
            OpenApiParameter(
                "q",
                str,
                required=True,
                description="Autocomplete query. Minimum 3 characters.",
            ),
        ],
        responses={
            200: ProductSuggestResponseSerializer,
            400: OpenApiResponse(description="Query must contain at least 3 characters."),
        },
        description="Return up to 10 product title suggestions.",
    )
    def get(self, request):
        keyword = (request.query_params.get("q") or "").strip()
        if len(keyword) < 3:
            raise ValidationError({"q": "Minimum 3 characters required."})

        cache_key = request_cache_key("products:suggest", request)
        cached_data = cache.get(cache_key)
        if cached_data is not None:
            return Response(cached_data)

        suggestions = (
            Product.objects.filter(title__icontains=keyword)
            .annotate(
                match_rank=Case(
                    When(title__istartswith=keyword, then=Value(0)),
                    default=Value(1),
                    output_field=IntegerField(),
                )
            )
            .order_by("match_rank", "title", "id")
            .values_list("title", flat=True)[:10]
        )

        response_data = {"results": list(suggestions)}
        cache.set(cache_key, response_data, settings.CACHE_TTL_SECONDS)
        return Response(response_data)
