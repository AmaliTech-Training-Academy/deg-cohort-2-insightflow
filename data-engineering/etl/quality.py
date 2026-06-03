"""Data quality checks and anomaly detection for the InsightFlow ETL pipeline.

Architecture
------------
``DataQualityChecker``
    Rule-based validation.  Individual ``check_*`` methods return a boolean
    Series (True = row passes).  ``score_dataframe()`` runs an arbitrary list
    of ``(name, check_fn)`` pairs and produces row-level ``QualityScore``
    objects plus an aggregate summary that now includes per-rule pass rates.
    ``score_source()`` is the high-level entry point: it selects the canonical
    rule suite for the named source and wraps results in a
    ``SourceQualityReport``.

``AnomalyDetector``
    Statistical outlier detection.  ``detect_iqr_outliers()`` and
    ``detect_zscore_outliers()`` flag rows where a numeric column falls
    unusually far from the batch distribution.  ``scan()`` runs IQR detection
    across a list of columns in one call.  ``detect_volume_spike()`` checks
    whether the current batch size deviates suspiciously from a baseline.

``SourceQualityReport``
    Immutable per-source summary produced by ``score_source()``.  Contains
    overall and per-rule pass rates, anomaly detail records, and a map of
    statistically-flagged outlier columns.  Includes a threshold-aware
    ``is_critical()`` predicate and a ``to_dict()`` helper for serialisation.

Per-source rule suites
----------------------
Rule suites mirror the backend ingestion validators
(``backend/apps/ingestion/validators/``) so the data-engineering layer enforces
the same constraints as the API:

  posTransactions  — 7 rules:
    null_keys, positive_quantities, positive_prices, date_not_future,
    discount_range, total_consistency, cashier_id_positive_int

  onlineOrders     — 7 rules:
    null_keys, positive_quantities, positive_prices, date_not_future,
    discount_range, order_status_valid, payment_method_present

  feedback         — 6 rules:
    null_keys, date_not_future, satisfaction_score_range, nps_score_range,
    product_rating_range, delivery_rating_range

  inventory        — 2 rules:
    null_keys, positive_quantities
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from typing import Any, Callable

import pandas as pd

log = logging.getLogger("insightflow.quality")

# ---------------------------------------------------------------------------
# Minimum acceptable quality scores per table (0–1)
# ---------------------------------------------------------------------------
QUALITY_THRESHOLDS: dict[str, float] = {
    "posTransactions": 0.95,
    "onlineOrders": 0.95,
    "feedback": 0.90,
    "inventory": 0.98,
    "factSales": 0.95,
    "factFeedback": 0.90,
    "factInventorySnapshot": 0.98,
}

# Accepted categorical values derived from backend validators
_VALID_ORDER_STATUSES: frozenset[str] = frozenset(
    {"pending", "processing", "shipped", "delivered", "cancelled", "refunded"}
)


def _utc_now() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass
class QualityScore:
    row_id: Any
    table: str
    passed_checks: int
    total_checks: int
    score: float
    failed_rules: list[str] = field(default_factory=list)


@dataclass
class SourceQualityReport:
    """Aggregate data-quality report for a single ingestion source.

    Produced by ``DataQualityChecker.score_source()`` and used for lineage
    recording, alert routing, and pipeline observability.

    Attributes
    ----------
    source:
        Source name — one of ``posTransactions``, ``onlineOrders``,
        ``feedback``, ``inventory``.
    total_rows:
        Number of rows evaluated.
    passed_rows:
        Rows where every check passed.
    failed_rows:
        Rows where at least one check failed.
    overall_score:
        ``passed_rows / total_rows``; 0–1 (1.0 = perfect).
    rule_scores:
        Per-rule pass rate: ``{rule_name: fraction_of_rows_that_passed}``.
    anomalies:
        Per-row anomaly records from ``score_dataframe()``.  Each dict
        contains ``row_id``, ``failed_rules``, and ``score``.
    flagged_outliers:
        Statistical outliers from ``AnomalyDetector.scan()``.  Maps column
        name → list of row indices where values are extreme.  Populated by
        the pipeline after calling ``score_source()``; empty by default.
    generated_at:
        UTC ISO timestamp when this report was produced.
    """

    source: str
    total_rows: int
    passed_rows: int
    failed_rows: int
    overall_score: float
    rule_scores: dict[str, float]
    anomalies: list[dict[str, Any]]
    flagged_outliers: dict[str, list[int]] = field(default_factory=dict)
    generated_at: str = field(default_factory=_utc_now)

    def is_critical(self) -> bool:
        """Return True when ``overall_score`` is below this source's threshold."""
        return self.overall_score < QUALITY_THRESHOLDS.get(self.source, 0.95)

    def to_dict(self) -> dict[str, Any]:
        """Serialise to a plain dict suitable for JSON logging."""
        return {
            "source": self.source,
            "total_rows": self.total_rows,
            "passed_rows": self.passed_rows,
            "failed_rows": self.failed_rows,
            "overall_score": round(self.overall_score, 4),
            "is_critical": self.is_critical(),
            "rule_scores": {k: round(v, 4) for k, v in self.rule_scores.items()},
            "anomaly_count": len(self.anomalies),
            "outlier_columns": {
                col: len(idxs) for col, idxs in self.flagged_outliers.items()
            },
            "generated_at": self.generated_at,
        }


