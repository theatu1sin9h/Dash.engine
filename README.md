# Dash Browser

**Less browser. More web.**

Dash Browser is a minimal desktop web browser built with Python, PyQt6, and
Qt WebEngine. It has a Chromium-based web view, an address/search bar,
multi-tab browsing, bookmarks, history, downloads, and local privacy controls.

## Technology

- **Python 3.10+:** browser window, navigation, settings, downloads, and local
  data management.
- **PyQt6 / Qt Widgets:** native desktop controls and application window.
- **Qt WebEngine:** Chromium-based page renderer and browser engine.
- **HTML, CSS, and JavaScript:** the built-in welcome/search page and its
  lightweight Devanagari character-rain backdrop. The effect is generated
  locally, pauses when the page is hidden, and is disabled for reduced-motion
  preferences.
- **Hatchling and pip:** Python package build/install workflow.

The browser is not based on Electron or a hosted web app. Web pages are rendered
by Qt WebEngine's bundled Chromium runtime.

The supported, documented source workflow is Linux-first and is exercised in
Ubuntu CI. Other operating systems have not been verified. This repository
does not provide signed installers, a package repository, or an application
update service.

## Clone, set up, and launch

On Ubuntu, install Python and the Qt/XCB system libraries used by PyQt6:

```bash
sudo apt update
sudo apt install python3 python3-venv \
  libegl1 libgl1 libxkbcommon-x11-0 libxcb-cursor0 libxcb-icccm4 \
  libxcb-keysyms1 libxcb-shape0 libxcb-xinerama0 libxcb-xkb1
```

Run these commands from a terminal. On first launch, the script creates a
project-local `.venv`, installs Dash Browser and its declared dependencies,
and starts the desktop app. Later launches reuse that environment.

```bash
git clone https://github.com/theatu1sin9h/Dash.engine.git
cd Dash.engine
./run.sh
```

`run.sh` is for Linux only. It does not use `sudo`, alter system Python, or
change desktop settings. If setup fails, it prints the failing command and
leaves the error visible in the terminal.

To set up manually instead:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e .
.venv/bin/dash-browser
```

The dependency ranges are declared in `pyproject.toml`; there is no lock file,
so pip resolves compatible releases at install time. Qt 6.11 is temporarily
excluded because its offscreen WebEngine integration failed the browser test
suite; the verified runtime is Qt 6.10. Qt WebEngine and its Chromium engine
are security-sensitive dependencies; keep them updated.

## Application-menu shortcut, desktop shortcut, and pinning

After setup, optionally create a launcher in the current Linux user's
application menu:

```bash
.venv/bin/dash-browser-install-shortcut
```

This explicit command writes only to the user's XDG data directory (normally
`~/.local/share/applications` and `~/.local/share/icons`). It does not use
`sudo`, write a desktop icon, or pin the app. Run it again to refresh the
launcher after moving the project or recreating its virtual environment.

To pin Dash Browser, launch it once and use the desktop environment's normal
interface:

- **Ubuntu GNOME:** open Activities, search for **Dash Browser**, then use
  **Add to Favorites** (or right-click its running dock icon and choose
  **Add to Favorites**).
- **KDE Plasma:** search for **Dash Browser** in the application launcher,
  right-click it, and choose **Pin to Task Manager**. Alternatively, right-click
  the running taskbar icon and pin it.
- **Desktop icon:** use your desktop environment's application-menu context
  action or its documented method to create a desktop shortcut. Availability
  and wording vary by environment.

Pinning is deliberately manual. This project does not automatically change
dock/taskbar settings. Windows and macOS shortcut creation and packaging have
not been tested or documented as supported workflows.

## What Dash Browser includes

- HTTP(S) address navigation and web search using DuckDuckGo, Google, Bing, or
  a custom HTTPS search template.
- Back, forward, Home (the welcome/new-tab page), reload, stop, page zoom, and
  multi-tab browsing.
- A black welcome page with direct search/address entry and a locally generated
  green Devanagari character-rain effect. It does not display a clock or date.
- Bookmarks, browsing history, download prompts and controls, and persistent
  regular browsing storage.
- Dark and light themes, configurable search, and keyboard shortcuts.
- Elevated toolbar, tab, and form styling with a bookmark panel that adapts to
  window width.
- A bounded local ad/tracker request blocker, session-only website permissions,
  Clear Browsing Data controls, and disposable Tear Tab sessions.

Top-level navigation accepts HTTP and HTTPS only. Unsupported schemes such as
`javascript:`, `data:`, and `file:` are rejected as browser destinations.
History and bookmark records retain their relevant visit/creation timestamps;
only the unrelated clock/date displays and preference have been removed.

The built-in request blocker covers a small static set of domains. It is not a
full filter-list engine and does not provide phishing detection, malware
scanning, or guaranteed ad removal. Clearing browsing data does not erase all
origin storage, downloaded files, or records outside Dash Browser. Tear Tab is
not a guarantee of anonymity or forensic erasure. See
[KNOWN_LIMITATIONS.md](./KNOWN_LIMITATIONS.md), [PRIVACY.md](./PRIVACY.md),
[THREAT_MODEL.md](./THREAT_MODEL.md), and [SECURITY_AUDIT.md](./SECURITY_AUDIT.md).

## Keyboard shortcuts

| Shortcut | Action |
|---|---|
| `Ctrl+T` | New regular tab |
| `Ctrl+W` | Close active tab |
| `Ctrl+Tab` / `Ctrl+Shift+Tab` | Next / previous tab |
| `Ctrl+L` / `Alt+D` | Focus and select the address bar |
| `Ctrl+J` | Downloads |
| `Ctrl+B` | Toggle the bookmarks panel |
| `Ctrl+H` | History |
| `Ctrl+,` | Settings |
| `Ctrl+Shift+N` | Open a disposable Tear Tab session |
| `Ctrl++` / `Ctrl+-` | Zoom in / out |
| `Ctrl+0` | Reset page zoom |

## Build and test

From the repository root, use the virtual environment created by `run.sh`:

```bash
QT_QPA_PLATFORM=offscreen QTWEBENGINE_CHROMIUM_FLAGS=--disable-gpu \
  .venv/bin/python -m unittest discover -s tests -v
