import json
import logging
import os

from groq import Groq

from src.models import Article

MODEL = os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile")
NUM_VARIANTS = 2
MAX_TREND_ITEMS = 15

logger = logging.getLogger(__name__)

SCRIPTWRITER_SYSTEM_PROMPT = f"""You are a scriptwriter for a gaming Instagram Reels channel. The audience is \
gamers aged 19-30 in India, the US, and Japan. You write scripts that the creator will read on camera and \
manually film/edit — you do NOT produce video, only the script and supporting text.

Write {NUM_VARIANTS} DIFFERENT script variants for a 30-45 second vertical video based on the article the user \
gives you. Each variant should take a distinctly different hook/angle on the same story (e.g. one shock/curiosity \
angle, one hot-take/opinion angle, one "here's what this means for you" angle) — not just reworded versions of \
each other.

Each variant needs these fields:
- hook: One punchy line (0-3s) that stops the scroll. No throat-clearing.
- beat1: What happened — the core news, stated fast and clearly.
- beat2: Why gamers should care — the stakes, the drama, or the implication for players.
- outro: A punchy closing line plus a soft call-to-action (ask a question, prompt a comment/follow).
- visuals: Concrete filming notes — what screenshot/gameplay clip/B-roll to grab for each beat, and when to add \
on-screen text. Written as short actionable bullets the creator can follow while filming.
- caption: A short on-screen/post caption, under 150 characters.
- hashtags: 3-5 relevant hashtags, space-separated, each starting with #.

Tone: energetic, casual, confident — like a gamer talking to gamer friends, not a news anchor. Avoid corporate \
phrasing, avoid explaining basic gaming terms this audience already knows. Keep hook+beat1+beat2+outro combined \
around 90-130 words so it fits 30-45 seconds at a natural speaking pace. Plain text in each field, no markdown.

Respond with ONLY a JSON object, no other text, in this exact shape:
{{"variants": [{{"label": "A", "hook": "...", "beat1": "...", "beat2": "...", "outro": "...", "visuals": "...", \
"caption": "...", "hashtags": "..."}}, ...]}}
"""


def write_scripts(article: Article, full_body: str, trend_context: list[str] | None = None) -> list[dict] | None:
    client = Groq(api_key=os.environ["GROQ_API_KEY"])

    sections = [
        f"Title: {article.title}\n"
        f"Source: {article.source}\n"
        f"URL: {article.url}\n\n"
        f"Article text:\n{full_body or article.summary}"
    ]
    if trend_context:
        trend_listing = "\n".join(f"- {t}" for t in trend_context[:MAX_TREND_ITEMS])
        sections.append(f"Today's trending gaming videos (IN/US/JP), for tone/reference if relevant:\n\n{trend_listing}")

    user_content = "\n\n---\n\n".join(sections)

    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": SCRIPTWRITER_SYSTEM_PROMPT},
                {"role": "user", "content": user_content},
            ],
            temperature=0.8,
            response_format={"type": "json_object"},
        )
        result = json.loads(response.choices[0].message.content)
        variants = result.get("variants")
        if not variants:
            logger.error("Scriptwriter returned no variants")
            return None
        return variants
    except Exception:
        logger.exception("Groq scriptwriting call failed")
        return None
