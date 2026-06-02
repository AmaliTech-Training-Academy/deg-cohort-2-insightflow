"""Shared pytest fixtures for the data-engineering test suite."""

import sys
from pathlib import Path

import pandas as pd
import pytest

# ---------------------------------------------------------------------------
# Make the data-engineering package importable from the qa/ tree
# ---------------------------------------------------------------------------
_DE_ROOT = Path(__file__).parent.parent.parent / "data-engineering"
if str(_DE_ROOT) not in sys.path:
    sys.path.insert(0, str(_DE_ROOT))

from etl.quality import DataQualityChecker  # noqa: E402
from etl.transform import Transformer  # noqa: E402

# ---------------------------------------------------------------------------
# Sample DataFrames
# ---------------------------------------------------------------------------


@pytest.fixture()
def sample_sales_df() -> pd.DataFrame:
    """Five valid rows covering the unified sales fact source columns.

    Column names mirror those produced by Transformer.cleanse_sales /
    extract_pos_transactions after normalisation into fact_sales.
    """
    data = [
        {
            "source_transaction_id": "POS-001",
            "product_sku": "SKU-A",
            "product_name": "Widget Alpha",
            "category_name": "Electronics",
            "store_id": 1,
            "store_name": "Accra Central",
            "province": "Greater Accra",
            "country": "Ghana",
            "channel": "POS",
            "payment_method": "Cash",
            "order_status": "Completed",
            "transaction_datetime": "2024-03-15 10:30:00",
            "customer_id": 1001,
            "quantity": 2,
            "unit_price": 50.00,
            "discount_applied": 5.00,
            "gross_amount": 100.00,
            "net_amount": 95.00,
        },
        {
            "source_transaction_id": "POS-002",
            "product_sku": "SKU-B",
            "product_name": "Gadget Beta",
            "category_name": "Accessories",
            "store_id": 1,
            "store_name": "Accra Central",
            "province": "Greater Accra",
            "country": "Ghana",
            "channel": "POS",
            "payment_method": "Card",
            "order_status": "Completed",
            "transaction_datetime": "2024-03-15 11:00:00",
            "customer_id": 1002,
            "quantity": 1,
            "unit_price": 120.00,
            "discount_applied": 0.00,
            "gross_amount": 120.00,
            "net_amount": 120.00,
        },
        {
            "source_transaction_id": "ONL-001",
            "product_sku": "SKU-C",
            "product_name": "Service Pro",
            "category_name": "Services",
            "store_id": 2,
            "store_name": "Kigali Hub",
            "province": "Kigali",
            "country": "Rwanda",
            "channel": "ONLINE",
            "payment_method": "MobileMoney",
            "order_status": "Delivered",
            "transaction_datetime": "2024-03-16 08:00:00",
            "customer_id": 2001,
            "quantity": 3,
            "unit_price": 30.00,
            "discount_applied": 3.00,
            "gross_amount": 90.00,
            "net_amount": 87.00,
        },
        {
            "source_transaction_id": "ONL-002",
            "product_sku": "SKU-A",
            "product_name": "Widget Alpha",
            "category_name": "Electronics",
            "store_id": 2,
            "store_name": "Kigali Hub",
            "province": "Kigali",
            "country": "Rwanda",
            "channel": "ONLINE",
            "payment_method": "Card",
            "order_status": "Delivered",
            "transaction_datetime": "2024-03-17 14:00:00",
            "customer_id": 2002,
            "quantity": 1,
            "unit_price": 50.00,
            "discount_applied": 0.00,
            "gross_amount": 50.00,
            "net_amount": 50.00,
        },
        {
            "source_transaction_id": "POS-003",
            "product_sku": "SKU-D",
            "product_name": "Gadget Delta",
            "category_name": "Electronics",
            "store_id": 3,
            "store_name": "Kumasi North",
            "province": "Ashanti",
            "country": "Ghana",
            "channel": "POS",
            "payment_method": "Cash",
            "order_status": "Completed",
            "transaction_datetime": "2024-03-18 09:30:00",
            "customer_id": 1003,
            "quantity": 4,
            "unit_price": 25.00,
            "discount_applied": 2.50,
            "gross_amount": 100.00,
            "net_amount": 97.50,
        },
    ]
    return pd.DataFrame(data)


