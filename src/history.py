import json
import os
from datetime import datetime, timedelta, timezone

HISTORY_PATH = os.path.join(os.path.dirname(__file__), "..", "docs", "data", "history.json")

# How many past nights to keep in the dashboard/history file
RETENTION_DAYS = 90

# How far back to look when telling the ranker "don't repeat this story"
RECENT_TOPICS_DAYS = 14


def load_history() -> list[dict]:
    if not os.path.exists(HISTORY_PATH):
        return []
    with open(HISTORY_PATH, "r") as f:
        return json.load(f)


def save_history(entries: list[dict]) -> None:
    cutoff = datetime.now(timezone.utc) - timedelta(days=RETENTION_DAYS)
    pruned = [e for e in entries if datetime.fromisoformat(e["date"]) >= cutoff]
    pruned.sort(key=lambda e: e["date"])
    os.makedirs(os.path.dirname(HISTORY_PATH), exist_ok=True)
    with open(HISTORY_PATH, "w") as f:
        json.dump(pruned, f, indent=2)


def append_entry(entries: list[dict], entry: dict) -> None:
    entries.append(entry)


def recent_topics(entries: list[dict]) -> list[str]:
    cutoff = datetime.now(timezone.utc) - timedelta(days=RECENT_TOPICS_DAYS)
    return [
        e["chosen"]["title"]
        for e in entries
        if e.get("chosen") and datetime.fromisoformat(e["date"]) >= cutoff
    ]


def recent_feedback(entries: list[dict], limit: int = 10) -> list[str]:
    notes = []
    for e in sorted(entries, key=lambda e: e["date"], reverse=True):
        if not e.get("chosen") or not e.get("feedback"):
            continue
        title = e["chosen"]["title"]
        for f in e["feedback"]:
            notes.append(f'On "{title}": {f["text"]}')
    return notes[:limit]


def new_entry(status: str, error: str | None = None) -> dict:
    return {
        "date": datetime.now(timezone.utc).isoformat(),
        "status": status,
        "error": error,
        "chosen": None,
        "trend_context": [],
        "variants": [],
        "feedback": [],
        "sources": [],
        "services": {},
        "feedback_collected": 0,
    }
