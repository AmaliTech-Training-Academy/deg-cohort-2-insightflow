from rest_framework import serializers


def validate_feedback_row(row: dict) -> dict:
    """Validate a single customer feedback data row."""
    errors = {}

    if not row.get("feedback_id"):
        errors["feedback_id"] = "feedback_id is required."
    if row.get("rating") is not None:
        try:
            rating = int(row["rating"])
            if not (1 <= rating <= 5):
                errors["rating"] = "rating must be between 1 and 5."
        except (TypeError, ValueError):
            errors["rating"] = "rating must be an integer."

    if errors:
        raise serializers.ValidationError(errors)

    return row
