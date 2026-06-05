# InsightFlow — Project Overview

InsightFlow is a **business intelligence data pipeline** built for a retail company with three ingestion sources: point-of-sale terminals (CSV uploads), an online orders API, and a customer feedback API. Raw transactional data flows through a validation and ingestion layer into an OLTP database, is then extracted and transformed into a star-schema data warehouse, and finally surfaced in Metabase dashboards for analysts.

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                            InsightFlow Platform                              │
│                                                                             │
│  ┌──────────────┐    ┌─────────────────────────────────────────────────┐   │
│  │   Frontend   │    │                   Backend                        │   │
│  │  Next.js 16  │───▶│  Django 4.2 + DRF   │   Celery Workers          │   │
│  │  (port 3000) │    │  (Gunicorn, 8080)   │   (2 concurrent)          │   │
│  └──────────────┘    └──────────────┬──────┴───────────┬───────────────┘   │
│                                     │                   │                   │
│                      ┌──────────────▼────┐    ┌────────▼────────────┐      │
│                      │  PostgreSQL OLTP  │    │       Redis          │      │
│                      │  (port 5432)      │    │  Broker + Results   │      │
│                      └──────────────┬────┘    └─────────────────────┘      │
│                                     │                                       │
│                      ┌──────────────▼────────────────┐                     │
│                      │          ETL Pipeline          │                     │
│                      │  (Celery workers, batch jobs)  │                     │
│                      └──────────────┬────────────────┘                     │
│                                     │                                       │
│                      ┌──────────────▼────┐    ┌──────────────────────┐    │
│                      │  PostgreSQL       │    │      Metabase         │    │
│                      │  Data Warehouse   │◀───│  BI Dashboards        │    │
│                      │  (port 5433)      │    │  (port 3001)          │    │
│                      └───────────────────┘    └──────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Data Flow

```
POS CSV Upload          ──▶  /api/ingestion/pos/            ──▶  InjectionJob  ──▶  Celery task
                                                                                      │
Online Orders API       ──▶  /api/ingestion/online-orders/  ──▶  OnlineInjectionJob ──▶  Celery task (every 5 min)
                                                                                      │
Feedback API            ──▶  /api/ingestion/feedback/       ──▶  FeedbackIngestionJob ──▶  Celery task
                                                                                      │
                                                                           PostgreSQL OLTP
                                                                                      │
                                                                           ETL Pipeline
                                                                                      │
                                                                           Star-Schema Warehouse
                                                                                      │
                                                                           Metabase Dashboards
```

---

## Tech Stack

| Layer | Technology | Version |
|---|---|---|
| **Frontend** | Next.js (App Router) | 16.2.7 |
| **Frontend State** | TanStack React Query | 5.100.14 |
| **Frontend Styles** | Tailwind CSS | v4 |
| **Backend API** | Django + Django REST Framework | 4.2.30 / 3.15.2 |
| **Task Queue** | Celery | 5.4.0 |
| **Message Broker** | Redis | 7 |
| **OLTP Database** | PostgreSQL | 15 (port 5432) |
| **Data Warehouse** | PostgreSQL | 15 (port 5433) |
| **BI Tool** | Metabase | latest |
| **Auth** | JWT (simplejwt) | 5.5.1 |
| **API Docs** | drf-spectacular (OpenAPI 3) | 0.27.2 |
| **CSV Processing** | pandas | 2.2.3 |
| **Container** | Docker + Docker Compose | — |
| **WSGI Server** | Gunicorn | 22.0.0 (4 workers) |

---

## Ingestion Sources

### 1. POS (Point of Sale) — CSV Upload
Retail staff upload daily transaction CSV files through the web UI. Each file contains transaction headers and line items. The service validates column presence and data types using pandas vectorized operations, then bulk-inserts records in a single Celery worker task.

- **Trigger:** Manual via frontend upload form
- **File format:** CSV with columns: `transaction_id, date, store_id, cashier_id, product_sku, quantity, unit_price, discount_applied, total`
- **Duplicate handling:** Pre-flight check against existing `posTransactionId` values; duplicates counted as `skipped` not re-inserted
- **Max file size:** 50 MB

