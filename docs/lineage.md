# InsightFlow Data Lineage

This document describes how data flows from OLTP source tables through the ETL
pipeline into the star-schema warehouse, how data quality is enforced at each
stage, and how individual fact rows can be traced back to their OLTP origin.

Lineage is written **at ETL load time**, not retroactively. Each pipeline run
records a `LineageEvent` for every extract-transform-load step and persists the
full run log to a JSON file under `data-engineering/lineage_runs/` before the
pipeline exits.

---

## Data Flow Diagram

```
OLTP Source DB                ETL Pipeline                Star Schema (OLAP)
──────────────────────────────────────────────────────────────────────────────

posTransaction          ──┐
posTransactionLine      ──┤  Extract            ┌─► dim_date
                          │     │               │
onlineOrder             ──┤     ▼               ├─► dim_product  (SCD2)
onlineOrderLine         ──┤  Quality Check      │
                          │     │               ├─► dim_customer (SCD2)
feedbackSurvey          ──┤     ▼               │
                          │  Transform          ├─► dim_store
inventory               ──┘     │               │
                                ▼               ├─► dim_geography
                             Load  ─────────────┤
                                                ├─► dim_channel
                                                │
                                                ├─► dim_payment_method
                                                │
                                                ├─► dim_order_status
                                                │
                                                ├─► fact_sales
                                                │
                                                ├─► fact_feedback
                                                │
                                                └─► fact_inventory_snapshot
```

---

## Transformation Steps

| Step | Source | Target | Description |
|------|--------|--------|-------------|
| `extract_pos_transactions` | `posTransaction` + `posTransactionLine` | Staging DataFrame | Joins transaction header with line items, store, cashier, product, and category; returns one row per line item with `channel = POS`. |
| `extract_online_orders` | `onlineOrder` + `onlineOrderLine` | Staging DataFrame | Joins order header with line items, customer, users, product, and category; returns one row per line item with `channel = ONLINE`. |
| `extract_feedback` | `feedbackSurvey` | Staging DataFrame | Joins survey responses with customer, users, and the related online order to resolve province. |
| `extract_inventory` | `inventory` | Staging DataFrame | Joins inventory with product, category, and store; computes `days_since_restock` relative to the supplied snapshot date. |
| `cleanse_sales` | Staging DataFrame | Cleansed DataFrame | Drops rows with null `source_transaction_id` or `product_sku`; clamps negative discounts to 0; recomputes `gross_amount = quantity x unit_price` and `net_amount = gross_amount - discount_applied`. |
| `build_dim_date` | List of `date` objects | `dim_date` DataFrame | Generates one row per unique date with year, quarter, month, week number, day name, weekend flag, and public-holiday flag. |
| `build_dim_product` (SCD2) | Cleansed sales DataFrame | `dim_product` DataFrame | Deduplicates by `product_sku`; sets `valid_from = today`, `valid_to = NULL`, `is_current = TRUE`. Historical versions are expired by the loader before inserting new rows. |
| `build_dim_customer` (SCD2) | Cleansed sales DataFrame | `dim_customer` DataFrame | Deduplicates by `customer_id`; sets `valid_from = today`, `valid_to = NULL`, `is_active = TRUE`. |
| `load_fact_sales` | Cleansed sales DataFrame + dimension keys | `fact_sales` | Resolves surrogate keys for all dimensions via lookup; inserts one row per transaction line. Stores `source_transaction_id` for reverse traceability. |
| `load_fact_feedback` | Cleansed feedback DataFrame + dimension keys | `fact_feedback` | Resolves surrogate keys; stores `source_order_id` and converts `free_text_comments` presence to a boolean `has_free_text` flag. |
| `load_fact_inventory_snapshot` | Cleansed inventory DataFrame + dimension keys | `fact_inventory_snapshot` | Inserts a daily snapshot per product/location; sets `is_below_reorder = stock_quantity < reorder_threshold`. |

---

## Data Quality

Quality is scored row-by-row on a **0 to 1 scale**: a row that passes all
checks scores 1.0; each failed check reduces the score proportionally.

