"""HTTP client for the external Online Orders API."""

import os
from typing import Any

import requests


class OnlineOrdersAPIClient:
    """Thin wrapper around the external online-orders REST API."""

    def __init__(self, base_url: str | None = None, api_key: str | None = None):
        env_base_url = os.environ.get("ONLINE_ORDERS_API_URL", "")
        self.base_url = (base_url or env_base_url or "").rstrip("/")
        self.api_key = api_key or os.environ.get("ONLINE_ORDERS_API_KEY", "")
        self.session = requests.Session()
        if self.api_key:
            self.session.headers["Authorization"] = f"Bearer {self.api_key}"

    def _get(self, path: str, params: dict | None = None) -> dict[Any, Any]:
        url = f"{self.base_url}{path}"
        response = self.session.get(url, params=params, timeout=30)
        response.raise_for_status()
        data: Any = response.json()
        if not isinstance(data, dict):
            return {}
        return data

    def fetch_orders(self, page: int = 1, page_size: int = 100) -> dict[Any, Any]:
        """Fetch a page of orders from the external API."""
        return self._get("/orders", params={"page": page, "page_size": page_size})

    def fetch_order(self, order_id: str) -> dict[Any, Any]:
        """Fetch a single order by ID."""
        return self._get(f"/orders/{order_id}")
