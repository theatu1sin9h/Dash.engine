# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Atul Singh Chandel

"""Dash Browser entry point."""

import os
import sys

if sys.platform.startswith("linux"):
    os.environ.setdefault("QT_QPA_PLATFORMTHEME", "generic")

from PyQt6.QtWidgets import QApplication

from browser.constants import APP_NAME
from browser.main_window import BrowserWindow


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setOrganizationName("Dash Browser")
    app.setStyle("Fusion")
    window = BrowserWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
