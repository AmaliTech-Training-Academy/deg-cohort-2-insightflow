import logging
import os
from collections.abc import Generator
from typing import Any

import requests

logger = logging.getLogger(__name__)

_DEFAULT_LIMIT = 100
_TIMEOUT = 30


class OnlineOrdersAPIError(Exception):
    pass


def _base_url() -> str:
    url = os.environ.get("ONLINE_ORDERS_API_URL", "").rstrip("/")
    if not url:
        raise OnlineOrdersAPIError("ONLINE_ORDERS_API_URL is not configured.")
    return url


def fetch_orders_page(page: int, limit: int = _DEFAULT_LIMIT) -> dict[str, Any]:
    url = f"{_base_url()}/api/orders"
    try:
        resp = requests.get(
            url, params={"page": page, "limit": limit}, timeout=_TIMEOUT
        )
        resp.raise_for_status()
        return resp.json()  # type: ignore[no-any-return]
    except requests.exceptions.RequestException as exc:
        logger.error("Online orders API error page=%s: %s", page, exc)
        raise OnlineOrdersAPIError(str(exc)) from exc


def iter_all_pages(
    limit: int = _DEFAULT_LIMIT,
) -> Generator[list[dict[str, Any]], None, None]:
    first = fetch_orders_page(page=1, limit=limit)
    yield first["data"]
    total_pages: int = first.get("totalPages", 1)
    for page in range(2, total_pages + 1):
        payload = fetch_orders_page(page=page, limit=limit)
        yield payload["data"]
