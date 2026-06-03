"""
Unit tests for online orders validator and connector.
No database or running server required.
"""

from unittest.mock import MagicMock, patch

import pytest
import requests as _requests
from apps.ingestion.connectors.online_orders import (
    OnlineOrdersAPIError,
    fetch_orders_page,
    iter_all_pages,
)
from apps.ingestion.validators.online_orders import validate_order, validate_order_line

VALID_ORDER: dict = {
    "onlineOrderId": 1,
    "customerId": "CUST-000001",
    "orderDatetime": "2026-05-20T16:10:32.002120",
    "shippingProvince": "Northern",
    "orderStatus": "shipped",
    "paymentMethod": "paypal",
    "lines": [],
}

VALID_LINE: dict = {
    "lineId": 1,
    "onlineOrderId": 1,
    "productSKU": "PROD-0000028",
    "quantity": 2,
    "unitPrice": "913.04",
    "discountApplied": "29.80",
    "totalAmount": "1796.28",
}

_PAGE_1: dict = {"page": 1, "limit": 100, "totalOrders": 1, "totalPages": 1, "data": [VALID_ORDER]}


class TestOnlineOrderValidator:
    def test_valid_order_returns_no_errors(self):
        assert validate_order(VALID_ORDER) == []

    def test_missing_order_id_returns_error(self):
        errors = validate_order({**VALID_ORDER, "onlineOrderId": None})
        assert any(e["field"] == "onlineOrderId" for e in errors)

    def test_missing_customer_id_returns_error(self):
        errors = validate_order({**VALID_ORDER, "customerId": ""})
        assert any(e["field"] == "customerId" for e in errors)

    def test_invalid_order_id_type_returns_error(self):
        errors = validate_order({**VALID_ORDER, "onlineOrderId": "not-an-int"})
        assert any(e["field"] == "onlineOrderId" for e in errors)

    def test_valid_line_returns_no_errors(self):
        assert validate_order_line(VALID_LINE) == []

    def test_missing_line_id_returns_error(self):
        errors = validate_order_line({**VALID_LINE, "lineId": None})
        assert any(e["field"] == "lineId" for e in errors)

    def test_negative_unit_price_returns_error(self):
        errors = validate_order_line({**VALID_LINE, "unitPrice": "-1.00"})
        assert any(e["field"] == "unitPrice" for e in errors)

    def test_zero_quantity_returns_error(self):
        errors = validate_order_line({**VALID_LINE, "quantity": 0})
        assert any(e["field"] == "quantity" for e in errors)

    def test_negative_discount_returns_error(self):
        errors = validate_order_line({**VALID_LINE, "discountApplied": "-5.00"})
        assert any(e["field"] == "discountApplied" for e in errors)


class TestOnlineOrderConnector:
    def test_fetch_page_success(self):
        mock_resp = MagicMock()
        mock_resp.json.return_value = _PAGE_1
        with patch(
            "apps.ingestion.connectors.online_orders.requests.get"
        ) as mock_get, patch.dict("os.environ", {"ONLINE_ORDERS_API_URL": "https://example.com"}):
            mock_get.return_value = mock_resp
            result = fetch_orders_page(page=1)
            assert result["totalPages"] == 1
            assert len(result["data"]) == 1

    def test_fetch_page_raises_on_http_error(self):
        mock_resp = MagicMock()
        mock_resp.raise_for_status.side_effect = _requests.exceptions.HTTPError("500")
        with patch(
            "apps.ingestion.connectors.online_orders.requests.get"
        ) as mock_get, patch.dict("os.environ", {"ONLINE_ORDERS_API_URL": "https://example.com"}):
            mock_get.return_value = mock_resp
            with pytest.raises(OnlineOrdersAPIError):
                fetch_orders_page(page=1)

    def test_fetch_page_raises_on_network_error(self):
        with patch(
            "apps.ingestion.connectors.online_orders.requests.get"
        ) as mock_get, patch.dict("os.environ", {"ONLINE_ORDERS_API_URL": "https://example.com"}):
            mock_get.side_effect = _requests.exceptions.ConnectionError("refused")
            with pytest.raises(OnlineOrdersAPIError):
                fetch_orders_page(page=1)

    def test_fetch_page_raises_when_url_not_configured(self):
        with patch.dict("os.environ", {"ONLINE_ORDERS_API_URL": ""}):
            with pytest.raises(OnlineOrdersAPIError, match="not configured"):
                fetch_orders_page(page=1)

    def test_iter_all_pages_single_page(self):
        with patch("apps.ingestion.connectors.online_orders.fetch_orders_page") as mock_fetch:
            mock_fetch.return_value = _PAGE_1
            pages = list(iter_all_pages())
            assert len(pages) == 1
            mock_fetch.assert_called_once_with(page=1, limit=100)

    def test_iter_all_pages_multiple_pages(self):
        with patch("apps.ingestion.connectors.online_orders.fetch_orders_page") as mock_fetch:
            mock_fetch.side_effect = [
                {**_PAGE_1, "totalPages": 3},
                {**_PAGE_1, "page": 2, "totalPages": 3},
                {**_PAGE_1, "page": 3, "totalPages": 3, "data": []},
            ]
            pages = list(iter_all_pages())
            assert mock_fetch.call_count == 3
            assert len(pages) == 3
