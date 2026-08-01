import json
import logging
import os
from datetime import datetime, timezone

from src import telegram

OFFSET_PATH = os.path.join(os.path.dirname(__file__), "..", "state", "telegram_offset.json")

logger = logging.getLogger(__name__)


def _load_offset() -> int | None:
    if not os.path.exists(OFFSET_PATH):
        return None
    with open(OFFSET_PATH, "r") as f:
        return json.load(f).get("last_update_id")


def _save_offset(update_id: int) -> None:
    os.makedirs(os.path.dirname(OFFSET_PATH), exist_ok=True)
    with open(OFFSET_PATH, "w") as f:
        json.dump({"last_update_id": update_id}, f, indent=2)


def collect_feedback(entries: list[dict]) -> int:
    """Polls Telegram for replies to past script messages and appends them to the
    matching history entry's feedback list. Returns how many replies were matched."""
    offset = _load_offset()
    updates = telegram.get_updates(offset)
    if not updates:
        return 0

    # Keyed by (chat_id, message_id) since message_id is only unique within a chat.
    message_map = {}
    for entry in entries:
        for variant in entry.get("variants", []):
            for sent in variant.get("telegram_message_ids", []):
                message_map[(sent["chat_id"], sent["message_id"])] = entry

    matched = 0
    max_update_id = offset or 0
    for update in updates:
        max_update_id = max(max_update_id, update["update_id"])
        message = update.get("message")
        if not message:
            continue
        reply_to = message.get("reply_to_message")
        if not reply_to:
            continue
        chat_id = message.get("chat", {}).get("id")
        target_entry = message_map.get((chat_id, reply_to.get("message_id")))
        if not target_entry:
            continue
        text = message.get("text", "").strip()
        if not text:
            continue
        target_entry.setdefault("feedback", []).append(
            {"text": text, "chat_id": chat_id, "at": datetime.now(timezone.utc).isoformat()}
        )
        matched += 1
        logger.info("Matched feedback to \"%s\": %s", target_entry["chosen"]["title"], text)

    _save_offset(max_update_id)
    return matched
