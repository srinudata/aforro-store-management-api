# Store and Ordering API

This is a small store and ordering API built with Django REST Framework. It lets you browse and search products, check what a store has in stock, and place orders.

The project uses PostgreSQL for its data and Redis to cache product and search results. There is also a Swagger page where you can explore and test the API from your browser.

## Features

- Product listing, keyword search, filtering, sorting, and pagination
- Product autocomplete suggestions
- Per-store inventory and stock availability
- Atomic order creation with stock validation and deduction
- Store order history
- Redis-backed response caching with automatic product-cache invalidation
- Celery order-confirmation task for confirmed orders
- OpenAPI schema and interactive Swagger documentation
- API tests for products, search, stores, and orders

## Tech stack

- Python 3.12 and Django 5.2
- Django REST Framework
- PostgreSQL 16
- Redis 7
- Celery 5
- drf-spectacular / OpenAPI
- Docker Compose

## Getting started with Docker

Docker Desktop (or Docker Engine with Compose) is the only prerequisite for this route. From the project root, run:

```bash
docker compose up --build -d
docker compose exec web python manage.py migrate
docker compose exec web python manage.py seed_data
```

Once everything is running, open <http://localhost:8000/api/docs/> to view and test the API. The server itself runs at <http://localhost:8000>.

To stop the services:

```bash
docker compose down
```

If you also want to delete the saved PostgreSQL and Redis data, use `docker compose down -v`.

## Local development

Prefer to run it without Docker? Install Python 3.12 and make sure PostgreSQL and Redis are running first. Then create a virtual environment and install the dependencies:

```bash
python -m venv .venv
# Windows PowerShell
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Copy `.env.example` to `.env`, then adjust the values if your local services use different credentials:

```powershell
Copy-Item .env.example .env
```

You can configure the project with the following environment variables. These are also the default values used during local development:

```env
POSTGRES_DB=aforro
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
REDIS_URL=redis://localhost:6379/1
CACHE_TTL_SECONDS=300
CELERY_BROKER_URL=redis://localhost:6379/1
CELERY_RESULT_BACKEND=redis://localhost:6379/1
```

Next, set up the database, add some sample data, and start the server:

```bash
python manage.py migrate
python manage.py seed_data
python manage.py runserver
```

The `seed_data` command gives you enough sample data to try the API right away: 14 categories, 1,200 products, 25 stores, and at least 320 inventory records per store. It reuses existing data where possible. You can request larger data sets:

```bash
python manage.py seed_data --categories 15 --products 2000 --stores 30 --min-inventory-per-store 400 --seed 42
```

The command enforces minimums of 10 categories, 1,000 products, 20 stores, and 300 inventory items per store. Use `--flush` to delete the existing catalogue and related orders before creating a fresh data set.

## Project structure

```text
apps/
  products/   Product and category models, listing endpoint, cache signals
  search/     Product search and autocomplete endpoints
  stores/     Store inventory endpoint and sample-data command
  orders/     Atomic order workflow, order history, and Celery task
project/      Django settings, root URLs, ASGI/WSGI, and Celery setup
tests/        Product, search, store, and order API tests
```

## API endpoints

| Method | Endpoint | Purpose |
| --- | --- | --- |
| `GET` | `/api/products/` | List products |
| `GET` | `/api/search/products/` | Search, filter, sort, and paginate products |
| `GET` | `/api/search/suggest/?q=term` | Return up to 10 product suggestions |
| `GET` | `/stores/{store_id}/inventory/` | List a store's inventory |
| `POST` | `/orders/` | Place an order |
| `GET` | `/stores/{store_id}/orders/` | List a store's orders |
| `GET` | `/api/schema/` | Download the OpenAPI schema |
| `GET` | `/api/docs/` | Open Swagger UI |

## Testing APIs with Swagger UI

You do not need Postman or another API client to try the endpoints. Once the server is running, open <http://localhost:8000/api/docs/> in your browser. This opens Swagger UI, where you can see and test all the available APIs in one place.

To try an endpoint:

1. Open the endpoint you want to test, such as `GET /api/search/products/` or `POST /orders/`.
2. Click **Try it out**.
3. Fill in the parameters or edit the JSON request body.
4. Click **Execute**.

Swagger will send the request and show you the status code, response body, response headers, request URL, and an equivalent curl command. For example, you can use the search endpoint to try different keywords and filters, or use the order endpoint to submit an order with an editable JSON body.

The OpenAPI schema behind Swagger UI is also available at <http://localhost:8000/api/schema/>. You can download it and import it into another OpenAPI-compatible tool if you ever need to.

## Sample API requests

List all products:

```bash
curl http://localhost:8000/api/products/
```

View a store's inventory and order history:

```bash
curl http://localhost:8000/stores/1/inventory/
curl http://localhost:8000/stores/1/orders/
```

### Product search parameters

| Parameter | Description |
| --- | --- |
| `q` or `keyword` | Case-insensitive match against title, description, or category name |
| `category` | Category ID or a case-insensitive category-name match |
| `min_price` | Minimum price, inclusive |
| `max_price` | Maximum price, inclusive |
| `store_id` | Only products carried by the selected store |
| `in_stock` | `true`/`false`, `1`/`0`, or `yes`/`no`; applies to the selected store when `store_id` is present |
| `sort` | `price`, `-price`, `newest`, or `relevance` |
| `page` | One-based page number; defaults to `1` |
| `page_size` | Results per page; defaults to `10` and has a maximum of `100` |

Example:

```bash
curl "http://localhost:8000/api/search/products/?q=juice&store_id=1&in_stock=true&sort=price&page=1&page_size=10"
```

Search responses contain `count`, `page`, `page_size`, `total_pages`, `next`, `previous`, and `results`. When filtering by `store_id`, each result also includes `inventory_quantity`.

Autocomplete requires at least three characters and returns up to ten matching product titles:

```bash
curl "http://localhost:8000/api/search/suggest/?q=ora"
```

### Orders

Example order request:

```bash
curl -X POST http://localhost:8000/orders/ \
  -H "Content-Type: application/json" \
  -d '{"store_id":1,"items":[{"product_id":1,"quantity_requested":2}]}'
