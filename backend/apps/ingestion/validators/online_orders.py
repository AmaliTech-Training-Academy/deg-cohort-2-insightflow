from decimal import Decimal, InvalidOperation
from typing import Any

REQUIRED_ORDER_FIELDS = {
    "onlineOrderId",
    "customerId",
    "orderDatetime",
    "shippingProvince",
    "orderStatus",
    "paymentMethod",
}
REQUIRED_LINE_FIELDS = {
    "lineId",
    "onlineOrderId",
    "productSKU",
    "quantity",
    "unitPrice",
    "discountApplied",
    "totalAmount",
}


def validate_order(order: dict[str, Any]) -> list[dict[str, Any]]:
    errors: list[dict[str, Any]] = []
    _check_required(order, REQUIRED_ORDER_FIELDS, errors)
    _check_positive_int(order, "onlineOrderId", errors)
    return errors


def validate_order_line(
    line: dict[str, Any], order_id: int | None = None
) -> list[dict[str, Any]]:
    errors: list[dict[str, Any]] = []
    _check_required(line, REQUIRED_LINE_FIELDS, errors)
    _check_positive_int(line, "lineId", errors)
    _check_positive_int(line, "quantity", errors)
    _check_positive_decimal(line, "unitPrice", errors)
    _check_non_negative_decimal(line, "discountApplied", errors)
    _check_positive_decimal(line, "totalAmount", errors)
    return errors


def _check_required(
    data: dict[str, Any], fields: set[str], errors: list[dict[str, Any]]
) -> None:
    for field in fields:
        val = data.get(field)
        if val is None or str(val).strip() == "":
            errors.append(
                {"field": field, "error": "Required — cannot be null or empty"}
            )


def _check_positive_int(
    data: dict[str, Any], field: str, errors: list[dict[str, Any]]
) -> None:
    val = data.get(field)
    if val is None:
        return
    try:
        if int(val) <= 0:
            errors.append(
                {"field": field, "error": f"Must be positive integer, got {val!r}"}
            )
    except (ValueError, TypeError):
        errors.append({"field": field, "error": f"Expected integer, got {val!r}"})


def _check_positive_decimal(
    data: dict[str, Any], field: str, errors: list[dict[str, Any]]
) -> None:
    val = data.get(field)
    if val is None:
        return
    try:
        if Decimal(str(val)) <= 0:
            errors.append(
                {"field": field, "error": f"Must be positive number, got {val!r}"}
            )
    except InvalidOperation:
        errors.append({"field": field, "error": f"Expected decimal, got {val!r}"})


def _check_non_negative_decimal(
    data: dict[str, Any], field: str, errors: list[dict[str, Any]]
) -> None:
    val = data.get(field)
    if val is None:
        return
    try:
        if Decimal(str(val)) < 0:
            errors.append(
                {"field": field, "error": f"Must be non-negative, got {val!r}"}
            )
    except InvalidOperation:
        errors.append({"field": field, "error": f"Expected decimal, got {val!r}"})
