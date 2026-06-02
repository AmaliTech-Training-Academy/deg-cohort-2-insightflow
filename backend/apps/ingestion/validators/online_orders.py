from rest_framework import serializers


def validate_online_order_row(row: dict) -> dict:
    """Validate a single online order data row."""
    errors = {}

    if not row.get("order_id"):
        errors["order_id"] = "order_id is required."
    if not row.get("customer_id"):
        errors["customer_id"] = "customer_id is required."
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
