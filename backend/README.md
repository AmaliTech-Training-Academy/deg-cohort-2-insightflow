# InsightFlow Backend Documentation

The backend is a **Django 4.2 REST API** running on Gunicorn with Celery workers handling background ingestion tasks. It provides JWT-authenticated endpoints for three data ingestion pipelines (POS CSV, Online Orders, Feedback), manages an OLTP PostgreSQL database, and publishes tasks to Redis for asynchronous processing.

---

## Table of Contents

1. [Tech Stack](#tech-stack)
2. [Application Layout](#application-layout)
3. [Django Apps](#django-apps)
4. [Data Models](#data-models)
5. [API Endpoints](#api-endpoints)
6. [Services Layer](#services-layer)
7. [Validators](#validators)
8. [Celery Tasks](#celery-tasks)
9. [Authentication and Authorization](#authentication-and-authorization)
10. [Exception Handling](#exception-handling)
11. [Configuration and Settings](#configuration-and-settings)
12. [Docker Setup](#docker-setup)
13. [Running Tests](#running-tests)

---

## Tech Stack

| Package | Version | Purpose |
|---|---|---|
| Django | 4.2.30 | Web framework |
| Django REST Framework | 3.15.2 | API toolkit |
| djangorestframework-simplejwt | 5.5.1 | JWT auth |
| Celery | 5.4.0 | Task queue |
| Redis (broker) | 7-alpine | Celery message broker and result backend |
| PostgreSQL | 15 | OLTP database (port 5432) |
| psycopg2-binary | — | PostgreSQL adapter |
| pandas | 2.2.3 | CSV validation (vectorized) |
| drf-spectacular | 0.27.2 | OpenAPI 3 schema generation |
| django-cors-headers | 4.4.0 | CORS middleware |
| python-json-logger | 2.0.7 | Structured JSON logging |
| requests | 2.33.0 | External API HTTP client |
| gunicorn | 22.0.0 | WSGI server (4 workers, 120 s timeout) |
| python-dotenv | 1.2.2 | `.env` file loading |
| Faker | 24.6.0 | Sample data generation |
| Python | 3.11 | Runtime |

---

## Application Layout

```
backend/
├── insightflow/              # Django project package
│   ├── settings/
│   │   ├── base.py           # Shared settings (DB, Celery, JWT, throttling, logging)
│   │   ├── dev.py            # DEBUG=True, relaxed CORS
│   │   ├── prod.py           # DEBUG=False, HTTPS enforcement, strict CORS
│   │   └── test.py           # In-memory SQLite, no Celery
│   ├── celery.py             # Celery app factory
│   ├── urls.py               # Root URL conf (api/, health/, schema/)
│   └── wsgi.py               # WSGI entry point
│
├── apps/
│   ├── authentication/       # User model, JWT login/logout, token blacklist
│   ├── core/                 # Shared exceptions, permissions, throttling, pagination
│   ├── ingestion/            # POS, online orders, and feedback pipelines
│   └── sampledata/           # Management command for test data generation
│
├── Dockerfile
├── requirements.txt
└── manage.py
```

---

## Django Apps

### `apps.authentication`

Owns the custom `User` model and all auth endpoints. Key responsibilities:
- Custom user with `role` field (`admin`, `analyst`, `viewer`)
- JWT login returning both access and refresh tokens
- Token blacklisting on logout (refresh token stored in DB so it cannot be re-used)
- Registration with password strength validation

**Internal structure:**
```
authentication/
├── models.py          # User (extends AbstractUser), TokenBlacklist
├── serializers.py     # RegisterSerializer, LoginSerializer, LogoutSerializer, RefreshTokenSerializer
├── views/
│   ├── register.py    # RegisterView
│   ├── login.py       # LoginView
│   ├── token.py       # CustomTokenObtainPairView, RefreshTokenView
│   └── logout.py      # LogoutView
└── urls.py
```

---

### `apps.core`

Shared infrastructure consumed by all other apps. Never exposes API endpoints.

```
core/
├── exceptions.py      # 10 custom exception classes + custom_exception_handler
├── permissions.py     # 6 DRF permission classes
├── throttling.py      # LoginThrottle, RefreshTokenThrottle
├── pagination.py      # StandardResultsPagination (page_size=20)
└── logging.py         # JSONFormatter for structured log output
```

---

### `apps.ingestion`

The core of the platform — three independent ingestion pipelines sharing a common set of models and infrastructure.

```
ingestion/
├── models/
│   ├── base.py                 # Customer, InjectionJob (POS upload tracker)
│   ├── pos.py                  # PosTransaction, PosTransactionLine, Cashier
│   ├── inventory.py            # Store, Category, Product, Inventory
│   ├── online_orders.py        # OnlineOrder, OnlineOrderLine
│   ├── online_injection_job.py # OnlineInjectionJob (online orders tracker)
│   ├── feedback.py             # FeedbackSurvey
│   └── feedback_ingestion_job.py # FeedbackIngestionJob (feedback tracker)
│
├── serializers/                # DRF serializers for each model group
├── validators/
│   ├── pos.py                  # Column presence + per-row field validation
│   ├── online_orders.py        # Order and order-line field validation
│   └── feedback.py             # (validation handled in service)
│
├── services/
│   ├── csv_services.py         # POSIngestionService — upload, validate, bulk insert
│   ├── online_orders_service.py # OnlineOrdersIngestionService — fetch, validate, upsert
│   └── feedback_ingestion_service.py # FeedbackIngestionService — fetch, deduplicate, insert
│
├── connectors/
│   ├── online_orders.py        # OnlineOrdersAPIConnector — paginated external API client
│   └── feedback.py             # FeedbackAPIConnector
│
├── tasks/
│   ├── process_pos.py          # process_pos_file Celery task
│   ├── fetch_online_orders.py  # schedule_online_orders_fetch + fetch_online_orders tasks
│   └── ingest_feedback.py      # ingest_feedback Celery task
│
├── views/                      # DRF views for all three pipelines
└── urls.py                     # Ingestion URL routing
```

---

### `apps.sampledata`

Provides a Django management command (`python manage.py generate_sample_data`) that uses Faker to seed reference data (stores, cashiers, products, customers) for local development.

---

## Data Models

### Authentication

**`User`** (`users` table)
| Field | Type | Notes |
|---|---|---|
| id | BigAutoField PK | |
| email | EmailField unique | Login identifier |
| username | CharField | Optional alias |
| first_name, last_name | CharField | Display name |
| role | CharField | `admin` / `analyst` / `viewer` |
| is_active | BooleanField | Disabled accounts cannot log in |
| password | CharField | bcrypt hash |

**`TokenBlacklist`** (`token_blacklist` table)
| Field | Type | Notes |
|---|---|---|
| id | AutoField PK | |
| token | TextField | Raw refresh token string |
| user | FK → User | CASCADE on delete |
| blacklisted_at | DateTimeField | auto_now_add |
| expires_at | DateTimeField | Token's `exp` claim; used for cleanup |

Indexes: `(token)`, `(user, blacklisted_at)`.

---

### Reference / Dimension Tables

**`Store`** — `store` table: `storeId` (PK), `storeName`, `province`

**`Category`** — `category` table: `categoryId` (PK), `name`

**`Product`** — `product` table: `productSKU` (PK), `productName`, `categoryId` (FK Category)

**`Inventory`** — `inventory` table: `inventoryId` (PK), `productSKU` (FK), `currentStockQty`, `reorderThreshold`, `lastRestockedDate`

**`Cashier`** — `cashier` table: `cashierId` (PK), `storeId` (FK), `fullName`, `userId` (FK User)

**`Customer`** — `customer` table: `customerId` (PK, CharField[20]), `userId` (FK User)

---

### POS Pipeline

**`InjectionJob`** — POS upload metadata
| Field | Type | Notes |
|---|---|---|
| id | AutoField PK | |
| file | FileField | Saved to `uploads/pos_csv/%Y/%m/%d/` |
| status | CharField | `pending` / `running` / `completed` / `failed` |
| total_rows | IntegerField | Row count from file (before validation) |
| valid_rows | IntegerField | Successfully inserted rows |
| rejected_rows | IntegerField | FK-miss rejections (unknown store/cashier/product) |
| error_rows | IntegerField | Bad CSV format rows |
| error_report | JSONField | `{ row_errors?, skipped_duplicates? }` |
| task_id | CharField | Celery task UUID |
| created_at | DateTimeField | auto_now_add |
| updated_at | DateTimeField | auto_now |

**`PosTransaction`** — `posTransaction`
| Field | Type | Notes |
|---|---|---|
| posTransactionId | IntegerField PK | From CSV `transaction_id` column |
| storeId | FK → Store | |
| cashierId | FK → Cashier | |
| transactionDatetime | DateTimeField | Timezone-aware |

**`PosTransactionLine`** — `posTransactionLine`
| Field | Type | Notes |
|---|---|---|
| lineId | IntegerField PK | Composite: `{txnId:012d}{lineIdx:03d}` |
| posTransactionId | FK → PosTransaction | |
| productSKU | FK → Product | |
| quantity | IntegerField | |
| unitPrice | DecimalField(10,2) | |
| discountApplied | DecimalField(10,2) | |
| totalAmount | DecimalField(10,2) | |

---

### Online Orders Pipeline

**`OnlineOrder`** — `onlineOrder`
| Field | Type | Notes |
|---|---|---|
| onlineOrderId | IntegerField PK | From external API |
| customerId | FK → Customer | |
| orderDatetime | DateTimeField | |
| shippingProvince | CharField(255) | |
| orderStatus | CharField(255) | |
| paymentMethod | CharField(255) | |

**`OnlineOrderLine`** — `onlineOrderLine`
| Field | Type | Notes |
|---|---|---|
| lineId | IntegerField PK | |
| onlineOrderId | FK → OnlineOrder | |
| productSKU | FK → Product | |
| quantity, unitPrice, discountApplied, totalAmount | Numeric | |

**`OnlineInjectionJob`** — `online_injection_job`
| Field | Type | Notes |
|---|---|---|
| id | AutoField PK | |
| status | CharField | `pending` / `running` / `completed` / `failed` |
| trigger | CharField | `scheduled` / `manual` |
| total_orders, valid_orders, error_orders, pages_fetched | IntegerField | |
| error_report | JSONField | |
| created_at, updated_at | DateTimeField | |

---

### Feedback Pipeline

**`FeedbackSurvey`** — `feedbackSurvey`
| Field | Type | Notes |
|---|---|---|
| responseId | IntegerField PK | From external API |
| customerId | FK → Customer | |
| onlineOrderId | FK → OnlineOrder | nullable |
| submissionDate | DateField | |
| satisfactionScore | SmallIntegerField | |
| npsScore | SmallIntegerField | |
| productRating | SmallIntegerField | |
| deliveryRating | SmallIntegerField | |
| freeTextComments | TextField | |

**`FeedbackIngestionJob`** — `feedback_ingestion_job`
| Field | Type | Notes |
|---|---|---|
| id | AutoField PK | |
| status | CharField | `pending` / `running` / `completed` / `failed` |
| total_fetched | IntegerField | |
| created_count | IntegerField | Net new records inserted |
| skipped_duplicates | IntegerField | Already-present responseIds |
| errors | IntegerField | Records that failed validation |
| error_details | JSONField | Per-record error list |
| created_at, updated_at | DateTimeField | |

---

## API Endpoints

All endpoints under `/api/` require `Authorization: Bearer <access_token>` unless marked **public**.

### Authentication — `/api/auth/`

| Method | Path | Auth | Body | Response |
|---|---|---|---|---|
| POST | `/auth/register/` | Public | `{email, username, password, first_name, last_name, role?}` | 201 `{message, user}` |
| POST | `/auth/login/` | Public | `{email, password}` | 200 `{tokens: {access, refresh}}` |
| POST | `/auth/token/` | Public | `{email, password}` | 200 `{access, refresh}` |
| POST | `/auth/token/refresh/` | Public | `{refresh}` | 200 `{access, refresh}` |
| POST | `/auth/logout/` | JWT | `{refresh}` | 200 `{message}` |

**Password requirements:** 8+ characters, at least one uppercase, one lowercase, one digit, one special character.

---

### POS Ingestion — `/api/ingestion/pos/`

| Method | Path | Body | Response |
|---|---|---|---|
| POST | `/ingestion/pos/` | `multipart/form-data { file: CSV }` | 202 `{job_id, status, total_rows, message}` |
| GET | `/ingestion/pos/` | — | 200 paginated list of `PosTransactionLine` records |
| GET | `/ingestion/pos/jobs/` | — | 200 paginated `InjectionJob` list |
| GET | `/ingestion/<job_id>/status/` | — | 200 `{job_id, status, total_rows, valid_rows, rejected_rows, error_rows, error_report?, created_at, updated_at}` |

**Upload flow:**
1. View calls `POSIngestionService.validate_upload()` — fails fast with 4xx on bad files
2. View calls `POSIngestionService.accept_upload()` — creates `InjectionJob`, saves file
3. View dispatches `process_pos_file.delay(job.id)` to Celery
4. Returns 202 immediately with the job ID

---

### Online Orders — `/api/ingestion/online-orders/`

| Method | Path | Body | Response |
|---|---|---|---|
| POST | `/ingestion/online-orders/trigger/` | `{}` | 202 `{id, status, trigger, ..., message}` |
| GET | `/ingestion/online-orders/jobs/` | — | 200 paginated `OnlineInjectionJob` list |
| GET | `/ingestion/online-orders/<job_id>/status/` | — | 200 `OnlineInjectionJob` detail |

---

### Feedback — `/api/ingestion/feedback/`

| Method | Path | Body | Response |
|---|---|---|---|
| POST | `/ingestion/feedback/trigger/` | `{}` | 202 `{job_id, status, message}` |
| GET | `/ingestion/feedback/jobs/` | — | 200 `[FeedbackIngestionJob]` |
| GET | `/ingestion/feedback/jobs/<job_id>/status/` | — | 200 `FeedbackIngestionJob` detail |

---

### Utilities

| Method | Path | Auth | Notes |
|---|---|---|---|
| GET | `/health/` | Public | Returns `{status: "ok"}` |
| GET | `/api/schema/` | Public | OpenAPI 3.0 JSON schema |
| GET | `/api-docs/` | Public | Swagger UI |
| GET | `/api/redoc/` | Public | ReDoc UI |

---

## Services Layer

### `POSIngestionService` (`apps/ingestion/services/csv_services.py`)

The service is split into two phases matching the request-response and async-worker lifecycle.

**Phase 1 — `validate_upload(file)`**

Called synchronously in the view before accepting the upload. Fails immediately on:
- File size > 50 MB → `FileSizeLimitException`
- Non-`.csv` extension → `UnsupportedFileTypeException`
- Unparseable CSV → `CSVParseException`
- Missing required columns → `ValidationException` with `missing_columns` detail

**Phase 2 — `process_job(job: InjectionJob)`**

Called by the Celery worker. Two-stage pipeline:

**Validation stage (vectorized):**
1. Read CSV with pandas, normalize column names (strip, lowercase)
2. Null/empty mask across all 9 required columns (numpy-level, no Python loop)
3. Numeric validation — `pd.to_numeric(errors="coerce")` for cashier_id, quantity, unit_price, discount_applied, total
4. Date parsing via `apply(_parse_date_field)` — supports ISO 8601, `YYYY-MM-DD`, `DD/MM/YYYY`, `MM/DD/YYYY`
5. Python loop only over the (small) **invalid** subset to build per-row error messages

**DB insertion stage (atomic transaction):**
1. Three FK queries (store IDs, cashier IDs, product SKUs) — O(1) set membership in loop
2. Group rows by `transaction_id` using `pandas.groupby`
3. Build `PosTransaction` objects; reject rows with unknown store or cashier FK
4. **Duplicate check:** `PosTransaction.objects.filter(posTransactionId__in=...)` to count rows already in DB
5. If all valid rows are already present → update job as COMPLETED with `skipped_duplicates` count, return early
6. `PosTransaction.objects.bulk_create(txn_objects, ignore_conflicts=True)` — one DB call
7. Build `PosTransactionLine` objects; reject lines with unknown product SKU
8. `PosTransactionLine.objects.bulk_create(all_lines, batch_size=1000, ignore_conflicts=True)` — one DB call

Line ID is a composite integer: `{txn_id:012d}{line_index:03d}` — zero-padded to prevent collisions between `txn=12/line=31` and `txn=123/line=1`.

**Final counts stored on `InjectionJob`:**
- `valid_rows` = validated rows − FK-miss rejections − skipped duplicates
- `rejected_rows` = FK-miss count
- `error_rows` = invalid CSV row count
- `error_report.skipped_duplicates` = rows already in DB (surfaced as "Already exists" in the frontend)

---

### `OnlineOrdersIngestionService` (`apps/ingestion/services/online_orders_service.py`)

1. `create_job(trigger)` — creates `OnlineInjectionJob`
2. `process_job(job)` — iterates all API pages via `OnlineOrdersAPIConnector.iter_all_pages()` (100 records/page)
3. Per-page: validates each order, auto-creates missing `Customer` records, bulk-upserts `OnlineOrder` and `OnlineOrderLine` with `update_conflicts=True`

---

### `FeedbackIngestionService` (`apps/ingestion/services/feedback_ingestion_service.py`)

1. Fetches all records from `FeedbackAPIConnector`
2. Bulk-queries existing `responseId` values to detect duplicates in one query
3. Validates each record (customer FK must exist; order FK is optional)
4. `FeedbackSurvey.objects.bulk_create(new_records, ignore_conflicts=True)`
5. Returns summary dict: `{total_fetched, created, skipped_duplicates, errors, error_details}`

---

## Validators

### `apps/ingestion/validators/pos.py`

**`validate_pos_file_columns(columns: list) → list[str]`**
Returns names of any missing columns from: `transaction_id`, `date`, `store_id`, `cashier_id`, `product_sku`, `quantity`, `unit_price`, `discount_applied`, `total`.

**`validate_pos_row(row: dict, row_num: int | None) → list[dict]`**
Returns a list of `{row, field, error}` dicts for each failing field. Rules:
- `transaction_id`, `store_id`, `product_sku` — required, non-empty string
- `cashier_id`, `quantity` — required positive integer
- `unit_price`, `total` — required positive decimal
- `discount_applied` — required non-negative decimal
- `date` — required, parseable as YYYY-MM-DD, DD/MM/YYYY, or MM/DD/YYYY

### `apps/ingestion/validators/online_orders.py`

**`validate_order(order: dict) → list[dict]`**
Checks presence of `onlineOrderId`, `customerId`, `orderDatetime`, `shippingProvince`, `orderStatus`, `paymentMethod`. Validates `onlineOrderId` is a positive integer.

**`validate_order_line(line: dict, order_id) → list[dict]`**
Validates `lineId`, `quantity`, `unitPrice`, `discountApplied`, `totalAmount` with the same numeric rules as POS.

---

## Celery Tasks

### `process_pos_file` (`apps/ingestion/tasks/process_pos.py`)

```python
@shared_task(bind=True, max_retries=3)
def process_pos_file(self, job_id: int) -> None
```

Calls `POSIngestionService().process_job(job)`. On failure:
- **Business failure** (bad data, validation error) — marks job FAILED, does not retry
- **Infrastructure failure** (DB connection, OS error) — retries with exponential backoff: `60 × 2^attempt` seconds

---

### `schedule_online_orders_fetch` (`apps/ingestion/tasks/fetch_online_orders.py`)

```python
@shared_task
def schedule_online_orders_fetch() -> None
```

Entry point for the Celery Beat schedule (every 5 minutes). Creates an `OnlineInjectionJob` with `trigger="scheduled"` then dispatches `fetch_online_orders.delay(job.id)`.

---

### `fetch_online_orders` (`apps/ingestion/tasks/fetch_online_orders.py`)

```python
@shared_task(bind=True, max_retries=3)
def fetch_online_orders(self, job_id: int) -> None
```

Calls `OnlineOrdersIngestionService().process_job(job)`. Same retry strategy as POS.

---

### `ingest_feedback` (`apps/ingestion/tasks/ingest_feedback.py`)

```python
@shared_task(bind=True, max_retries=3)
def ingest_feedback(self, job_id: int) -> dict
```

Calls `FeedbackIngestionService().ingest()`, stores results on `FeedbackIngestionJob`. Returns a summary dict. Same retry strategy.

---

### Celery Beat Schedule

```python
CELERY_BEAT_SCHEDULE = {
    "fetch-online-orders-every-5-min": {
        "task": "apps.ingestion.tasks.fetch_online_orders.schedule_online_orders_fetch",
        "schedule": crontab(minute="*/5"),
    }
}
```

---

## Authentication and Authorization

### JWT Token Lifecycle

| Step | Endpoint | Result |
|---|---|---|
| Register | `POST /auth/register/` | User created, no tokens returned |
| Login | `POST /auth/login/` | Access token (1 day) + Refresh token (7 days) |
| Refresh | `POST /auth/token/refresh/` | New access token |
| Logout | `POST /auth/logout/` | Refresh token blacklisted in DB |

**Algorithm:** HS256, signed with `SECRET_KEY`.

**Blacklist mechanism:** On logout, the raw refresh token string is stored in `TokenBlacklist` with its expiry timestamp. The `RefreshTokenView` checks this table before issuing a new access token.

### Permission Classes (`apps/core/permissions.py`)

| Class | Rule |
|---|---|
| `IsAdminRole` | `user.role == "admin"` |
| `IsOwnerOrAdmin` | Object owner or admin role |
| `IsOwner` | Object owner only |
| `IsSuperAdmin` | `user.is_superuser` |
| `IsAdminOrReadOnly` | Safe methods allowed; write requires `is_staff` |
| `IsAuthenticatedOrReadOnly` | Safe methods public; write requires login |

All ingestion endpoints use the default `IsAuthenticated`.

### Throttling (`apps/core/throttling.py`)

| Class | Scope | Rate | Key |
|---|---|---|---|
| `AnonRateThrottle` (built-in) | `anon` | 100/hour | REMOTE_ADDR |
| `UserRateThrottle` (built-in) | `user` | 1000/hour | user ID |
| `LoginThrottle` | `login` | 20/hour | email or REMOTE_ADDR |
| `RefreshTokenThrottle` | `refresh_token` | 100/hour | user ID or REMOTE_ADDR |
| `POSUploadThrottle` | `pos_upload` | 5000/hour | user ID |

---

## Exception Handling

All exceptions are caught by `custom_exception_handler` in `apps/core/exceptions.py` and normalised to:

```json
{
  "error": true,
  "message": "Human-readable description",
  "code": "EXCEPTION_CLASS_NAME",
  "details": {}
}
```

### Custom Exception Classes

| Exception | HTTP Code | Typical Use |
|---|---|---|
| `ValidationException` | 400 | Field validation failures |
| `FileSizeLimitException` | 400 | Upload > 50 MB |
| `UnsupportedFileTypeException` | 400 | Non-CSV upload |
| `CSVParseException` | 400 | Unreadable CSV file |
| `UnauthorizedException` | 401 | Missing or invalid token |
| `ForbiddenException` | 403 | Insufficient permissions |
| `NotFoundException` | 404 | Resource not found |
| `ConflictException` | 409 | Duplicate resource |
| `RateLimitException` | 429 | Throttle limit hit |
| `InternalServerException` | 500 | Unhandled server error |

Errors are logged as `WARNING` with `status_code`, `error_code`, and request path. Unhandled exceptions are logged as `ERROR`.

---

## Configuration and Settings

Settings are split by environment. The active module is selected via `DJANGO_SETTINGS_MODULE`.

| Module | Use |
|---|---|
| `insightflow.settings.dev` | Local development, DEBUG=True |
| `insightflow.settings.prod` | Production, DEBUG=False, HTTPS enforcement |
| `insightflow.settings.test` | CI/unit tests, SQLite in-memory |

### Key `base.py` Values

**Database:**
```python
DATABASES["default"] = {
    "ENGINE": "django.db.backends.postgresql",
    "NAME":     os.environ.get("DB_NAME",     "insightflow_app"),
    "USER":     os.environ.get("DB_USER",     "postgres"),
    "PASSWORD": os.environ.get("DB_PASSWORD", "postgres"),
    "HOST":     os.environ.get("DB_HOST",     "localhost"),
    "PORT":     os.environ.get("DB_PORT",     "5432"),
    "OPTIONS":  {"sslmode": os.environ.get("DB_SSLMODE", "prefer")},
}
```

**Celery:**
```python
CELERY_BROKER_URL     = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
CELERY_RESULT_BACKEND = CELERY_BROKER_URL
CELERY_TASK_EXPIRES   = 3600   # task result TTL (seconds)
CELERY_TIMEZONE       = "UTC"
```

**JWT (simplejwt):**
```python
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME":  timedelta(days=1),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ALGORITHM":    "HS256",
    "SIGNING_KEY":  SECRET_KEY,
    "AUTH_HEADER_TYPES": ("Bearer",),
}
```

**DRF defaults:**
```python
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": ["rest_framework_simplejwt.authentication.JWTAuthentication"],
    "DEFAULT_PERMISSION_CLASSES":     ["rest_framework.permissions.IsAuthenticated"],
    "DEFAULT_SCHEMA_CLASS":           "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_PAGINATION_CLASS":       "apps.core.pagination.StandardResultsPagination",
    "PAGE_SIZE": 20,
    "EXCEPTION_HANDLER": "apps.core.exceptions.custom_exception_handler",
}
```

**File uploads:**
```python
DATA_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024   # Django limit: 10 MB in memory
# Service-level limit: 50 MB (enforced in POSIngestionService.validate_upload)
MEDIA_ROOT = os.environ.get("MEDIA_ROOT", str(BASE_DIR / "media"))
MEDIA_URL  = "/media/"
```

**Logging:**

All log records are emitted as JSON using `python-json-logger`. The `apps.*` logger is set to `DEBUG`; `django.*` follows `DJANGO_LOG_LEVEL` (default `INFO`). In production, logs are shipped to CloudWatch via the Docker log driver.

### Production-Only Settings (`prod.py`)

```python
DEBUG                = False
SECURE_SSL_REDIRECT  = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE   = True
CORS_ALLOW_ALL_ORIGINS = False
CORS_ALLOWED_ORIGINS   = os.environ.get("CORS_ALLOWED_ORIGINS", "").split(",")
```

---

## Docker Setup

All services are defined in `docker-compose.yml` at the repository root.

### Services

| Service | Image | Port | Purpose |
|---|---|---|---|
| `postgres-app` | postgres:15-alpine | 5432 | OLTP database |
| `postgres-warehouse` | postgres:15-alpine | 5433 | Star-schema data warehouse |
| `redis` | redis:7-alpine | 6379 | Celery broker and result backend |
| `backend` | local Dockerfile | 8080 | Gunicorn Django API (4 workers) |
| `celery-worker` | local Dockerfile | — | Celery worker (concurrency=2) |
| `frontend` | Node.js | 3000 | Next.js application |
| `etl` | Python | — | OLTP→warehouse ETL pipeline |
| `metabase` | metabase/metabase | 3001 | BI dashboards (reads from warehouse) |

### Backend Container

```dockerfile
FROM python:3.11-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8080
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "--workers", "4", "--timeout", "120", "insightflow.wsgi:application"]
```

On startup, the compose command runs `manage.py migrate` then `gunicorn`.

### Celery Worker Container

Same image as the backend, different command:

```
celery -A insightflow worker --loglevel=info --concurrency=2
```

### Environment Variables (backend)

| Variable | Default | Notes |
|---|---|---|
| `DJANGO_SETTINGS_MODULE` | — | Required; use `insightflow.settings.prod` in production |
| `SECRET_KEY` | — | Required; Django secret key |
| `DB_HOST` | `localhost` | PostgreSQL host |
| `DB_PORT` | `5432` | |
| `DB_NAME` | `insightflow_app` | |
| `DB_USER` | `postgres` | |
| `DB_PASSWORD` | `postgres` | |
| `DB_SSLMODE` | `prefer` | Set to `require` in production |
| `REDIS_URL` | `redis://localhost:6379/0` | Celery broker |
| `MEDIA_ROOT` | `./media` | File storage path |
| `CORS_ALLOWED_ORIGINS` | `""` | Comma-separated list; production only |
| `DJANGO_LOG_LEVEL` | `INFO` | Django framework log level |

---

## Running Tests

Integration and API tests live in `qa/api-tests/tests/` and use **pytest** with Django's test runner.

```bash
cd backend
pip install -r requirements.txt

# All tests (uses insightflow.settings.test — SQLite in-memory)
DJANGO_SETTINGS_MODULE=insightflow.settings.test pytest

# Specific test file
DJANGO_SETTINGS_MODULE=insightflow.settings.test pytest qa/api-tests/tests/test_pos_service.py -v
```

The test settings (`insightflow/settings/test.py`) override the database to SQLite in-memory and disable Celery task execution (tasks run synchronously with `CELERY_TASK_ALWAYS_EAGER=True`).

### Mocking the Duplicate Check

Tests that call `POSIngestionService.process_job()` must mock the `PosTransaction.objects.filter` duplicate-check call, otherwise the test runner raises `RuntimeError: Database access not allowed`:

```python
patch(
    "apps.ingestion.services.csv_services.PosTransaction.objects.filter",
    return_value=MagicMock(values_list=MagicMock(return_value=[])),
)
```
