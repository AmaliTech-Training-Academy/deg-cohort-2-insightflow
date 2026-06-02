from rest_framework import serializers


def validate_pos_row(row: dict) -> dict:
    """Validate POS data row and return cleaned data or raise ValidationError."""
    errors = {}

    if not row.get("transaction_id"):
        errors["transaction_id"] = "transaction_id is required."
    if not row.get("store_id"):
        errors["store_id"] = "store_id is required."
    if row.get("amount") is not None:
        try:
            amount = float(row["amount"])
            if amount < 0:
                errors["amount"] = "amount must be non-negative."
        except (TypeError, ValueError):
            errors["amount"] = "amount must be a valid number."

    if errors:
        raise serializers.ValidationError(errors)

    return row