### 2. Online Orders — External API
Online orders are fetched from an external API on a scheduled basis (every 5 minutes via Celery Beat) and can also be manually triggered from the history page.

- **Trigger:** Scheduled (crontab `*/5`) + manual "Sync Online Orders" button
- **Pagination:** 100 records per page, all pages fetched per run
- **Duplicate handling:** `update_conflicts=True` upsert on `onlineOrderId`

### 3. Feedback — External API
Customer survey responses are fetched from an external API and inserted as `FeedbackSurvey` records linked to customers and orders.

- **Trigger:** Manual "Sync Feedbacks" button
- **Duplicate detection:** `responseId` uniqueness check before insert
- **Validation:** Customer FK must exist; `onlineOrderId` is optional

---

## Repository Structure

```
deg-cohort-2-insightflow/
├── backend/                   # Django application
│   ├── apps/
│   │   ├── authentication/    # JWT auth, user model, token blacklist
│   │   ├── core/              # Shared exceptions, permissions, throttling
│   │   ├── ingestion/         # POS, online orders, feedback pipelines
│   │   └── sampledata/        # Test data generation
│   ├── insightflow/           # Django project settings (base/dev/prod/test)
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/                  # Next.js application
│   ├── src/
│   │   ├── api/               # API client and per-source modules
│   │   ├── app/               # Next.js App Router pages
│   │   ├── components/        # UI component library
│   │   ├── hooks/             # useAuth
│   │   ├── lib/               # queryClient, tokenStorage
│   │   └── types/             # Shared TypeScript interfaces
│   └── package.json
├── docs/
│   ├── README.md              # This file — project overview
│   ├── lineage.md             # ETL data lineage documentation
│   ├── frontend/README.md     # Frontend technical reference
│   └── backend/README.md      # Backend technical reference
├── qa/                        # API integration tests (pytest)
└── docker-compose.yml         # Full-stack service definitions
```

---

## Quick Start

### Prerequisites
- Docker and Docker Compose
- Node.js 20+ (for local frontend development)
- Python 3.11+ (for local backend development)

### Run with Docker Compose

```bash
# Clone and start all services
git clone <repo>
cd deg-cohort-2-insightflow
docker compose up --build
```

| Service | URL |
|---|---|
| Frontend | http://localhost:3000 |
| Backend API | http://localhost:8080/api |
| Swagger UI | http://localhost:8080/api-docs |
| Metabase | http://localhost:3001 |

### Environment Variables

Create `backend/.env` (or set in Docker Compose `environment`):

```env
DJANGO_SETTINGS_MODULE=insightflow.settings.dev
SECRET_KEY=your-secret-key
DB_HOST=postgres-app
DB_PORT=5432
DB_NAME=insightflow_app
DB_USER=postgres
DB_PASSWORD=postgres
REDIS_URL=redis://redis:6379/0
CORS_ALLOWED_ORIGINS=http://localhost:3000
MEDIA_ROOT=/app/media
```

Create `frontend/.env.local`:

```env
NEXT_PUBLIC_API_BASE_URL=http://localhost:8080/api
```

### Local Development (without Docker)

**Backend:**
```bash
cd backend
python -m venv .venv && source .venv/bin/activate  # or .venv\Scripts\activate on Windows
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver 8080

# In a second terminal — Celery worker
celery -A insightflow worker --loglevel=info

# In a third terminal — Celery Beat scheduler
celery -A insightflow beat --loglevel=info
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev   # http://localhost:3000
```

---

## Authentication

All API calls require a JWT bearer token obtained via `POST /api/auth/login/`. Tokens expire after **1 day** (access) and **7 days** (refresh). On logout, the refresh token is blacklisted server-side so it cannot be re-used.

```
POST /api/auth/login/
{ "email": "user@example.com", "password": "..." }
→ { "tokens": { "access": "eyJ...", "refresh": "eyJ..." } }

Authorization: Bearer eyJ...
```

---

## Further Reading

- [Frontend Documentation](frontend/README.md) — pages, components, API layer, state management, typography system
- [Backend Documentation](backend/README.md) — apps, models, services, Celery tasks, API endpoints, configuration
- [ETL Data Lineage](lineage.md) — OLTP→warehouse mappings, quality gates, pipeline stages, anomaly detection
