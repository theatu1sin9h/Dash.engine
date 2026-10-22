# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Atul Singh Chandel

"""Validated bookmark storage and portable import/export."""

import logging
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

from PyQt6.QtCore import QUrl

from browser.storage import data_directory, read_json, write_json_atomic

logger = logging.getLogger(__name__)
MAX_BOOKMARKS = 5000


@dataclass(frozen=True)
class Bookmark:
    title: str
    url: str
    created_at: str


def validate_bookmark(title: object, url: object, created_at: object | None = None) -> Bookmark:
    """Normalize and validate one bookmark, rejecting unsafe schemes."""
    if not isinstance(title, str) or not isinstance(url, str):
        raise ValueError("Bookmark title and URL must be text")
    clean_title = title.strip()[:512] or "Untitled"
    clean_url = url.strip()
    parsed = QUrl(clean_url)
    if not parsed.isValid() or parsed.scheme().lower() not in {"http", "https"} or not parsed.host():
        raise ValueError("Bookmarks must have a valid HTTP or HTTPS URL")
    if parsed.userName() or parsed.password():
        raise ValueError("Bookmark URLs cannot contain embedded credentials")
    timestamp = created_at or datetime.now(timezone.utc).isoformat()
    if not isinstance(timestamp, str):
        raise ValueError("Bookmark creation time must be text")
    try:
        datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    except ValueError as error:
        raise ValueError("Bookmark creation time must be an ISO 8601 timestamp") from error
    return Bookmark(clean_title, parsed.toString(), timestamp)


def parse_bookmark_export(payload: object) -> list[Bookmark]:
    """Validate a versioned Dash bookmark export before importing any data."""
    if not isinstance(payload, dict) or payload.get("version") != 1:
        raise ValueError("Unsupported bookmark file format")
    entries = payload.get("bookmarks")
    if not isinstance(entries, list) or len(entries) > MAX_BOOKMARKS:
        raise ValueError("Bookmark file has an invalid number of entries")
    result = []
    for entry in entries:
        if not isinstance(entry, dict):
            raise ValueError("Bookmark entries must be objects")
        result.append(validate_bookmark(entry.get("title"), entry.get("url"), entry.get("created_at")))
    return result


class BookmarkStore:
    """Manage bookmarks in a private, atomically updated JSON file."""

    def __init__(self, path: Path | None = None) -> None:
        self.path = path or data_directory() / "bookmarks.json"
        self._bookmarks: list[Bookmark] = []
        self.load()

    @property
    def bookmarks(self) -> tuple[Bookmark, ...]:
        return tuple(self._bookmarks)

    def load(self) -> tuple[Bookmark, ...]:
        try:
            payload = read_json(self.path)
            if not isinstance(payload, dict) or payload.get("version") != 1:
                raise ValueError("Unsupported bookmark file format")
            entries = payload.get("bookmarks")
            if not isinstance(entries, list) or len(entries) > MAX_BOOKMARKS:
                raise ValueError("Bookmark file has an invalid number of entries")
            self._bookmarks = [
                validate_bookmark(item.get("title"), item.get("url"), item.get("created_at"))
                for item in entries
                if isinstance(item, dict)
            ]
            if len(self._bookmarks) != len(entries):
                raise ValueError("Bookmark file contains a malformed entry")
        except FileNotFoundError:
            self._bookmarks = []
        except (OSError, ValueError, TypeError, AttributeError) as error:
            logger.warning("Could not load bookmarks; starting with an empty list: %s", error)
            self._bookmarks = []
        return self.bookmarks

    def add(self, title: str, url: str) -> Bookmark:
        bookmark = validate_bookmark(title, url)
        if any(existing.url == bookmark.url for existing in self._bookmarks):
            return next(existing for existing in self._bookmarks if existing.url == bookmark.url)
        if len(self._bookmarks) >= MAX_BOOKMARKS:
            raise ValueError("Bookmark limit reached")
        self._bookmarks.append(bookmark)
        self.save()
        return bookmark

    def remove(self, url: str) -> bool:
        updated = [bookmark for bookmark in self._bookmarks if bookmark.url != url]
        if len(updated) == len(self._bookmarks):
            return False
        self._bookmarks = updated
        self.save()
        return True

    def import_file(self, path: Path) -> int:
        imported = parse_bookmark_export(read_json(path))
        merged = {bookmark.url: bookmark for bookmark in self._bookmarks}
        for bookmark in imported:
            merged.setdefault(bookmark.url, bookmark)
        if len(merged) > MAX_BOOKMARKS:
            raise ValueError("Import would exceed the bookmark limit")
        self._bookmarks = list(merged.values())
        self.save()
        return len(imported)

    def export_file(self, path: Path) -> None:
        write_json_atomic(
            path,
            {"version": 1, "bookmarks": [asdict(bookmark) for bookmark in self._bookmarks]},
        )

    def save(self) -> None:
        write_json_atomic(
            self.path,
            {"version": 1, "bookmarks": [asdict(bookmark) for bookmark in self._bookmarks]},
        )
