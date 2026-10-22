# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Atul Singh Chandel

"""Tests for the page-viewport fragment animation."""

import os
import unittest
from types import SimpleNamespace
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtCore import QRect, QEventLoop, QTimer
from PyQt6.QtGui import QColor, QPixmap
from PyQt6.QtWidgets import QApplication, QWidget

from browser.tear_effect import TearEffect, system_prefers_reduced_motion


class TearEffectTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication(["dash-tear-test"])

    def test_fragment_count_is_bounded_to_viewport(self) -> None:
        parent = QWidget()
        pixmap = QPixmap(1920, 1200)
        pixmap.setDevicePixelRatio(2)
        pixmap.fill(QColor("#456"))
        effect = TearEffect(parent, pixmap, QRect(0, 0, 960, 600), "#000", True)

        self.assertGreaterEqual(len(effect._fragments), 100)
        self.assertLessEqual(len(effect._fragments), 352)
        self.assertEqual(effect.geometry(), QRect(0, 0, 960, 600))

        effect._animation.stop()
        effect.deleteLater()
        parent.deleteLater()
        self.app.processEvents()

    def test_reduced_motion_transition_finishes(self) -> None:
        parent = QWidget()
        pixmap = QPixmap(320, 240)
        pixmap.fill(QColor("#abc"))
        effect = TearEffect(parent, pixmap, QRect(0, 0, 320, 240), "#000", True)
        loop = QEventLoop()
        destroyed = []
        effect.destroyed.connect(lambda: (destroyed.append(True), loop.quit()))
        QTimer.singleShot(1000, loop.quit)
        loop.exec()

        self.assertTrue(destroyed)
        parent.deleteLater()
        self.app.processEvents()

    def test_reduced_motion_uses_gnome_animation_setting(self) -> None:
        system_prefers_reduced_motion.cache_clear()
        with patch(
            "browser.tear_effect.subprocess.run",
            return_value=SimpleNamespace(stdout="false\n"),
        ):
            self.assertTrue(system_prefers_reduced_motion())
        system_prefers_reduced_motion.cache_clear()


if __name__ == "__main__":
    unittest.main()
