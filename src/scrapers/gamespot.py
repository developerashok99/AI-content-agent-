import logging

import feedparser

from src.html_utils import html_to_text
from src.models import Article

FEED_URL = "https://www.gamespot.com/feeds/news/"
SOURCE = "GameSpot"

logger = logging.getLogger(__name__)


def fetch() -> list[Article]:
    try:
        feed = feedparser.parse(FEED_URL)
        if feed.bozo and not feed.entries:
            raise feed.bozo_exception
    except Exception:
        logger.exception("GameSpot RSS fetch failed")
        return []

    articles = []
    for entry in feed.entries:
        body = html_to_text(entry.get("summary", ""))
        articles.append(
            Article(
                title=entry.get("title", "").strip(),
                url=entry.get("link", ""),
                summary=body[:400],
                source=SOURCE,
                published_at=entry.get("published", ""),
                body=body,
            )
        )
    return articles
