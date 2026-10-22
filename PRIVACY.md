# Dash Browser Privacy Notice

**Draft for product review.** This describes the current development build; it
is not legal advice or a jurisdiction-specific compliance statement.

## Data stored locally

Dash stores settings, bookmarks, and its bounded browsing history in
user-specific XDG directories. Qt WebEngine stores regular-profile cookies,
HTTP cache, and website data in the user's profile. Downloads are written only
to a destination selected by the user. Dash does not run an analytics or
account service.

## Data sent to other parties

When you visit a site or search, the destination provider and network services
may receive the request, IP address, and submitted information. A custom search
provider receives the search URL and query. Dash does not proxy these requests.
External providers' retention and privacy practices are outside Dash's control.

Dash does not make a separate public-address lookup. Browser traffic uses the
network configured by the operating system; Dash does not change network
routing.

When enabled, Dash locally blocks requests to a small built-in list of known
third-party ad and tracker domains using Qt WebEngine's request interceptor.
No visited URLs are sent to a filtering service. The list is not comprehensive,
has no remote updater, and does not guarantee ad/tracker removal. Blocked
counts are session-only intercepted requests. Users can disable blocking or
persistently allowlist websites in the Privacy dashboard or Settings.

## Permissions and clearing

Dash displays a native prompt for supported Qt WebEngine site permission
requests. Decisions are stored in memory for the current app session and can be
reviewed or revoked in Settings. Closing Dash discards these permission
decisions.

The Clear Browsing Data controls can clear Dash history, cookies, HTTP cache,
and permission decisions in the regular profile. Qt WebEngine does not expose a
safe supported API to clear all origins' local storage, IndexedDB, cache
storage, or service-worker data while the profile remains active. Those data
are not removed by this control. Downloaded files are not removed. Tear Tab
uses an off-the-record profile, excludes visits from Dash history, and retains
downloads; it is not a guarantee of forensic erasure or anonymity.

## Safety limitations

Dash does not scan downloaded files for malware, provide phishing reputation
checks, or provide complete site-data deletion. Its limited local request
blocker is not a substitute for a comprehensive content blocker. Do not rely on
Dash as a security scanner or anonymity tool.

## Contact and review

No dedicated privacy contact or legal review has been configured for this
development project. A release owner must add a contact and obtain review for
the intended jurisdictions before public distribution.