.venv/bin/python -m compileall -q browser tests main.py
.venv/bin/python -m pip install build
.venv/bin/python -m build
```

The build creates a source distribution and wheel in `dist/`. To build without
launching the app first, create the environment and install the project using
the manual setup commands above. The installable Python package is not a
self-contained operating-system installer; the host still provides its
graphical desktop and native runtime libraries.

CI runs the test suite, compile check, pinned direct-dependency audit, and
source/wheel build on Ubuntu 24.04. Its audit input is not a full lock file or
a security certification. Review [RELEASE_CHECKLIST.md](./RELEASE_CHECKLIST.md)
before distributing binaries.

## Troubleshooting

- **`python3 -m venv` fails:** install the Python virtual-environment package
  for your Linux distribution (`python3-venv` on Ubuntu), then run `./run.sh`
  again.
- **Qt reports that the `xcb` platform plugin cannot load:** install the Ubuntu
  libraries listed above, ensure a Qt-compatible graphical desktop session is
  running, and retry.
- **GNOME reports a missing `xsettings.antialiasing` key and the app aborts:**
  Dash Browser selects Qt's generic platform theme before startup because its
  interface already uses the Fusion style. If `QT_QPA_PLATFORMTHEME` is
  explicitly set to `gtk3` in your shell, unset it and retry:
  `unset QT_QPA_PLATFORMTHEME && ./run.sh`.
- **An existing `.venv` still uses Qt 6.11:** the launcher reruns setup when
  `pyproject.toml` changes. If needed, remove only the project-local `.venv`
  and run `./run.sh` again.
- **No window appears:** run `./run.sh` in a terminal so startup errors remain
  visible. Dash Browser requires a graphical session; it is not a headless
  command-line browser.
- **The shortcut command is missing:** run `./run.sh` once to complete
  installation, then run `.venv/bin/dash-browser-install-shortcut`.

## Project layout

```text
.
├── main.py                         Application entry point
├── pyproject.toml                  Dependencies, scripts, and build metadata
├── run.sh                          Linux first-run setup and application launcher
├── browser/
│   ├── main_window.py              Main window, tabs, shortcuts, and UI wiring
│   ├── browser_tab.py              WebEngine page/view and welcome page
│   ├── desktop.py                  Opt-in Linux application-menu shortcut
│   ├── navigation.py               Address and search URL validation
│   ├── settings.py                 Settings model and persistence
│   ├── storage.py                  Private atomic JSON storage helpers
│   ├── bookmarks.py                Bookmark validation and import/export
│   ├── history.py                  Bounded browsing-history storage
│   ├── downloads.py                Download prompt, progress, and controls
│   ├── dialogs.py                  Settings and browser management dialogs
│   ├── privacy.py                  Local request blocker and site validation
│   ├── tear_effect.py              Disposable-tab viewport animation
│   ├── constants.py                App labels and theme styling
│   └── assets/                     Dash Browser logo assets
└── tests/                          Standard-library unittest suite
```

The application command is `dash-browser`; the explicit Linux shortcut
installer command is `dash-browser-install-shortcut`. Both are declared in
`pyproject.toml` and require Python 3.10 or newer with PyQt6 and Qt WebEngine.
