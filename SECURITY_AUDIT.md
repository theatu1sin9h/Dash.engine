# Dash Browser Security Audit

**Review date:** 2026-10-21
**Scope:** repository source, tests, README, current Python/Qt WebEngine runtime,
and a read-only code review. This is a development-stage review, not an
independent penetration test, formal audit, legal assessment, or certification.

## Technology and scope

Dash is a Python desktop application using PyQt6 and Qt WebEngine (Chromium).
The checked development environment reports Python 3.14.4, PyQt 6.10.2,
Qt 6.10.2, Qt WebEngine 6.10.0, and Chromium 134.0.6998.208. The README
currently documents Ubuntu as the supported development platform. The
application uses system Qt packages for its documented Ubuntu installation.

The independent code review found **no confirmed exploitable vulnerability in
the reviewed changes**. The following table records product gaps and limits;
they are not vulnerability claims.

| Finding | Severity | Status | Evidence and impact | Remediation / verification |
|---|---|---|---|---|
| Website permissions had no user prompt or management. | Medium | Addressed for supported Qt WebEngine permission types | A page-level permission request could not be inspected or managed in the Dash UI. | Requests now require an explicit native prompt, decisions are memory-only, and Settings lists/revokes them. Automated GUI tests cover prompts, session policy, and revoke controls. |
| No in-app controls cleared persistent profile data. | Medium | Partially addressed | Cookies and HTTP cache persisted in the regular profile without an app control. Qt does not expose a safe all-origin local-storage/service-worker wipe while the profile is active. | Settings clears Dash history, cookies, HTTP cache, and permission decisions. The UI and tests explicitly disclose that origin storage, service workers, downloads, and external records are not cleared. |
| No package metadata or dependency audit gate existed. | Medium | Partially addressed | The source tree had no build manifest or CI configuration, so a package and dependency-update process could not be reproduced from the repository. | Added Python package metadata, an Ubuntu CI workflow, a direct-dependency audit input, tests, and build steps. The first CI run, transitive lock, signatures, update channel, and release artifact remain unverified. |
| Downloaded files are not malware-scanned. | Medium | Unresolved, disclosed | `browser/downloads.py` warns about executable types and never opens downloads automatically, but does not scan file contents. | Keep the limitation visible; public/enterprise release should decide whether to integrate a maintained host scanner or reputation service after privacy and threat-model review. |
| Ad/tracker filtering is limited. | Medium | Partially addressed | A local Qt WebEngine interceptor blocks a small built-in set of known third-party ad/tracker domains and counts blocked requests. It has no full filter syntax, cosmetic rules, remote updates, or comprehensive coverage. | Do not claim comprehensive ad blocking. Any future list updater needs trusted sources, bounded parsing, license review, and tests. |
| General origin-storage deletion is unavailable in the current live-profile design. | Medium | Unresolved, disclosed | Qt WebEngine exposes cookie/cache/permission APIs but no supported all-origin local storage, IndexedDB, or service-worker clearing API in the APIs inspected. | Design and test a profile-shutdown/recreation lifecycle before claiming full site-data deletion. Do not delete active profile databases directly. |
| Production security, release, and legal assessment have not been performed. | High release blocker | Unresolved | No independent penetration test, supported release package, signed update flow, SBOM/license review, or jurisdiction-specific privacy/legal review is present. | Block stable public release until the release checklist is completed and the remaining reviews are independently approved. |

## Verified controls

- Top-level page navigation is limited to HTTP(S); unsupported schemes are
  rejected in `browser/browser_tab.py`.
- Search templates require HTTPS, one `{query}` placeholder, and no embedded
  credentials in `browser/settings.py`.
- Dash browsing history accepts bounded, validated HTTP(S) entries and stores
  them through private atomic JSON writes.
- Download names are reduced to a basename, existing paths are not overwritten
  by Dash, potentially executable suffixes trigger a warning, and downloads
  never open automatically. File contents are not scanned.
- Tear Tabs use an off-the-record `QWebEngineProfile`; their visits are excluded
  from Dash history. The profile is cleaned up after its last tab closes.
  Downloaded files remain.
- The default profile now asks before granting Qt WebEngine permission requests;
  decisions are stored in memory only. Users can review and revoke them.
- Settings can request deletion of Dash history, cookies, HTTP cache, and
  in-memory permission decisions. Cache deletion completes asynchronously.
- A Qt WebEngine request interceptor blocks a small local domain set for
  third-party subresource requests and counts actual blocked requests.
- `tests/` includes offline unit tests and local-HTTP Qt WebEngine integration
  tests. These do not constitute comprehensive security testing.

## Not established by this audit

This review did not independently verify sandbox enforcement, operating-system
renderer isolation, all TLS/certificate failure cases, mixed-content handling,
cross-origin behavior, update integrity, memory safety, malware reputation,
crash recovery, transitive dependency advisories, all permission types on
physical devices, or legal compliance. The selected Qt/Chromium build and host
distribution control many of these behaviors; use supported OS packages and
keep them updated. No vulnerability scanning result or certificate of
compliance is implied by the tests or workflow.

## Release blockers

The stable release blockers are:

1. No reviewed, signed, reproducible release artifact or update mechanism.
2. No completed independent browser-engine/security assessment.
3. No complete all-origin persistent site-data clearing control.
4. Limited ad/tracker domain coverage; no phishing or malware reputation
   integration.
5. No final SBOM, transitive dependency and license review, or supported update
   policy.
6. No documented security-reporting contact has been configured for users.
7. No completed privacy/legal review for intended markets.
8. No measured installed size or runtime resource baseline.
