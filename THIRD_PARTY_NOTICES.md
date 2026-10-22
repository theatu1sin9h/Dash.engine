# Third-Party Notices

Dash is distributed under GPL-3.0-or-later. This file records the direct and
transitive Python runtime packages used by the PyPI-based development install,
plus the Qt WebEngine/Chromium components and their licensing families.
Review the exact licenses and required notices for the selected Qt/Chromium
build before distributing an installer.

## Python packages

The installed Python package names, versions, license identifiers, and project
URLs below were generated with `pip-licenses` from the Ubuntu development
environment. The two Qt runtime wheel packages are included by PyPI
installations of PyQt6 / PyQt6-WebEngine; the Ubuntu system-package install
uses distribution-provided Qt libraries instead.

The resolved PyPI runtime dependency chain is `PyQt6` -> `PyQt6-Qt6` and
`PyQt6-sip`, plus `PyQt6-WebEngine` -> `PyQt6`, `PyQt6-WebEngine-Qt6`, and
`PyQt6-sip`. That gives the five Python distributions listed here; the
transitive native libraries and Chromium components are listed separately
below and require their distribution-provided notices.

| Package | License | Project |
|---|---|---|
| PyQt6 | GPL-3.0-only | [Riverbank Computing](https://www.riverbankcomputing.com/software/pyqt/) |
| PyQt6-WebEngine | GPL-3.0-only | [Riverbank Computing](https://www.riverbankcomputing.com/software/pyqtwebengine/) |
| PyQt6-sip | BSD-2-Clause | [Python-SIP](https://github.com/Python-SIP/sip) |
| PyQt6-Qt6 | LGPL v3 | [Riverbank Computing](https://www.riverbankcomputing.com/software/pyqt/) |
| PyQt6-WebEngine-Qt6 | LGPL v3 | [Riverbank Computing](https://www.riverbankcomputing.com/software/pyqt/) |

The `pip-licenses` output observed for this environment was:

| Name | Version | License | URL |
|---|---:|---|---|
| PyQt6 | 6.10.2 | GPL-3.0-only | https://www.riverbankcomputing.com/software/pyqt/ |
| PyQt6-WebEngine | 6.10.0 | GPL-3.0-only | https://www.riverbankcomputing.com/software/pyqtwebengine/ |
| PyQt6_sip | 13.11.0 | BSD-2-Clause | https://github.com/Python-SIP/sip |

Qt6 runtime package license declarations were checked against the corresponding
PyPI project metadata. These versions and metadata can change; regenerate the
inventory for each release. CI runs `pip-licenses --allow-only` against the
installed environment and rejects license identifiers outside the reviewed
compatibility allowlist.

## Qt and browser engine components

| Component | License information | Notes |
|---|---|---|
| Qt | LGPLv3 and GPLv3 options, depending on module and distribution | Verify the modules actually shipped and provide applicable license texts and notices. |
| Qt WebEngine | LGPLv3/GPLv3 distribution options | Includes a Chromium-based engine; the selected Qt package's notices must accompany a release. |
| Chromium | BSD-3-Clause plus bundled third-party licenses | The Chromium and Qt WebEngine distributions provide additional third-party notices; include the notices for the exact binaries shipped. |

These are high-level license families, not a complete file-by-file inventory or
legal opinion. The Ubuntu system-package route inherits the distribution's
Qt/Chromium build and its corresponding licensing/notice files. An AppImage or
other bundled artifact must retain and ship the notices for the exact Qt
WebEngine, Chromium, and other binaries included.

## Release inventory requirements

- Regenerate the Python package inventory after changing runtime dependencies
  or the supported Qt/Chromium distribution.
- Include every license/notice file required by the exact packaged Qt and
  Chromium artifacts.
- Review license compatibility and redistribution obligations before release.
- Generate a release SBOM; this file is not an SBOM and does not replace legal
  review.
