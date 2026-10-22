# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Atul Singh Chandel

"""Tests for user-facing site permission and data controls."""

import os
import unittest
from types import SimpleNamespace
from unittest.mock import Mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtCore import QUrl
from PyQt6.QtTest import QSignalSpy
from PyQt6.QtWidgets import QApplication

from browser.dialogs import ClearBrowsingDataDialog, SettingsDialog, SitePermissionsDialog
from browser.dialogs import PrivacyDashboardDialog
from browser.privacy import RequestBlocker
from browser.settings import BrowserSettings


class _Permission:
    def __init__(self, origin: str, feature: str, state: str) -> None:
        self._origin = QUrl(origin)
        self._feature = feature
        self._state = state
        self._valid = True
        self.reset_count = 0

    def isValid(self) -> bool:
        return self._valid

    def state(self):
        return SimpleNamespace(name=self._state)

    def origin(self) -> QUrl:
        return self._origin

    def permissionType(self):
        return SimpleNamespace(name=self._feature)

    def reset(self) -> None:
        self._valid = False
        self.reset_count += 1


class PrivacyControlDialogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication(["dash-privacy-test"])

    def test_clear_data_defaults_to_supported_profile_controls(self) -> None:
        dialog = ClearBrowsingDataDialog()
        self.assertEqual(
            dialog.selected_data(),
            frozenset({"history", "cookies", "cache", "permissions"}),
        )
        dialog.history.setChecked(False)
        dialog.cookies.setChecked(False)
        self.assertEqual(dialog.selected_data(), frozenset({"cache", "permissions"}))

    def test_settings_exposes_and_emits_privacy_controls(self) -> None:
        dialog = SettingsDialog(BrowserSettings())
        permissions_spy = QSignalSpy(dialog.manageSitePermissions)
        clear_data_spy = QSignalSpy(dialog.clearBrowsingData)
        dashboard_spy = QSignalSpy(dialog.openPrivacyDashboard)
        dialog.permissions_button.click()
        dialog.clear_data_button.click()
        dialog.privacy_dashboard_button.click()
        self.assertEqual(len(permissions_spy), 1)
        self.assertEqual(len(clear_data_spy), 1)
        self.assertEqual(len(dashboard_spy), 1)

    def test_settings_exposes_filter_preferences_without_clock_controls(self) -> None:
        settings = BrowserSettings(
            ad_blocking_enabled=False,
            ad_allowlist=["example.com"],
        )
        dialog = SettingsDialog(settings)

        self.assertFalse(hasattr(dialog, "clock_format"))
        self.assertFalse(dialog.ad_blocking.isChecked())
        self.assertEqual(dialog.ad_allowlist.toPlainText(), "example.com")
        updated = dialog.updated_settings(settings)
        self.assertFalse(updated.ad_blocking_enabled)
        self.assertEqual(updated.ad_allowlist, ["example.com"])

    def test_settings_exposes_new_tab_background_options(self) -> None:
        settings = BrowserSettings(
            new_tab_background="gradient",
            new_tab_gradient_start="#123456",
            new_tab_gradient_end="#abcdef",
        )
        dialog = SettingsDialog(settings)

        self.assertEqual(dialog.new_tab_background.currentData(), "gradient")
        self.assertTrue(dialog.gradient_start_row.isVisibleTo(dialog))
        self.assertFalse(dialog.wallpaper_row.isVisibleTo(dialog))
        updated = dialog.updated_settings(settings)

        self.assertEqual(updated.new_tab_background, "gradient")
        self.assertEqual(updated.new_tab_gradient_start, "#123456")
        self.assertEqual(updated.new_tab_gradient_end, "#abcdef")

    def test_privacy_dashboard_exposes_real_status_and_allowlist_controls(self) -> None:
        settings = BrowserSettings(ad_allowlist=["example.com"])
        blocker = RequestBlocker(
            settings.ad_blocking_enabled, tuple(settings.ad_allowlist)
        )
        dialog = PrivacyDashboardDialog(
            settings, blocker, "www.example.com"
        )
        changed = QSignalSpy(dialog.settingsChanged)

        self.assertTrue(dialog.current_site_toggle.isChecked())
        self.assertFalse(hasattr(dialog, "vpn_status"))
        self.assertFalse(hasattr(dialog, "refresh_ip_button"))
        self.assertIn("12 known domains", dialog.filter_status.text())
        dialog.blocking_toggle.setChecked(False)
        self.assertEqual(len(changed), 1)
        self.assertFalse(changed[0][0])
        dialog.current_site_toggle.setChecked(False)
        self.assertEqual(dialog._allowlist_values(), [])
        dialog.restore_defaults()
        self.assertTrue(dialog.blocking_toggle.isChecked())
        self.assertEqual(dialog._allowlist_values(), [])
        dialog.close()

    def test_site_permission_dialog_lists_and_revokes_decisions(self) -> None:
        first = _Permission("https://example.com", "Geolocation", "Granted")
        second = _Permission("https://other.example", "Notifications", "Denied")
        permissions = [first, second]
        profile = Mock(listAllPermissions=lambda: [
            permission for permission in permissions if permission.isValid()
        ])

        dialog = SitePermissionsDialog(profile)
        self.assertEqual(dialog.table.rowCount(), 2)
        dialog.revoke_all()
        self.assertEqual(first.reset_count, 1)
        self.assertEqual(second.reset_count, 1)
        self.assertEqual(dialog.table.rowCount(), 0)


if __name__ == "__main__":
    unittest.main()
