import json
import os
from datetime import datetime, timezone

STATE_PATH = os.path.join(os.path.dirname(__file__), "..", "state", "seen_articles.json")

# Only keep dedup history for this many days so the file doesn't grow forever
RETENTION_DAYS = 30


def load_seen() -> dict:
    if not os.path.exists(STATE_PATH):
        return {}
    with open(STATE_PATH, "r") as f:
        return json.load(f)


def save_seen(seen: dict) -> None:
    cutoff = datetime.now(timezone.utc).timestamp() - RETENTION_DAYS * 86400
    pruned = {
        url: date_str
        for url, date_str in seen.items()
        if datetime.fromisoformat(date_str).timestamp() >= cutoff
    }
    os.makedirs(os.path.dirname(STATE_PATH), exist_ok=True)
    with open(STATE_PATH, "w") as f:
        json.dump(pruned, f, indent=2, sort_keys=True)


def mark_seen(seen: dict, url: str) -> None:
    seen[url] = datetime.now(timezone.utc).isoformat()
