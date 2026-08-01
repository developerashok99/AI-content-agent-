import logging
import os

import requests

API_URL = "https://www.googleapis.com/youtube/v3/videos"
GAMING_CATEGORY_ID = "20"
REGIONS = ("IN", "US", "JP")
MAX_RESULTS_PER_REGION = 10
TIMEOUT = 15

logger = logging.getLogger(__name__)


def fetch_trend_context() -> list[str]:
    api_key = os.environ.get("YOUTUBE_API_KEY")
    if not api_key:
        logger.warning("YOUTUBE_API_KEY not set, skipping trend context")
        return []

    context = []
    for region in REGIONS:
        try:
            resp = requests.get(
                API_URL,
                params={
                    "part": "snippet",
                    "chart": "mostPopular",
                    "regionCode": region,
                    "videoCategoryId": GAMING_CATEGORY_ID,
                    "maxResults": MAX_RESULTS_PER_REGION,
                    "key": api_key,
                },
                timeout=TIMEOUT,
            )
            resp.raise_for_status()
            items = resp.json().get("items", [])
        except Exception:
            logger.exception("YouTube trending fetch failed for region %s", region)
            continue

        for item in items:
            title = item.get("snippet", {}).get("title", "").strip()
            if title:
                context.append(f"[{region} trending] {title}")

    logger.info("Fetched %d trending gaming video titles across %s", len(context), REGIONS)
    return context
