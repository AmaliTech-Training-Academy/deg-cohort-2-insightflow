"""
Unit tests for POS CSV validator.

Tests validate_pos_file_columns() and validate_pos_row() functions
for correct error detection and acceptance of valid data.
"""

import pytest
from apps.ingestion.validators.pos import (
    validate_pos_file_columns,
    validate_pos_row,
)


class TestValidatePosFileColumns:
    """Test validate_pos_file_columns() — header validation."""

    def test_all_required_columns_present(self):
        """All required columns present returns empty list."""
        columns = [
            "transaction_id",
            "date",
            "store_id",
            "cashier_id",
            "product_sku",
            "quantity",
            "unit_price",
            "discount_applied",
            "total",
        ]
        missing = validate_pos_file_columns(columns)
        assert missing == []

    def test_all_required_columns_present_uppercase(self):
        """Column names case-insensitive."""
        columns = [
            "TRANSACTION_ID",
            "DATE",
            "STORE_ID",
            "CASHIER_ID",
            "PRODUCT_SKU",
            "QUANTITY",
            "UNIT_PRICE",
            "DISCOUNT_APPLIED",
            "TOTAL",
        ]
        missing = validate_pos_file_columns(columns)
        assert missing == []

    def test_extra_columns_ignored(self):
        """Extra columns beyond required are ignored."""
        columns = [
            "transaction_id",
            "date",
            "store_id",
            "cashier_id",
            "product_sku",
            "quantity",
            "unit_price",
            "discount_applied",
            "total",
            "extra_col_1",
            "extra_col_2",
        ]
        missing = validate_pos_file_columns(columns)
        assert missing == []

    def test_missing_single_column(self):
        """Missing one required column detected."""
        columns = [
            "transaction_id",
            "date",
            "store_id",
            "product_sku",
            "quantity",
            "unit_price",
            "discount_applied",
            "total",
            # missing: cashier_id
        ]
        missing = validate_pos_file_columns(columns)
        assert "cashier_id" in missing

    def test_missing_multiple_columns(self):
        """Missing multiple columns all detected."""
        columns = ["transaction_id", "date", "store_id"]
        missing = validate_pos_file_columns(columns)
        assert len(missing) > 3

    def test_empty_column_list(self):
        """Empty column list returns all required columns."""
        missing = validate_pos_file_columns([])
        assert len(missing) == 9


