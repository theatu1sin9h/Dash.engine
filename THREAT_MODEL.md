# Dash Browser Threat Model

**Status:** Initial development-stage model; validate with an independent
security review before public release.

## Assets

- Persistent cookies, web cache, origin storage, and active page state.
- Dash browsing history, bookmarks, settings, and download records.
- Files selected by the user as download destinations.
- The integrity of Dash, Qt WebEngine/Chromium, the operating system, and
  future update artifacts.
- User awareness of site permissions, insecure sites, and download risks.

## Actors and assumptions

- A remote website or third-party resource may be malicious or compromised.
- Downloaded files and filenames are untrusted.
- A local process running as the same operating-system user may access that
  user's profile files; Dash does not defend against a compromised account.
- The operating system, Qt WebEngine, Chromium, TLS trust store, and packaging
  system are trusted dependencies and must receive security updates.
- Dash does not promise anonymity, forensic erasure, malware detection, or
  enterprise policy enforcement.

## Trust boundaries

1. Remote web content is rendered by Qt WebEngine and must not receive a Dash
   native API or unrestricted filesystem/command access.
2. Browser chrome and native dialogs are trusted UI; web-page permission
   requests pass through a native prompt.
3. The regular persistent profile is separate from disposable off-the-record
   Tear Tab profiles.
4. Download content crosses from the network into a user-selected filesystem
   location only after the user accepts the save dialog.
5. Third-party search providers, websites, network operators, and OS package
   repositories are external services with their own privacy and security
   properties.

## Existing mitigations

- HTTP(S)-only top-level navigation, with unsupported schemes rejected.
- Qt WebEngine's built-in process and web security boundaries are not
  intentionally disabled by application code.
- HTTPS-only custom search templates, credential rejection, and query encoding.
- Native file destination selection, filename sanitization, collision avoidance,
  executable-extension warning, and no automatic download execution.
- Permission prompts with memory-only decisions and a Settings revocation list.
- Off-the-record profile for Tear Tab and a bounded, persistent Dash history.
- Bounded, permission-restricted app-owned JSON files with atomic replacement.

## Main threats and current gaps

| Threat | Current mitigation | Remaining risk |
|---|---|---|
| Malicious site seeks native access | No web-exposed native bridge; Qt WebEngine page isolation; explicit feature permission prompt | Engine vulnerabilities remain possible; not independently tested |
| Permission prompt abuse or overgrant | Native per-request prompt; decisions are memory-only; users can revoke | No per-site policy editor before a request; unsupported features are denied |
| Persistent tracking after data clearing | Clear-history, cookies, HTTP cache, and permissions controls | Local storage, IndexedDB, cache storage, and service workers are not cleared |
| Malicious download | User-selected path, filename handling, warning for executable suffixes, no auto-open | No content scanner, reputation check, or safe-browsing service |
| Ads and tracker requests | Qt WebEngine request interceptor blocks a small local set of third-party domains | Limited static coverage; no full filter syntax, remote updates, cosmetic filtering, phishing reputation, or guarantee that ads are removed |
| Network path privacy | Browser follows OS network configuration | Dash does not provide network routing controls |
| Supply-chain compromise | Ubuntu package install instructions and CI dependency audit input | No signed app update channel, full lock/SBOM, or artifact provenance |
| Local profile exposure | User-only app-owned data directory permissions where supported | Same-user malware and OS administrator access are outside the app's boundary |
| Private-session data persistence | Off-the-record profile, no Dash history, temporary profile cleanup | No forensic erasure guarantee; websites, network operators, OS, and downloads retain independent records |

## Security objectives

- Preserve Qt/Chromium defaults and host sandboxing; do not weaken them for
  compatibility or visual features.
- Keep permission decisions explicit and session-limited until durable,
  auditable site controls exist.
- Never claim data was cleared beyond the specific Qt APIs invoked.
- Never auto-run downloaded files.
- Keep the web rendering process separate from privileged application logic.
- Require independent review and release provenance before stable distribution.
