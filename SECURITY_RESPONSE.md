# Security Incident Response

This is a maintainer workflow draft. No dedicated private reporting contact is
configured yet; see [SECURITY.md](./SECURITY.md).

## Triage

1. Receive the report through a private channel; avoid requesting real user
   cookies, browsing history, or credentials.
2. Acknowledge receipt and record a private tracking identifier, affected
   versions, engine versions, platform, impact, and reproduction status.
3. Reproduce with harmless fixtures in an isolated test environment. Do not
   test against users or production third-party systems.
4. Assess severity, exploit preconditions, affected trust boundary, and whether
   data or users may be at risk. Request independent review for browser-engine
   boundary issues.

## Containment and patch

1. Restrict access to the report and artifacts.
2. Identify safe mitigations that do not disable TLS validation, Chromium
   sandboxing, or other engine protections.
3. Develop a minimal fix and regression tests; review changes independently.
4. Check Python and OS Qt/Chromium dependency advisories.
5. Prepare signed release artifacts and an advisory before public disclosure.
   Do not publish binaries until the signing and update processes are in place.

## Disclosure and recovery

1. Coordinate disclosure timing with the reporter where practical.
2. Publish affected versions, impact, mitigation, fixed versions, and known
   limitations without exposing user data.
3. Notify users through a verified project channel once one exists.
4. Preserve a post-incident record and add tests or release gates to prevent
   recurrence.
