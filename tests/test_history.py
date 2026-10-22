# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Atul Singh Chandel

"""Offline tests for persistent browsing history."""

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication, QMessageBox

from browser.dialogs import HistoryDialog
from browser.history import MAX_HISTORY_ENTRIES, HistoryStore


class HistoryStoreTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def test_visit_persists_and_newest_entry_comes_first(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "history.json"
            store = HistoryStore(path)
            store.add("First", "https://first.example")
            store.add("Second", "https://second.example")

            loaded = HistoryStore(path)
            self.assertEqual(
                [entry.url for entry in loaded.entries],
                ["https://second.example", "https://first.example"],
            )
            self.assertEqual(loaded.entries[0].title, "Second")

    def test_rejects_unsafe_urls_without_adding_entry(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = HistoryStore(Path(directory) / "history.json")
            for url in ("javascript:alert(1)", "file:///etc/passwd", "https://user:pass@example.com"):
                with self.subTest(url=url), self.assertRaises(ValueError):
                    store.add("Unsafe", url)
            self.assertEqual(store.entries, ())

    def test_clear_persists_empty_history(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "history.json"
            store = HistoryStore(path)
            store.add("Example", "https://example.com")
            store.clear()
            self.assertEqual(HistoryStore(path).entries, ())

    def test_history_dialog_clear_button_clears_store(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = HistoryStore(Path(directory) / "history.json")
            store.add("Example", "https://example.com")
            dialog = HistoryDialog(store, lambda _url: None)

            with patch(
                "browser.dialogs.QMessageBox.question",
                return_value=QMessageBox.StandardButton.Yes,
            ):
                dialog.clear_button.click()

            self.assertEqual(store.entries, ())
            self.assertEqual(dialog.table.rowCount(), 0)
            dialog.close()

    def test_history_dialog_deletes_only_selected_visit(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = HistoryStore(Path(directory) / "history.json")
            store.add("Keep", "https://keep.example")
            store.add("Delete", "https://delete.example")
            dialog = HistoryDialog(store, lambda _url: None)
            dialog.table.selectRow(0)

            with patch(
                "browser.dialogs.QMessageBox.question",
                return_value=QMessageBox.StandardButton.Yes,
            ):
                dialog.delete_button.click()

            self.assertEqual([entry.title for entry in store.entries], ["Keep"])
            self.assertEqual(dialog.table.rowCount(), 1)
            dialog.close()

    def test_history_keeps_only_the_most_recent_limit(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "history.json"
            entries = [
                {
                    "title": f"Page {index}",
                    "url": f"https://page-{index}.example",
                    "visited_at": "2026-01-01T00:00:00+00:00",
                }
                for index in range(MAX_HISTORY_ENTRIES)
            ]
            path.write_text(json.dumps({"version": 1, "entries": entries}), encoding="utf-8")

            store = HistoryStore(path)
            store.add("Newest", "https://newest.example")

            self.assertEqual(len(store.entries), MAX_HISTORY_ENTRIES)
            self.assertEqual(store.entries[0].url, "https://newest.example")
            self.assertEqual(store.entries[-1].url, "https://page-998.example")


if __name__ == "__main__":
    unittest.main()
