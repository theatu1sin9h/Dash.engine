# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Atul Singh Chandel

"""Local privacy services supported by Qt WebEngine."""

import ipaddress
from urllib.parse import urlsplit

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWebEngineCore import QWebEngineUrlRequestInfo, QWebEngineUrlRequestInterceptor

AD_DOMAINS = frozenset({
    "ad.doubleclick.net",
    "adservice.google.com",
    "googleadservices.com",
    "googlesyndication.com",
    "adnxs.com",
    "adsrvr.org",
})
TRACKER_DOMAINS = frozenset({
    "google-analytics.com",
    "googletagmanager.com",
    "connect.facebook.net",
    "pixel.facebook.com",
    "segment.io",
    "hotjar.com",
})


def normalize_site(value: object) -> str:
    """Validate and normalize a hostname or HTTP(S) URL for the allowlist."""
    if not isinstance(value, str):
        raise ValueError("Website must be text.")
    candidate = value.strip()
    if not candidate or len(candidate) > 2048:
        raise ValueError("Enter a valid website host.")
    if "://" not in candidate:
        if ":" in candidate:
            raise ValueError("Enter a hostname without a port or unsupported scheme.")
        candidate = f"https://{candidate}"
    parsed = urlsplit(candidate)
    if parsed.scheme.lower() not in {"http", "https"} or not parsed.hostname:
        raise ValueError("Allowlist entries must be HTTP or HTTPS websites.")
    if parsed.username or parsed.password:
        raise ValueError("Website addresses must not contain credentials.")
    host = parsed.hostname.rstrip(".").encode("idna").decode("ascii").lower()
    try:
        parsed.port
    except ValueError as exc:
        raise ValueError("Enter a valid website host.") from exc
    try:
        host = str(ipaddress.ip_address(host))
    except ValueError:
        labels = host.split(".")
        if not host or any(
            not label
            or len(label) > 63
            or label.startswith("-")
            or label.endswith("-")
            or not all(character.isalnum() or character == "-" for character in label)
            for label in labels
        ):
            raise ValueError("Enter a valid website host.")
    if len(host) > 253:
        raise ValueError("Enter a valid website host.")
    return host


def _domain_matches(host: str, domains: frozenset[str]) -> str | None:
    for domain in domains:
        if host == domain or host.endswith(f".{domain}"):
            return domain
    return None


class RequestBlocker(QWebEngineUrlRequestInterceptor):
    """Block a small built-in set of known third-party ad/tracker domains."""

    countsChanged = pyqtSignal(int, int)

    def __init__(self, enabled: bool = True, allowlist: tuple[str, ...] = (), parent=None):
        super().__init__(parent)
        self.enabled = enabled
        self.allowlist = frozenset(allowlist)
        self.ads_blocked = 0
        self.trackers_blocked = 0

    def configure(self, enabled: bool, allowlist: tuple[str, ...]) -> None:
        self.enabled = enabled
        self.allowlist = frozenset(allowlist)

    def reset_counts(self) -> None:
        self.ads_blocked = 0
        self.trackers_blocked = 0
        self.countsChanged.emit(0, 0)

    def interceptRequest(self, info: QWebEngineUrlRequestInfo) -> None:
        if not self.enabled:
            return
        request_url = info.requestUrl()
        first_party_url = info.firstPartyUrl()
        host = request_url.host().rstrip(".").lower()
        first_party_host = first_party_url.host().rstrip(".").lower()
        if not host or not first_party_host or host == first_party_host:
            return
        if any(
            first_party_host == allowed or first_party_host.endswith(f".{allowed}")
            for allowed in self.allowlist
        ):
            return
        resource_type = info.resourceType()
        if resource_type in {
            QWebEngineUrlRequestInfo.ResourceType.ResourceTypeMainFrame,
            QWebEngineUrlRequestInfo.ResourceType.ResourceTypeSubFrame,
        }:
            return
        ad_domain = _domain_matches(host, AD_DOMAINS)
        tracker_domain = _domain_matches(host, TRACKER_DOMAINS)
        if ad_domain is None and tracker_domain is None:
            return
        info.block(True)
        if ad_domain is not None:
            self.ads_blocked += 1
        if tracker_domain is not None:
            self.trackers_blocked += 1
        self.countsChanged.emit(self.ads_blocked, self.trackers_blocked)
