# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Atul Singh Chandel

"""Tests for the explicit, per-user Linux desktop launcher."""

import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from browser.desktop import install_desktop_entry


class DesktopEntryTests(unittest.TestCase):
    def test_installs_user_launcher_and_icon(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            data_home = Path(directory)
            entry_path = install_desktop_entry(
                data_home, "/home/user name/.venv/bin/python"
            )

            entry = entry_path.read_text(encoding="utf-8")
            icon_path = (
                data_home
                / "icons"
                / "hicolor"
                / "scalable"
                / "apps"
                / "dash-browser.svg"
            )
            self.assertTrue(icon_path.is_file())

        self.assertEqual(entry_path, data_home / "applications" / "dash-browser.desktop")
        self.assertIn("Name=Dash Browser", entry)
        self.assertIn(
            f'Exec="/home/user name/.venv/bin/python" '
            f'"{Path(__file__).resolve().parents[1] / "main.py"}"',
            entry,
        )
        self.assertIn("Icon=dash-browser", entry)

    def test_rejects_shortcut_installation_outside_linux(self) -> None:
        with patch("browser.desktop.sys.platform", "win32"):
            with self.assertRaisesRegex(RuntimeError, "Linux only"):
                install_desktop_entry(Path(tempfile.gettempdir()))


if __name__ == "__main__":
    unittest.main()
