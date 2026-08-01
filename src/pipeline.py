import logging
import sys

from src import ranker, scriptwriter, state, telegram
from src.models import Article
from src.scrapers import gamerant, gamespot, pcgamer, pcgamesn

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

# Maps source name -> scraper module, used to fetch full article body for
# whichever article the ranker picks (only needed for sources whose RSS
# feed gives a short teaser rather than full text).
SCRAPER_MODULES = {
    gamespot.SOURCE: gamespot,
    gamerant.SOURCE: gamerant,
    pcgamer.SOURCE: pcgamer,
    pcgamesn.SOURCE: pcgamesn,
}


def scrape_all() -> list[Article]:
    articles: list[Article] = []
    for module in (gamespot, gamerant, pcgamer, pcgamesn):
        try:
            fetched = module.fetch()
        except Exception:
            logger.exception("Scraper %s raised unexpectedly", module.SOURCE)
            fetched = []
        logger.info("%s: fetched %d articles", module.SOURCE, len(fetched))
        articles.extend(fetched)
    return articles


def get_full_body(article: Article) -> str:
    if article.body:
        return article.body
    module = SCRAPER_MODULES.get(article.source)
    if module and hasattr(module, "fetch_body"):
        return module.fetch_body(article.url)
    return article.summary


def run() -> int:
    all_articles = scrape_all()
    if not all_articles:
        logger.warning("No articles fetched from any source, aborting run")
        return 1

    seen = state.load_seen()
    new_articles = [a for a in all_articles if a.url not in seen]
    logger.info("%d new articles out of %d fetched", len(new_articles), len(all_articles))

    if not new_articles:
        logger.info("No new articles tonight, nothing to do")
        return 0

    ranking = ranker.rank(new_articles)
    if ranking is None:
        logger.error("Ranking failed, aborting run without updating state")
        return 1

    chosen = next(a for a in new_articles if a.url == ranking["chosen_url"])
    logger.info("Chosen story: %s (%s)", chosen.title, chosen.source)
    logger.info("Reasoning: %s", ranking.get("reasoning", ""))

    full_body = get_full_body(chosen)
    script = scriptwriter.write_script(chosen, full_body)
    if script is None:
        logger.error("Script generation failed, aborting run without updating state")
        return 1

    message = (
        f"\U0001f3ae Tonight's Reel script\n\n"
        f"Source: {chosen.source} — {chosen.title}\n"
        f"{chosen.url}\n\n"
        f"{script}"
    )
    delivered = telegram.send_message(message)
    if not delivered:
        logger.error("Telegram delivery failed, aborting run without updating state")
        return 1

    for article in new_articles:
        state.mark_seen(seen, article.url)
    state.save_seen(seen)
    logger.info("Run complete, state updated")
    return 0


if __name__ == "__main__":
    sys.exit(run())
