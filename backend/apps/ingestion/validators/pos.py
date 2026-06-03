# from rest_framework import serializers
import logging
from datetime import datetime
from decimal import Decimal, InvalidOperation

logger = logging.getLogger(__name__)

REQUIRED_COLUMNS = {
    "transaction_id",
    "date",
    "store_id",
    "cashier_id",
    "product_sku",
    "quantity",
    "unit_price",
    "discount_applied",
    "total",
}

ACCEPTED_DATE_FORMATS = ["%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y"]


def validate_pos_file_columns(columns: list) -> list:
    """
    Checks the header row has all required columns.
    Returns list of missing column names. Empty = all good.
    """
    actual = {str(col).strip().lower() for col in columns}
    missing = sorted(REQUIRED_COLUMNS - actual)
    if missing:
        logger.warning(f"POS upload rejected — missing columns: {missing}")
    return missing


def validate_pos_row(row: dict, row_num: int | None = None) -> list:
    """
    Checks data types only.
    Does NOT clean, coerce, or transform anything.
    Returns list of error dicts. Empty = row is fine.
    """
    errors = []

    # ── transaction_id — must be present ─────
    txn_id = row.get("transaction_id")
    if txn_id is None or str(txn_id).strip() == "":
        errors.append(
            {
                "row": row_num,
                "field": "transaction_id",
                "error": "Required — cannot be null or empty",
            }
        )

    # ── store_id — must be present ────────────
    store_id = row.get("store_id")
    if store_id is None or str(store_id).strip() == "":
        errors.append(
            {
                "row": row_num,
                "field": "store_id",
                "error": "Required — cannot be null or empty",
            }
        )

    # ── cashier_id — must be a positive integer ────
    cashier_id = row.get("cashier_id")
    if cashier_id is None or str(cashier_id).strip() == "":
        errors.append(
            {
                "row": row_num,
                "field": "cashier_id",
                "error": "Required — cannot be null or empty",
            }
        )
    else:
        try:
            cid = int(str(cashier_id))
            if cid <= 0:
                errors.append(
                    {
                        "row": row_num,
                        "field": "cashier_id",
                        "error": f'Must be a positive integer, got "{cashier_id}"',
                    }
                )
        except ValueError:
            errors.append(
                {
                    "row": row_num,
                    "field": "cashier_id",
                    "error": f'Expected an integer, got "{cashier_id}"',
                }
            )

    # ── quantity — must be a positive integer ─
    quantity = row.get("quantity")
    if quantity is None or str(quantity).strip() == "":
        errors.append(
            {
                "row": row_num,
                "field": "quantity",
                "error": "Required — cannot be null or empty",
            }
        )
    else:
        try:
            qty = int(float(str(quantity)))
            if qty <= 0:
                errors.append(
                    {
                        "row": row_num,
                        "field": "quantity",
                        "error": f'Must be a positive integer, got "{quantity}"',
                    }
                )
        except ValueError:
            errors.append(
                {
                    "row": row_num,
                    "field": "quantity",
                    "error": f'Expected an integer, got "{quantity}"',
                }
            )

    # ── unit_price — must be a positive number ──
    unit_price = row.get("unit_price")
    if unit_price is None or str(unit_price).strip() == "":
        errors.append(
            {
                "row": row_num,
                "field": "unit_price",
                "error": "Required — cannot be null or empty",
            }
        )
    else:
        try:
            price = Decimal(str(unit_price))
            if price <= 0:
                errors.append(
                    {
                        "row": row_num,
                        "field": "unit_price",
                        "error": f'Must be a positive number, got "{unit_price}"',
                    }
                )
        except InvalidOperation:
            errors.append(
                {
                    "row": row_num,
                    "field": "unit_price",
                    "error": f'Expected a number, got "{unit_price}"',
                }
            )

    # ── discount_applied — must be a non-negative number ──
    discount = row.get("discount_applied")
    if discount is None or str(discount).strip() == "":
        errors.append(
            {
                "row": row_num,
                "field": "discount_applied",
                "error": "Required — cannot be null or empty",
            }
        )
    else:
        try:
            disc = Decimal(str(discount))
            if disc < 0:
                errors.append(
                    {
                        "row": row_num,
                        "field": "discount_applied",
                        "error": f'Must be non-negative, got "{discount}"',
                    }
                )
        except InvalidOperation:
            errors.append(
                {
                    "row": row_num,
                    "field": "discount_applied",
                    "error": f'Expected a number, got "{discount}"',
                }
            )

    # ── total — must be a positive number ──────────────
    total = row.get("total")
    if total is None or str(total).strip() == "":
        errors.append(
            {
                "row": row_num,
                "field": "total",
                "error": "Required — cannot be null or empty",
            }
        )
    else:
        try:
            tot = Decimal(str(total))
            if tot <= 0:
                errors.append(
                    {
                        "row": row_num,
                        "field": "total",
                        "error": f'Must be a positive number, got "{total}"',
                    }
                )
        except InvalidOperation:
            errors.append(
                {
                    "row": row_num,
                    "field": "total",
                    "error": f'Expected a number, got "{total}"',
                }
            )

    # ── date — must be a recognisable date ────
    raw_date = row.get("date")
    if raw_date is None or str(raw_date).strip() == "":
        errors.append(
            {
                "row": row_num,
                "field": "date",
                "error": "Required — cannot be null or empty",
            }
        )
    else:
        if not _is_valid_date(str(raw_date)):
            errors.append(
                {
                    "row": row_num,
                    "field": "date",
                    "error": (
                        f'Cannot parse "{raw_date}" as a date — '
                        f"accepted formats: YYYY-MM-DD, DD/MM/YYYY, MM/DD/YYYY"
                    ),
                }
            )

    return errors


# ── helper ────────────────────────────────────────────────────


def _is_valid_date(raw: str) -> bool:
    for fmt in ACCEPTED_DATE_FORMATS:
        try:
            datetime.strptime(raw.strip(), fmt)
            return True
        except ValueError:
            continue
    return False
