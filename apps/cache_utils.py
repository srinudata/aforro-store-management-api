from hashlib import sha256
from urllib.parse import urlencode

from django.core.cache import cache


def request_cache_key(prefix, request):
    query_items = []
    for key in sorted(request.query_params):
        for value in sorted(request.query_params.getlist(key)):
            query_items.append((key, value))

    normalized_url = "{}://{}{}?{}".format(
        request.scheme,
        request.get_host(),
        request.path,
        urlencode(query_items, doseq=True),
    )
    digest = sha256(normalized_url.encode("utf-8")).hexdigest()
    return f"{prefix}:{digest}"


def clear_product_cache():
    delete_pattern = getattr(cache, "delete_pattern", None)
    if delete_pattern:
        delete_pattern("products:*")
