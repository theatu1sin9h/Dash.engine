# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Atul Singh Chandel

"""Safe address-bar and search-query handling."""

import re
from urllib.parse import quote_plus

from PyQt6.QtCore import QUrl

from browser.constants import SEARCH_URL

_HOST_WITH_PORT = re.compile(r"^(?:[A-Za-z0-9.-]+|\[[0-9A-Fa-f:]+\]):\d+(?:/.*)?$")
_HOST_LIKE = re.compile(
    r"^(?:localhost|(?:[A-Za-z0-9-]+\.)+[A-Za-z]{2,}|"
    r"(?:\d{1,3}\.){3}\d{1,3}|\[[0-9A-Fa-f:]+\])(?::\d+)?(?:/.*)?$"
)


class AddressError(ValueError):
    """Raised when an address uses an invalid or unsafe URL scheme."""


def address_to_url(text: str, search_url: str = SEARCH_URL) -> QUrl:
    """Resolve address-bar text to an HTTP(S) URL or a web search URL."""
    value = text.strip()
    if not value:
        raise AddressError("Enter a website address or search query.")

    lowered = value.lower()
    if lowered.startswith(("javascript:", "data:", "file:", "intent:")):
        raise AddressError("That URL scheme is not allowed.")

    if value.startswith("//"):
        value = f"https:{value}"
    elif _HOST_WITH_PORT.fullmatch(value) or _HOST_LIKE.fullmatch(value):
        value = f"https://{value}"

    candidate = QUrl(value)
    scheme = candidate.scheme().lower()
    if scheme:
        if scheme not in {"http", "https"}:
            raise AddressError("Only HTTP and HTTPS addresses are supported.")
        if not candidate.isValid() or not candidate.host():
            raise AddressError("Enter a valid HTTP or HTTPS address.")
        if candidate.userName() or candidate.password():
            raise AddressError("Addresses containing embedded credentials are not supported.")
        return candidate

    query_url = QUrl(search_url.format(query=quote_plus(value)))
    if not query_url.isValid():
        raise AddressError("Could not create a search URL.")
    return query_url