### Check types

| Check | Description |
|-------|-------------|
| `check_null_keys` | Required identifier columns (`product_sku`, `customer_id`, etc.) must be non-null. |
| `check_positive_quantities` | `quantity` must be greater than 0. |
| `check_positive_prices` | `unit_price` must be greater than 0. |
| `check_discount_range` | `discount_applied` must be >= 0 and < `unit_price`. |
| `check_date_not_future` | Date columns must be <= today. |
| `check_score_range` | Feedback scores must fall within their defined ranges (e.g. `satisfaction_score` in [1, 10]). |

### Thresholds

The `QUALITY_THRESHOLDS` constant in `etl/quality.py` defines the minimum
acceptable `overall_score` (fraction of fully-passing rows) before a pipeline
run is considered failed:

| Table | Minimum score |
|-------|--------------|
| `fact_sales` | 0.95 |
| `fact_feedback` | 0.90 |
| `fact_inventory_snapshot` | 0.98 |

### Anomaly alerting

`AlertManager` collects `AnomalyAlert` objects during the quality-check phase.
When `AlertManager.flush()` is called:

- If `overall_score >= threshold` — alerts are logged at **WARNING** level and
  the pipeline continues.
- If `overall_score < threshold` — all alerts are promoted to **CRITICAL** and
  a `RuntimeError` is raised, halting the pipeline before any data is loaded.

---

## Metric Traceability

Every row written to a fact table carries a `source_transaction_id` column
that maps back to the originating OLTP identifier:

| Fact table | `source_transaction_id` maps to |
|------------|----------------------------------|
| `fact_sales` (POS) | `posTransaction.posTransactionId` |
| `fact_sales` (ONLINE) | `onlineOrder.onlineOrderId` |
| `fact_feedback` | `feedbackSurvey.responseId` (via `source_order_id`) |
| `fact_inventory_snapshot` | Snapshot date + `inventory.inventoryId` |

To trace a metric back to its source:

1. Note the `source_transaction_id` of the fact row in question.
2. Open the lineage JSON file for the relevant run under
   `data-engineering/lineage_runs/lineage_<run_id>.json`.
3. Or call the helper programmatically:

```python
from etl.lineage import LineageTracker

tracker = LineageTracker(run_id="run-20250101-083000")
# (populate tracker.record(...) calls from the saved JSON, or query directly)
records = tracker.get_source_records("fact_sales", "POS-00123")
# returns a list of dicts: source_table, step, run_id, source_db, timestamp...
```

Lineage JSON files are stored per run under `data-engineering/lineage_runs/`
with the filename pattern `lineage_<run_id>.json`.

---

## Lineage File Format

Each run produces one JSON file containing a list of `LineageEvent` objects.
Example snippet:

```json
[
  {
    "run_id": "run-20250101-083000",
    "step": "extract",
    "source_table": "posTransaction",
    "target_table": "fact_sales",
    "source_db": "insightflow_oltp",
    "target_db": "insightflow_star_schema",
    "rows_extracted": 1842,
    "rows_loaded": 0,
    "quality_score": 1.0,
    "filters_applied": ["transactionDatetime >= 2025-01-01"],
    "transformations": [],
    "timestamp": "2025-01-01T08:30:05.123456+00:00"
  },
  {
    "run_id": "run-20250101-083000",
    "step": "load",
    "source_table": "posTransaction",
    "target_table": "fact_sales",
    "source_db": "insightflow_oltp",
    "target_db": "insightflow_star_schema",
    "rows_extracted": 1842,
    "rows_loaded": 1839,
    "quality_score": 0.9984,
    "filters_applied": [],
    "transformations": [
      "cleanse_sales",
      "build_dim_product",
      "build_dim_customer"
    ],
    "timestamp": "2025-01-01T08:31:12.654321+00:00"
  }
]
```

---

## Running the Pipeline

```bash
python etl_pipeline.py --since 2025-01-01
```

This performs an incremental load: only OLTP rows created on or after
`2025-01-01` are extracted. Omit `--since` for a full historical load.