class TestValidatePosRow:
    """Test validate_pos_row() — row-level validation."""

    @pytest.fixture
    def valid_row(self):
        """A valid POS row."""
        return {
            "transaction_id": "12345",
            "store_id": "5",
            "cashier_id": "101",
            "product_sku": "SKU001",
            "quantity": "10",
            "unit_price": "25.99",
            "discount_applied": "0.00",
            "total": "259.90",
            "date": "2024-06-01",
        }

    def test_valid_row_returns_no_errors(self, valid_row):
        """Valid row returns empty error list."""
        errors = validate_pos_row(valid_row, row_num=2)
        assert errors == []

    def test_transaction_id_required(self):
        """transaction_id is required."""
        row = {
            "transaction_id": "",
            "store_id": "5",
            "cashier_id": "101",
            "product_sku": "SKU001",
            "quantity": "10",
            "unit_price": "25.99",
            "discount_applied": "0.00",
            "total": "259.90",
            "date": "2024-06-01",
        }
        errors = validate_pos_row(row, row_num=2)
        assert len(errors) > 0
        assert any(e["field"] == "transaction_id" for e in errors)

    def test_transaction_id_null(self):
        """transaction_id null is rejected."""
        row = {
            "transaction_id": None,
            "store_id": "5",
            "cashier_id": "101",
            "product_sku": "SKU001",
            "quantity": "10",
            "unit_price": "25.99",
            "discount_applied": "0.00",
            "total": "259.90",
            "date": "2024-06-01",
        }
        errors = validate_pos_row(row, row_num=2)
        assert any(e["field"] == "transaction_id" for e in errors)

    def test_cashier_id_must_be_positive_integer(self):
        """cashier_id must be positive integer."""
        row = {
            "transaction_id": "12345",
            "store_id": "5",
            "cashier_id": "-5",
            "product_sku": "SKU001",
            "quantity": "10",
            "unit_price": "25.99",
            "discount_applied": "0.00",
            "total": "259.90",
            "date": "2024-06-01",
        }
        errors = validate_pos_row(row, row_num=2)
        assert any(
            e["field"] == "cashier_id" and "positive" in e["error"] for e in errors
        )

    def test_cashier_id_zero_rejected(self):
        """cashier_id of 0 rejected."""
        row = {
            "transaction_id": "12345",
            "store_id": "5",
            "cashier_id": "0",
            "product_sku": "SKU001",
            "quantity": "10",
            "unit_price": "25.99",
            "discount_applied": "0.00",
            "total": "259.90",
            "date": "2024-06-01",
        }
        errors = validate_pos_row(row, row_num=2)
        assert any(e["field"] == "cashier_id" for e in errors)

    def test_cashier_id_not_integer(self):
        """cashier_id non-integer rejected."""
        row = {
            "transaction_id": "12345",
            "store_id": "5",
            "cashier_id": "abc",
            "product_sku": "SKU001",
            "quantity": "10",
            "unit_price": "25.99",
            "discount_applied": "0.00",
            "total": "259.90",
            "date": "2024-06-01",
        }
        errors = validate_pos_row(row, row_num=2)
        assert any(
            e["field"] == "cashier_id" and "Expected an integer" in e["error"]
            for e in errors
        )

    def test_quantity_must_be_positive_integer(self):
        """quantity must be positive integer."""
        row = {
            "transaction_id": "12345",
            "store_id": "5",
            "cashier_id": "101",
            "product_sku": "SKU001",
            "quantity": "0",
            "unit_price": "25.99",
            "discount_applied": "0.00",
            "total": "259.90",
            "date": "2024-06-01",
        }
        errors = validate_pos_row(row, row_num=2)
        assert any(e["field"] == "quantity" for e in errors)

    def test_unit_price_must_be_positive_decimal(self):
        """unit_price must be positive decimal."""
        row = {
            "transaction_id": "12345",
            "store_id": "5",
            "cashier_id": "101",
            "product_sku": "SKU001",
            "quantity": "10",
            "unit_price": "-5.99",
            "discount_applied": "0.00",
            "total": "259.90",
            "date": "2024-06-01",
        }
        errors = validate_pos_row(row, row_num=2)
        assert any(
            e["field"] == "unit_price" and "positive" in e["error"] for e in errors
        )

    def test_unit_price_invalid_decimal(self):
        """unit_price invalid decimal rejected."""
        row = {
            "transaction_id": "12345",
            "store_id": "5",
            "cashier_id": "101",
            "product_sku": "SKU001",
            "quantity": "10",
            "unit_price": "invalid",
            "discount_applied": "0.00",
            "total": "259.90",
            "date": "2024-06-01",
        }
        errors = validate_pos_row(row, row_num=2)
        assert any(e["field"] == "unit_price" for e in errors)

    def test_discount_applied_must_be_non_negative(self):
        """discount_applied must be non-negative."""
        row = {
            "transaction_id": "12345",
            "store_id": "5",
            "cashier_id": "101",
            "product_sku": "SKU001",
            "quantity": "10",
            "unit_price": "25.99",
            "discount_applied": "-5.00",
            "total": "259.90",
            "date": "2024-06-01",
        }
        errors = validate_pos_row(row, row_num=2)
        assert any(e["field"] == "discount_applied" for e in errors)

    def test_discount_applied_zero_allowed(self):
        """discount_applied of 0 is valid."""
        row = {
            "transaction_id": "12345",
            "store_id": "5",
            "cashier_id": "101",
            "product_sku": "SKU001",
            "quantity": "10",
            "unit_price": "25.99",
            "discount_applied": "0",
            "total": "259.90",
            "date": "2024-06-01",
        }
        errors = validate_pos_row(row, row_num=2)
        discount_errors = [e for e in errors if e["field"] == "discount_applied"]
        assert len(discount_errors) == 0

    def test_total_must_be_positive(self):
        """total must be positive."""
        row = {
            "transaction_id": "12345",
            "store_id": "5",
            "cashier_id": "101",
            "product_sku": "SKU001",
            "quantity": "10",
            "unit_price": "25.99",
            "discount_applied": "0.00",
            "total": "0",
            "date": "2024-06-01",
        }
        errors = validate_pos_row(row, row_num=2)
        assert any(e["field"] == "total" and "positive" in e["error"] for e in errors)

    def test_date_accepted_formats(self):
        """All accepted date formats pass validation."""
        for date_str in ["2024-06-01", "01/06/2024", "06/01/2024"]:
            row = {
                "transaction_id": "12345",
                "store_id": "5",
                "cashier_id": "101",
                "product_sku": "SKU001",
                "quantity": "10",
                "unit_price": "25.99",
                "discount_applied": "0.00",
                "total": "259.90",
                "date": date_str,
            }
            errors = validate_pos_row(row, row_num=2)
            date_errors = [e for e in errors if e["field"] == "date"]
            assert (
                len(date_errors) == 0
            ), f"Date format {date_str} failed: {date_errors}"

    def test_date_invalid_format(self):
        """Invalid date format rejected."""
        row = {
            "transaction_id": "12345",
            "store_id": "5",
            "cashier_id": "101",
            "product_sku": "SKU001",
            "quantity": "10",
            "unit_price": "25.99",
            "discount_applied": "0.00",
            "total": "259.90",
            "date": "invalid-date",
        }
        errors = validate_pos_row(row, row_num=2)
        assert any(e["field"] == "date" for e in errors)

    def test_row_number_in_error_message(self):
        """Row number appears in error messages."""
        row = {
            "transaction_id": "",
            "store_id": "5",
            "cashier_id": "101",
            "product_sku": "SKU001",
            "quantity": "10",
            "unit_price": "25.99",
            "discount_applied": "0.00",
            "total": "259.90",
            "date": "2024-06-01",
        }
        errors = validate_pos_row(row, row_num=42)
        assert any(e["row"] == 42 for e in errors)
