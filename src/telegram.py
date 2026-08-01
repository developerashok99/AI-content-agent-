import logging
import os

import requests

TELEGRAM_MESSAGE_LIMIT = 4096
TIMEOUT = 15

logger = logging.getLogger(__name__)


def _base_url() -> str:
    token = os.environ["TELEGRAM_BOT_TOKEN"]
    return f"https://api.telegram.org/bot{token}"


def chat_ids() -> list[int]:
    raw = os.environ["TELEGRAM_CHAT_IDS"]
    return [int(c.strip()) for c in raw.split(",") if c.strip()]


def send_message(text: str, chat_id: int) -> int | None:
    """Sends a message to a single chat and returns its message_id, or None on failure."""
    try:
        resp = requests.post(
            f"{_base_url()}/sendMessage",
            json={
                "chat_id": chat_id,
                "text": text[:TELEGRAM_MESSAGE_LIMIT],
                "disable_web_page_preview": True,
            },
            timeout=TIMEOUT,
        )
        resp.raise_for_status()
        return resp.json()["result"]["message_id"]
    except Exception:
        logger.exception("Telegram send failed for chat_id %s", chat_id)
        return None


def send_to_all(text: str) -> list[dict]:
    """Sends a message to every configured recipient. Returns one
    {"chat_id": ..., "message_id": ...} entry per successful send."""
    sent = []
    for chat_id in chat_ids():
        message_id = send_message(text, chat_id)
        if message_id is not None:
            sent.append({"chat_id": chat_id, "message_id": message_id})
    return sent


def get_updates(offset: int | None) -> list[dict]:
    """Fetches new messages since `offset` (exclusive). Pass None for the first-ever call."""
    params = {"timeout": 0}
    if offset is not None:
        params["offset"] = offset + 1

    try:
        resp = requests.get(f"{_base_url()}/getUpdates", params=params, timeout=TIMEOUT)
        resp.raise_for_status()
        return resp.json().get("result", [])
    except Exception:
        logger.exception("Telegram getUpdates failed")
        return []
