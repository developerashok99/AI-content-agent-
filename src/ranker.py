import json
import logging
import os

from groq import Groq

from src.models import Article

MODEL = os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile")

logger = logging.getLogger(__name__)

RANKER_SYSTEM_PROMPT = """You are a gaming-industry trend analyst for a short-form video (Instagram Reels) \
channel. The channel's audience is gamers aged 19-30 in India, the US, and Japan. Your job is to look at \
today's new gaming articles and pick the SINGLE story with the highest potential to make a viral, \
highly-engaging 30-45 second Reel for that audience.

Favor stories that are: about video games, consoles, or the gaming industry specifically (not generic tech, \
AI, or hardware stories that only tangentially mention gaming); genuinely trending / high buzz right now \
(major releases, big controversies, surprising reveals, esports moments, shutdowns, price changes, \
review-bomb dramas, viral community reactions); and easy to turn into a punchy, curiosity-driven hook in the \
first 3 seconds.

Avoid: routine deals/sales roundups, minor patch notes, and stories with little emotional or curiosity hook.

Respond with ONLY a JSON object, no other text, in this exact shape:
{"chosen_url": "<url of the winning article>", "reasoning": "<one sentence on why this wins today>"}
"""


def rank(articles: list[Article]) -> dict | None:
    if not articles:
        return None

    client = Groq(api_key=os.environ["GROQ_API_KEY"])

    listing = "\n".join(
        f"- url: {a.url}\n  source: {a.source}\n  title: {a.title}\n  summary: {a.summary[:300]}"
        for a in articles
    )

    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": RANKER_SYSTEM_PROMPT},
                {"role": "user", "content": f"Today's new articles:\n\n{listing}"},
            ],
            temperature=0.3,
            response_format={"type": "json_object"},
        )
        result = json.loads(response.choices[0].message.content)
    except Exception:
        logger.exception("Groq ranking call failed")
        return None

    chosen_url = result.get("chosen_url")
    if not chosen_url or not any(a.url == chosen_url for a in articles):
        logger.error("Ranker returned an unknown URL: %s", chosen_url)
        return None

    return result
