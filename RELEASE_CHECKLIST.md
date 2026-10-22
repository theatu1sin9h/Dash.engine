# Release Checklist

This project has no approved public release yet. A checklist item is complete
only when evidence is attached to the release record.

## Current release blockers

- [ ] Choose supported OS versions and maintain a Qt WebEngine/Chromium update
      commitment.
- [ ] Produce reproducible Ubuntu package artifacts and test installation,
      upgrade, rollback, and uninstall on clean systems.
- [ ] Sign release artifacts and updates; publish and test key rotation and
      rollback protection.
- [ ] Complete independent security review, including sandbox, TLS,
      navigation, permission, download, and profile lifecycle behavior.
- [ ] Implement/test safe all-origin site-data deletion or document an approved
      alternative that accurately names what remains.
- [ ] Decide whether to add and maintain phishing/download reputation or host
      malware-scanner integration; assess privacy before enabling it.
- [ ] Decide whether request filtering will be expanded beyond Dash's small
      built-in third-party domain list. Clearly disclose its limited coverage.
- [ ] Generate and retain an SBOM; review direct and transitive dependency
      advisories and licenses.
- [ ] Configure and test a private security-reporting channel and incident
      process; the public contact in `SECURITY.md` is not an encrypted channel.
- [ ] Complete privacy, consumer-protection, accessibility, and legal review in
      each target jurisdiction.
- [ ] Measure installer size, installed size, startup time, and memory use.
- [ ] Verify accessibility, screen-reader labels, keyboard navigation, and
      reduced-motion behavior on supported platforms.
- [ ] Run the complete automated suite on each supported OS and archive results.

## Ubuntu development/release validation

- [ ] Build source distribution and wheel from `pyproject.toml`.
- [ ] Run `python -m unittest discover -s tests -v`.
- [ ] Run `python -m compileall -q browser tests main.py`.
- [ ] Run `pip-audit --strict -r requirements-audit.txt`; triage and record
      advisories. The audit input pins direct packages, not every transitive
      artifact.
- [ ] Install the release artifact on a clean supported Ubuntu image with
      system Qt WebEngine dependencies.
- [ ] Verify actual Chromium version and host sandbox status; do not infer
      sandboxing from the presence of a browser window.
- [ ] Verify invalid TLS certificate handling and HTTP downgrade behavior.
- [ ] Verify actual permissions, clear-data behavior, private-profile cleanup,
      downloads, and crash paths manually and automatically.
- [ ] Confirm installed browser engine receives OS security updates.

## Go/no-go

Do not call a build production-ready merely because this checklist exists or
CI passes. Any unresolved critical/high vulnerability, missing artifact
signature, unsupported engine baseline, or materially misleading privacy claim
is a no-go.
