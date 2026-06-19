import random

from django.core.management.base import BaseCommand
from django.db import transaction
from faker import Faker

from apps.products.models import Category, Product
from apps.stores.models import Inventory, Store


BASE_CATEGORY_NAMES = [
    "Electronics",
    "Groceries",
    "Apparel",
    "Home & Kitchen",
    "Beauty",
    "Sports & Outdoors",
    "Toys & Games",
    "Books",
    "Automotive",
    "Health",
    "Office Supplies",
    "Pet Supplies",
    "Garden & Patio",
    "Furniture",
    "Footwear",
    "Jewelry",
    "Music & Movies",
    "Baby Products",
]

ADJECTIVES = [
    "Premium",
    "Classic",
    "Deluxe",
    "Compact",
    "Pro",
    "Eco",
    "Smart",
    "Essential",
    "Ultra",
    "Everyday",
    "Portable",
    "Heavy-Duty",
]

# Zero-stock rows make the stock filters and rejected-order path easy to test.
QUANTITY_CHOICES = [0, 0, 3, 5, 10, 12, 25, 40, 60, 100, 150, 250]


class Command(BaseCommand):
    help = "Seed categories, products, stores, and store inventory."

    category_names = BASE_CATEGORY_NAMES

    def add_arguments(self, parser):
        parser.add_argument("--categories", type=int, default=14)
        parser.add_argument("--products", type=int, default=1200)
        parser.add_argument("--stores", type=int, default=25)
        parser.add_argument(
            "--min-inventory-per-store",
            "--inventory-per-store",
            dest="inventory_per_store",
            type=int,
            default=320,
            help="Minimum number of distinct products stocked by each store.",
        )
        parser.add_argument("--seed", type=int, default=42)
        parser.add_argument(
            "--flush",
            action="store_true",
            help="Delete existing catalogue, stores, inventory, and related orders first.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        if options["flush"]:
            self.stdout.write("Deleting existing demo data...")
            Inventory.objects.all().delete()
            Product.objects.all().delete()
            Category.objects.all().delete()
            Store.objects.all().delete()

        category_count = max(options["categories"], 10)
        product_count = max(options["products"], 1000)
        store_count = max(options["stores"], 20)
        inventory_per_store = max(options["inventory_per_store"], 300)
        self.seed = options["seed"]
        self.fake = Faker()
        Faker.seed(self.seed)
        random.seed(self.seed)

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
        existing_names = set(Category.objects.values_list("name", flat=True))
        missing_count = max(0, count - Category.objects.count())
        Category.objects.bulk_create(
            [
                Category(name=name)
                for name in names
                if name not in existing_names
            ][:missing_count],
            batch_size=100,
        )

        return list(Category.objects.order_by("id")[:count])

    def _seed_products(self, count, categories):
        existing_count = Product.objects.count()
        if existing_count < count:
            products_to_create = []
            for index in range(existing_count + 1, count + 1):
                category = categories[index % len(categories)]
                products_to_create.append(
                    Product(
                        title=(
                            f"{random.choice(ADJECTIVES)} {self.fake.word().title()} "
                            f"{self.fake.word().title()} #{index}"
                        ),
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
        store_fake = Faker()
        store_fake.seed_instance(self.seed + 1)
        existing_names = set(Store.objects.values_list("name", flat=True))
        missing_count = max(0, count - Store.objects.count())
        candidates = [
            Store(
                name=f"{store_fake.company()} Store {index}",
                location=f"{store_fake.city()}, {store_fake.country()}",
            )
            for index in range(1, count + 1)
        ]
        Store.objects.bulk_create(
            [store for store in candidates if store.name not in existing_names][
                :missing_count
            ],
            batch_size=100,
        )

        return list(Store.objects.order_by("id")[:count])

    def _seed_inventory(self, stores, products, inventory_per_store):
        if inventory_per_store > len(products):
            inventory_per_store = len(products)

        product_ids = [product.id for product in products]
        inventory_to_create = []

        for store in stores:
            existing_product_ids = set(
                Inventory.objects.filter(store=store).values_list(
                    "product_id", flat=True
                )
            )
            missing_count = max(0, inventory_per_store - len(existing_product_ids))
            available_product_ids = [
                product_id
                for product_id in product_ids
                if product_id not in existing_product_ids
            ]
            store_random = random.Random(self.seed + store.id)
            selected_product_ids = store_random.sample(
                available_product_ids,
                missing_count,
            )
            for product_id in selected_product_ids:
                inventory_to_create.append(
                    Inventory(
                        store_id=store.id,
                        product_id=product_id,
                        quantity=store_random.choice(QUANTITY_CHOICES),
                    )
                )

        if inventory_to_create:
            Inventory.objects.bulk_create(inventory_to_create, batch_size=1000)

        return Inventory.objects.filter(store__in=stores).count()
