# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Atul Singh Chandel

"""GUI integration checks for browser-level navigation controls."""

import json
import os
import tempfile
import threading
import unittest
from types import SimpleNamespace
from unittest.mock import Mock
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtCore import QCoreApplication, QEvent, QEventLoop, QTimer, QUrl
from PyQt6.QtTest import QSignalSpy
from PyQt6.QtWidgets import QApplication, QPushButton

from browser.main_window import BrowserWindow
from browser.settings import BrowserSettings, SettingsStore


class _PageHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        body = f"<!doctype html><title>{self.path}</title><p>{self.path}</p>".encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        try:
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def log_message(self, _format: str, *_args) -> None:
        pass


class BrowserNavigationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.temp_directory = tempfile.TemporaryDirectory()
        root = Path(cls.temp_directory.name)
        os.environ["XDG_DATA_HOME"] = str(root / "data")
        os.environ["XDG_CONFIG_HOME"] = str(root / "config")
        SettingsStore().save(BrowserSettings())
        cls.app = QApplication.instance() or QApplication(["dash-test"])
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), _PageHandler)
        cls.server_thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.server_thread.start()

    @classmethod
    def tearDownClass(cls) -> None:
        cls.server.shutdown()
        cls.server.server_close()
        cls.server_thread.join(timeout=2)
        cls.temp_directory.cleanup()

    def test_back_forward_actions_track_and_change_page_history(self) -> None:
        window = BrowserWindow()
        window.show()
        self.assertEqual(window.statusBar().maximumHeight(), 18)
        self.assertEqual(window.progress.maximumHeight(), 5)
        self.assertEqual(window.brand_button.text(), "")
        self.assertFalse(window.brand_button.icon().isNull())
        self.assertEqual(window.back_action.text(), "")
        self.assertEqual(window.forward_action.text(), "")
        self.assertFalse(window.back_action.icon().isNull())
        self.assertFalse(window.forward_action.icon().isNull())
        self.assertEqual(window.back_action.toolTip(), "Back")
        self.assertEqual(window.forward_action.toolTip(), "Forward")
        window.settings.theme = "light"
        window.apply_theme()
        self.assertFalse(window.brand_button.icon().isNull())
        window.settings.theme = "dark"
        window.apply_theme()
        view = window.current_view()
        self.assertIsNotNone(view)
        view.page().customizeRequested.disconnect()
        customize_requested = QSignalSpy(view.page().customizeRequested)
        self.assertFalse(
            view.page().acceptNavigationRequest(
                QUrl("dash://customize-background"),
                view.page().NavigationType.NavigationTypeLinkClicked,
                True,
            )
        )
        self.assertEqual(len(customize_requested), 1)
        base_url = f"http://127.0.0.1:{self.server.server_port}"
        self.assertFalse(
            any("Manage bookmarks" in action.text() for action in window.bookmarks_bar.actions())
        )
        self.assertEqual(
            next(
                button.text()
                for button in window.bookmarks_panel.findChildren(QPushButton)
                if button.text().startswith("Manage")
            ),
            "Manage bookmarks…",
        )
        window.settings.search_engine = "Local"
        window.settings.custom_search_engines = {
            "Local": f"{base_url}/search?q={{query}}"
        }
        view.set_appearance(window.settings.theme, f"{base_url}/search?q={{query}}")
        self._wait_for_load(view, lambda: None)
        self._submit_new_tab_search(view, "matrix code")
        self.assertEqual(view.url().path(), "/search")
        self.assertEqual(view.url().query(), "q=matrix code")

        self._load_url(view, f"{base_url}/first")
        self.assertTrue(window.back_action.isEnabled())
        self.assertFalse(window.forward_action.isEnabled())

        self._load_url(view, f"{base_url}/second")
        self.assertTrue(window.back_action.isEnabled())
        self.assertFalse(window.forward_action.isEnabled())

        self._wait_for_load(view, window.back_action.trigger)
        self.assertEqual(view.url().path(), "/first")
        self.assertTrue(window.back_action.isEnabled())
        self.assertTrue(window.forward_action.isEnabled())

        self._wait_for_load(view, window.forward_action.trigger)
        self.assertEqual(view.url().path(), "/second")
        self.assertTrue(window.back_action.isEnabled())
        self.assertFalse(window.forward_action.isEnabled())

        window.new_tab()
        background_view = window.current_view()
        self._load_url(background_view, f"{base_url}/background-one")
        self._load_url(background_view, f"{base_url}/background-two")
        self.assertTrue(window.back_action.isEnabled())

        window.tabs.setCurrentWidget(view)
        self.assertTrue(window.back_action.isEnabled())
        self.assertFalse(window.forward_action.isEnabled())
        self._load_url(background_view, f"{base_url}/background-three")
        self.assertTrue(window.back_action.isEnabled())
        self.assertFalse(window.forward_action.isEnabled())

        for index in reversed(range(window.tabs.count())):
            tab = window.tabs.widget(index)
            window.tabs.removeTab(index)
            if tab is not None:
                tab.stop()
                tab.deleteLater()
        window.close()
        window.deleteLater()
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
        self.app.processEvents()

    def test_new_tab_matrix_background_and_search_adapt_to_theme(self) -> None:
        window = BrowserWindow()
        window.show()
        view = window.current_view()
        self.assertIsNotNone(view)

        try:
            for theme in ("dark", "light"):
                window.settings.theme = theme
                self._wait_for_load(view, window.apply_theme)
                state = json.loads(
                    self._evaluate_javascript(
                        view,
                        """JSON.stringify({
                            theme: document.body.dataset.theme,
                            background: getComputedStyle(document.body).backgroundColor,
                            glitter: Boolean(document.querySelector(
                                'canvas#glitter[aria-hidden="true"]'
                            )),
                            glassBlur: getComputedStyle(
                                document.querySelector('form')
                            ).backdropFilter,
                            horizontalOverflow:
                                document.documentElement.scrollWidth >
                                document.documentElement.clientWidth,
                            hasInteractiveSearch:
                                Boolean(document.querySelector('input[name="q"]'))
                        })""",
                    )
                )
                self.assertIn("theme", state, state)
                self.assertEqual(state["theme"], theme)
                self.assertTrue(state["glitter"])
                if theme == "dark":
                    self.assertEqual(state["background"], "rgb(8, 12, 9)")
                else:
                    self.assertEqual(state["background"], "rgb(243, 246, 243)")
                self.assertIn("blur(16px)", state["glassBlur"])
                self.assertFalse(state["horizontalOverflow"])
                self.assertTrue(state["hasInteractiveSearch"])

            window.settings.new_tab_background = "gradient"
            window.settings.new_tab_gradient_start = "#123456"
            window.settings.new_tab_gradient_end = "#abcdef"
            self._wait_for_load(view, window.apply_theme)
            background = self._evaluate_javascript(
                view, "getComputedStyle(document.body).backgroundImage"
            )
            self.assertIn("rgb(18, 52, 86)", background)
            self.assertIn("rgb(171, 205, 239)", background)
        finally:
            for index in reversed(range(window.tabs.count())):
                tab = window.tabs.widget(index)
                window.tabs.removeTab(index)
                if tab is not None:
                    tab.stop()
                    tab.deleteLater()
            window.close()
            window.deleteLater()
            QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
            self.app.processEvents()

    def test_burning_tab_starts_cleanup_while_viewport_fragments_run(self) -> None:
        window = BrowserWindow()
        window.show()
        self.assertEqual(window.tear_button.toolTip(), "Tear Page / Burn Tab")
        window.new_tab(burnable=True)
        view = window.current_view()
        self.assertIsNotNone(view)
        self.assertTrue(view.page().profile().isOffTheRecord())
        self._load_url(
            view, f"http://127.0.0.1:{self.server.server_port}/tear-page"
        )

        window.tear_current_tab()

        self.assertNotIn(view, window._burn_profiles)
        self.assertNotIn(view, [window.tabs.widget(i) for i in range(window.tabs.count())])
        self.assertEqual(len(window._tear_effects), 1)
        effect = next(iter(window._tear_effects))
        self.assertIs(effect.parent(), window.tabs)
        self.assertFalse(effect._snapshot.isNull())
        self.assertGreater(len(effect._fragments), 100)

        loop = QEventLoop()
        QTimer.singleShot(850, loop.quit)
        loop.exec()
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
        self.app.processEvents()
        self.assertFalse(window._tear_effects)

        for index in reversed(range(window.tabs.count())):
            tab = window.tabs.widget(index)
            window.tabs.removeTab(index)
            if tab is not None:
                tab.stop()
                tab.deleteLater()
        window.close()
        window.deleteLater()
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
        self.app.processEvents()

    def test_site_permissions_are_prompted_and_browsing_data_can_be_cleared(self) -> None:
        window = BrowserWindow()
        window.show()
        self.assertEqual(
            window._profile.persistentPermissionsPolicy(),
            window._profile.PersistentPermissionsPolicy.StoreInMemory,
        )

        allowed = self._permission("https://example.com", "Geolocation")
        window.confirm_site_permission = lambda _origin, _feature: True
        window.handle_permission_request(allowed)
        allowed.grant.assert_called_once()
        allowed.deny.assert_not_called()

        denied = self._permission("https://example.com", "Unsupported")
        window.handle_permission_request(denied)
        denied.deny.assert_called_once()

        self._load_url(
            window.current_view(),
            f"http://127.0.0.1:{self.server.server_port}/clear-history-test",
        )
        self.assertTrue(window.history.entries)
        window._clear_browsing_data(frozenset({"history", "cookies", "cache", "permissions"}))
        self.assertFalse(window.history.entries)
        self.assertIn("Local site storage", window.statusBar().currentMessage())

        for index in reversed(range(window.tabs.count())):
            tab = window.tabs.widget(index)
            window.tabs.removeTab(index)
            if tab is not None:
                tab.stop()
                tab.deleteLater()
        window.close()
        window.deleteLater()
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
        self.app.processEvents()

    @staticmethod
    def _permission(origin: str, feature: str):
        permission = Mock()
        permission.isValid.return_value = True
        permission.origin.return_value = QUrl(origin)
        permission.permissionType.return_value = SimpleNamespace(name=feature)
        return permission

    def _load_url(self, view, url: str) -> None:
        self._wait_for_load(view, lambda: view.setUrl(QUrl(url)))
        self.assertEqual(view.url().toString(), url)

    def _wait_for_load(self, view, start_navigation) -> None:
        loop = QEventLoop()
        callback = lambda _success: loop.quit()
        view.loadFinished.connect(callback)
        start_navigation()
        QTimer.singleShot(5000, loop.quit)
        loop.exec()
        view.loadFinished.disconnect(callback)

    def _submit_new_tab_search(self, view, query: str) -> None:
        loop = QEventLoop()

        def finish_local_search(_success: bool) -> None:
            if view.url().host() == "127.0.0.1" and view.url().path() == "/search":
                loop.quit()

        view.loadFinished.connect(finish_local_search)
        script = (
            "const input = document.querySelector('input[name=q]'); "
            f"input.value = {json.dumps(query)}; "
            "document.querySelector('form').requestSubmit();"
        )
        view.page().runJavaScript(script)
        QTimer.singleShot(5000, loop.quit)
        loop.exec()
        view.loadFinished.disconnect(finish_local_search)

    @staticmethod
    def _evaluate_javascript(view, script: str):
        loop = QEventLoop()
        result = []

        def finished(value) -> None:
            result.append(value)
            loop.quit()

        view.page().runJavaScript(script, finished)
        QTimer.singleShot(5000, loop.quit)
        loop.exec()
        if not result:
            raise AssertionError("JavaScript evaluation timed out")
        return result[0]

if __name__ == "__main__":
    unittest.main()
