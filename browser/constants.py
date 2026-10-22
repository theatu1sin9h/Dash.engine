# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Atul Singh Chandel

"""Shared application labels and styling."""

APP_NAME = "Dash Browser"
TAGLINE = "Less browser. More web."
SEARCH_URL = "https://duckduckgo.com/?q={query}"

THEMES = {
    "dark": {
        "background": "#111214",
        "sidebar": "#101113",
        "surface": "#1b1d21",
        "toolbar": "#141518",
        "tab": "#141518",
        "active_tab": "#292c32",
        "border": "#292b30",
        "text": "#e9eaec",
        "secondary": "#969aa3",
        "muted": "#686d77",
        "accent": "#aeb6c2",
        "error": "#e06c75",
    },
    "light": {
        "background": "#f5f6f8",
        "sidebar": "#ffffff",
        "surface": "#ffffff",
        "toolbar": "#f0f1f4",
        "tab": "#f0f1f4",
        "active_tab": "#e1e4e9",
        "border": "#d8dbe1",
        "text": "#202328",
        "secondary": "#555b65",
        "muted": "#747b86",
        "accent": "#596579",
        "error": "#b42332",
    },
}


def theme_colors(theme: str) -> dict[str, str]:
    return THEMES.get(theme, THEMES["dark"])


def stylesheet_for_theme(theme: str) -> str:
    colors = theme_colors(theme)
    return f"""
QMainWindow, QWidget {{
    background: {colors['background']};
    color: {colors['text']};
    font-family: sans-serif;
    font-size: 13px;
}}
QTabWidget::pane {{
    border: 0;
    background: {colors['background']};
}}
QTabBar {{
    background: {colors['toolbar']};
}}
QTabBar::tab {{
    background: {colors['tab']};
    color: {colors['secondary']};
    border: 1px solid transparent;
    border-bottom: 2px solid transparent;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    min-width: 88px;
    max-width: 210px;
    padding: 6px 10px;
}}
QTabBar::tab:selected {{
    background: {colors['surface']};
    border-top-color: {colors['border']};
    border-left-color: {colors['border']};
    border-right-color: {colors['border']};
    border-bottom-color: {colors['accent']};
    color: {colors['text']};
}}
QTabBar::tab:hover:!selected {{
    background: {colors['surface']};
    border-top-color: {colors['border']};
    border-left-color: {colors['border']};
    border-right-color: {colors['border']};
}}
QToolBar {{
    background: qlineargradient(
        x1: 0, y1: 0, x2: 0, y2: 1,
        stop: 0 {colors['surface']}, stop: 1 {colors['toolbar']}
    );
    border: 0;
    border-bottom: 1px solid {colors['border']};
    spacing: 6px;
    padding: 7px 10px;
}}
QWidget#sidebar {{
    background: qlineargradient(
        x1: 0, y1: 0, x2: 1, y2: 0,
        stop: 0 {colors['sidebar']}, stop: 1 {colors['toolbar']}
    );
    border-right: 1px solid {colors['border']};
}}
QWidget#bookmarksPanel {{
    background: {colors['toolbar']};
    border-right: 1px solid {colors['border']};
}}
QToolButton {{
    background: transparent;
    border: 1px solid transparent;
    border-radius: 8px;
    color: {colors['text']};
    min-width: 30px;
    min-height: 30px;
}}
QToolButton:hover {{
    background: {colors['active_tab']};
    border-color: {colors['border']};
}}
QToolButton:pressed {{
    background: {colors['toolbar']};
    border-color: {colors['muted']};
}}
QLineEdit {{
    background: qlineargradient(
        x1: 0, y1: 0, x2: 0, y2: 1,
        stop: 0 {colors['background']}, stop: 1 {colors['surface']}
    );
    border: 1px solid {colors['border']};
    border-radius: 10px;
    color: {colors['text']};
    padding: 7px 12px;
    selection-background-color: {colors['active_tab']};
}}
QLineEdit:focus {{
    border-color: {colors['accent']};
}}
QPushButton {{
    background: qlineargradient(
        x1: 0, y1: 0, x2: 0, y2: 1,
        stop: 0 {colors['active_tab']}, stop: 1 {colors['surface']}
    );
    border: 1px solid {colors['border']};
    border-radius: 8px;
    color: {colors['text']};
    padding: 6px 12px;
}}
QPushButton:hover {{
    border-color: {colors['accent']};
}}
QPushButton:pressed {{
    background: {colors['toolbar']};
}}
QStatusBar {{
    background: {colors['surface']};
    color: {colors['secondary']};
    border-top: 1px solid {colors['border']};
    min-height: 17px;
    max-height: 17px;
    padding: 0 4px;
    font-size: 11px;
}}
QStatusBar::item {{
    border: 0;
}}
QProgressBar {{
    background: {colors['surface']};
    border: 0;
    min-height: 5px;
    max-height: 5px;
}}
QProgressBar::chunk {{
    background: {colors['accent']};
}}
"""


COLORS = theme_colors("dark")
STYLESHEET = stylesheet_for_theme("dark")
