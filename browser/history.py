# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Atul Singh Chandel

"""Validated, bounded browsing-history storage."""

import logging
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

from PyQt6.QtCore import QUrl

from browser.storage import data_directory, read_json, write_json_atomic

logger = logging.getLogger(__name__)
MAX_HISTORY_ENTRIES = 1000


@dataclass(frozen=True)
class HistoryEntry:
    title: str
    url: str
    visited_at: str


def validate_history_entry(
    title: object, url: object, visited_at: object | None = None
) -> HistoryEntry:
    """Normalize and validate one HTTP(S) history entry."""
    if not isinstance(title, str) or not isinstance(url, str):
        raise ValueError("History title and URL must be text")
    clean_title = title.strip()[:512] or "Untitled"
    clean_url = url.strip()
    parsed = QUrl(clean_url)
    if not parsed.isValid() or parsed.scheme().lower() not in {"http", "https"} or not parsed.host():
        raise ValueError("History entries must have a valid HTTP or HTTPS URL")
    if parsed.userName() or parsed.password():
        raise ValueError("History URLs cannot contain embedded credentials")
    timestamp = visited_at or datetime.now(timezone.utc).isoformat()
    if not isinstance(timestamp, str):
        raise ValueError("History visit time must be text")
    try:
        datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    except ValueError as error:
        raise ValueError("History visit time must be an ISO 8601 timestamp") from error
    return HistoryEntry(clean_title, parsed.toString(), timestamp)


class HistoryStore:
    """Manage a bounded browsing history in a private JSON file."""

    def __init__(self, path: Path | None = None) -> None:
        self.path = path or data_directory() / "history.json"
        self._entries: list[HistoryEntry] = []
        self.load()

    @property
    def entries(self) -> tuple[HistoryEntry, ...]:
        return tuple(self._entries)

    def load(self) -> tuple[HistoryEntry, ...]:
        try:
            payload = read_json(self.path)
            if not isinstance(payload, dict) or payload.get("version") != 1:
                raise ValueError("Unsupported history file format")
            entries = payload.get("entries")
            if not isinstance(entries, list) or len(entries) > MAX_HISTORY_ENTRIES:
                raise ValueError("History file has an invalid number of entries")
            self._entries = [
                validate_history_entry(
                    item.get("title"), item.get("url"), item.get("visited_at")
                )
                for item in entries
                if isinstance(item, dict)
            ]
            if len(self._entries) != len(entries):
                raise ValueError("History file contains a malformed entry")
        except FileNotFoundError:
            self._entries = []
        except (OSError, ValueError, TypeError, AttributeError) as error:
            logger.warning("Could not load browsing history; starting empty: %s", error)
            self._entries = []
        return self.entries

    def add(self, title: str, url: str) -> HistoryEntry:
        entry = validate_history_entry(title, url)
        updated = [entry, *self._entries][:MAX_HISTORY_ENTRIES]
        self._write_entries(updated)
        self._entries = updated
        return entry

    def clear(self) -> None:
        self._write_entries([])
        self._entries = []

    def remove_entries(self, entries: tuple[HistoryEntry, ...]) -> int:
        """Remove selected entries while preserving any unselected duplicates."""
        selected = Counter(entries)
        updated = []
        removed = 0
        for entry in self._entries:
            if selected[entry]:
                selected[entry] -= 1
                removed += 1
            else:
                updated.append(entry)
        if removed:
            self._write_entries(updated)
            self._entries = updated
        return removed

    def save(self) -> None:
        self._write_entries(self._entries)

    def _write_entries(self, entries: list[HistoryEntry]) -> None:
        write_json_atomic(self.path, {"version": 1, "entries": [asdict(e) for e in entries]})
