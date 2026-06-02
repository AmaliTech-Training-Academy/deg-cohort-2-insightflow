from rest_framework import serializers


def validate_inventory_row(row: dict) -> dict:
    """Validate a single inventory data row."""
    errors = {}

    if not row.get("product_id"):
        errors["product_id"] = "product_id is required."
    if not row.get("warehouse_id"):
        errors["warehouse_id"] = "warehouse_id is required."
    if row.get("quantity") is not None:
        try:
            qty = int(row["quantity"])
            if qty < 0:
                errors["quantity"] = "quantity must be non-negative."
        except (TypeError, ValueError):
            errors["quantity"] = "quantity must be an integer."

    if errors:
        raise serializers.ValidationError(errors)

    return row
