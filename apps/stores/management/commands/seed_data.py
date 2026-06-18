import random

from django.core.management.base import BaseCommand
from django.db import transaction
from faker import Faker

from apps.products.models import Category, Product
from apps.stores.models import Inventory, Store


class Command(BaseCommand):
    help = "Seed categories, products, stores, and store inventory."

    category_names = [
        "Groceries",
        "Beverages",
        "Snacks",
        "Personal Care",
        "Household",
        "Dairy",
        "Bakery",
        "Frozen Foods",
        "Produce",
        "Meat",
        "Seafood",
        "Pharmacy",
    ]

    def add_arguments(self, parser):
        parser.add_argument("--categories", type=int, default=12)
        parser.add_argument("--products", type=int, default=1000)
        parser.add_argument("--stores", type=int, default=20)
        parser.add_argument("--inventory-per-store", type=int, default=300)
        parser.add_argument("--seed", type=int, default=42)

    @transaction.atomic
    def handle(self, *args, **options):
        category_count = max(options["categories"], 10)
        product_count = max(options["products"], 1000)
        store_count = max(options["stores"], 20)
        inventory_per_store = max(options["inventory_per_store"], 300)
        self.fake = Faker()
        Faker.seed(options["seed"])
        random.seed(options["seed"])

        categories = self._seed_categories(category_count)
        products = self._seed_products(product_count, categories)
        stores = self._seed_stores(store_count)
        inventory_count = self._seed_inventory(stores, products, inventory_per_store)

        self.stdout.write(
            self.style.SUCCESS(
                "Seed data ready: "
                f"{len(categories)} categories, "
                f"{len(products)} products, "
                f"{len(stores)} stores, "
                f"{inventory_count} inventory rows."
            )
        )

    def _seed_categories(self, count):
        names = list(self.category_names)
        names.extend(f"Category {index}" for index in range(len(names) + 1, count + 1))

        for name in names[:count]:
            Category.objects.get_or_create(name=name)

        return list(Category.objects.order_by("id")[:count])

    def _seed_products(self, count, categories):
        existing_count = Product.objects.count()
        if existing_count < count:
            products_to_create = []
            for index in range(existing_count + 1, count + 1):
                category = categories[index % len(categories)]
                products_to_create.append(
                    Product(
                        title=f"{self.fake.catch_phrase()} {index}",
                        description=self.fake.paragraph(nb_sentences=2),
                        price=self.fake.pydecimal(
                            left_digits=3,
                            right_digits=2,
                            positive=True,
                            min_value=1,
                            max_value=999,
                        ),
                        category=category,
                    )
                )
            Product.objects.bulk_create(products_to_create, batch_size=500)

        return list(Product.objects.order_by("id")[:count])

    def _seed_stores(self, count):
        for index in range(1, count + 1):
            Store.objects.get_or_create(
                name=f"{self.fake.company()} Store {index}",
                defaults={"location": self.fake.city()},
            )

        return list(Store.objects.order_by("id")[:count])

    def _seed_inventory(self, stores, products, inventory_per_store):
        if inventory_per_store > len(products):
            inventory_per_store = len(products)

        product_ids = [product.id for product in products]
        existing_pairs = set(
            Inventory.objects.filter(store__in=stores)
            .values_list("store_id", "product_id")
        )
        inventory_to_create = []

        for store in stores:
            selected_product_ids = random.sample(product_ids, inventory_per_store)
            for product_id in selected_product_ids:
                if (store.id, product_id) in existing_pairs:
                    continue
                inventory_to_create.append(
                    Inventory(
                        store_id=store.id,
                        product_id=product_id,
                        quantity=random.randint(0, 500),
                    )
                )
                existing_pairs.add((store.id, product_id))

        if inventory_to_create:
            Inventory.objects.bulk_create(inventory_to_create, batch_size=1000)

        return Inventory.objects.filter(store__in=stores).count()
