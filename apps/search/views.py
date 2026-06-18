from decimal import Decimal, InvalidOperation

from django.core.paginator import EmptyPage, Paginator
from django.db.models import Case, Exists, IntegerField, OuterRef, Q, Subquery, Value, When
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.products.models import Product
from apps.stores.models import Inventory

from .serializers import ProductSearchResultSerializer


class ProductSearchAPIView(APIView):
    default_page_size = 10
    max_page_size = 100

    def get(self, request):
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
        return Response(self._paginated_response(request, queryset))

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
