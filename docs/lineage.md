# InsightFlow Data Lineage

This document describes how data flows from the Django application database
(**OLTP**) through the ETL pipeline into the analytics warehouse (**OLAP**).
It is written for **backend developers** who need to understand what happens
to data they write, how it is validated, and how to trace a specific record
end-to-end.

---

## Contents

1. [Data flow diagram](#1-data-flow-diagram)
2. [OLTP → OLAP table mapping](#2-oltp--olap-table-mapping)
3. [Pipeline stages](#3-pipeline-stages)
4. [Data quality rules](#4-data-quality-rules)
5. [Anomaly detection](#5-anomaly-detection)
6. [Lineage artefacts on disk](#6-lineage-artefacts-on-disk)
7. [How to trace a specific record](#7-how-to-trace-a-specific-record)
8. [Programmatic lineage queries](#8-programmatic-lineage-queries)
9. [Quality report emails](#9-quality-report-emails)

---

## 1. Data flow diagram

```
OLTP  (insightflow_app)              ETL Pipeline               OLAP  (insightflow_warehouse)
─────────────────────────────────────────────────────────────────────────────────────────────

"posTransaction"          ──┐                               ┌─► "dimDate"
"posTransactionLine"      ──┤   ┌──────────────────────┐   ├─► "dimProduct"      (SCD Type 2)
                            │   │  1. EXTRACT           │   │
"onlineOrder"             ──┤   │  2. QUALITY_CHECK     │   ├─► "dimCustomer"     (SCD Type 2)
"onlineOrderLine"         ──┤   │  3. CLEANSE           │   │
                            │──►│  4. LOAD_DIMENSION    │──►├─► "dimStore"
"feedbackSurvey"          ──┤   │  5. LOAD_FACT         │   │
                            │   │  6. REPORTING (TBD)   │   ├─► "dimGeography"
"inventory"               ──┘   └──────────────────────┘   │
                                                            ├─► "dimChannel"
"product"  + "category" ────────────────────────────────►  │
"store"    + "cashier"  ────────────────────────────────►  ├─► "dimPaymentMethod"
"customer" + "users"    ────────────────────────────────►  │
                                                            ├─► "dimOrderStatus"
                                                            │
                                                            ├─► "factSales"
                                                            ├─► "factFeedback"
                                                            └─► "factInventorySnapshot"
```

The pipeline runs **incrementally**: each run reads only records newer than the
**watermark** (the latest `fullDate` already present in `"dimDate"`).
Pass `--full-reload` to ignore the watermark and reload everything.

---

## 2. OLTP → OLAP table mapping

### Fact tables

| OLAP fact table | Source OLTP tables | Join key | Channel |
|---|---|---|---|
| `"factSales"` | `"posTransaction"` + `"posTransactionLine"` | `posTransactionId` | POS |
| `"factSales"` | `"onlineOrder"` + `"onlineOrderLine"` | `onlineOrderId` | Online |
| `"factFeedback"` | `"feedbackSurvey"` + `"customer"` + `"users"` + `"onlineOrder"` | `customerId` / `onlineOrderId` | — |
| `"factInventorySnapshot"` | `"inventory"` + `"product"` + `"category"` + `"store"` | `productSKU` | — |

### Dimension tables

| OLAP dimension | Source OLTP tables | Type | Notes |
|---|---|---|---|
| `"dimDate"` | Derived from timestamps | Static | Year, quarter, month, week, day name, public holidays |
| `"dimProduct"` | `"product"` + `"category"` | **SCD Type 2** | Expires old row on name/category change |
| `"dimCustomer"` | `"customer"` + `"users"` | **SCD Type 2** | Expires old row on name/email change |
| `"dimStore"` | `"store"` | Static | `storeId`, `storeName`, `province` |
| `"dimGeography"` | `"store".province` / `"onlineOrder".shippingProvince` | Static | Province + country (default: Rwanda) |
| `"dimChannel"` | Hardcoded | Static | `POS` (In-Store), `Online` (E-Commerce) |
| `"dimPaymentMethod"` | `"onlineOrder".paymentMethod` | Static | Populated from distinct values in each run |
| `"dimOrderStatus"` | `"onlineOrder".orderStatus` | Static | Populated from distinct values in each run |

### Column mapping — POS transactions

| OLTP column | OLAP column | Transformation |
|---|---|---|
| `"posTransaction"."posTransactionId"` | `"factSales"."sourceTransactionId"` | Cast to `VARCHAR` |
| `"posTransaction"."transactionDatetime"` | `"factSales"."dateKey"` → `"dimDate"` | Date extracted; surrogate key resolved |
| `"posTransaction"."storeId"` | `"factSales"."storeKey"` → `"dimStore"` | Surrogate key resolved |
| `"posTransaction"."cashierId"` | _(not stored)_ | Used only for quality validation |
| `"posTransactionLine"."productSKU"` | `"factSales"."productKey"` → `"dimProduct"` | Surrogate key resolved |
| `"posTransactionLine"."quantity"` | `"factSales"."quantity"` | Validated > 0 |
| `"posTransactionLine"."unitPrice"` | `"factSales"."unitPrice"` | Validated > 0 |
| `"posTransactionLine"."discountApplied"` | `"factSales"."discountApplied"` | Clamped to ≥ 0 |
| `"posTransactionLine"."totalAmount"` | `"factSales"."netAmount"` | Recomputed: `qty × price − discount` |
| _(derived)_ | `"factSales"."grossAmount"` | Computed: `qty × unitPrice` |
| _(hardcoded)_ | `"factSales"."channelKey"` → `"dimChannel"."POS"` | Surrogate key resolved |

### Column mapping — Online orders

| OLTP column | OLAP column | Transformation |
|---|---|---|
| `"onlineOrder"."onlineOrderId"` | `"factSales"."sourceTransactionId"` | Cast to `VARCHAR` |
| `"onlineOrder"."orderDatetime"` | `"factSales"."dateKey"` → `"dimDate"` | Surrogate key resolved |
| `"onlineOrder"."shippingProvince"` | `"factSales"."geographyKey"` → `"dimGeography"` | Surrogate key resolved |
| `"onlineOrder"."orderStatus"` | `"factSales"."orderStatusKey"` → `"dimOrderStatus"` | Validated against accepted set |
| `"onlineOrder"."paymentMethod"` | `"factSales"."paymentMethodKey"` → `"dimPaymentMethod"` | Must be non-null |
| `"customer"."customerId"` | `"factSales"."customerKey"` → `"dimCustomer"` | Surrogate key resolved |
| `"users"."username"` | `"dimCustomer"."fullName"` | Title-cased |
| `"users"."email"` | `"dimCustomer"."email"` | Stored as-is |

### Column mapping — Feedback surveys

| OLTP column | OLAP column | Transformation |
|---|---|---|
| `"feedbackSurvey"."submissionDate"` | `"factFeedback"."dateKey"` → `"dimDate"` | Surrogate key resolved |
| `"feedbackSurvey"."satisfactionScore"` | `"factFeedback"."satisfactionScore"` | Validated 1–10 |
| `"feedbackSurvey"."npsScore"` | `"factFeedback"."npsScore"` | Validated 0–10 |
| `"feedbackSurvey"."productRating"` | `"factFeedback"."productRating"` | Validated 1–5 |
| `"feedbackSurvey"."deliveryRating"` | `"factFeedback"."deliveryRating"` | Validated 1–5 |
| `"feedbackSurvey"."freeTextComments"` | `"factFeedback"."hasFreeText"` | `TRUE` if non-empty |
| `"feedbackSurvey"."onlineOrderId"` | `"factFeedback"."sourceOrderId"` | Cast to `VARCHAR` |
| `"customer"."customerId"` | `"factFeedback"."customerKey"` → `"dimCustomer"` | Surrogate key resolved |

---

## 3. Pipeline stages

Every source passes through the stages below in order.  Each stage records a
`LineageEvent` (see [section 6](#6-lineage-artefacts-on-disk)).

| # | Stage constant | What happens | Rows affected |
|---|---|---|---|
| 1 | `EXTRACT` | SQL query runs against `insightflow_app`.  `since` filter applied for incremental loads. | `rows_extracted` = raw OLTP rows |
| 2 | `QUALITY_CHECK` | 6–7 rule-based checks + IQR statistical outlier scan (see sections 4–5).  Pipeline **aborts** if the source score falls below its threshold. | `rows_filtered` = rows failing ≥ 1 rule |
| 3 | `CLEANSE` | Null key rows dropped.  Negative discounts clamped to 0.  `grossAmount` and `netAmount` recomputed.  Product names title-cased. | `rows_filtered` = rows dropped |
| 4 | `LOAD_DIMENSION` | Dimension rows upserted (`ON CONFLICT DO NOTHING`, or SCD-2 expiry for `"dimProduct"` / `"dimCustomer"`).  Surrogate keys fetched for FK resolution. | Idempotent — safe to re-run |
| 5 | `LOAD_FACT` | Fact rows inserted after FK resolution.  Rows missing required FKs are skipped silently. | `rows_filtered` = rows skipped (missing FK) |
| 6 | `REPORTING` | Downstream metric refresh — **not yet implemented**; stage is reserved. | N/A |

All database writes (steps 4–5) run inside **a single transaction**.  If the
pipeline aborts at any stage, the transaction rolls back — the warehouse is
never left in a partial state.

---

## 4. Data quality rules

Rules are in `data-engineering/etl/quality.py` and intentionally mirror the
backend validators in `backend/apps/ingestion/validators/` so the two layers
enforce the same constraints.

### Quality thresholds

| Source | Threshold | Pipeline behaviour below threshold |
|---|---|---|
| `posTransactions` | **95%** | Abort with `RuntimeError` (no warehouse write) |
| `onlineOrders` | **95%** | Abort with `RuntimeError` |
| `feedback` | **90%** | Abort with `RuntimeError` |
| `inventory` | **98%** | Abort with `RuntimeError` |

### POS transactions — 7 rules

| Rule | What is checked | Mirrors backend validator |
|---|---|---|
| `null_keys` | `sourceTransactionId` + `productSKU` must not be null | `validate_pos_file_columns` |
| `positive_quantities` | `quantity > 0` | `validate_pos_row` → `quantity` |
| `positive_prices` | `unitPrice > 0` | `validate_pos_row` → `unit_price` |
| `date_not_future` | `transactionDatetime ≤ today` | `validate_pos_row` → `date` |
| `discount_range` | `0 ≤ discountApplied < unitPrice` | `validate_pos_row` → `discount_applied` |
| `total_consistency` | `\|totalAmount − (qty × price − discount)\| ≤ 0.01` | Derived from POS validator arithmetic |
| `cashier_id_positive_int` | `cashierId` parses as integer > 0 | `validate_pos_row` → `cashier_id` |

### Online orders — 7 rules

| Rule | What is checked |
|---|---|
| `null_keys` | `sourceTransactionId` + `productSKU` not null |
| `positive_quantities` | `quantity > 0` |
| `positive_prices` | `unitPrice > 0` |
| `date_not_future` | `transactionDatetime ≤ today` |
| `discount_range` | `0 ≤ discountApplied < unitPrice` |
| `order_status_valid` | `orderStatus` ∈ `{pending, processing, shipped, delivered, cancelled, refunded}` |
| `payment_method_present` | `paymentMethod` not null / not empty |

### Feedback surveys — 6 rules

| Rule | What is checked |
|---|---|
| `null_keys` | `customerId` + `sourceOrderId` not null |
| `date_not_future` | `submissionDate ≤ today` |
| `satisfaction_score_range` | `satisfactionScore` ∈ [1, 10] |
| `nps_score_range` | `npsScore` ∈ [0, 10] |
| `product_rating_range` | `productRating` ∈ [1, 5] |
| `delivery_rating_range` | `deliveryRating` ∈ [1, 5] |

### Inventory — 2 rules

| Rule | What is checked |
|---|---|
| `null_keys` | `productSKU` not null |
| `positive_quantities` | `stockQuantity > 0` |

---

## 5. Anomaly detection

After rule-based checks, `AnomalyDetector` runs **IQR (Interquartile Range)**
outlier detection on numeric columns.  A row is flagged when its value falls
outside `[Q1 − 1.5 × IQR, Q3 + 1.5 × IQR]`.

Outlier rows are registered as **WARNING** alerts — they never abort the
pipeline but are visible in the quality report email.

| Source | Columns scanned for IQR outliers |
|---|---|
| `posTransactions` | `quantity`, `unitPrice`, `discountApplied`, `totalAmount` |
| `onlineOrders` | `quantity`, `unitPrice`, `discountApplied`, `totalAmount` |
| `feedback` | `satisfactionScore`, `npsScore`, `productRating`, `deliveryRating` |
| `inventory` | `stockQuantity`, `daysSinceRestock` |

**What triggers a flag:**  an unusually large `unitPrice` (possible data entry
error or test record), a bulk `quantity` spike, or a `satisfactionScore` of 0
(outside the valid 1–10 range in the source data before rule checks run).

---

## 6. Lineage artefacts on disk

Three files are written to `data-engineering/lineage/` after each run:

```
data-engineering/lineage/
├── lineage_<run_id>.json           # raw event log — one object per stage/source
├── lineage_report_<run_id>.json    # grouped summary — keyed by data source
└── quality_report_<run_id>.md      # Markdown quality/anomaly report (also emailed)
```

### `lineage_<run_id>.json` — event object format

```jsonc
{
  "run_id": "3f7b2a1c-...",
  "step": "extract_pos",
  "stage": "extract",          // extract | quality_check | cleanse
                               // load_dimension | load_fact | reporting
  "data_source": "pos",        // pos | online_orders | feedback | inventory
  "source_table": "pos",
  "target_table": "DataFrame",
  "source_db": "insightflow_app",
  "target_db": "memory",
  "rows_extracted": 5000,
  "rows_loaded": 5000,
  "rows_filtered": 0,          // rows dropped or skipped at this step
  "quality_score": 1.0,        // rows_loaded / rows_extracted
  "filters_applied": ["since=2024-03-01"],
  "transformations": [],
  "timestamp": "2026-06-03T14:30:00+00:00"
}
```

### `lineage_report_<run_id>.json` — grouped summary

```jsonc
{
  "run_id": "3f7b2a1c-...",
  "total_events": 18,
  "generated_at": "2026-06-03T14:31:00+00:00",
  "sources": {
    "pos":           [ /* EXTRACT → QUALITY_CHECK → CLEANSE events */ ],
    "online_orders": [ /* EXTRACT → QUALITY_CHECK → CLEANSE events */ ],
    "feedback":      [ /* EXTRACT → QUALITY_CHECK events */ ],
    "inventory":     [ /* EXTRACT → QUALITY_CHECK events */ ],
    "unknown":       [ /* LOAD_FACT events from Loader (no data_source tag) */ ]
  }
}
```

> **Note on `"unknown"` events:** `Loader` writes `LineageEvent` objects for
> `LOAD_FACT` without a `data_source` field (it processes a merged DataFrame).
> These appear under `"unknown"` in the grouped report.  They carry the
> `quality_score = rows_loaded / rows_extracted` ratio that matters most for
> warehouse accuracy.

---

## 7. How to trace a specific record

**Example:** POS transaction `posTransactionId = 12345` was written to
`insightflow_app`.  Did it reach the warehouse?

### Step 1 — Find the relevant pipeline run

```bash
ls data-engineering/lineage/lineage_report_*.json
```

Open the most recent file (or the one whose `since` date covers the transaction
date).  Look at `sources.pos[0].filters_applied` to confirm the watermark
window.

### Step 2 — Check extract count

In `sources.pos`, find the `extract` event.
- `rows_extracted` should include your transaction.  If it's unexpectedly low,
  the watermark may have excluded it — re-run with `--full-reload`.

### Step 3 — Check quality drop

Find the `quality_check` event for `pos`.
- `rows_filtered > 0` means some rows failed validation.
- Open `quality_report_<run_id>.md` to see which rules failed and how many rows
  were affected.  If the total failed rows is small and `posTransactionId=12345`
  happened to have a malformed `cashierId` or mismatched `totalAmount`, it may
  have been flagged here.

### Step 4 — Check the warehouse

```sql
SELECT *
FROM   "factSales"
WHERE  "sourceTransactionId" = '12345';
```

If the row is absent and it passed quality, look at `load_fact.rows_filtered`
in the grouped report — this counts rows skipped during FK resolution (e.g.
the transaction's `storeId` was missing from `"dimStore"`).

### Step 5 — Trace programmatically

```python
from etl.lineage import LineageTracker

records = tracker.get_source_records("factSales", "12345")
for r in records:
    print(r)
# {source_table, step, run_id, source_db, target_db, timestamp}
```

---

## 8. Programmatic lineage queries

```python
import json
from pathlib import Path
from etl.lineage import LineageTracker

# --- A. Load a saved run from disk ---
run_id = "3f7b2a1c-..."
events = json.loads(
    (Path("data-engineering/lineage") / f"lineage_{run_id}.json").read_text()
)
# events is a list of dicts, one per stage per source

# --- B. Query a live tracker inside the pipeline ---
chain = tracker.get_lineage_chain("pos")
# Returns LineageEvent objects in stage order:
# EXTRACT → QUALITY_CHECK → CLEANSE → LOAD_DIMENSION → LOAD_FACT

for event in chain:
    print(
        f"{event.stage:<15} "
        f"extracted={event.rows_extracted:>6}  "
        f"loaded={event.rows_loaded:>6}  "
        f"filtered={event.rows_filtered:>4}  "
        f"quality={event.quality_score:.2%}"
    )

# --- C. Get the full grouped summary ---
report = tracker.to_report()
# report["sources"]["pos"]  → list of stage-level event dicts for POS
# report["sources"]["online_orders"]  → same for online orders
```

---

## 9. Quality report emails

At the end of each pipeline run, a Markdown quality/anomaly report is:

1. **Always saved to disk** at `data-engineering/lineage/quality_report_<run_id>.md`.
2. **Emailed** as an attachment when `SMTP_USER` is set in the environment.

Email is implemented in `data-engineering/etl/notify.py` using Python's
stdlib `smtplib` — no extra packages are required.

### Environment variables

| Variable | Description | Current value |
|---|---|---|
| `SMTP_HOST` | SMTP server hostname | `pro.turbo-smtp.com` |
| `SMTP_PORT` | SMTP port (SSL) | `465` |
| `SMTP_USER` | TurboSMTP API key (**required to enable email**) | set in `.env` |
| `SMTP_PASSWORD` | TurboSMTP API secret | set in `.env` |
| `SMTP_FROM` | Verified sender address | `okeke.makuochukwu@amalitechtraining.org` |
| `REPORT_EMAIL_TO` | Report recipient address | `okeke.makuochukwu@amalitech.com` |

> **TurboSMTP note:** `SMTP_USER` and `SMTP_PASSWORD` are the API credentials
> from your TurboSMTP account. `SMTP_FROM` must be a sender address verified
> in your TurboSMTP account — it is separate from the API key used for auth.
> Port 465 uses implicit SSL (`SMTP_SSL`); port 587 uses STARTTLS.

### Report attachment contents

The `.md` attachment includes:

| Section | What you see |
|---|---|
| Quality scores table | Total/passed/failed rows + overall score per source |
| Rule-level pass rates | Per-rule pass % with ASCII progress bar |
| Rule-failure anomalies | Count of rows failing each rule |
| Statistical outliers | IQR-flagged row counts per numeric column |
| Lineage journey | Stage × rows extracted/loaded/filtered/quality score |

The email subject reads:

```
[InsightFlow ETL] Quality Report — 2026-06-03 — OK
```

where the badge is `OK`, `WARNING` (any score < 99%), or `CRITICAL` (any
source below its quality threshold).
