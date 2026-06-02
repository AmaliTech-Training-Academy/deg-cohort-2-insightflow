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
    extract_pos_transactions after normalisation into factSales.
    """
    data = [
        {
            "sourceTransactionId": "POS-001",
            "productSKU": "SKU-A",
            "productName": "Widget Alpha",
            "categoryName": "Electronics",
            "storeId": 1,
            "storeName": "Accra Central",
            "province": "Greater Accra",
            "country": "Ghana",
            "channel": "POS",
            "paymentMethod": "Cash",
            "orderStatus": "Completed",
            "transactionDatetime": "2024-03-15 10:30:00",
            "customerId": 1001,
            "quantity": 2,
            "unitPrice": 50.00,
            "discountApplied": 5.00,
            "grossAmount": 100.00,
            "netAmount": 95.00,
        },
        {
            "sourceTransactionId": "POS-002",
            "productSKU": "SKU-B",
            "productName": "Gadget Beta",
            "categoryName": "Accessories",
            "storeId": 1,
            "storeName": "Accra Central",
            "province": "Greater Accra",
            "country": "Ghana",
            "channel": "POS",
            "paymentMethod": "Card",
            "orderStatus": "Completed",
            "transactionDatetime": "2024-03-15 11:00:00",
            "customerId": 1002,
            "quantity": 1,
            "unitPrice": 120.00,
            "discountApplied": 0.00,
            "grossAmount": 120.00,
            "netAmount": 120.00,
        },
        {
            "sourceTransactionId": "ONL-001",
            "productSKU": "SKU-C",
            "productName": "Service Pro",
            "categoryName": "Services",
            "storeId": 2,
            "storeName": "Kigali Hub",
            "province": "Kigali",
            "country": "Rwanda",
            "channel": "ONLINE",
            "paymentMethod": "MobileMoney",
            "orderStatus": "Delivered",
            "transactionDatetime": "2024-03-16 08:00:00",
            "customerId": 2001,
            "quantity": 3,
            "unitPrice": 30.00,
            "discountApplied": 3.00,
            "grossAmount": 90.00,
            "netAmount": 87.00,
        },
        {
            "sourceTransactionId": "ONL-002",
            "productSKU": "SKU-A",
            "productName": "Widget Alpha",
            "categoryName": "Electronics",
            "storeId": 2,
            "storeName": "Kigali Hub",
            "province": "Kigali",
            "country": "Rwanda",
            "channel": "ONLINE",
            "paymentMethod": "Card",
            "orderStatus": "Delivered",
            "transactionDatetime": "2024-03-17 14:00:00",
            "customerId": 2002,
            "quantity": 1,
            "unitPrice": 50.00,
            "discountApplied": 0.00,
            "grossAmount": 50.00,
            "netAmount": 50.00,
        },
        {
            "sourceTransactionId": "POS-003",
            "productSKU": "SKU-D",
            "productName": "Gadget Delta",
            "categoryName": "Electronics",
            "storeId": 3,
            "storeName": "Kumasi North",
            "province": "Ashanti",
            "country": "Ghana",
            "channel": "POS",
            "paymentMethod": "Cash",
            "orderStatus": "Completed",
            "transactionDatetime": "2024-03-18 09:30:00",
            "customerId": 1003,
            "quantity": 4,
            "unitPrice": 25.00,
            "discountApplied": 2.50,
            "grossAmount": 100.00,
            "netAmount": 97.50,
        },
    ]
    return pd.DataFrame(data)


@pytest.fixture()
def sample_feedback_df() -> pd.DataFrame:
    """Five valid rows covering the feedbackSurvey source columns."""
    data = [
        {
            "sourceOrderId": "ONL-001",
            "customerId": 2001,
            "fullName": "Kwame Asante",
            "email": "kwame@example.com",
            "province": "Greater Accra",
            "country": "Ghana",
            "submissionDate": "2024-03-20",
            "satisfactionScore": 8,
            "npsScore": 7,
            "productRating": 4,
            "deliveryRating": 5,
            "freeTextComments": "Great service overall.",
        },
        {
            "sourceOrderId": "ONL-002",
            "customerId": 2002,
            "fullName": "Amina Uwimana",
            "email": "amina@example.com",
            "province": "Kigali",
            "country": "Rwanda",
            "submissionDate": "2024-03-21",
            "satisfactionScore": 6,
            "npsScore": 5,
            "productRating": 3,
            "deliveryRating": 3,
            "freeTextComments": "Delivery was a bit slow.",
        },
        {
            "sourceOrderId": "ONL-003",
            "customerId": 2003,
            "fullName": "Kofi Mensah",
            "email": "kofi@example.com",
            "province": "Ashanti",
            "country": "Ghana",
            "submissionDate": "2024-03-22",
            "satisfactionScore": 10,
            "npsScore": 9,
            "productRating": 5,
            "deliveryRating": 5,
            "freeTextComments": "Excellent!",
        },
        {
            "sourceOrderId": "ONL-004",
            "customerId": 2004,
            "fullName": "Diane Mukamana",
            "email": "diane@example.com",
            "province": "Eastern",
            "country": "Rwanda",
            "submissionDate": "2024-03-23",
            "satisfactionScore": 5,
            "npsScore": 4,
            "productRating": 3,
            "deliveryRating": 2,
            "freeTextComments": "Product okay, packaging poor.",
        },
        {
            "sourceOrderId": "ONL-005",
            "customerId": 2005,
            "fullName": "Esi Boateng",
            "email": "esi@example.com",
            "province": "Western",
            "country": "Ghana",
            "submissionDate": "2024-03-24",
            "satisfactionScore": 9,
            "npsScore": 8,
            "productRating": 4,
            "deliveryRating": 4,
            "freeTextComments": "",
        },
    ]
    return pd.DataFrame(data)


@pytest.fixture()
def sample_inventory_df() -> pd.DataFrame:
    """Five valid rows for inventory snapshot tests."""
    data = [
        {
            "productSKU": "SKU-A",
            "productName": "Widget Alpha",
            "categoryName": "Electronics",
            "storeId": 1,
            "storeName": "Accra Central",
            "province": "Greater Accra",
            "stockQuantity": 50,
            "reorderThreshold": 10,
            "lastRestockedDate": "2024-03-01",
            "daysSinceRestock": 14,
        },
        {
            "productSKU": "SKU-B",
            "productName": "Gadget Beta",
            "categoryName": "Accessories",
            "storeId": 1,
            "storeName": "Accra Central",
            "province": "Greater Accra",
            "stockQuantity": 8,
            "reorderThreshold": 10,
            "lastRestockedDate": "2024-02-20",
            "daysSinceRestock": 24,
        },
        {
            "productSKU": "SKU-C",
            "productName": "Service Pro",
            "categoryName": "Services",
            "storeId": 2,
            "storeName": "Kigali Hub",
            "province": "Kigali",
            "stockQuantity": 100,
            "reorderThreshold": 20,
            "lastRestockedDate": "2024-03-10",
            "daysSinceRestock": 5,
        },
        {
            "productSKU": "SKU-D",
            "productName": "Gadget Delta",
            "categoryName": "Electronics",
            "storeId": 3,
            "storeName": "Kumasi North",
            "province": "Ashanti",
            "stockQuantity": 5,
            "reorderThreshold": 15,
            "lastRestockedDate": "2024-02-15",
            "daysSinceRestock": 29,
        },
        {
            "productSKU": "SKU-E",
            "productName": "Widget Epsilon",
            "categoryName": "Electronics",
            "storeId": 2,
            "storeName": "Kigali Hub",
            "province": "Kigali",
            "stockQuantity": 25,
            "reorderThreshold": 10,
            "lastRestockedDate": "2024-03-05",
            "daysSinceRestock": 10,
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
