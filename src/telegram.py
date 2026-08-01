import logging
import os

import requests

TELEGRAM_MESSAGE_LIMIT = 4096

logger = logging.getLogger(__name__)


def send_message(text: str) -> bool:
    token = os.environ["TELEGRAM_BOT_TOKEN"]
    chat_id = os.environ["TELEGRAM_CHAT_ID"]
    url = f"https://api.telegram.org/bot{token}/sendMessage"

    try:
        resp = requests.post(
            url,
            json={
                "chat_id": chat_id,
                "text": text[:TELEGRAM_MESSAGE_LIMIT],
                "disable_web_page_preview": True,
            },
            timeout=15,
        )
        resp.raise_for_status()
    except Exception:
        logger.exception("Telegram send failed")
        return False
    return True
