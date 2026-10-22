# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Atul Singh Chandel

"""Unit tests for safe address-bar parsing."""

import unittest

from browser.navigation import AddressError, address_to_url


class AddressToUrlTests(unittest.TestCase):
    def test_adds_https_to_domain(self) -> None:
        self.assertEqual(address_to_url("example.com").toString(), "https://example.com")

    def test_preserves_explicit_http(self) -> None:
        self.assertEqual(address_to_url("http://example.com").scheme(), "http")

    def test_adds_https_to_local_port_address(self) -> None:
        self.assertEqual(address_to_url("localhost:8080").toString(), "https://localhost:8080")

    def test_adds_https_to_ipv4_address(self) -> None:
        self.assertEqual(address_to_url("127.0.0.1:8080").toString(), "https://127.0.0.1:8080")

    def test_searches_ordinary_text(self) -> None:
        url = address_to_url("Dash Browser")
        self.assertEqual(url.host(), "duckduckgo.com")
        self.assertEqual(url.query(), "q=Dash+Browser")

    def test_rejects_unsafe_schemes(self) -> None:
        for value in ("javascript:alert(1)", "data:text/html,test", "file:///etc/passwd"):
            with self.subTest(value=value), self.assertRaises(AddressError):
                address_to_url(value)

    def test_rejects_embedded_credentials(self) -> None:
        with self.assertRaises(AddressError):
            address_to_url("https://user:password@example.com")

    def test_rejects_empty_input(self) -> None:
        with self.assertRaises(AddressError):
            address_to_url(" ")


if __name__ == "__main__":
    unittest.main()
