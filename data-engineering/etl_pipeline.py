"""InsightFlow ETL Pipeline — main orchestrator.

Usage
-----
    python etl_pipeline.py                      # full load
    python etl_pipeline.py --since 2024-01-01   # incremental load

The pipeline:
1.  Creates engines for the OLTP source and OLAP warehouse.
2.  Extracts four datasets (POS sales, online orders, feedback, inventory).
3.  Runs data-quality checks; flushes alerts (may abort on CRITICAL quality).
4.  Transforms raw extracts into star-schema shapes.
5.  Loads dimensions (in dependency order), then facts.
6.  Saves a lineage JSON file.
7.  Prints a summary of rows loaded per table.
"""

from __future__ import annotations

import argparse
import logging
import sys
import uuid
from datetime import date, datetime, timezone
from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine

# ---------------------------------------------------------------------------
# Config — gracefully handle both old and new config layouts
# ---------------------------------------------------------------------------
try:
    from config import (  # type: ignore[import]
        SOURCE_DATABASE_URL,
        WAREHOUSE_DATABASE_URL,
    )
except ImportError:
    from config import DATABASE_URL  # type: ignore[import]

    SOURCE_DATABASE_URL = DATABASE_URL
    WAREHOUSE_DATABASE_URL = DATABASE_URL

# ---------------------------------------------------------------------------
# ETL sub-modules
# ---------------------------------------------------------------------------
from etl.alerts import AlertManager, AnomalyAlert
from etl.extract import Extractor
from etl.lineage import LineageStage, LineageTracker  # noqa: F401
from etl.load import Loader
from etl.notify import send_pipeline_report
from etl.quality import AnomalyDetector, DataQualityChecker, SourceQualityReport
from etl.state import get_watermark_date
from etl.transform import Transformer

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s  %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
log = logging.getLogger("insightflow.pipeline")

_LINEAGE_DIR = Path(__file__).parent / "lineage"


# ---------------------------------------------------------------------------
# Quality + anomaly helper
# ---------------------------------------------------------------------------

# Numeric columns to scan for statistical outliers per source
_ANOMALY_COLS: dict[str, list[str]] = {
    "posTransactions": ["quantity", "unitPrice", "discountApplied", "totalAmount"],
    "onlineOrders": ["quantity", "unitPrice", "discountApplied", "totalAmount"],
    "feedback": ["satisfactionScore", "npsScore", "productRating", "deliveryRating"],
    "inventory": ["stockQuantity", "daysSinceRestock"],
}


def _check_source_quality(
    df: pd.DataFrame,
    source: str,
    checker: DataQualityChecker,
    alert_mgr: AlertManager,
    tracker: LineageTracker,
) -> SourceQualityReport:
    """Score quality, detect anomalies, register alerts, record lineage.

    Applies the canonical rule suite via ``DataQualityChecker.score_source()``,
    runs IQR outlier detection, registers ``AnomalyAlert`` objects on
    *alert_mgr*, and records a QUALITY_CHECK lineage event on *tracker*.

    Returns
    -------
    SourceQualityReport
        Callers use this to flush alerts and collect reports for the
        end-of-run email.
    """
    _, report = checker.score_source(df, source)

    # Statistical outlier detection
    detector = AnomalyDetector()
    outlier_cols = _ANOMALY_COLS.get(source, [])
    report.flagged_outliers = detector.scan(df, outlier_cols)

    for col, outlier_idxs in report.flagged_outliers.items():
        sample = [str(df.at[i, col]) for i in outlier_idxs[:3] if i in df.index]
        alert_mgr.add(
            AnomalyAlert(
                table=source,
                rule=f"outlier_{col}",
                affected_rows=len(outlier_idxs),
                sample_values=sample,
                severity="WARNING",
            )
        )

    # Rule-failure alerts
    for anomaly in report.anomalies:
        for rule in anomaly.get("failed_rules", []):
            severity = "CRITICAL" if report.is_critical() else "WARNING"
            alert_mgr.add(
                AnomalyAlert(
                    table=source,
                    rule=rule,
                    affected_rows=report.failed_rows,
                    sample_values=[anomaly.get("row_id")],
                    severity=severity,
                )
            )

    tracker.record_quality(source, report)

    log.info(
        "Quality [%s]: score=%.4f (%d/%d rows passed)%s",
        source,
        report.overall_score,
        report.passed_rows,
        report.total_rows,
        " — CRITICAL" if report.is_critical() else "",
    )
    return report


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------


