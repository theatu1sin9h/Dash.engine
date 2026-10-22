# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Atul Singh Chandel

"""Tests for local request blocking and site normalization."""

import unittest
from unittest.mock import Mock

from PyQt6.QtCore import QUrl
from PyQt6.QtWebEngineCore import QWebEngineUrlRequestInfo

from browser.privacy import (
    RequestBlocker,
    normalize_site,
)


class SiteNormalizationTests(unittest.TestCase):
    def test_normalizes_hosts_urls_and_idna(self) -> None:
        self.assertEqual(normalize_site("HTTPS://Example.COM/path"), "example.com")
        self.assertEqual(normalize_site("bücher.example"), "xn--bcher-kva.example")

    def test_rejects_invalid_schemes_and_credentials(self) -> None:
        for site in ("", "file:///tmp/page", "javascript:alert(1)", "https://u:p@example.com"):
            with self.subTest(site=site), self.assertRaises(ValueError):
                normalize_site(site)


class RequestBlockerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.blocker = RequestBlocker()

    @staticmethod
    def request(url: str, first_party: str, resource_type=None):
        info = Mock()
        info.requestUrl.return_value = QUrl(url)
        info.firstPartyUrl.return_value = QUrl(first_party)
        info.resourceType.return_value = (
            resource_type
            or QWebEngineUrlRequestInfo.ResourceType.ResourceTypeImage
        )
        return info

    def test_blocks_known_third_party_ads_and_tracks_real_counts(self) -> None:
        ad = self.request("https://ads.googlesyndication.com/banner.js", "https://news.example")
        tracker = self.request("https://www.google-analytics.com/collect", "https://news.example")

        self.blocker.interceptRequest(ad)
        self.blocker.interceptRequest(tracker)

        ad.block.assert_called_once_with(True)
        tracker.block.assert_called_once_with(True)
        self.assertEqual(self.blocker.ads_blocked, 1)
        self.assertEqual(self.blocker.trackers_blocked, 1)

    def test_does_not_block_first_party_main_frame_or_allowlisted_site(self) -> None:
        first_party = self.request(
            "https://ad.doubleclick.net/page",
            "https://ad.doubleclick.net",
        )
        main_frame = self.request(
            "https://ad.doubleclick.net/page",
            "https://publisher.example",
            QWebEngineUrlRequestInfo.ResourceType.ResourceTypeMainFrame,
        )
        allowlisted = RequestBlocker(True, ("publisher.example",))
        allowed_request = self.request(
            "https://ad.doubleclick.net/ad.js",
            "https://www.publisher.example",
        )

        self.blocker.interceptRequest(first_party)
        self.blocker.interceptRequest(main_frame)
        allowlisted.interceptRequest(allowed_request)

        first_party.block.assert_not_called()
        main_frame.block.assert_not_called()
        allowed_request.block.assert_not_called()

    def test_global_disable_stops_blocking_and_reset_clears_counters(self) -> None:
        self.blocker.configure(False, ())
        request = self.request("https://ad.doubleclick.net/a", "https://site.example")
        self.blocker.interceptRequest(request)
        request.block.assert_not_called()
        self.blocker.ads_blocked = 3
        self.blocker.trackers_blocked = 2

        self.blocker.reset_counts()

        self.assertEqual((self.blocker.ads_blocked, self.blocker.trackers_blocked), (0, 0))


if __name__ == "__main__":
    unittest.main()
