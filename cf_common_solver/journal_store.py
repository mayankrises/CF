"""
Tiny local storage for the problem journal.

This is a single-user, no-login app, so we just keep everything in a
JSON file next to the app (journal_data.json). Keyed by a stable
string derived from each problem's (contestId, index, name).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

JOURNAL_PATH = Path(__file__).parent / "journal_data.json"


def load_journal() -> dict[str, dict[str, Any]]:
    """Load the journal file. Returns {} if it doesn't exist or is corrupt."""
    if not JOURNAL_PATH.exists():
        return {}
    try:
        with JOURNAL_PATH.open("r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (json.JSONDecodeError, OSError):
        return {}


def save_journal(data: dict[str, dict[str, Any]]) -> None:
    """Persist the journal file, pretty-printed for easy manual inspection/backup."""
    with JOURNAL_PATH.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False, sort_keys=True)


def get_entry(journal: dict[str, dict[str, Any]], key: str) -> dict[str, Any]:
    """Return the (stars, review) entry for a problem key, defaulting to unrated/blank."""
    entry = journal.get(key, {})
    return {
        "stars": entry.get("stars", 0),
        "review": entry.get("review", ""),
    }