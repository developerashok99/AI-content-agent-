import logging
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from src.models import Article

LISTING_URL = "https://gamerant.com/gaming/"
SOURCE = "GameRant"
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
        resp = requests.get(LISTING_URL, headers=HEADERS, timeout=TIMEOUT)
        resp.raise_for_status()
    except Exception:
        logger.exception("GameRant listing fetch failed")
        return []

    soup = BeautifulSoup(resp.text, "html.parser")
    articles = []
    for card in soup.select("div.display-card"):
        title_el = card.select_one(".display-card-title a")
        excerpt_el = card.select_one(".display-card-excerpt")
        if not title_el or not title_el.get("href"):
            continue
        url = urljoin(LISTING_URL, title_el["href"])
        articles.append(
            Article(
                title=title_el.get_text(strip=True),
                url=url,
                summary=excerpt_el.get_text(strip=True) if excerpt_el else "",
                source=SOURCE,
                published_at="",
            )
        )
    return articles


def fetch_body(url: str) -> str:
    """Fetch the full article text for a single GameRant article page."""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        resp.raise_for_status()
    except Exception:
        logger.exception("GameRant article body fetch failed: %s", url)
        return ""

    soup = BeautifulSoup(resp.text, "html.parser")
    article_el = soup.select_one("article.w-article")
    if not article_el:
        return ""
    paragraphs = article_el.select("p")
    return " ".join(p.get_text(" ", strip=True) for p in paragraphs)
