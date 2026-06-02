from decimal import Decimal, InvalidOperation
from datetime import date
from dateutil import parser as date_parser
from dateutil.parser import ParserError
from rest_framework import serializers


# ─────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────

REQUIRED_CSV_COLUMNS = {
    'transaction_id', 'date', 'store_id',
    'product_sku', 'quantity', 'unit_price', 'total'
}

EARLIEST_ALLOWED_DATE = date(2000, 1, 1)
TOTAL_TOLERANCE = Decimal('0.02')   # allow 2 cent rounding difference


# ─────────────────────────────────────────────
# Level 1 — file-level (called from the view)
# ─────────────────────────────────────────────

def validate_pos_file_columns(df_header_columns: list) -> list:
    """
    Called once per upload with just the header row.
    Returns a list of missing column names (empty = all good).
    Fatal — if anything returned, reject the whole file immediately.
    """
    actual = {col.strip().lower() for col in df_header_columns}
    missing = REQUIRED_CSV_COLUMNS - actual
    return sorted(list(missing))


# ─────────────────────────────────────────────
# Level 2 — batch-level duplicate check
# ─────────────────────────────────────────────

def find_duplicate_transaction_ids(df) -> dict:
    """
    Called once on the full dataframe before row-by-row processing.
    Returns a dict of { transaction_id: [row_numbers] } for any duplicates.
    """
    duplicates = {}
    seen = {}

    for idx, value in df['transaction_id'].items():
        if value is None or str(value).strip() == '':
            continue
        key = str(value).strip()
        row_num = idx + 2  # +2 = 1-indexed + skip header

        if key in seen:
            if key not in duplicates:
                duplicates[key] = [seen[key]]
            duplicates[key].append(row_num)
        else:
            seen[key] = row_num

    return duplicates


# ─────────────────────────────────────────────
# Level 3+4 — row-level (called per row in Celery task)
# ─────────────────────────────────────────────

def validate_pos_row(row: dict, row_num: int = None) -> dict:
    """
    Validates a single POS CSV row dict.
    
    - Returns cleaned row dict on success (types coerced, ready for model)
    - Raises serializers.ValidationError with full error dict on failure
    
    row_num is optional — only used for error messages if provided.
    """
    errors = {}
    cleaned = {}
    row_ref = f"row {row_num}" if row_num else "row"

    # ── transaction_id ───────────────────────
    txn_id = row.get('transaction_id')
    if txn_id is None or str(txn_id).strip() == '':
        errors['transaction_id'] = 'Required — cannot be null or empty'
    else:
        cleaned['transaction_id'] = str(txn_id).strip()

    # ── store_id ─────────────────────────────
    store_id = row.get('store_id')
    if store_id is None or str(store_id).strip() == '':
        errors['store_id'] = 'Required — cannot be null or empty'
    else:
        cleaned['store_id'] = str(store_id).strip()

    # ── product_sku (optional but warned) ────
    product_sku = row.get('product_sku')
    if product_sku is None or str(product_sku).strip() == '':
        cleaned['product_sku'] = None          # allowed, saved as null
        cleaned['_warnings'] = cleaned.get('_warnings', [])
        cleaned['_warnings'].append('product_sku is missing — row will be saved without product link')
    else:
        cleaned['product_sku'] = str(product_sku).strip()

    # ── quantity ─────────────────────────────
    quantity = row.get('quantity')
    if quantity is None or str(quantity).strip() == '':
        errors['quantity'] = 'Required — cannot be null or empty'
    else:
        try:
            qty_int = int(Decimal(str(quantity)))   # handles "2.0" → 2
            if qty_int <= 0:
                errors['quantity'] = f'Must be a positive integer, got {qty_int}'
            else:
                cleaned['quantity'] = qty_int
        except (InvalidOperation, ValueError):
            errors['quantity'] = f'Expected a whole number, got "{quantity}"'

    # ── unit_price ───────────────────────────
    unit_price = row.get('unit_price')
    if unit_price is None or str(unit_price).strip() == '':
        errors['unit_price'] = 'Required — cannot be null or empty'
    else:
        try:
            price = Decimal(str(unit_price)).quantize(Decimal('0.01'))
            if price < 0:
                errors['unit_price'] = f'Must be non-negative, got {price}'
            else:
                cleaned['unit_price'] = price
        except InvalidOperation:
            errors['unit_price'] = f'Expected a decimal number, got "{unit_price}"'

    # ── total ────────────────────────────────
    total = row.get('total')
    if total is None or str(total).strip() == '':
        errors['total'] = 'Required — cannot be null or empty'
    else:
        try:
            total_decimal = Decimal(str(total)).quantize(Decimal('0.01'))
            if total_decimal < 0:
                errors['total'] = f'Must be non-negative, got {total_decimal}'
            else:
                cleaned['total'] = total_decimal
        except InvalidOperation:
            errors['total'] = f'Expected a decimal number, got "{total}"'

    # ── date ─────────────────────────────────
    raw_date = row.get('date')
    if raw_date is None or str(raw_date).strip() == '':
        errors['date'] = 'Required — cannot be null or empty'
    else:
        try:
            parsed_date = date_parser.parse(str(raw_date)).date()

            if parsed_date < EARLIEST_ALLOWED_DATE:
                errors['date'] = f'Date {parsed_date} is before the earliest allowed date (2000-01-01)'
            elif parsed_date > date.today():
                errors['date'] = f'Date {parsed_date} is in the future'
            else:
                cleaned['date'] = parsed_date
        except ParserError:
            errors['date'] = f'Cannot parse "{raw_date}" as a date — use YYYY-MM-DD format'

    #cross-field: total == qty × unit_price
    # only runs if all three fields passed their individual checks
    if 'quantity' in cleaned and 'unit_price' in cleaned and 'total' in cleaned:
        expected_total = (cleaned['unit_price'] * cleaned['quantity']).quantize(Decimal('0.01'))
        diff = abs(cleaned['total'] - expected_total)
        if diff > TOTAL_TOLERANCE:
            errors['total'] = (
                f'Does not match quantity × unit_price: '
                f'expected {expected_total}, got {cleaned["total"]} '
                f'(difference: {diff})'
            )

    # raise if any fatal errors
    if errors:
        raise serializers.ValidationError(errors)

    return cleaned