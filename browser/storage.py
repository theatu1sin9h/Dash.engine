# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Atul Singh Chandel

"""Small atomic JSON storage helpers for browser-owned state."""

import json
import logging
import os
import tempfile
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)
MAX_JSON_BYTES = 5 * 1024 * 1024


def data_directory() -> Path:
    """Return the per-user Dash data directory, creating it privately."""
    root = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    directory = root / "dash-browser"
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    try:
        directory.chmod(0o700)
    except OSError:
        logger.warning("Could not restrict permissions on the browser data directory")
    return directory


def config_directory() -> Path:
    """Return the per-user Dash settings directory, creating it privately."""
    root = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    directory = root / "dash-browser"
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    try:
        directory.chmod(0o700)
    except OSError:
        logger.warning("Could not restrict permissions on the browser settings directory")
    return directory


def read_json(path: Path) -> Any:
    """Read bounded JSON data; malformed or oversized files are rejected."""
    if path.stat().st_size > MAX_JSON_BYTES:
        raise ValueError(f"{path.name} exceeds the permitted size")
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def write_json_atomic(path: Path, value: Any) -> None:
    """Replace a JSON file atomically, restricting its permissions."""
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    temporary_path = None
    try:
        with tempfile.NamedTemporaryFile(
            "w", encoding="utf-8", dir=path.parent, prefix=f".{path.name}.", delete=False
        ) as file:
            temporary_path = Path(file.name)
            os.chmod(file.name, 0o600)
            json.dump(value, file, ensure_ascii=False, indent=2)
            file.write("\n")
            file.flush()
            os.fsync(file.fileno())
        os.replace(temporary_path, path)
    except OSError:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)
        logger.exception("Could not save browser data file %s", path.name)
        raise
