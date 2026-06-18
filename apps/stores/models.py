from django.db import models


class Store(models.Model):
    name = models.CharField(max_length=255)
    location = models.CharField(max_length=255)

    def __str__(self):
        return self.name


class Inventory(models.Model):
    store = models.ForeignKey(
        Store,
        on_delete=models.CASCADE,
        related_name="inventory",
    )
    product = models.ForeignKey(
        "products.Product",
        on_delete=models.CASCADE,
        related_name="inventory",
    )
    quantity = models.PositiveIntegerField()

    class Meta:
        verbose_name_plural = "inventory"
        constraints = [
            models.UniqueConstraint(
                fields=["store", "product"],
                name="unique_inventory_product_per_store",
            ),
        ]

    def __str__(self):
        return f"{self.store} - {self.product}"
