# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Atul Singh Chandel

"""Opt-in installation of a per-user Linux application-menu entry."""

import os
from pathlib import Path
import sys

from browser.constants import APP_NAME


def _desktop_exec_argument(value: str) -> str:
    escaped = (
        value.replace("\\", "\\\\")
        .replace('"', '\\"')
        .replace("`", "\\`")
        .replace("$", "\\$")
    )
    return f'"{escaped}"'


def install_desktop_entry(
    data_home: Path | None = None,
    python_executable: str | None = None,
) -> Path:
    """Create a user-level launcher; never writes outside the XDG data home."""
    if not sys.platform.startswith("linux"):
        raise RuntimeError(
            "Shortcut installation is currently supported on Linux only."
        )

    if data_home is None:
        configured_data_home = os.environ.get("XDG_DATA_HOME")
        candidate = (
            Path(configured_data_home).expanduser()
            if configured_data_home
            else Path.home() / ".local" / "share"
        )
        data_home = (
            candidate
            if candidate.is_absolute()
            else Path.home() / ".local" / "share"
        )

    applications_directory = data_home / "applications"
    icons_directory = data_home / "icons" / "hicolor" / "scalable" / "apps"
    applications_directory.mkdir(parents=True, exist_ok=True)
    icons_directory.mkdir(parents=True, exist_ok=True)

    icon_source = Path(__file__).parent / "assets" / "dash-logo.svg"
    icon_path = icons_directory / "dash-browser.svg"
    icon_path.write_bytes(icon_source.read_bytes())

    executable = python_executable or sys.executable
    entry_path = applications_directory / "dash-browser.desktop"
    main_script = Path(__file__).resolve().parent.parent / "main.py"
    entry = "\n".join(
        (
            "[Desktop Entry]",
            "Version=1.0",
            "Type=Application",
            f"Name={APP_NAME}",
            "Comment=Browse the web with Dash Browser",
            f"Exec={_desktop_exec_argument(executable)} "
            f"{_desktop_exec_argument(str(main_script))}",
            "Icon=dash-browser",
            "Terminal=false",
            "Categories=Network;WebBrowser;",
            "StartupNotify=true",
            "",
        )
    )
    entry_path.write_text(entry, encoding="utf-8")
    return entry_path


def install_shortcut_main() -> int:
    """CLI entry point for the explicit shortcut-install command."""
    try:
        entry_path = install_desktop_entry()
    except (OSError, RuntimeError) as error:
        print(
            "Could not install the Dash Browser application-menu shortcut: "
            f"{error}",
            file=sys.stderr,
        )
        return 1
    print(f"Installed the Dash Browser application-menu shortcut: {entry_path}")
    print("Pin Dash Browser to your dock or taskbar using your desktop environment.")
    return 0
