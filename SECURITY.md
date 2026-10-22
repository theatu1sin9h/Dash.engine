# Security Policy

Dash Browser is an early development project, not a stable public release.
Please do not include real browsing history, cookies, credentials, tokens,
private URLs, or personal data in a report.

## Reporting a vulnerability

No dedicated security-reporting address or private advisory channel is
configured in this repository yet. Before publishing Dash, maintainers must
configure a private contact method in the repository hosting service and
replace this notice with that contact.

Until then, do not publish an unredacted report containing exploit details or
user data in a public issue. Use the private contact route provided by the
project owner, if one has been separately shared with you. Do not assume a
public issue is monitored for security reports.

## Current support

- No stable release or supported release branch is declared.
- The application depends on the host's Qt WebEngine/Chromium security updates.
- Users should keep the operating system and Qt WebEngine packages updated.
- No bug-bounty program, response-time guarantee, or security certification is
  offered.

## Maintainer response expectations

Once a private contact channel is configured, maintainers should acknowledge
reports, reproduce them on a supported setup, assess impact and affected
versions, coordinate a fix and disclosure date with the reporter, and publish
an advisory for confirmed vulnerabilities. See [SECURITY_RESPONSE.md](./SECURITY_RESPONSE.md).
