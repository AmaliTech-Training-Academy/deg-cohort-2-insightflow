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
# Structure tests
# ---------------------------------------------------------------------------


def test_schema_sql_parses() -> None:
    """Schema file must parse into exactly 24 non-empty SQL statements
    (8 dim tables + 3 fact tables + 13 indexes)."""
    sql = _load_schema()
    statements = _parse_statements(sql)
    assert len(statements) == 24, f"Expected 24 statements, got {len(statements)}"


def test_dim_tables_present() -> None:
    """Schema must declare CREATE TABLE IF NOT EXISTS for every dimension."""
    sql = _load_schema()
    required_dims = [
        "dimDate",
        "dimProduct",
        "dimCustomer",
        "dimStore",
        "dimGeography",
        "dimChannel",
        "dimPaymentMethod",
        "dimOrderStatus",
    ]
    for table in required_dims:
        pattern = rf'CREATE\s+TABLE\s+IF\s+NOT\s+EXISTS\s+"{re.escape(table)}"'
        assert re.search(
            pattern, sql, re.IGNORECASE
        ), f'Schema missing: CREATE TABLE IF NOT EXISTS "{table}"'


def test_fact_tables_present() -> None:
    """Schema must declare CREATE TABLE IF NOT EXISTS for every fact table."""
    sql = _load_schema()
    required_facts = [
        "factSales",
        "factFeedback",
        "factInventorySnapshot",
    ]
    for table in required_facts:
        pattern = rf'CREATE\s+TABLE\s+IF\s+NOT\s+EXISTS\s+"{re.escape(table)}"'
        assert re.search(
            pattern, sql, re.IGNORECASE
        ), f'Schema missing: CREATE TABLE IF NOT EXISTS "{table}"'


# ---------------------------------------------------------------------------
# FK tests
# ---------------------------------------------------------------------------


def test_fact_sales_has_fks() -> None:
    """factSales must REFERENCES dimDate, dimProduct, dimGeography, dimChannel."""
    sql = _load_schema()

    match = re.search(
        r'CREATE\s+TABLE\s+IF\s+NOT\s+EXISTS\s+"factSales"\s*\((.+?)\);',
        sql,
        re.IGNORECASE | re.DOTALL,
    )
    assert match, "factSales CREATE TABLE block not found"
    block = match.group(0)

    required_refs = ["dimDate", "dimProduct", "dimGeography", "dimChannel"]
    for ref in required_refs:
        assert (
            f'REFERENCES "{ref}"' in block
        ), f'factSales is missing REFERENCES "{ref}"'


def test_fact_feedback_has_fks() -> None:
    """factFeedback must REFERENCES dimDate and dimCustomer."""
    sql = _load_schema()

    match = re.search(
        r'CREATE\s+TABLE\s+IF\s+NOT\s+EXISTS\s+"factFeedback"\s*\((.+?)\);',
        sql,
        re.IGNORECASE | re.DOTALL,
    )
    assert match, "factFeedback CREATE TABLE block not found"
    block = match.group(0)

    for ref in ["dimDate", "dimCustomer"]:
        assert (
            f'REFERENCES "{ref}"' in block
        ), f'factFeedback is missing REFERENCES "{ref}"'


# ---------------------------------------------------------------------------
# SCD-2 column tests
# ---------------------------------------------------------------------------


def test_scd2_columns_on_dim_product() -> None:
    """dimProduct must contain the SCD-2 columns: validFrom, validTo, isCurrent."""
    sql = _load_schema()

    match = re.search(
        r'CREATE\s+TABLE\s+IF\s+NOT\s+EXISTS\s+"dimProduct"\s*\((.+?)\);',
        sql,
        re.IGNORECASE | re.DOTALL,
    )
    assert match, "dimProduct CREATE TABLE block not found"
    block = match.group(0)

    for col in ('"validFrom"', '"validTo"', '"isCurrent"'):
        assert col in block, f"dimProduct missing SCD-2 column: {col}"


def test_scd2_columns_on_dim_customer() -> None:
    """dimCustomer must contain the SCD-2 columns: validFrom, validTo, isActive."""
    sql = _load_schema()

    match = re.search(
        r'CREATE\s+TABLE\s+IF\s+NOT\s+EXISTS\s+"dimCustomer"\s*\((.+?)\);',
        sql,
        re.IGNORECASE | re.DOTALL,
    )
    assert match, "dimCustomer CREATE TABLE block not found"
    block = match.group(0)

    for col in ('"validFrom"', '"validTo"', '"isActive"'):
        assert col in block, f"dimCustomer missing SCD-2 column: {col}"


def test_dim_customer_id_is_varchar() -> None:
    """dimCustomer.customerId must be VARCHAR(255).

    Source customer.customerId is character varying, not integer.
    """
    sql = _load_schema()

    match = re.search(
        r'CREATE\s+TABLE\s+IF\s+NOT\s+EXISTS\s+"dimCustomer"\s*\((.+?)\);',
        sql,
        re.IGNORECASE | re.DOTALL,
    )
    assert match, "dimCustomer CREATE TABLE block not found"
    block = match.group(0)

    assert '"customerId"' in block, "dimCustomer missing customerId column"
    assert "VARCHAR(255)" in block, (
        "dimCustomer.customerId must be VARCHAR(255); "
        "source customer.customerId is character varying, not integer"
    )


# ---------------------------------------------------------------------------
# Index tests
# ---------------------------------------------------------------------------


def test_indexes_present() -> None:
    """Schema must contain exactly 13 CREATE INDEX IF NOT EXISTS statements."""
    sql = _load_schema()
    pattern = r"CREATE\s+INDEX\s+IF\s+NOT\s+EXISTS"
    matches = re.findall(pattern, sql, re.IGNORECASE)
    assert (
        len(matches) == 13
    ), f"Expected 13 CREATE INDEX IF NOT EXISTS, found {len(matches)}"


def test_dim_customer_partial_index_uses_isactive() -> None:
    """idxDimCustomerCurrent partial index must filter on isActive (not isCurrent).

    dimCustomer uses isActive for its SCD-2 active flag; isCurrent is
    dimProduct's field.  Using the wrong column causes schema creation to fail.
    """
    sql = _load_schema()

    match = re.search(
        r'"idxDimCustomerCurrent"\s+ON\s+"dimCustomer"[^;]+;',
        sql,
        re.IGNORECASE | re.DOTALL,
    )
    assert match, "idxDimCustomerCurrent index definition not found"
    idx_sql = match.group(0)

    assert (
        '"isActive"' in idx_sql
    ), 'idxDimCustomerCurrent must use WHERE "isActive" = TRUE, not "isCurrent"'
    assert (
        '"isCurrent"' not in idx_sql
    ), "idxDimCustomerCurrent must not reference isCurrent (dimProduct's column)"


def test_dim_product_partial_index_uses_iscurrent() -> None:
    """idxDimProductCurrent partial index must filter on isCurrent."""
    sql = _load_schema()

    match = re.search(
        r'"idxDimProductCurrent"\s+ON\s+"dimProduct"[^;]+;',
        sql,
        re.IGNORECASE | re.DOTALL,
    )
    assert match, "idxDimProductCurrent index definition not found"
    assert '"isCurrent"' in match.group(
        0
    ), 'idxDimProductCurrent must use WHERE "isCurrent" = TRUE'
