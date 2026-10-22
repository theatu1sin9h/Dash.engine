# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Atul Singh Chandel

"""Validated settings with atomic, per-user persistence."""

import logging
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path

from PyQt6.QtCore import QUrl

from browser.privacy import normalize_site
from browser.storage import config_directory, read_json, write_json_atomic

logger = logging.getLogger(__name__)
SEARCH_ENGINES = {
    "DuckDuckGo": "https://duckduckgo.com/?q={query}",
    "Google": "https://www.google.com/search?q={query}",
    "Bing": "https://www.bing.com/search?q={query}",
}
MAX_CUSTOM_SEARCH_ENGINES = 20
_HEX_COLOR = re.compile(r"^#[0-9a-fA-F]{6}$")


def validate_search_engine(name: object, template: object) -> tuple[str, str]:
    """Validate a custom engine name and HTTPS search URL template."""
    if not isinstance(name, str) or not isinstance(template, str):
        raise ValueError("Search engine name and URL must be text.")
    clean_name = name.strip()
    clean_template = template.strip()
    if not clean_name or len(clean_name) > 40:
        raise ValueError("Search engine name must be between 1 and 40 characters.")
    if clean_name.casefold() in {item.casefold() for item in SEARCH_ENGINES}:
        raise ValueError("Built-in search engine names cannot be reused.")
    if "{query}" not in clean_template or clean_template.count("{query}") != 1:
        raise ValueError("Search URL must contain exactly one {query} placeholder.")
    if "{" in clean_template.replace("{query}", "") or "}" in clean_template.replace(
        "{query}", ""
    ):
        raise ValueError("Search URL contains an unsupported placeholder.")
    parsed = QUrl(clean_template.replace("{query}", "dash-search"))
    if (
        not parsed.isValid()
        or parsed.scheme().lower() != "https"
        or not parsed.host()
        or parsed.userName()
        or parsed.password()
    ):
        raise ValueError("Search URL must be a valid HTTPS URL without embedded credentials.")
    return clean_name, clean_template


@dataclass
class BrowserSettings:
    search_engine: str = "DuckDuckGo"
    download_directory: str = str(Path.home() / "Downloads")
    show_bookmarks_bar: bool = True
    theme: str = "dark"
    custom_search_engines: dict[str, str] = field(default_factory=dict)
    ad_blocking_enabled: bool = True
    ad_allowlist: list[str] = field(default_factory=list)
    new_tab_background: str = "ambient"
    new_tab_solid_color: str = "#11151b"
    new_tab_gradient_start: str = "#090b0f"
    new_tab_gradient_end: str = "#11151b"
    new_tab_wallpaper: str = ""

    def __post_init__(self) -> None:
        custom: dict[str, str] = {}
        if isinstance(self.custom_search_engines, dict):
            for name, template in self.custom_search_engines.items():
                try:
                    valid_name, valid_template = validate_search_engine(name, template)
                except ValueError:
                    continue
                if len(custom) >= MAX_CUSTOM_SEARCH_ENGINES:
                    break
                custom[valid_name] = valid_template
        self.custom_search_engines = custom
        available = {**SEARCH_ENGINES, **custom}
        if not isinstance(self.search_engine, str) or self.search_engine not in available:
            self.search_engine = "DuckDuckGo"
        if not isinstance(self.theme, str) or self.theme not in {"dark", "light"}:
            self.theme = "dark"
        try:
            download_path = Path(self.download_directory).expanduser()
            if not download_path.is_absolute():
                raise ValueError("Download directory must be an absolute path")
            self.download_directory = str(download_path)
        except (TypeError, ValueError):
            self.download_directory = str(Path.home() / "Downloads")
        if not isinstance(self.show_bookmarks_bar, bool):
            self.show_bookmarks_bar = True
        if not isinstance(self.ad_blocking_enabled, bool):
            self.ad_blocking_enabled = True
        if not isinstance(self.new_tab_background, str) or self.new_tab_background not in {
            "ambient", "solid", "gradient", "image"
        }:
            self.new_tab_background = "ambient"
        for field_name, fallback in (
            ("new_tab_solid_color", "#11151b"),
            ("new_tab_gradient_start", "#090b0f"),
            ("new_tab_gradient_end", "#11151b"),
        ):
            color = getattr(self, field_name)
            if not isinstance(color, str) or not _HEX_COLOR.fullmatch(color):
                setattr(self, field_name, fallback)
            else:
                setattr(self, field_name, color.lower())
        try:
            wallpaper_path = Path(self.new_tab_wallpaper).expanduser()
            self.new_tab_wallpaper = (
                str(wallpaper_path)
                if wallpaper_path.is_absolute()
                else ""
            )
        except (TypeError, ValueError):
            self.new_tab_wallpaper = ""
        allowlist: list[str] = []
        if isinstance(self.ad_allowlist, (list, tuple)):
            for site in self.ad_allowlist:
                try:
                    normalized = normalize_site(site)
                except (ValueError, UnicodeError):
                    continue
                if normalized not in allowlist and len(allowlist) < 1000:
                    allowlist.append(normalized)
        self.ad_allowlist = allowlist


class SettingsStore:
    """Load and save settings without making corrupt JSON fatal."""

    def __init__(self, path: Path | None = None) -> None:
        self.path = path or config_directory() / "settings.json"

    def load(self) -> BrowserSettings:
        try:
            content = read_json(self.path)
            if not isinstance(content, dict) or content.get("version") != 1:
                raise ValueError("Unsupported settings format")
            return BrowserSettings(
                search_engine=content.get("search_engine"),
                download_directory=content.get("download_directory"),
                show_bookmarks_bar=content.get("show_bookmarks_bar"),
                theme=content.get("theme", "dark"),
                custom_search_engines=content.get("custom_search_engines"),
                ad_blocking_enabled=content.get("ad_blocking_enabled", True),
                ad_allowlist=content.get("ad_allowlist", []),
                new_tab_background=content.get("new_tab_background", "ambient"),
                new_tab_solid_color=content.get("new_tab_solid_color", "#11151b"),
                new_tab_gradient_start=content.get(
                    "new_tab_gradient_start", "#090b0f"
                ),
                new_tab_gradient_end=content.get(
                    "new_tab_gradient_end", "#11151b"
                ),
                new_tab_wallpaper=content.get("new_tab_wallpaper", ""),
            )
        except FileNotFoundError:
            return BrowserSettings()
        except (OSError, ValueError, TypeError) as error:
            logger.warning("Could not load browser settings; using safe defaults: %s", error)
            return BrowserSettings()

    def save(self, settings: BrowserSettings) -> None:
        write_json_atomic(self.path, {"version": 1, **asdict(settings)})
