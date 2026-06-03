# InsightFlow ETL Pipeline

Complete documentation for the InsightFlow data-engineering pipeline — covering
architecture, data sources, quality framework, lineage tracking, event-driven
triggering, and deployment.

---

## Contents

1. [Overview](#1-overview)
2. [Directory structure](#2-directory-structure)
3. [Architecture](#3-architecture)
4. [Pipeline stages](#4-pipeline-stages)
5. [Data sources and extraction](#5-data-sources-and-extraction)
6. [Data quality and anomaly detection](#6-data-quality-and-anomaly-detection)
7. [Transformation](#7-transformation)
8. [Loading the star schema](#8-loading-the-star-schema)
9. [Event-driven triggering](#9-event-driven-triggering)
10. [Lineage tracking](#10-lineage-tracking)
11. [Quality report emails](#11-quality-report-emails)
12. [Configuration reference](#12-configuration-reference)
13. [Running the pipeline](#13-running-the-pipeline)
14. [Deployment services](#14-deployment-services)
15. [Observability](#15-observability)

---

## 1. Overview

The InsightFlow ETL pipeline moves data from the Django application's
operational database (**OLTP** — `insightflow_app` on AWS RDS) into an
analytics-optimised star-schema warehouse (**OLAP** —
`insightflow_warehouse` on AWS RDS).

Key properties:

- **Incremental** — each run extracts only records newer than the last
  successful load, determined by a watermark derived from the warehouse itself.
  A full reload is available via `--full-reload`.
- **Event-driven** — PostgreSQL `NOTIFY` triggers on the OLTP tables fire
  whenever new data is written by the backend API. A dedicated listener service
  debounces these events and dispatches an ETL run via Celery automatically.
- **Quality-gated** — every source is scored against a rule suite before any
  data reaches the warehouse. A source whose score drops below its threshold
  aborts the run; the warehouse is never left in a partial state.
- **Observable** — every run produces three artefacts: a raw lineage event log,
  a grouped lineage report, and a Markdown quality/anomaly report that is also
  emailed to the data team.

---

## 2. Directory structure

```
data-engineering/
├── etl/
│   ├── __init__.py
│   ├── extract.py          # Extractor — SQL queries against OLTP
│   ├── transform.py        # Transformer — dimension and fact builders
│   ├── load.py             # Loader — warehouse upserts and inserts
│   ├── quality.py          # DataQualityChecker, AnomalyDetector, SourceQualityReport
│   ├── lineage.py          # LineageTracker, LineageEvent, LineageStage
│   ├── alerts.py           # AlertManager, AnomalyAlert
│   ├── state.py            # Watermark detection from the warehouse
│   ├── notify.py           # Markdown report builder + SMTP emailer
│   ├── tasks.py            # Celery task wrapping run_pipeline()
│   ├── listener.py         # PostgreSQL NOTIFY listener with debounce
│   └── triggers.sql        # SQL trigger definitions for OLTP tables
├── warehouse/
│   └── schema.sql          # Star-schema DDL (idempotent CREATE IF NOT EXISTS)
├── lineage/                # Generated at runtime — gitignored
│   ├── lineage_<run_id>.json
│   ├── lineage_report_<run_id>.json
│   └── quality_report_<run_id>.md
├── celery_app.py           # Celery application configuration
├── config.py               # Database URLs and SMTP config from env vars
├── create_star_schema.py   # One-shot schema initialisation script
├── etl_pipeline.py         # Main pipeline orchestrator (CLI entry point)
├── trigger_setup.py        # CLI to install / remove / status DB triggers
├── sample_data.py          # Seed script for development/testing
├── requirements.txt        # Python dependencies
├── Dockerfile              # Container image for all ETL services
└── ETL.md                  # This document
```

---

## 3. Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  AWS RDS — insightflow_app (OLTP)                                           │
│                                                                             │
│  "posTransactionLine"  ─── INSERT ──► pg_notify('etl_trigger')             │
│  "onlineOrderLine"     ─── INSERT ──► pg_notify('etl_trigger')             │
│  "feedbackSurvey"      ─── INSERT ──► pg_notify('etl_trigger')             │
│  "inventory"           ─── INSERT/UPDATE ──► pg_notify('etl_trigger')     │
└─────────────────────────────────────────────────────────────────────────────┘
         │  NOTIFY
         ▼
┌─────────────────────┐      ┌──────────────────────────────────────────┐
│  etl-listener       │      │  Redis (db/1)                            │
│                     │─────►│  etl:pending_task_id  (debounce key)     │
│  - LISTEN loop      │      │  etl:run_lock          (execution lock)  │
│  - 5-min debounce   │      └──────────────────────────────────────────┘
│  - revoke / reschedule      │  Celery queue: etl
└─────────────────────┘      │
                             ▼
                    ┌─────────────────────┐
                    │  etl-worker         │
                    │  (Celery, 1 thread) │
                    └──────────┬──────────┘
                               │  run_pipeline()
                               ▼
              ┌────────────────────────────────────┐
              │  ETL Pipeline                      │
              │                                    │
              │  1. EXTRACT      (OLTP → DataFrames)│
              │  2. QUALITY CHECK (score + anomaly) │
              │  3. CLEANSE      (business rules)   │
              │  4. LOAD DIMS    (upsert)            │
              │  5. LOAD FACTS   (insert)            │
              │  6. LINEAGE      (save artefacts)    │
              │  7. EMAIL REPORT (notify data team)  │
              └────────────────────────────────────┘
                               │
                               ▼
              ┌─────────────────────────────────────┐
              │  AWS RDS — insightflow_warehouse     │
              │  (OLAP star schema)                  │
              └─────────────────────────────────────┘
```

---

## 4. Pipeline stages

The pipeline is orchestrated in `etl_pipeline.py::run_pipeline()`.
Each stage records a `LineageEvent` tagged with a `LineageStage` constant.

| # | Stage | `LineageStage` constant | What happens |
|---|---|---|---|
| 1 | **Extract** | `EXTRACT` | SQL queries pull raw rows from OLTP into pandas DataFrames. The watermark (`etl/state.py`) filters to rows newer than the last successful load. |
| 2 | **Quality check** | `QUALITY_CHECK` | Per-source rule suites score every row. IQR statistical outlier detection scans numeric columns. Alerts are raised; the pipeline **aborts** if a source score falls below its threshold. |
| 3 | **Cleanse** | `CLEANSE` | Null key rows are dropped. Negative discounts are clamped to 0. `grossAmount` and `netAmount` are recomputed. Product names are title-cased. |
| 4 | **Load dimensions** | `LOAD_DIMENSION` | Dimension rows are upserted. `dimProduct` and `dimCustomer` use SCD Type 2 (old row expired, new row inserted on attribute change). All others use `ON CONFLICT DO NOTHING`. |
| 5 | **Load facts** | `LOAD_FACT` | Surrogate keys resolved from dimension maps. Fact rows inserted. Rows with missing required FKs are skipped. |
| 6 | **Save lineage** | — | Raw event log and grouped report written to `lineage/`. |
| 7 | **Email report** | — | Markdown quality/anomaly report saved and emailed. |

All database writes (stages 4–5) execute within a **single transaction**.
If the pipeline aborts at any earlier stage, no warehouse writes occur.

### Watermark logic

The watermark is derived directly from the warehouse — no separate state table:

```python
# etl/state.py
SELECT MAX(d."fullDate")
FROM "dimDate" d
WHERE EXISTS (SELECT 1 FROM "factSales" fs WHERE fs."dateKey" = d."dateKey")
   OR EXISTS (SELECT 1 FROM "factFeedback" ff WHERE ff."dateKey" = d."dateKey")
   OR EXISTS (SELECT 1 FROM "factInventorySnapshot" fi WHERE fi."dateKey" = d."dateKey")
```

`None` on first run → full load. Subsequent runs extract only records on or
after this date.

---

## 5. Data sources and extraction

All extraction logic lives in `etl/extract.py::Extractor`.

### POS transactions

**OLTP tables:** `"posTransaction"` JOIN `"posTransactionLine"` + `"store"` +
`"cashier"` + `"product"` + `"category"`

Extracts one row per line item. `since` filter applied to
`"posTransaction"."transactionDatetime"`.

Key columns extracted: `lineId`, `sourceTransactionId`, `transactionDatetime`,
`storeId`, `storeName`, `province`, `cashierId`, `cashierName`, `productSKU`,
`productName`, `categoryName`, `quantity`, `unitPrice`, `discountApplied`,
`totalAmount`

### Online orders

**OLTP tables:** `"onlineOrder"` JOIN `"onlineOrderLine"` + `"customer"` +
`"users"` + `"product"` + `"category"`

Extracts one row per line item. `since` filter applied to
`"onlineOrder"."orderDatetime"`.

Additional columns: `orderStatus`, `paymentMethod`, `customerId`,
`customerName`, `email`, `shippingProvince`

### Feedback surveys

**OLTP tables:** `"feedbackSurvey"` JOIN `"customer"` + `"users"` +
`"onlineOrder"`

`since` filter applied to `"feedbackSurvey"."submissionDate"`.

Key columns: `responseId`, `submissionDate`, `satisfactionScore`, `npsScore`,
`productRating`, `deliveryRating`, `freeTextComments`, `sourceOrderId`,
`customerId`, `customerName`, `email`, `province`

### Inventory snapshot

**OLTP tables:** `"inventory"` JOIN `"product"` + `"category"` + `"store"`

Takes a daily snapshot — no incremental filter. `daysSinceRestock` is computed
from the snapshot date.

---

## 6. Data quality and anomaly detection

Quality is implemented in `etl/quality.py`.

### Rule-based scoring — `DataQualityChecker`

Each source has a canonical rule suite applied by `score_source(df, source)`.
Rules mirror the backend validators in
`backend/apps/ingestion/validators/` to enforce consistent constraints
across the stack.

#### Quality thresholds

| Source | Threshold | Below threshold |
|---|---|---|
| `posTransactions` | 95% | Pipeline aborts — no warehouse write |
| `onlineOrders` | 95% | Pipeline aborts |
| `feedback` | 90% | Pipeline aborts |
| `inventory` | 98% | Pipeline aborts |

#### POS transactions — 7 rules

| Rule | Check |
|---|---|
| `null_keys` | `sourceTransactionId` and `productSKU` not null |
| `positive_quantities` | `quantity > 0` |
| `positive_prices` | `unitPrice > 0` |
| `date_not_future` | `transactionDatetime ≤ today` |
| `discount_range` | `0 ≤ discountApplied < unitPrice` |
| `total_consistency` | `\|totalAmount − (qty × price − discount)\| ≤ 0.01` |
| `cashier_id_positive_int` | `cashierId` parses as integer > 0 |

#### Online orders — 7 rules

| Rule | Check |
|---|---|
| `null_keys` | `sourceTransactionId` and `productSKU` not null |
| `positive_quantities` | `quantity > 0` |
| `positive_prices` | `unitPrice > 0` |
| `date_not_future` | `transactionDatetime ≤ today` |
| `discount_range` | `0 ≤ discountApplied < unitPrice` |
| `order_status_valid` | `orderStatus` in accepted set |
| `payment_method_present` | `paymentMethod` not null / not empty |

#### Feedback surveys — 6 rules

| Rule | Check |
|---|---|
| `null_keys` | `customerId` and `sourceOrderId` not null |
| `date_not_future` | `submissionDate ≤ today` |
| `satisfaction_score_range` | `satisfactionScore` in [1, 10] |
| `nps_score_range` | `npsScore` in [0, 10] |
| `product_rating_range` | `productRating` in [1, 5] |
| `delivery_rating_range` | `deliveryRating` in [1, 5] |

#### Inventory — 2 rules

| Rule | Check |
|---|---|
| `null_keys` | `productSKU` not null |
| `positive_quantities` | `stockQuantity > 0` |

### Statistical anomaly detection — `AnomalyDetector`

After rule-based scoring, IQR outlier detection runs on the numeric columns
listed below. An outlier is any value outside `[Q1 − 1.5×IQR, Q3 + 1.5×IQR]`.

| Source | Columns scanned |
|---|---|
| `posTransactions` | `quantity`, `unitPrice`, `discountApplied`, `totalAmount` |
| `onlineOrders` | `quantity`, `unitPrice`, `discountApplied`, `totalAmount` |
| `feedback` | `satisfactionScore`, `npsScore`, `productRating`, `deliveryRating` |
| `inventory` | `stockQuantity`, `daysSinceRestock` |

Outliers are flagged as **WARNING** alerts — they never abort the pipeline but
are visible in the quality report email.

`AnomalyDetector` also exposes `detect_zscore_outliers()` (threshold = 3σ) and
`detect_volume_spike()` (flags batch-size deviations from a baseline) for use
in custom scripts.

### `SourceQualityReport`

`score_source()` returns a `SourceQualityReport` dataclass with:

- `overall_score` — fraction of fully-passing rows (0–1)
- `rule_scores` — per-rule pass rates
- `anomalies` — per-row failure records
- `flagged_outliers` — IQR outlier row indices per column
- `is_critical()` — True when `overall_score < threshold`
- `to_dict()` — serialisable summary for lineage and email

---

## 7. Transformation

Transformation logic lives in `etl/transform.py::Transformer`.
All methods are pure pandas — no database I/O.

| Method | Output | Notes |
|---|---|---|
| `cleanse_sales(df)` | Cleansed sales DataFrame | Drops null keys, clamps discount, recomputes amounts |
| `build_dim_date(dates)` | `dimDate` DataFrame | Year, quarter, month, week, day name, weekend flag, public holidays |
| `build_dim_product(df)` | `dimProduct` DataFrame | Deduplicates by SKU; SCD-2 defaults |
| `build_dim_customer(df)` | `dimCustomer` DataFrame | Deduplicates by `customerId`; SCD-2 defaults |
| `build_dim_store(df)` | `dimStore` DataFrame | Deduplicates by `storeId` |
| `build_dim_geography(df)` | `dimGeography` DataFrame | Province + country (default: Rwanda) |

---

## 8. Loading the star schema

Loading is handled by `etl/load.py::Loader`.

### Dimension loading order

Dimensions are loaded before facts so surrogate keys are available for FK
resolution. Order: `dimDate` → `dimProduct` → `dimCustomer` → `dimStore` →
`dimGeography` → `dimChannel` → `dimPaymentMethod` → `dimOrderStatus`

### SCD Type 2 — `dimProduct` and `dimCustomer`

When a product's `productName` or `categoryName` changes:

1. The current row is expired (`validTo = today`, `isCurrent = FALSE`).
2. A new row is inserted (`validFrom = today`, `validTo = NULL`, `isCurrent = TRUE`).

Historical fact rows retain their original `productKey`, preserving the
attribute values that were true at the time of the transaction.

### Fact loading

After all dimension keys are resolved, facts are inserted:

| Fact table | Source | `sourceTransactionId` maps to |
|---|---|---|
| `"factSales"` | POS + Online orders | `posTransactionId` / `onlineOrderId` |
| `"factFeedback"` | Feedback surveys | `feedbackSurvey.responseId` (via `sourceOrderId`) |
| `"factInventorySnapshot"` | Inventory | Snapshot date + `inventoryId` |

Rows with any missing required FK are silently skipped and counted in
`rows_filtered` on the `LOAD_FACT` lineage event.

---

## 9. Event-driven triggering

### PostgreSQL triggers — `etl/triggers.sql`

Four statement-level triggers are installed on the OLTP source database:

| Trigger | Table | Fires on |
|---|---|---|
| `trg_etl_pos` | `"posTransactionLine"` | INSERT |
| `trg_etl_online` | `"onlineOrderLine"` | INSERT |
| `trg_etl_feedback` | `"feedbackSurvey"` | INSERT |
| `trg_etl_inventory` | `"inventory"` | INSERT, UPDATE |

Each calls the shared function `notify_etl_trigger()` which executes
`pg_notify('etl_trigger', TG_TABLE_NAME)`.

`FOR EACH STATEMENT` means one notification per batch insert, not per row.
A bulk upload of 50,000 rows sends exactly one notification.

Install, remove, or inspect triggers via `trigger_setup.py`:

```bash
python trigger_setup.py install   # idempotent — safe to re-run
python trigger_setup.py status    # show installed triggers
python trigger_setup.py remove    # remove all ETL triggers
```

### Listener service — `etl/listener.py`

The `etl-listener` Docker service runs a long-lived Python process that:

1. Opens a `psycopg2` connection to the OLTP DB in `AUTOCOMMIT` mode
   (required for `LISTEN`).
2. Issues `LISTEN etl_trigger;`.
3. Calls `select.select()` in a loop (blocks up to 30 s per iteration).
4. On notification: applies the **debounce** logic via Redis.
5. Reconnects automatically if the DB connection drops.

#### Debounce mechanism

```
Notification received
    │
    ├── Redis key 'etl:pending_task_id' exists?
    │       YES → revoke that Celery task (cancel before it starts)
    │
    └── Schedule run_etl_task(countdown=300s)
        Store new task_id in Redis with TTL=360s
```

If no further notifications arrive for 5 minutes, the task executes.
If another notification arrives within those 5 minutes, the countdown resets.
A burst of 100 rapid inserts still produces exactly one ETL run.

The debounce window is configurable via `ETL_DEBOUNCE_SECONDS`.

### Celery task — `etl/tasks.py`

`run_etl_task` wraps `run_pipeline()` with:

- **Redis distributed lock** (`etl:run_lock`, 1-hour TTL) — prevents two
  workers executing the pipeline simultaneously.
- **Late acknowledgement** (`acks_late=True`) — the task is not acknowledged
  until it completes, so it is re-queued if the worker dies mid-run.
- **Retries** — up to 3 retries with 60-second backoff on any exception.

```python
@app.task(name="etl.run_pipeline", bind=True, max_retries=3,
          acks_late=True, reject_on_worker_lost=True)
def run_etl_task(self):
    # Acquire Redis lock → run_pipeline() → release lock
```

---

## 10. Lineage tracking

Lineage is tracked in `etl/lineage.py`.

### Events

Every pipeline stage records a `LineageEvent`:

```python
@dataclass
class LineageEvent:
    run_id: str          # UUID for this pipeline run
    step: str            # e.g. "extract_pos"
    stage: str           # LineageStage constant
    data_source: str     # "pos" | "online_orders" | "feedback" | "inventory"
    source_table: str
    target_table: str
    source_db: str
    target_db: str
    rows_extracted: int
    rows_loaded: int
    rows_filtered: int   # rows dropped or skipped at this step
    quality_score: float # rows_loaded / rows_extracted
    filters_applied: list[str]
    transformations: list[str]
    timestamp: str
```

### Output artefacts

After each run, three files are written to `lineage/`:

```
lineage_<run_id>.json          # full ordered event log
lineage_report_<run_id>.json   # events grouped by data_source
quality_report_<run_id>.md     # human-readable quality/anomaly report
```

### Querying lineage programmatically

```python
from etl.lineage import LineageTracker

# Get all events for one source in pipeline order
chain = tracker.get_lineage_chain("pos")
# EXTRACT → QUALITY_CHECK → CLEANSE → LOAD_FACT

# Get grouped summary dict
report = tracker.to_report()
# report["sources"]["pos"] → list of stage-level dicts

# Trace a fact row back to its OLTP source
records = tracker.get_source_records("factSales", "POS-00123")
```

---

## 11. Quality report emails

After each pipeline run, `etl/notify.py::send_pipeline_report()`:

1. Builds a Markdown report with five sections: quality scores, rule-level pass
   rates, rule-failure anomalies, IQR outlier counts, and the lineage journey.
2. Saves it as `lineage/quality_report_<run_id>.md` (always).
3. Emails it as an attachment if `SMTP_USER` is set (optional).

Email delivery uses Python's stdlib `smtplib` — no extra packages.
Port 465 → implicit SSL. Port 587 → STARTTLS.

Subject line example:

```
[InsightFlow ETL] Quality Report — 2026-06-03 — WARNING
```

---

## 12. Configuration reference

All settings are loaded from environment variables via `.env`.

### Database

| Variable | Description |
|---|---|
| `DB_HOST` | OLTP source DB hostname (AWS RDS) |
| `DB_PORT` | OLTP port (default `5432`) |
| `DB_NAME` | OLTP database name |
| `DB_USER` | OLTP user |
| `DB_PASSWORD` | OLTP password |
| `WAREHOUSE_DB_HOST` | OLAP warehouse hostname (AWS RDS) |
| `WAREHOUSE_DB_PORT` | Warehouse port (default `5432`) |
| `WAREHOUSE_DB_NAME` | Warehouse database name |
| `WAREHOUSE_DB_USER` | Warehouse user |
| `WAREHOUSE_DB_PASSWORD` | Warehouse password |

### Celery / Redis

| Variable | Description | Default |
|---|---|---|
| `REDIS_URL` | Redis broker and backend URL | `redis://localhost:6379/1` |
| `ETL_DEBOUNCE_SECONDS` | Quiet period before ETL fires after a NOTIFY | `300` |

### Email reporting

| Variable | Description | Default |
|---|---|---|
| `SMTP_HOST` | SMTP server hostname | `smtp.gmail.com` |
| `SMTP_PORT` | SMTP port (465 = SSL, 587 = STARTTLS) | `587` |
| `SMTP_USER` | SMTP auth username / API key | — |
| `SMTP_PASSWORD` | SMTP password or API secret | — |
| `SMTP_FROM` | Verified sender address | falls back to `SMTP_USER` |
| `REPORT_EMAIL_TO` | Recipient address | `okeke.makuochukwu@amalitech.com` |

---

## 13. Running the pipeline

### Prerequisites

```bash
cd data-engineering
pip install -r requirements.txt
cp ../.env.example ../.env   # fill in DB and SMTP credentials
```

### One-off commands

```bash
# Initialise the warehouse schema (idempotent)
python create_star_schema.py

# Install NOTIFY triggers on the OLTP DB
python trigger_setup.py install

# Full pipeline run (ignores watermark)
python etl_pipeline.py --full-reload

# Incremental run from a specific date
python etl_pipeline.py --since 2024-01-01

# Incremental run (auto-detects watermark from warehouse)
python etl_pipeline.py
```

### Running the event-driven services locally

```bash
# Terminal 1 — Celery worker (processes ETL tasks)
celery -A celery_app worker --loglevel=info --queues=etl --concurrency=1

# Terminal 2 — NOTIFY listener (watches OLTP for changes)
python trigger_setup.py install
python -m etl.listener
```

---

## 14. Deployment services

Three data-engineering services are defined in `docker-compose.yml`, all
built from the same `Dockerfile` (`python:3.11-slim`).

| Service | Container | Role | Restart policy |
|---|---|---|---|
| `etl` | `insightflow-etl` | One-shot: initialise schema + first full load | None (exits after run) |
| `etl-listener` | `insightflow-etl-listener` | Long-running: installs triggers, then listens for NOTIFY events and schedules debounced ETL tasks | `unless-stopped` |
| `etl-worker` | `insightflow-etl-worker` | Long-running: Celery worker that executes the ETL pipeline task | `unless-stopped` |

Both `etl-listener` and `etl-worker` load all DB credentials from `env_file: .env`
and only need `redis` as a Docker service dependency — the databases are
external AWS RDS instances.

### Service start-up sequence

```
redis (healthy)
    │
    ├──► etl            → create_star_schema.py → etl_pipeline.py (exits)
    │
    ├──► etl-listener   → trigger_setup.py install → python -m etl.listener
    │
    └──► etl-worker     → celery -A celery_app worker --queues=etl --concurrency=1
```

---

## 15. Observability

### Logs

All pipeline modules log under the `insightflow.*` namespace:

| Logger | Module |
|---|---|
| `insightflow.pipeline` | `etl_pipeline.py` |
| `insightflow.extract` | `etl/extract.py` |
| `insightflow.transform` | `etl/transform.py` |
| `insightflow.load` | `etl/load.py` |
| `insightflow.quality` | `etl/quality.py` |
| `insightflow.lineage` | `etl/lineage.py` |
| `insightflow.alerts` | `etl/alerts.py` |
| `insightflow.notify` | `etl/notify.py` |
| `insightflow.listener` | `etl/listener.py` |
| `insightflow.tasks` | `etl/tasks.py` |

### Quality summary log line

Every run logs a summary for each source:

```
Quality [posTransactions]: score=0.9962 (1835/1842 rows passed)
```

### Lineage artefacts

```
lineage/
├── lineage_<run_id>.json           # full event log — one object per stage
├── lineage_report_<run_id>.json    # grouped by data source
└── quality_report_<run_id>.md      # human-readable; also emailed
```

### Email alert subject

The email subject encodes the run date and health at a glance:

```
[InsightFlow ETL] Quality Report — 2026-06-03 — OK
[InsightFlow ETL] Quality Report — 2026-06-03 — WARNING   ← any score < 99%
[InsightFlow ETL] Quality Report — 2026-06-03 — CRITICAL  ← any source below threshold
```
