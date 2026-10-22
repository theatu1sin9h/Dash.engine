# Known Security and Privacy Limitations

Dash is an early development build and is **not ready for public distribution**.

- Site permissions cover Qt WebEngine permission requests exposed through the
  native API. Decisions are session-memory-only; unsupported permission types
  are denied. No persistent per-site policy editor exists.
- Clear Browsing Data clears Dash's own history, regular-profile cookies, HTTP
  cache, and in-memory permission decisions. It does **not** clear all-origin
  local storage, IndexedDB, cache storage, service workers, downloads, or
  records outside Dash.
- Tear Tab uses an off-the-record Qt WebEngine profile and excludes those
  visits from Dash history. It does not guarantee forensic erasure and does not
  remove downloads or external records.
- Ad/tracker blocking covers only a small fixed set of third-party domains.
  There is no remote filter-list update, full rule syntax, cosmetic filtering,
  phishing reputation service, or safe-browsing URL check.
- Browser traffic follows the operating system's network setup; Dash does not
  provide network routing controls.
- Downloaded file contents are not malware-scanned. Executable-like suffixes
  produce a warning and files are never opened automatically.
- Site permissions, certificate error edge cases, sandbox behavior, and the
  exact Chromium patch cadence depend on the installed Qt WebEngine and host
  operating system. They still require platform testing.
- No signed updater, release-signing process, generated SBOM, completed
  transitive dependency/license assessment, or production installer is
  provided.
- No dedicated security contact, independent security audit, or
  jurisdiction-specific legal/privacy assessment is configured.
- The approximately 60 MB size target has not been measured. A packaged Qt
  WebEngine browser may exceed it; do not reduce security protections to meet
  an unverified size target.
- New-tab wallpaper images are embedded into each new-tab document after
  optimization and limited to 5 MiB and 24 megapixels at selection time. If a
  selected image is moved, removed, or becomes unreadable, the page uses a safe
  gradient background instead.
- New-tab wallpaper images are embedded into each new-tab document and limited
  to 5 MiB and 24 megapixels. If a selected image is moved, removed, or becomes
  unreadable, the page uses a safe gradient background instead.
