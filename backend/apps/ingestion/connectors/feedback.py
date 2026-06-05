import logging

import requests

logger = logging.getLogger(__name__)

REQUEST_TIMEOUT = 30


class FeedbackAPIConnector:
    """Fetches feedback survey records from the external source API."""

    def fetch_all(self) -> list[dict]:
        """
        Returns all feedback records.
        Handles both a flat-array response and a paginated `{data: [...]}` shape.
        """
        feedbacks_url = "https://ext-amali.vercel.app/api/feedbacks"

        response = requests.get(feedbacks_url, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        payload = response.json()

        if isinstance(payload, list):
            logger.debug(f"Feedback API returned flat array — {len(payload)} records")
            return payload

        records = list(payload.get("data", []))
        total_pages = payload.get("totalPages", 1)
        for page in range(2, total_pages + 1):
            resp = requests.get(
                feedbacks_url,
                params={"page": page, "limit": 100},
                timeout=REQUEST_TIMEOUT,
            )
            resp.raise_for_status()
            body = resp.json()
            records.extend(body.get("data", []))

        logger.debug(
            f"Feedback API fetched {len(records)} records across {total_pages} pages"
        )
        return records
