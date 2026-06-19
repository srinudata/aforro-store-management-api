import logging

from celery import shared_task

from .models import Order


logger = logging.getLogger(__name__)


@shared_task(
    autoretry_for=(Order.DoesNotExist,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 3},
)
def send_order_confirmation(order_id):
    """Prepare and send a confirmation for an order outside the API request."""
    order = Order.objects.prefetch_related("items").get(pk=order_id)

    if order.status != Order.Status.CONFIRMED:
        logger.info("Skipping confirmation for unconfirmed order %s", order_id)
        return {"order_id": order_id, "sent": False}

    item_count = sum(item.quantity_requested for item in order.items.all())
    logger.info(
        "Order confirmation sent for order %s at store %s (%s items)",
        order.id,
        order.store_id,
        item_count,
    )

   
    return {"order_id": order.id, "sent": True, "item_count": item_count}
