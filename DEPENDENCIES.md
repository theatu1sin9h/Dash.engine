# Dependency Inventory

This is a source-level inventory, not a generated SBOM or complete license
audit.

## Runtime

| Dependency | Role | Development version observed | Source / update owner |
|---|---|---:|---|
| Python | Application runtime | 3.14.4 | Ubuntu/system Python |
| PyQt6 | Native UI and Qt bindings | 6.10.2 | Ubuntu packages or Python package index |
| PyQt6-WebEngine | Chromium-backed browser view | 6.10.0 | Ubuntu packages or Python package index |
| Qt / Qt WebEngine | UI, networking, browser engine | 6.10.2 / 6.10.0 | Ubuntu packages |
| Chromium | Web content engine | 134.0.6998.208 user-agent build | Shipped/updated by Qt WebEngine distribution |

The Ubuntu development installation command is in `README.md`. `pyproject.toml`
declares supported Python-package installation dependencies; `requirements-audit.txt`
records the directly pinned development versions used as the input to CI's
transitive advisory scan. It is not a full lockfile and does not pin hashes.

## Build and test

- Build backend: Hatchling.
- Test framework: Python standard-library `unittest`, with PyQt6 and Qt
  WebEngine integration tests.
- CI: GitHub Actions workflow at `.github/workflows/ci.yml` builds source/wheel,
  runs tests, compile-checks, and runs `pip-audit`.

## License and supply-chain review status

The project is licensed under GPL-3.0-or-later. `THIRD_PARTY_NOTICES.md`
records the Python packages and the Qt/Chromium licensing families currently
identified. Still requiring release-specific verification:

- The exact license obligations for the Qt and Qt WebEngine distribution
  selected for a release, including PyQt GPL/commercial licensing implications.
- Complete license inventory for transitive native and system-package
  dependencies, and the exact bundled Chromium notices.
- SBOM generation and release artifact provenance.
- Whether distro backports or upstream Python packages provide the appropriate
  Chromium security-update cadence for each supported platform.

Before distribution, generate an SBOM for the actual artifact and review the
license notices and obligations with qualified counsel. The current dependency
scan is advisory triage, not proof that dependencies are vulnerability-free.