# ---------------------------------------------------------------------------
# Statistical anomaly detection
# ---------------------------------------------------------------------------


class AnomalyDetector:
    """Detect statistically unusual values in incoming data batches.

    Methods
    -------
    detect_iqr_outliers(df, col, multiplier=1.5)
        Flag rows where *col* falls outside ``[Q1 - k·IQR, Q3 + k·IQR]``.
    detect_zscore_outliers(df, col, threshold=3.0)
        Flag rows where ``|z-score|`` of *col* exceeds *threshold*.
    scan(df, numeric_cols)
        Run IQR detection on every column in *numeric_cols*; return a dict
        mapping column name → list of outlier row indices.
    detect_volume_spike(current, baseline, threshold=0.5)
        Return ``(is_anomaly, ratio)`` where
        ``ratio = |current - baseline| / baseline``.

    Notes
    -----
    IQR is preferred over z-score for small or skewed distributions.
    Both methods require at least four non-null values; smaller batches
    return an empty list.
    """

    @staticmethod
    def detect_iqr_outliers(
        df: pd.DataFrame,
        col: str,
        multiplier: float = 1.5,
    ) -> list[int]:
        """Return row indices where *col* is an IQR outlier.

        Parameters
        ----------
        df:
            Input DataFrame.
        col:
            Numeric column to inspect.
        multiplier:
            IQR fence multiplier (1.5 = mild outlier, 3.0 = extreme).
        """
        if col not in df.columns:
            return []
        numeric = pd.to_numeric(df[col], errors="coerce")
        valid = numeric.dropna()
        if len(valid) < 4:
            return []
        q1, q3 = float(valid.quantile(0.25)), float(valid.quantile(0.75))
        iqr = q3 - q1
        if iqr == 0:
            return []
        lower, upper = q1 - multiplier * iqr, q3 + multiplier * iqr
        mask = (numeric < lower) | (numeric > upper)
        outliers: list[int] = [int(i) for i in df.index[mask.fillna(False)]]
        if outliers:
            log.debug(
                "IQR outliers in '%s': %d rows (fence=[%.2f, %.2f])",
                col,
                len(outliers),
                lower,
                upper,
            )
        return outliers

    @staticmethod
    def detect_zscore_outliers(
        df: pd.DataFrame,
        col: str,
        threshold: float = 3.0,
    ) -> list[int]:
        """Return row indices where ``|z-score|`` of *col* exceeds *threshold*.

        Parameters
        ----------
        df:
            Input DataFrame.
        col:
            Numeric column to inspect.
        threshold:
            Z-score cutoff (default 3.0 ≈ 0.3% of a normal distribution).
        """
        if col not in df.columns:
            return []
        numeric = pd.to_numeric(df[col], errors="coerce")
        valid = numeric.dropna()
        if len(valid) < 4:
            return []
        mean, std = float(valid.mean()), float(valid.std())
        if std == 0:
            return []
        zscores = (numeric - mean).abs() / std
        outliers: list[int] = [
            int(i) for i in df.index[(zscores > threshold).fillna(False)]
        ]
        if outliers:
            log.debug(
                "Z-score outliers in '%s': %d rows (threshold=%.1f)",
                col,
                len(outliers),
                threshold,
            )
        return outliers

    def scan(
        self,
        df: pd.DataFrame,
        numeric_cols: list[str],
        multiplier: float = 1.5,
    ) -> dict[str, list[int]]:
        """Run IQR outlier detection on each column in *numeric_cols*.

        Parameters
        ----------
        df:
            Input DataFrame.
        numeric_cols:
            Column names to check; missing or non-numeric columns are skipped.
        multiplier:
            Passed to ``detect_iqr_outliers``.

        Returns
        -------
        dict
            ``{col_name: [outlier_row_indices]}`` — only columns with at least
            one outlier appear in the result.
        """
        result: dict[str, list[int]] = {}
        for col in numeric_cols:
            outliers = self.detect_iqr_outliers(df, col, multiplier=multiplier)
            if outliers:
                result[col] = outliers
                log.warning(
                    "AnomalyDetector: %d IQR outlier(s) in column '%s'",
                    len(outliers),
                    col,
                )
        return result

    @staticmethod
    def detect_volume_spike(
        current_count: int,
        baseline_count: int,
        threshold: float = 0.5,
    ) -> tuple[bool, float]:
        """Check whether *current_count* deviates from *baseline_count* by
        more than *threshold* (fraction of the baseline).

        Parameters
        ----------
        current_count:
            Number of rows in the current batch.
        baseline_count:
            Expected or historical average row count.
        threshold:
            Fraction deviation that triggers the flag (default 0.5 = ±50%).

        Returns
        -------
        (is_anomaly, ratio)
            ``is_anomaly`` is True when ``ratio > threshold``.
        """
        if baseline_count == 0:
            return False, 0.0
        ratio = abs(current_count - baseline_count) / baseline_count
        return ratio > threshold, ratio