def run_pipeline(since: date | None = None) -> None:
    """Execute the full InsightFlow ETL pipeline.

    Parameters
    ----------
    since:
        If provided, only rows with a transaction/submission date >= *since*
        are extracted (incremental mode).
    """
    run_id = str(uuid.uuid4())
    snapshot_date = date.today()
    log.info("=" * 60)
    log.info("InsightFlow ETL pipeline starting  run_id=%s", run_id)
    log.info("since=%s  snapshot_date=%s", since, snapshot_date)
    log.info("=" * 60)

    # ------------------------------------------------------------------
    # 1. Engines
    # ------------------------------------------------------------------
    source_engine = create_engine(SOURCE_DATABASE_URL, echo=False)
    warehouse_engine = create_engine(WAREHOUSE_DATABASE_URL, echo=False)

    # Resolve incremental cutoff: explicit --since overrides the watermark;
    # no --since means auto-detect from the latest date already in the
    # warehouse (None on first run triggers a full load).
    if since is None:
        since = get_watermark_date(warehouse_engine)
        log.info("Auto-detected watermark since=%s from warehouse", since)

    # Tracker is created here (before extraction) so extract-stage events
    # can be recorded alongside quality, cleanse, and load events.
    tracker = LineageTracker(run_id=run_id)

    # ------------------------------------------------------------------
    # 2. Extract
    # ------------------------------------------------------------------
    extractor = Extractor(source_engine)
    log.info("Extracting POS transactions …")
    pos_df = extractor.extract_pos_transactions(since=since)
    tracker.record_extraction("pos", rows=len(pos_df), since=since)

    log.info("Extracting online orders …")
    online_df = extractor.extract_online_orders(since=since)
    tracker.record_extraction("online_orders", rows=len(online_df), since=since)

    log.info("Extracting feedback surveys …")
    feedback_df = extractor.extract_feedback(since=since)
    tracker.record_extraction("feedback", rows=len(feedback_df), since=since)

    log.info("Extracting inventory snapshot …")
    inventory_df = extractor.extract_inventory(snapshot_date=snapshot_date)
    tracker.record_extraction("inventory", rows=len(inventory_df), since=None)

    # Combine sales for shared processing
    # Tag channel before combining
    if not pos_df.empty:
        pos_df["channel"] = "POS"
        pos_df["paymentMethod"] = None
        pos_df["orderStatus"] = None
        pos_df["customerId"] = None

    if not online_df.empty:
        online_df["channel"] = "Online"
        online_df["storeId"] = None
        online_df["storeName"] = None
        online_df["cashierId"] = None
        online_df["cashierName"] = None

    # ------------------------------------------------------------------
    # 3. Data quality checks + anomaly detection
    # ------------------------------------------------------------------
    checker = DataQualityChecker()
    quality_reports: list[SourceQualityReport] = []

    if not pos_df.empty:
        alert_mgr_pos = AlertManager()
        pos_report = _check_source_quality(
            pos_df, "posTransactions", checker, alert_mgr_pos, tracker
        )
        quality_reports.append(pos_report)
        if alert_mgr_pos.to_dict():
            alert_mgr_pos.flush(pos_report.to_dict())

    if not online_df.empty:
        alert_mgr_online = AlertManager()
        online_report = _check_source_quality(
            online_df, "onlineOrders", checker, alert_mgr_online, tracker
        )
        quality_reports.append(online_report)
        if alert_mgr_online.to_dict():
            alert_mgr_online.flush(online_report.to_dict())

    if not feedback_df.empty:
        alert_mgr_fb = AlertManager()
        fb_report = _check_source_quality(
            feedback_df, "feedback", checker, alert_mgr_fb, tracker
        )
        quality_reports.append(fb_report)
        if alert_mgr_fb.to_dict():
            alert_mgr_fb.flush(fb_report.to_dict())

    if not inventory_df.empty:
        alert_mgr_inv = AlertManager()
        inv_report = _check_source_quality(
            inventory_df, "inventory", checker, alert_mgr_inv, tracker
        )
        quality_reports.append(inv_report)
        if alert_mgr_inv.to_dict():
            alert_mgr_inv.flush(inv_report.to_dict())

    # ------------------------------------------------------------------
    # 4. Transform
    # ------------------------------------------------------------------
    transformer = Transformer()

    # Cleanse sales dataframes and record how many rows each step dropped
    pos_clean = transformer.cleanse_sales(pos_df) if not pos_df.empty else pos_df
    tracker.record_cleanse(
        "pos",
        rows_before=len(pos_df),
        rows_after=len(pos_clean),
        transformations=[
            "drop_null_keys",
            "title_case_product_name",
            "clamp_negative_discount",
            "recompute_gross_net",
        ],
    )

    online_clean = (
        transformer.cleanse_sales(online_df) if not online_df.empty else online_df
    )
    tracker.record_cleanse(
        "online_orders",
        rows_before=len(online_df),
        rows_after=len(online_clean),
        transformations=[
            "drop_null_keys",
            "title_case_product_name",
            "clamp_negative_discount",
            "recompute_gross_net",
        ],
    )

    # Combine for dimension building
    all_sales = pd.concat(
        [df for df in [pos_clean, online_clean] if not df.empty],
        ignore_index=True,
    )

    # Collect all transaction dates
    all_dates: list[date] = []
    for df, col in [
        (all_sales, "transactionDatetime"),
        (feedback_df, "submissionDate"),
        (inventory_df, None),
    ]:
        if df is not None and not df.empty:
            if col and col in df.columns:
                all_dates.extend(
                    pd.to_datetime(df[col], errors="coerce").dropna().dt.date.tolist()
                )
    all_dates.append(snapshot_date)

    dates_df = transformer.build_dim_date(all_dates)

    products_df = (
        transformer.build_dim_product(all_sales)
        if not all_sales.empty
        else transformer.build_dim_product(inventory_df)
    )

    customers_df = (
        transformer.build_dim_customer(
            pd.concat(
                [
                    df[["customerId", "customerName", "email"]]
                    for df in [online_clean, feedback_df]
                    if not df.empty and "customerId" in df.columns
                ],
                ignore_index=True,
            )
        )
        if (not online_clean.empty or not feedback_df.empty)
        else pd.DataFrame()
    )

    stores_df = (
        transformer.build_dim_store(pos_clean)
        if not pos_clean.empty
        else pd.DataFrame()
    )

    geo_df = (
        transformer.build_dim_geography(all_sales)
        if not all_sales.empty
        else pd.DataFrame()
    )

    # Static lookup rows — ensure they exist
    channel_df = pd.DataFrame(
        [
            {"channelName": "POS", "channelType": "In-Store"},
            {"channelName": "Online", "channelType": "E-Commerce"},
        ]
    )

    payment_methods: list[str] = []
    if not online_clean.empty and "paymentMethod" in online_clean.columns:
        payment_methods = online_clean["paymentMethod"].dropna().unique().tolist()
    payment_df = pd.DataFrame(
        [{"methodName": m, "methodType": "Electronic"} for m in payment_methods]
    )

    order_statuses: list[str] = []
    if not online_clean.empty and "orderStatus" in online_clean.columns:
        order_statuses = online_clean["orderStatus"].dropna().unique().tolist()
    status_df = pd.DataFrame([{"statusName": s} for s in order_statuses])

    # ------------------------------------------------------------------
    # 5. Load — within a single transaction
    # ------------------------------------------------------------------
    loader = Loader(warehouse_engine, tracker)

    rows_loaded: dict[str, int] = {}

    with warehouse_engine.begin() as conn:
        # --- Dimensions ---
        date_map = loader.upsert_dim_date(dates_df, conn)
        rows_loaded["dimDate"] = len(date_map)

        product_map = loader.upsert_dim_product(products_df, conn)
        rows_loaded["dimProduct"] = len(product_map)

        customer_map = (
            loader.upsert_dim_customer(customers_df, conn)
            if not customers_df.empty
            else {}
        )
        rows_loaded["dimCustomer"] = len(customer_map)

        store_map: dict = {}
        if not stores_df.empty:
            store_map_raw = loader.upsert_dim_lookup(
                stores_df,
                "dimStore",
                "storeId",
                conn,
            )
            store_map = {int(k): v for k, v in store_map_raw.items()}
        rows_loaded["dimStore"] = len(store_map)

        geo_map: dict = {}
        if not geo_df.empty:
            geo_map_raw = loader.upsert_dim_lookup(
                geo_df, "dimGeography", "province", conn
            )
            geo_map = geo_map_raw
        rows_loaded["dimGeography"] = len(geo_map)

        channel_map = loader.upsert_dim_lookup(
            channel_df, "dimChannel", "channelName", conn
        )
        rows_loaded["dimChannel"] = len(channel_map)

        payment_map: dict = {}
        if not payment_df.empty:
            payment_map = loader.upsert_dim_lookup(
                payment_df, "dimPaymentMethod", "methodName", conn
            )
        rows_loaded["dimPaymentMethod"] = len(payment_map)

        status_map: dict = {}
        if not status_df.empty:
            status_map = loader.upsert_dim_lookup(
                status_df, "dimOrderStatus", "statusName", conn
            )
        rows_loaded["dimOrderStatus"] = len(status_map)

        # --- Facts ---
        key_maps_sales: dict = {
            "dates": date_map,
            "products": product_map,
            "customers": customer_map,
            "stores": store_map,
            "geographies": geo_map,
            "channels": channel_map,
            "payment_methods": payment_map,
            "order_statuses": status_map,
        }

        n_pos = loader.load_fact_sales(pos_clean, key_maps_sales, conn, tracker, run_id)
        n_online = loader.load_fact_sales(
            online_clean, key_maps_sales, conn, tracker, run_id
        )
        rows_loaded["factSales"] = n_pos + n_online

        rows_loaded["factFeedback"] = loader.load_fact_feedback(
            feedback_df, key_maps_sales, conn, tracker, run_id
        )

        key_maps_inv = {
            "dates": date_map,
            "products": product_map,
            "snapshot_date": snapshot_date,
        }
        rows_loaded["factInventorySnapshot"] = loader.load_fact_inventory(
            inventory_df, key_maps_inv, conn, tracker, run_id
        )

    # ------------------------------------------------------------------
    # 6. Save lineage
    # ------------------------------------------------------------------
    tracker.save(_LINEAGE_DIR)  # raw event log: lineage_<run_id>.json
    tracker.save_report(_LINEAGE_DIR)  # grouped summary: lineage_report_<run_id>.json

    # ------------------------------------------------------------------
    # 6b. Quality/anomaly report — save to disk and email
    # ------------------------------------------------------------------
    send_pipeline_report(
        run_id=run_id,
        quality_reports=[r.to_dict() for r in quality_reports],
        lineage_report=tracker.to_report(),
        output_dir=_LINEAGE_DIR,
    )

    # ------------------------------------------------------------------
    # 7. Summary
    # ------------------------------------------------------------------
    log.info("=" * 60)
    log.info(
        "Pipeline complete  run_id=%s  finished=%s",
        run_id,
        datetime.now(timezone.utc).isoformat(),
    )
    log.info("Rows loaded per table:")
    for tbl, cnt in rows_loaded.items():
        log.info("  %-35s %d", tbl, cnt)
    log.info("=" * 60)

    print("InsightFlow ETL pipeline finished successfully.")
    print(f"run_id: {run_id}")
    for tbl, cnt in rows_loaded.items():
        print(f"  {tbl:<35} {cnt}")


# ---------------------------------------------------------------------------
# Entry-point
# ---------------------------------------------------------------------------


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="InsightFlow ETL pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--since",
        metavar="YYYY-MM-DD",
        help="Incremental load: only process records on or after this date.",
        default=None,
    )
    parser.add_argument(
        "--full-reload",
        action="store_true",
        help="Ignore stored state and reload all records from the beginning.",
    )
    return parser.parse_args(argv)


if __name__ == "__main__":
    args = _parse_args()
    since_date: date | None = None
    if args.full_reload:
        log.info("--full-reload flag set: ignoring stored state, loading all records")
    elif args.since:
        try:
            since_date = date.fromisoformat(args.since)
        except ValueError:
            log.error("Invalid --since value: %r (expected YYYY-MM-DD)", args.since)
            sys.exit(1)
    run_pipeline(since=since_date)
