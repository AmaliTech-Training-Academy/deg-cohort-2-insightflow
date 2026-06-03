"""Data quality checks for the InsightFlow ETL pipeline."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date
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


# ---------------------------------------------------------------------------
# Dataclass
# ---------------------------------------------------------------------------
@dataclass
class QualityScore:
    row_id: Any
    table: str
    passed_checks: int
    total_checks: int
    score: float
    failed_rules: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Checker
# ---------------------------------------------------------------------------
class DataQualityChecker:
    """Collection of row-level and column-level quality checks."""

    # ------------------------------------------------------------------
    # Individual rule checks — each returns a boolean Series (True = pass)
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
            One QualityScore per row.
        summary:
            Aggregate statistics dict.
        """
        if df.empty:
            log.warning("score_dataframe: %s is empty — skipping", table_name)
            summary: dict[str, Any] = {
                "overall_score": 1.0,
                "total_rows": 0,
                "passed_rows": 0,
                "failed_rows": 0,
                "anomalies": [],
            }
            return [], summary

        n_checks = len(checks)
        # Build a matrix: rows × rules (True = pass)
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

        summary = {
            "overall_score": overall,
            "total_rows": len(scores),
            "passed_rows": passed_rows,
            "failed_rows": failed_rows,
            "anomalies": anomalies,
        }
        log.info(
            "Quality summary for %s: %.2f%% passed (%d/%d rows)",
            table_name,
            overall * 100,
            passed_rows,
            len(scores),
        )
        return scores, summary