# ---------------------------------------------------------------------------
# Rule-based checker
# ---------------------------------------------------------------------------


class DataQualityChecker:
    """Collection of row-level and column-level quality checks.

    Individual ``check_*`` methods return a boolean Series (True = passes).
    ``score_dataframe()`` runs an arbitrary ``(name, fn)`` list and produces
    per-row ``QualityScore`` objects plus an aggregate summary that includes
    per-rule pass rates (``summary["rule_scores"]``).
    ``score_source()`` selects the canonical rule suite for each known source
    and returns a ``SourceQualityReport``.
    """

    # ------------------------------------------------------------------
    # Generic rule checks — each returns a boolean Series (True = pass)
    # ------------------------------------------------------------------

    def check_null_keys(self, df: pd.DataFrame, key_cols: list[str]) -> pd.Series:
        """All required key columns must be non-null."""
        mask = pd.Series(True, index=df.index)
        for col in key_cols:
            if col in df.columns:
                mask = mask & df[col].notna()
        return mask

    def check_positive_quantities(self, df: pd.DataFrame) -> pd.Series:
        """quantity must be > 0."""
        if "quantity" not in df.columns:
            return pd.Series(True, index=df.index)
        return df["quantity"] > 0

    def check_positive_prices(self, df: pd.DataFrame) -> pd.Series:
        """unitPrice must be > 0."""
        if "unitPrice" not in df.columns:
            return pd.Series(True, index=df.index)
        return df["unitPrice"] > 0

    def check_date_not_future(self, df: pd.DataFrame, date_col: str) -> pd.Series:
        """date_col must be <= today."""
        if date_col not in df.columns:
            return pd.Series(True, index=df.index)
        today = pd.Timestamp(date.today())
        col = pd.to_datetime(df[date_col], errors="coerce")
        return col.notna() & (col <= today)

    def check_discount_range(self, df: pd.DataFrame, discount_col: str) -> pd.Series:
        """0 <= discount_col < unitPrice."""
        if discount_col not in df.columns:
            return pd.Series(True, index=df.index)
        discount = pd.to_numeric(df[discount_col], errors="coerce").fillna(0)
        lower_ok = discount >= 0
        if "unitPrice" in df.columns:
            price = pd.to_numeric(df["unitPrice"], errors="coerce").fillna(0)
            upper_ok = discount < price
        else:
            upper_ok = pd.Series(True, index=df.index)
        return lower_ok & upper_ok

    def check_score_range(
        self,
        df: pd.DataFrame,
        col: str,
        lo: float,
        hi: float,
    ) -> pd.Series:
        """Values in col must be within [lo, hi] (NaN rows pass)."""
        if col not in df.columns:
            return pd.Series(True, index=df.index)
        numeric = pd.to_numeric(df[col], errors="coerce")
        valid = numeric.notna()
        in_range = (numeric >= lo) & (numeric <= hi)
        return ~valid | in_range  # NaN rows are not penalised

    # ------------------------------------------------------------------
    # Source-specific rule checks
    # ------------------------------------------------------------------

    def check_total_consistency(self, df: pd.DataFrame) -> pd.Series:
        """POS: totalAmount ≈ (quantity × unitPrice) − discountApplied (±0.01).

        Mirrors the backend POS validator which requires
        ``total = qty * unit_price - discount``.  Rows where any of the four
        input columns is null pass vacuously (caught by ``check_null_keys``).
        Only evaluated when all four columns are present.
        """
        required = {"quantity", "unitPrice", "discountApplied", "totalAmount"}
        if not required.issubset(df.columns):
            return pd.Series(True, index=df.index)

        qty = pd.to_numeric(df["quantity"], errors="coerce")
        price = pd.to_numeric(df["unitPrice"], errors="coerce")
        discount = pd.to_numeric(df["discountApplied"], errors="coerce").fillna(0)
        total = pd.to_numeric(df["totalAmount"], errors="coerce")

        expected = qty * price - discount
        tolerance = 0.01
        has_null = qty.isna() | price.isna() | total.isna()
        within_tolerance = (total - expected).abs() <= tolerance
        return has_null | within_tolerance

    def check_cashier_id_positive_int(self, df: pd.DataFrame) -> pd.Series:
        """cashierId must be a positive integer (mirrors backend POS validator).

        Null rows pass vacuously; non-integer or non-positive values fail.
        Accepts both ``cashierId`` and ``cashier_id`` column names.
        """
        col = next((c for c in ("cashierId", "cashier_id") if c in df.columns), None)
        if col is None:
            return pd.Series(True, index=df.index)

        def _ok(val: Any) -> bool:
            if val is None or (isinstance(val, float) and pd.isna(val)):
                return True  # null: caught by null_keys check
            try:
                return int(float(str(val))) > 0
            except (ValueError, TypeError):
                return False

        return df[col].apply(_ok)

    def check_order_status_valid(self, df: pd.DataFrame) -> pd.Series:
        """orderStatus must be one of the accepted values (null rows pass).

        Accepted (case-insensitive): pending, processing, shipped,
        delivered, cancelled, refunded.
        """
        if "orderStatus" not in df.columns:
            return pd.Series(True, index=df.index)
        is_null = df["orderStatus"].isna()
        is_valid = df["orderStatus"].str.lower().isin(_VALID_ORDER_STATUSES)
        return is_null | is_valid

    def check_payment_method_present(self, df: pd.DataFrame) -> pd.Series:
        """paymentMethod must be non-null and non-empty for online orders."""
        if "paymentMethod" not in df.columns:
            return pd.Series(True, index=df.index)
        not_null = df["paymentMethod"].notna()
        not_empty = df["paymentMethod"].astype(str).str.strip() != ""
        return not_null & not_empty

    # ------------------------------------------------------------------
    # Composite scoring
    # ------------------------------------------------------------------

    def score_dataframe(
        self,
        df: pd.DataFrame,
        table_name: str,
        checks: list[tuple[str, Callable[[pd.DataFrame], pd.Series]]],
    ) -> tuple[list[QualityScore], dict[str, Any]]:
        """Run every (rule_name, check_fn) pair and produce QualityScores.

        Parameters
        ----------
        df:
            The dataframe to validate.
        table_name:
            Label used in QualityScore records.
        checks:
            List of ``(rule_name, callable)`` pairs.  Each callable accepts
            the dataframe and returns a boolean Series aligned to ``df.index``.

        Returns
        -------
        scores:
            One ``QualityScore`` per row.
        summary:
            Aggregate statistics dict with keys: ``overall_score``,
            ``total_rows``, ``passed_rows``, ``failed_rows``, ``anomalies``,
            and ``rule_scores`` (per-rule pass fractions).
        """
        if df.empty:
            log.warning("score_dataframe: %s is empty — skipping", table_name)
            summary: dict[str, Any] = {
                "overall_score": 1.0,
                "total_rows": 0,
                "passed_rows": 0,
                "failed_rows": 0,
                "anomalies": [],
                "rule_scores": {},
            }
            return [], summary

        n_checks = len(checks)
        results: dict[str, pd.Series] = {}
        for rule_name, check_fn in checks:
            try:
                results[rule_name] = check_fn(df).reindex(df.index).fillna(False)
            except Exception as exc:  # noqa: BLE001
                log.warning("Check '%s' raised %s — marking all fail", rule_name, exc)
                results[rule_name] = pd.Series(False, index=df.index)

        scores: list[QualityScore] = []
        anomalies: list[dict[str, Any]] = []

        for idx in df.index:
            passed = 0
            failed: list[str] = []
            for rule_name, series in results.items():
                if series.at[idx]:
                    passed += 1
                else:
                    failed.append(rule_name)
            row_score = passed / n_checks if n_checks else 1.0
            scores.append(
                QualityScore(
                    row_id=idx,
                    table=table_name,
                    passed_checks=passed,
                    total_checks=n_checks,
                    score=row_score,
                    failed_rules=failed,
                )
            )
            if failed:
                anomalies.append(
                    {
                        "row_id": idx,
                        "table": table_name,
                        "failed_rules": failed,
                        "score": row_score,
                    }
                )

        passed_rows = sum(1 for s in scores if s.score == 1.0)
        failed_rows = len(scores) - passed_rows
        overall = passed_rows / len(scores) if scores else 1.0

        # Per-rule pass rates
        total = len(scores)
        rule_scores: dict[str, float] = {
            name: float(series.sum()) / total if total else 1.0
            for name, series in results.items()
        }

        summary = {
            "overall_score": overall,
            "total_rows": len(scores),
            "passed_rows": passed_rows,
            "failed_rows": failed_rows,
            "anomalies": anomalies,
            "rule_scores": rule_scores,
        }
        log.info(
            "Quality summary for %s: %.2f%% passed (%d/%d rows)",
            table_name,
            overall * 100,
            passed_rows,
            len(scores),
        )
        return scores, summary

    # ------------------------------------------------------------------
    # Per-source scoring
    # ------------------------------------------------------------------

    def score_source(
        self,
        df: pd.DataFrame,
        source: str,
    ) -> tuple[list[QualityScore], SourceQualityReport]:
        """Run the canonical quality rule suite for *source*.

        This is the high-level entry point for per-source scoring.  The rule
        suite mirrors the backend ingestion validators so that constraints are
        enforced consistently across the stack.

        Parameters
        ----------
        df:
            Raw extracted DataFrame for the source.
        source:
            One of ``"posTransactions"``, ``"onlineOrders"``,
            ``"feedback"``, ``"inventory"``.  Unknown values fall back to a
            minimal null-key check with a WARNING log.

        Returns
        -------
        (scores, report)
            Row-level ``QualityScore`` list and a ``SourceQualityReport``.
        """
        checks: list[tuple[str, Callable]]

        if source == "posTransactions":
            checks = [
                (
                    "null_keys",
                    lambda d: self.check_null_keys(
                        d, ["sourceTransactionId", "productSKU"]
                    ),
                ),
                ("positive_quantities", self.check_positive_quantities),
                ("positive_prices", self.check_positive_prices),
                (
                    "date_not_future",
                    lambda d: self.check_date_not_future(d, "transactionDatetime"),
                ),
                (
                    "discount_range",
                    lambda d: self.check_discount_range(d, "discountApplied"),
                ),
                ("total_consistency", self.check_total_consistency),
                ("cashier_id_positive_int", self.check_cashier_id_positive_int),
            ]

        elif source == "onlineOrders":
            checks = [
                (
                    "null_keys",
                    lambda d: self.check_null_keys(
                        d, ["sourceTransactionId", "productSKU"]
                    ),
                ),
                ("positive_quantities", self.check_positive_quantities),
                ("positive_prices", self.check_positive_prices),
                (
                    "date_not_future",
                    lambda d: self.check_date_not_future(d, "transactionDatetime"),
                ),
                (
                    "discount_range",
                    lambda d: self.check_discount_range(d, "discountApplied"),
                ),
                ("order_status_valid", self.check_order_status_valid),
                ("payment_method_present", self.check_payment_method_present),
            ]

        elif source == "feedback":
            checks = [
                (
                    "null_keys",
                    lambda d: self.check_null_keys(d, ["customerId", "sourceOrderId"]),
                ),
                (
                    "date_not_future",
                    lambda d: self.check_date_not_future(d, "submissionDate"),
                ),
                (
                    "satisfaction_score_range",
                    lambda d: self.check_score_range(d, "satisfactionScore", 1, 10),
                ),
                (
                    "nps_score_range",
                    lambda d: self.check_score_range(d, "npsScore", 0, 10),
                ),
                (
                    "product_rating_range",
                    lambda d: self.check_score_range(d, "productRating", 1, 5),
                ),
                (
                    "delivery_rating_range",
                    lambda d: self.check_score_range(d, "deliveryRating", 1, 5),
                ),
            ]

        elif source == "inventory":
            checks = [
                ("null_keys", lambda d: self.check_null_keys(d, ["productSKU"])),
                ("positive_quantities", self.check_positive_quantities),
            ]

        else:
            log.warning(
                "score_source: unknown source %r — applying null-key check only",
                source,
            )
            checks = [("null_keys", lambda d: self.check_null_keys(d, []))]

        scores, summary = self.score_dataframe(df, source, checks)

        report = SourceQualityReport(
            source=source,
            total_rows=summary["total_rows"],
            passed_rows=summary["passed_rows"],
            failed_rows=summary["failed_rows"],
            overall_score=summary["overall_score"],
            rule_scores=summary.get("rule_scores", {}),
            anomalies=summary["anomalies"],
        )
        return scores, report