```

An order is confirmed only when the store has enough stock for every requested item. If anything is unavailable, the order is marked as rejected and no stock is removed.

Successful requests return HTTP `201` for both confirmed and rejected orders. The response includes the final `status` and the created order:

```json
{
  "status": "CONFIRMED",
  "order": {
    "id": 1,
    "store_id": 1,
    "status": "CONFIRMED",
    "created_at": "2026-06-19T12:00:00Z",
    "items": [
      {"product_id": 1, "quantity_requested": 2}
    ]
  }
}
```

Order creation runs inside a database transaction and locks the relevant store and inventory rows. Duplicate product entries in one request are combined when checking and deducting stock, while the original item entries are preserved on the order.

## Caching

Product lists, searches, and suggestions are cached in Redis for `CACHE_TTL_SECONDS` (300 seconds by default). Cache keys include the complete normalized query string. Saving or deleting a product, category, or inventory record clears cached product reads.

## Background tasks with Celery

Celery uses Redis as its message broker. A worker starts automatically when you run the project with Docker Compose:

```bash
docker compose up --build
```

You can follow the worker output with:

```bash
docker compose logs -f worker
```

For local development, keep Redis running and start the worker in a separate terminal:

```bash
celery -A project worker --loglevel=info
```

When `POST /orders/` creates a confirmed order, Django queues the `send_order_confirmation` task after the database transaction commits. Rejected orders do not trigger it. Because orders do not currently include a customer email address or phone number, the example task writes the confirmation to the worker log. The logging call can later be replaced with an email or SMS provider.

You can also trigger the task manually from the Django shell:

```bash
python manage.py shell
```

```python
from apps.orders.tasks import send_order_confirmation
send_order_confirmation.delay(1)
```

## Scalability considerations

The current design already separates the web process, PostgreSQL, Redis, and Celery worker, so each service can be scaled independently. Multiple web containers can share the same database and cache, while additional Celery workers can process more background jobs.

Order creation uses database transactions and row locks to prevent concurrent requests from overselling inventory. This favors correctness, but very high traffic to the same store or product can create lock contention. At that scale, shorter transactions, retry handling, and partitioning work by store would be worth considering.

Redis reduces repeated product and search reads, but wildcard cache invalidation becomes more expensive as the key set grows. Versioned cache namespaces or targeted invalidation would scale better for a much larger catalogue.

The search endpoint currently uses PostgreSQL case-insensitive substring matching and offset pagination. For a large catalogue, add database indexes and PostgreSQL full-text or trigram search; at greater scale, a dedicated search service and cursor pagination may be more appropriate. The unpaginated `/api/products/` endpoint should also be paginated before exposing a very large catalogue.

In production, run Django behind a production WSGI/ASGI server and reverse proxy rather than `runserver`. Monitor database query time, cache hit rate, Celery queue depth, task failures, and inventory-lock contention before deciding which component to scale.

## Useful commands

```bash
python manage.py check
python manage.py createsuperuser
python manage.py makemigrations
python manage.py migrate
```

After creating a superuser, you can sign in to the Django admin at <http://localhost:8000/admin/>.

## Tests

Install the dependencies and run the test suite with:

```bash
pip install -r requirements.txt
pytest
```

Run one test module while developing:

```bash
pytest tests/test_search.py -q
```

With Docker, run:

```bash
docker compose exec web pytest
```

The suite covers product serialization, search filters and validation, suggestions, store inventory ordering and missing stores, and confirmed-order stock deduction/task dispatch.