@pytest.fixture()
def sample_feedback_df() -> pd.DataFrame:
    """Five valid rows covering the feedbackSurvey source columns."""
    data = [
        {
            "source_order_id": "ONL-001",
            "customer_id": 2001,
            "full_name": "Kwame Asante",
            "email": "kwame@example.com",
            "province": "Greater Accra",
            "country": "Ghana",
            "submission_date": "2024-03-20",
            "satisfaction_score": 8,
            "nps_score": 7,
            "product_rating": 4,
            "delivery_rating": 5,
            "free_text_comments": "Great service overall.",
        },
        {
            "source_order_id": "ONL-002",
            "customer_id": 2002,
            "full_name": "Amina Uwimana",
            "email": "amina@example.com",
            "province": "Kigali",
            "country": "Rwanda",
            "submission_date": "2024-03-21",
            "satisfaction_score": 6,
            "nps_score": 5,
            "product_rating": 3,
            "delivery_rating": 3,
            "free_text_comments": "Delivery was a bit slow.",
        },
        {
            "source_order_id": "ONL-003",
            "customer_id": 2003,
            "full_name": "Kofi Mensah",
            "email": "kofi@example.com",
            "province": "Ashanti",
            "country": "Ghana",
            "submission_date": "2024-03-22",
            "satisfaction_score": 10,
            "nps_score": 9,
            "product_rating": 5,
            "delivery_rating": 5,
            "free_text_comments": "Excellent!",
        },
        {
            "source_order_id": "ONL-004",
            "customer_id": 2004,
            "full_name": "Diane Mukamana",
            "email": "diane@example.com",
            "province": "Eastern",
            "country": "Rwanda",
            "submission_date": "2024-03-23",
            "satisfaction_score": 5,
            "nps_score": 4,
            "product_rating": 3,
            "delivery_rating": 2,
            "free_text_comments": "Product okay, packaging poor.",
        },
        {
            "source_order_id": "ONL-005",
            "customer_id": 2005,
            "full_name": "Esi Boateng",
            "email": "esi@example.com",
            "province": "Western",
            "country": "Ghana",
            "submission_date": "2024-03-24",
            "satisfaction_score": 9,
            "nps_score": 8,
            "product_rating": 4,
            "delivery_rating": 4,
            "free_text_comments": "",
        },
    ]
    return pd.DataFrame(data)


@pytest.fixture()
def sample_inventory_df() -> pd.DataFrame:
    """Five valid rows for inventory snapshot tests."""
    data = [
        {
            "product_sku": "SKU-A",
            "product_name": "Widget Alpha",
            "category_name": "Electronics",
            "store_id": 1,
            "store_name": "Accra Central",
            "province": "Greater Accra",
            "stock_quantity": 50,
            "reorder_threshold": 10,
            "last_restocked_date": "2024-03-01",
            "days_since_restock": 14,
        },
        {
            "product_sku": "SKU-B",
            "product_name": "Gadget Beta",
            "category_name": "Accessories",
            "store_id": 1,
            "store_name": "Accra Central",
            "province": "Greater Accra",
            "stock_quantity": 8,
            "reorder_threshold": 10,
            "last_restocked_date": "2024-02-20",
            "days_since_restock": 24,
        },
        {
            "product_sku": "SKU-C",
            "product_name": "Service Pro",
            "category_name": "Services",
            "store_id": 2,
            "store_name": "Kigali Hub",
            "province": "Kigali",
            "stock_quantity": 100,
            "reorder_threshold": 20,
            "last_restocked_date": "2024-03-10",
            "days_since_restock": 5,
        },
        {
            "product_sku": "SKU-D",
            "product_name": "Gadget Delta",
            "category_name": "Electronics",
            "store_id": 3,
            "store_name": "Kumasi North",
            "province": "Ashanti",
            "stock_quantity": 5,
            "reorder_threshold": 15,
            "last_restocked_date": "2024-02-15",
            "days_since_restock": 29,
        },
        {
            "product_sku": "SKU-E",
            "product_name": "Widget Epsilon",
            "category_name": "Electronics",
            "store_id": 2,
            "store_name": "Kigali Hub",
            "province": "Kigali",
            "stock_quantity": 25,
            "reorder_threshold": 10,
            "last_restocked_date": "2024-03-05",
            "days_since_restock": 10,
        },
    ]
    return pd.DataFrame(data)


# ---------------------------------------------------------------------------
# Module-level instances
# ---------------------------------------------------------------------------


@pytest.fixture()
def quality_checker() -> DataQualityChecker:
    """Return a fresh DataQualityChecker instance."""
    return DataQualityChecker()


@pytest.fixture()
def transformer() -> Transformer:
    """Return a fresh Transformer instance."""
    return Transformer()
