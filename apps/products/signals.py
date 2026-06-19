from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from apps.cache_utils import clear_product_cache
from apps.stores.models import Inventory

from .models import Category, Product


@receiver([post_save, post_delete], sender=Product)
@receiver([post_save, post_delete], sender=Category)
@receiver([post_save, post_delete], sender=Inventory)
def clear_cached_product_reads(**kwargs):
    clear_product_cache()
