import logging

import feedparser
import requests
from bs4 import BeautifulSoup

from src.html_utils import html_to_text
from src.models import Article

FEED_URL = "https://www.pcgamer.com/rss/"
SOURCE = "PC Gamer"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
    )
}
TIMEOUT = 15

logger = logging.getLogger(__name__)


def fetch() -> list[Article]:
    try:
        feed = feedparser.parse(FEED_URL)
        if feed.bozo and not feed.entries:
            raise feed.bozo_exception
    except Exception:
        logger.exception("PC Gamer RSS fetch failed")
        return []

    articles = []
    for entry in feed.entries:
        summary = html_to_text(entry.get("summary", ""))
        articles.append(
            Article(
                title=entry.get("title", "").strip(),
                url=entry.get("link", ""),
                summary=summary,
                source=SOURCE,
                published_at=entry.get("published", ""),
            )
        )
    return articles


def fetch_body(url: str) -> str:
    """Fetch the full article text for a single PC Gamer article page."""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        resp.raise_for_status()
    except Exception:
        logger.exception("PC Gamer article body fetch failed: %s", url)
        return ""

    soup = BeautifulSoup(resp.text, "html.parser")
    body_el = soup.select_one("div#article-body")
    if not body_el:
        return ""
    paragraphs = body_el.select("p")
    return " ".join(p.get_text(" ", strip=True) for p in paragraphs)
