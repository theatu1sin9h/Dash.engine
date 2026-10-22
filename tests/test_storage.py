# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Atul Singh Chandel

"""Offline tests for settings, bookmarks, and download-name safety."""

import json
import tempfile
import unittest
from pathlib import Path

from browser.bookmarks import BookmarkStore
from browser.downloads import nonconflicting_path, safe_download_name
from browser.navigation import address_to_url
from browser.settings import BrowserSettings, SettingsStore, validate_search_engine


class SettingsStoreTests(unittest.TestCase):
    def test_defaults_and_round_trip(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = SettingsStore(Path(directory) / "settings.json")
            defaults = store.load()
            self.assertEqual(defaults.search_engine, "DuckDuckGo")
            updated = BrowserSettings("Google", directory, False)
            store.save(updated)
            self.assertEqual(store.load(), updated)

    def test_corrupt_settings_use_safe_defaults(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "settings.json"
            path.write_text("{ broken", encoding="utf-8")
            self.assertEqual(SettingsStore(path).load(), BrowserSettings())

    def test_invalid_settings_values_are_sanitized(self) -> None:
        settings = BrowserSettings("Unknown", "relative/path", "no")
        self.assertEqual(settings.search_engine, "DuckDuckGo")
        self.assertTrue(Path(settings.download_directory).is_absolute())
        self.assertIs(settings.show_bookmarks_bar, True)
        self.assertEqual(settings.theme, "dark")

    def test_theme_and_custom_search_engine_round_trip(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = SettingsStore(Path(directory) / "settings.json")
            custom_engines = {"Brave Search": "https://search.brave.com/search?q={query}"}
            settings = BrowserSettings(
                "Brave Search", directory, True, "light", custom_engines
            )
            store.save(settings)
            self.assertEqual(store.load(), settings)

    def test_privacy_preferences_and_allowlist_round_trip(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = SettingsStore(Path(directory) / "settings.json")
            settings = BrowserSettings(
                ad_blocking_enabled=False,
                ad_allowlist=["HTTPS://Example.COM/path", "example.com", "bad value"],
            )
            store.save(settings)

            loaded = store.load()

            self.assertFalse(loaded.ad_blocking_enabled)
            self.assertEqual(loaded.ad_allowlist, ["example.com"])

    def test_legacy_clock_preference_is_removed_when_settings_are_saved(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "settings.json"
            path.write_text(
                json.dumps({"version": 1, "clock_24_hour": True}),
                encoding="utf-8",
            )
            store = SettingsStore(path)
            store.save(store.load())

            self.assertNotIn("clock_24_hour", json.loads(path.read_text(encoding="utf-8")))

    def test_new_tab_background_preferences_round_trip_and_validation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = SettingsStore(Path(directory) / "settings.json")
            settings = BrowserSettings(
                new_tab_background="gradient",
                new_tab_gradient_start="#AABBCC",
                new_tab_gradient_end="#123456",
            )
            store.save(settings)

            loaded = store.load()

        self.assertEqual(loaded.new_tab_background, "gradient")
        self.assertEqual(loaded.new_tab_gradient_start, "#aabbcc")
        self.assertEqual(loaded.new_tab_gradient_end, "#123456")
        self.assertEqual(
            BrowserSettings(new_tab_background="javascript").new_tab_background,
            "ambient",
        )
        self.assertEqual(
            BrowserSettings(new_tab_solid_color="url(javascript:alert(1))").new_tab_solid_color,
            "#11151b",
        )

    def test_custom_search_engine_requires_safe_https_template(self) -> None:
        self.assertEqual(
            validate_search_engine("Example", "https://example.com/search?q={query}"),
            ("Example", "https://example.com/search?q={query}"),
        )
        for name, template in (
            ("Google", "https://example.com/?q={query}"),
            ("Bad", "http://example.com/?q={query}"),
            ("Bad", "https://user:pass@example.com/?q={query}"),
            ("Bad", "https://example.com/?q={query}&x={other}"),
            ("Bad", "https://example.com/"),
        ):
            with self.subTest(name=name, template=template), self.assertRaises(ValueError):
                validate_search_engine(name, template)


class BookmarkStoreTests(unittest.TestCase):
    def test_add_remove_and_round_trip_export(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bookmarks.json"
            store = BookmarkStore(path)
            added = store.add("Example", "https://example.com")
            self.assertEqual(store.add("Duplicate", "https://example.com"), added)
            self.assertEqual(len(store.bookmarks), 1)

            export_path = Path(directory) / "export.json"
            store.export_file(export_path)
            imported = BookmarkStore(Path(directory) / "imported.json")
            self.assertEqual(imported.import_file(export_path), 1)
            self.assertEqual(imported.bookmarks[0].url, "https://example.com")
            self.assertTrue(imported.remove("https://example.com"))
            self.assertFalse(imported.bookmarks)

    def test_import_rejects_unsafe_url_without_partial_changes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            store = BookmarkStore(root / "bookmarks.json")
            store.add("Existing", "https://existing.example")
            bad_export = root / "bad.json"
            bad_export.write_text(
                json.dumps({
                    "version": 1,
                    "bookmarks": [
                        {"title": "Good", "url": "https://good.example", "created_at": "2026-01-01T00:00:00+00:00"},
                        {"title": "Bad", "url": "javascript:alert(1)", "created_at": "2026-01-01T00:00:00+00:00"},
                    ],
                }),
                encoding="utf-8",
            )
            with self.assertRaises(ValueError):
                store.import_file(bad_export)
            self.assertEqual([item.url for item in store.bookmarks], ["https://existing.example"])

    def test_corrupt_bookmark_store_recovers_empty(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bookmarks.json"
            path.write_text("[]", encoding="utf-8")
            self.assertEqual(BookmarkStore(path).bookmarks, ())


class DownloadPathTests(unittest.TestCase):
    def test_sanitizes_path_traversal_and_control_characters(self) -> None:
        self.assertEqual(safe_download_name("../../report.txt"), "report.txt")
        self.assertEqual(safe_download_name("bad\nname.exe"), "bad_name.exe")
        self.assertEqual(safe_download_name(".."), "download")

    def test_adds_suffix_for_existing_destination(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            existing = Path(directory) / "report.txt"
            existing.touch()
            self.assertEqual(nonconflicting_path(existing).name, "report (1).txt")


class SearchEngineTests(unittest.TestCase):
    def test_search_engine_template_is_used(self) -> None:
        url = address_to_url("hello dash", "https://www.google.com/search?q={query}")
        self.assertEqual(url.host(), "www.google.com")
        self.assertEqual(url.query(), "q=hello+dash")


if __name__ == "__main__":
    unittest.main()
