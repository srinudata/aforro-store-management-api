# Aforro API

Aforro is a small store and ordering API built with Django REST Framework. It lets you browse and search products, check what a store has in stock, and place orders.

The project uses PostgreSQL for its data and Redis to cache product and search results. There is also a Swagger page where you can explore and test the API from your browser.

## Tech stack

- Python 3.12 and Django 5.2
- Django REST Framework
- PostgreSQL 16
- Redis 7
- Celery 5
- drf-spectacular / OpenAPI
- Docker Compose

## Getting started with Docker

If you already have Docker installed, this is the easiest way to run the project:

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

Prefer to run it without Docker? Make sure PostgreSQL and Redis are running first. Then create a virtual environment and install the dependencies:

```bash
python -m venv .venv
# Windows PowerShell
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
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

The `seed_data` command gives you enough sample data to try the API right away: 12 categories, 1,000 products, 20 stores, and 300 inventory records per store. You can change those numbers if you want:

```bash
python manage.py seed_data --categories 15 --products 2000 --stores 25 --inventory-per-store 400 --seed 42
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

The product search endpoint supports the following query parameters: `q` (or `keyword`), `category`, `min_price`, `max_price`, `store_id`, `in_stock`, `sort`, `page`, and `page_size`.

For sorting, use `price`, `-price`, `newest`, or `relevance`. A page can contain up to 100 results.

Example order request:

```bash
curl -X POST http://localhost:8000/orders/ \
  -H "Content-Type: application/json" \
  -d '{"store_id":1,"items":[{"product_id":1,"quantity_requested":2}]}'
```

An order is confirmed only when the store has enough stock for every requested item. If anything is unavailable, the order is marked as rejected and no stock is removed.

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

## Useful commands

```bash
python manage.py check
python manage.py createsuperuser
python manage.py makemigrations
python manage.py migrate
```

After creating a superuser, you can sign in to the Django admin at <http://localhost:8000/admin/>.
