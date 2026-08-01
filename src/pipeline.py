import logging
import sys

from src import feedback, history, ranker, scriptwriter, state, telegram, trends
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


def scrape_all() -> tuple[list[Article], list[dict]]:
    articles: list[Article] = []
    source_stats: list[dict] = []
    for module in (gamespot, gamerant, pcgamer, pcgamesn):
        try:
            fetched = module.fetch()
            ok = True
        except Exception:
            logger.exception("Scraper %s raised unexpectedly", module.SOURCE)
            fetched = []
            ok = False
        logger.info("%s: fetched %d articles", module.SOURCE, len(fetched))
        source_stats.append({"name": module.SOURCE, "count": len(fetched), "ok": ok})
        articles.extend(fetched)
    return articles, source_stats


def get_full_body(article: Article) -> str:
    if article.body:
        return article.body
    module = SCRAPER_MODULES.get(article.source)
    if module and hasattr(module, "fetch_body"):
        return module.fetch_body(article.url)
    return article.summary


def notify_failure(reason: str) -> None:
    telegram.send_to_all(f"⚠️ Tonight's run failed: {reason}")


def format_lead_message(chosen: Article, reasoning: str, trend_context: list[str]) -> str:
    lines = [
        "\U0001f3ae Tonight's pick",
        "",
        f"{chosen.source} — {chosen.title}",
        chosen.url,
        "",
        f"Why: {reasoning}",
    ]
    if trend_context:
        lines += ["", "Trend signals used:"] + [f"- {t}" for t in trend_context[:5]]
    return "\n".join(lines)


def format_variant_message(variant: dict) -> str:
    return (
        f"\U0001f4dd Script {variant.get('label', '')}\n\n"
        f"HOOK: {variant.get('hook', '')}\n\n"
        f"BEAT 1: {variant.get('beat1', '')}\n\n"
        f"BEAT 2: {variant.get('beat2', '')}\n\n"
        f"OUTRO: {variant.get('outro', '')}\n\n"
        f"VISUALS: {variant.get('visuals', '')}\n\n"
        f"CAPTION: {variant.get('caption', '')}\n"
        f"HASHTAGS: {variant.get('hashtags', '')}"
    )


def fail(entries: list[dict], entry: dict, reason: str) -> int:
    entry["status"] = "failed"
    entry["error"] = reason
    logger.error(reason)
    notify_failure(reason)
    history.append_entry(entries, entry)
    history.save_history(entries)
    return 1


def run() -> int:
    entries = history.load_history()
    entry = history.new_entry("failed", "run did not complete")

    entry["feedback_collected"] = feedback.collect_feedback(entries)
    if entry["feedback_collected"]:
        history.save_history(entries)
        logger.info("Recorded %d new feedback replies", entry["feedback_collected"])

    all_articles, source_stats = scrape_all()
    entry["sources"] = source_stats
    if not all_articles:
        return fail(entries, entry, "all scrapers returned nothing")

    seen = state.load_seen()
    new_articles = [a for a in all_articles if a.url not in seen]
    logger.info("%d new articles out of %d fetched", len(new_articles), len(all_articles))

    if not new_articles:
        logger.info("No new articles tonight, nothing to do")
        entry["status"] = "no_new_articles"
        entry["error"] = None
        history.append_entry(entries, entry)
        history.save_history(entries)
        return 0

    trend_context = trends.fetch_trend_context()
    entry["services"]["youtube_trends"] = {"count": len(trend_context)}
    recent_topics = history.recent_topics(entries)
    feedback_notes = history.recent_feedback(entries)

    ranking = ranker.rank(new_articles, trend_context, recent_topics, feedback_notes)
    entry["services"]["groq_ranker"] = {"ok": ranking is not None}
    if ranking is None:
        return fail(entries, entry, "Groq ranking call failed")

    chosen = next(a for a in new_articles if a.url == ranking["chosen_url"])
    logger.info("Chosen story: %s (%s)", chosen.title, chosen.source)
    logger.info("Reasoning: %s", ranking.get("reasoning", ""))

    full_body = get_full_body(chosen)
    variants = scriptwriter.write_scripts(chosen, full_body, trend_context)
    entry["services"]["groq_scriptwriter"] = {"ok": bool(variants)}
    if not variants:
        return fail(entries, entry, "Groq scriptwriting call failed")

    total_recipients = len(telegram.chat_ids())
    lead_sent = telegram.send_to_all(
        format_lead_message(chosen, ranking.get("reasoning", ""), trend_context)
    )
    entry["services"]["telegram"] = {"reached": len(lead_sent), "total": total_recipients}
    if not lead_sent:
        return fail(entries, entry, "Telegram delivery failed for every recipient")

    for variant in variants:
        variant["telegram_message_ids"] = telegram.send_to_all(format_variant_message(variant))

    entry["status"] = "success"
    entry["error"] = None
    entry["chosen"] = {
        "title": chosen.title,
        "url": chosen.url,
        "source": chosen.source,
        "reasoning": ranking.get("reasoning", ""),
    }
    entry["trend_context"] = trend_context
    entry["variants"] = variants
    history.append_entry(entries, entry)
    history.save_history(entries)

    for article in new_articles:
        state.mark_seen(seen, article.url)
    state.save_seen(seen)
    logger.info("Run complete, state updated")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(run())
    except Exception:
        logger.exception("Pipeline crashed unexpectedly")
        notify_failure("unexpected crash, check GitHub Actions logs")
        sys.exit(1)
