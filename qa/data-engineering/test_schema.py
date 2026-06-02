"""Tests for the InsightFlow star-schema DDL (warehouse/schema.sql)."""

import re
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Resolve the schema file relative to this test file
# ---------------------------------------------------------------------------
_DE_ROOT = Path(__file__).parent.parent.parent / "data-engineering"
_SCHEMA_FILE = _DE_ROOT / "warehouse" / "schema.sql"

if str(_DE_ROOT) not in sys.path:
    sys.path.insert(0, str(_DE_ROOT))


def _load_schema() -> str:
    return _SCHEMA_FILE.read_text(encoding="utf-8")


def _parse_statements(sql: str) -> list[str]:
    """Strip comments and split on semicolons.

    Mirrors the logic in create_star_schema._parse_sql.
    """
    sql = re.sub(r"/\*.*?\*/", "", sql, flags=re.DOTALL)
    sql = re.sub(r"--[^\n]*", "", sql)
    return [s.strip() for s in sql.split(";") if s.strip()]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_schema_sql_parses() -> None:
    """Schema file must parse into at least 11 non-empty SQL statements."""
    sql = _load_schema()
    statements = _parse_statements(sql)
    assert len(statements) >= 11, f"Expected ≥11 statements, got {len(statements)}"


def test_dim_tables_present() -> None:
    """Schema must declare CREATE TABLE IF NOT EXISTS for every dimension."""
    sql = _load_schema()
    required_dims = [
        "dim_date",
        "dim_product",
        "dim_customer",
        "dim_store",
        "dim_geography",
        "dim_channel",
        "dim_payment_method",
        "dim_order_status",
    ]
    for table in required_dims:
        pattern = rf"CREATE\s+TABLE\s+IF\s+NOT\s+EXISTS\s+{re.escape(table)}"
        assert re.search(
            pattern, sql, re.IGNORECASE
        ), f"Schema missing: CREATE TABLE IF NOT EXISTS {table}"


def test_fact_tables_present() -> None:
    """Schema must declare CREATE TABLE IF NOT EXISTS for every fact table."""
    sql = _load_schema()
    required_facts = [
        "fact_sales",
        "fact_feedback",
        "fact_inventory_snapshot",
    ]
    for table in required_facts:
        pattern = rf"CREATE\s+TABLE\s+IF\s+NOT\s+EXISTS\s+{re.escape(table)}"
        assert re.search(
            pattern, sql, re.IGNORECASE
        ), f"Schema missing: CREATE TABLE IF NOT EXISTS {table}"


def test_fact_sales_has_fks() -> None:
    """fact_sales must REFERENCES dim_date, dim_product, dim_geography, dim_channel."""
    sql = _load_schema()

    # Extract just the fact_sales CREATE TABLE block
    match = re.search(
        r"CREATE\s+TABLE\s+IF\s+NOT\s+EXISTS\s+fact_sales\s*\((.+?)\);",
        sql,
        re.IGNORECASE | re.DOTALL,
    )
    assert match, "fact_sales CREATE TABLE block not found"
    block = match.group(0)

    required_refs = ["dim_date", "dim_product", "dim_geography", "dim_channel"]
    for ref in required_refs:
        assert f"REFERENCES {ref}" in block, f"fact_sales is missing REFERENCES {ref}"


def test_scd2_columns_on_dim_product() -> None:
    """dim_product must contain the SCD-2 columns: valid_from, valid_to, is_current."""
    sql = _load_schema()

    match = re.search(
        r"CREATE\s+TABLE\s+IF\s+NOT\s+EXISTS\s+dim_product\s*\((.+?)\);",
        sql,
        re.IGNORECASE | re.DOTALL,
    )
    assert match, "dim_product CREATE TABLE block not found"
    block = match.group(0)

    for col in ("valid_from", "valid_to", "is_current"):
        assert col in block, f"dim_product missing SCD-2 column: {col}"


def test_scd2_columns_on_dim_customer() -> None:
    """dim_customer must contain the SCD-2 columns: valid_from, valid_to, is_active."""
    sql = _load_schema()

    match = re.search(
        r"CREATE\s+TABLE\s+IF\s+NOT\s+EXISTS\s+dim_customer\s*\((.+?)\);",
        sql,
        re.IGNORECASE | re.DOTALL,
    )
    assert match, "dim_customer CREATE TABLE block not found"
    block = match.group(0)

    for col in ("valid_from", "valid_to", "is_active"):
        assert col in block, f"dim_customer missing SCD-2 column: {col}"


def test_indexes_present() -> None:
    """Schema must contain at least 5 CREATE INDEX IF NOT EXISTS statements."""
    sql = _load_schema()
    pattern = r"CREATE\s+INDEX\s+IF\s+NOT\s+EXISTS"
    matches = re.findall(pattern, sql, re.IGNORECASE)
    assert (
        len(matches) >= 5
    ), f"Expected ≥5 CREATE INDEX IF NOT EXISTS, found {len(matches)}"
