# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Atul Singh Chandel

"""Offline checks for the welcome and search experience on new tabs."""

import unittest
import tempfile
from pathlib import Path

from PyQt6.QtGui import QColor, QImage

from browser.browser_tab import _new_tab_html


class NewTabPageTests(unittest.TestCase):
    def test_welcome_page_has_search_and_randomized_devanagari_matrix(self) -> None:
        html = _new_tab_html("https://example.com/search?q={query}")

        self.assertIn("background: #000", html)
        self.assertIn('<canvas id="matrix" aria-hidden="true">', html)
        self.assertIn("Array.from(", html)
        self.assertIn("अआइईउऊऋएऐओऔ", html)
        self.assertIn("Math.random()", html)
        self.assertIn("requestAnimationFrame(draw)", html)
        self.assertIn('(prefers-reduced-motion: reduce)', html)
        self.assertIn("It’s yours. Go ahead.", html)
        self.assertNotIn("local-time", html)
        self.assertNotIn("local-date", html)
        self.assertNotIn("DateTimeFormat", html)
        self.assertIn('name="q" type="search"', html)
        self.assertIn("this.dataset.searchUrl.replace('{query}', encodeURIComponent(q))", html)
        self.assertIn("https://example.com/search?q={query}", html)
        self.assertIn('aria-label="Dismiss welcome screen"', html)
        self.assertIn("backdrop-filter: blur(16px)", html)
        self.assertIn("pointer-events: none", html)
        self.assertIn("overflow-x: hidden; overflow-y: auto", html)
        self.assertIn("@media (max-width: 520px)", html)
        self.assertIn("@media (prefers-reduced-motion: reduce)", html)
        self.assertIn("#matrix { display: none; }", html)
        self.assertNotIn("stickman", html)
        self.assertIn("body.dismissed", html)
        self.assertIn("dash://customize-background", html)

    def test_welcome_screen_uses_selected_dark_or_light_theme(self) -> None:
        dark_html = _new_tab_html("https://example.com/?q={query}", "dark")
        light_html = _new_tab_html("https://example.com/?q={query}", "light")
        unexpected_html = _new_tab_html("https://example.com/?q={query}", "invalid")

        self.assertIn('<body data-theme="dark" data-custom-background="false">', dark_html)
        self.assertIn('<body data-theme="light" data-custom-background="false">', light_html)
        self.assertIn('<body data-theme="dark" data-custom-background="false">', unexpected_html)
        self.assertIn('body[data-theme="light"]', light_html)
        self.assertIn("background: #000;", light_html)
        self.assertIn("background: #000;", dark_html)

    def test_new_tab_supports_custom_solid_and_gradient_backgrounds(self) -> None:
        solid_html = _new_tab_html(
            "https://example.com/?q={query}",
            background_mode="solid",
            solid_color="#123456",
        )
        gradient_html = _new_tab_html(
            "https://example.com/?q={query}",
            background_mode="gradient",
            gradient_start="#123456",
            gradient_end="#abcdef",
        )

        self.assertIn("background: #123456;", solid_html)
        self.assertIn(
            "background: linear-gradient(135deg, #123456, #abcdef);",
            gradient_html,
        )
        self.assertIn('data-custom-background="true"', gradient_html)

    def test_new_tab_embeds_a_valid_wallpaper_without_file_url_access(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "wallpaper.png"
            image = QImage(4, 4, QImage.Format.Format_RGB32)
            image.fill(QColor("#336699"))
            self.assertTrue(image.save(str(path)))

            html = _new_tab_html(
                "https://example.com/?q={query}",
                background_mode="image",
                wallpaper_path=str(path),
            )

        self.assertIn("data:image/jpeg;base64,", html)
        self.assertNotIn("file://", html)
        self.assertIn("background-size: cover, cover;", html)

    def test_invalid_wallpaper_falls_back_to_safe_gradient(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "not-an-image.png"
            path.write_text("not an image", encoding="utf-8")
            html = _new_tab_html(
                "https://example.com/?q={query}",
                background_mode="image",
                wallpaper_path=str(path),
            )

        self.assertIn("linear-gradient(145deg, #090b0f", html)
        self.assertNotIn("data:image/", html)


if __name__ == "__main__":
    unittest.main()
