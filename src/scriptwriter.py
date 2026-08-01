import logging
import os

from groq import Groq

from src.models import Article

MODEL = os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile")

logger = logging.getLogger(__name__)

SCRIPTWRITER_SYSTEM_PROMPT = """You are a scriptwriter for a gaming Instagram Reels channel. The audience is \
gamers aged 19-30 in India, the US, and Japan. You write scripts that the creator will read on camera and \
manually film/edit — you do NOT produce video, only the script and supporting text.

Write a script for a 30-45 second vertical video based on the article the user gives you. Structure it as:

HOOK (0-3s): One punchy line that stops the scroll — curiosity, shock, or a bold claim. No throat-clearing.
BEAT 1: What happened — the core news, stated fast and clearly.
BEAT 2: Why gamers should care — the stakes, the drama, or the implication for players.
OUTRO: A punchy closing line and a soft call-to-action (e.g. ask a question, prompt a comment/follow).

After the script, add:
CAPTION: a short on-screen/post caption (under 150 characters).
HASHTAGS: 3-5 relevant hashtags.

Tone: energetic, casual, confident — like a gamer talking to gamer friends, not a news anchor. Avoid corporate \
phrasing, avoid explaining basic gaming terms this audience already knows. Keep total spoken word count around \
90-130 words so it fits 30-45 seconds at a natural speaking pace. Plain text output only, no markdown \
formatting, no asterisks."""


def write_script(article: Article, full_body: str) -> str | None:
    client = Groq(api_key=os.environ["GROQ_API_KEY"])

    user_content = (
        f"Title: {article.title}\n"
        f"Source: {article.source}\n"
        f"URL: {article.url}\n\n"
        f"Article text:\n{full_body or article.summary}"
    )

    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": SCRIPTWRITER_SYSTEM_PROMPT},
                {"role": "user", "content": user_content},
            ],
            temperature=0.8,
        )
        return response.choices[0].message.content.strip()
    except Exception:
        logger.exception("Groq scriptwriting call failed")
        return None
