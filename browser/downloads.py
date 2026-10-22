# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Atul Singh Chandel

"""Download destination validation and a small download-history dialog."""

from dataclasses import dataclass
from pathlib import Path

from PyQt6.QtCore import QUrl
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)
from PyQt6.QtWebEngineCore import QWebEngineDownloadRequest

from browser.settings import BrowserSettings

EXECUTABLE_SUFFIXES = {
    ".appimage",
    ".bat",
    ".cmd",
    ".com",
    ".deb",
    ".desktop",
    ".exe",
    ".jar",
    ".msi",
    ".ps1",
    ".py",
    ".rpm",
    ".scr",
    ".sh",
}


def safe_download_name(suggested_name: str) -> str:
    """Reduce an untrusted suggested download name to a safe basename."""
    name = suggested_name.replace("\\", "/").split("/")[-1]
    name = "".join(
        "_" if ord(character) < 32 or character in '<>:"|?*' else character
        for character in name
    ).strip(" .")
    if name in {"", ".", ".."}:
        return "download"
    if name.upper().split(".", 1)[0] in {
        "CON", "PRN", "AUX", "NUL", *(f"COM{i}" for i in range(1, 10)), *(f"LPT{i}" for i in range(1, 10))
    }:
        name = f"_{name}"
    return name[:240]


def nonconflicting_path(path: Path) -> Path:
    """Return a path that will not overwrite an existing file."""
    candidate = path
    index = 1
    while candidate.exists():
        candidate = path.with_name(f"{path.stem} ({index}){path.suffix}")
        index += 1
    return candidate


@dataclass
class DownloadRecord:
    request: QWebEngineDownloadRequest
    path: Path
    row: int


class DownloadManagerDialog(QDialog):
    """Show progress and user-initiated actions for downloads."""

    def __init__(self, settings: BrowserSettings, parent=None) -> None:
        super().__init__(parent)
        self.settings = settings
        self.setWindowTitle("Downloads")
        self.resize(720, 300)
        self._records: dict[int, DownloadRecord] = {}

        layout = QVBoxLayout(self)
        self.table = QTableWidget(0, 4, self)
        self.table.setHorizontalHeaderLabels(["File", "Status", "Progress", "Destination"])
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.table)

        actions = QHBoxLayout()
        self.cancel_button = QPushButton("Cancel", self)
        self.remove_button = QPushButton("Remove from list", self)
        self.open_button = QPushButton("Open file", self)
        self.folder_button = QPushButton("Open folder", self)
        for button in (
            self.cancel_button,
            self.remove_button,
            self.open_button,
            self.folder_button,
        ):
            actions.addWidget(button)
        layout.addLayout(actions)
        self.cancel_button.clicked.connect(self.cancel_selected)
        self.remove_button.clicked.connect(self.remove_selected)
        self.open_button.clicked.connect(self.open_selected)
        self.folder_button.clicked.connect(self.open_folder_selected)
        self.table.itemSelectionChanged.connect(self.update_actions)
        self.update_actions()

    @property
    def has_active_downloads(self) -> bool:
        return any(
            record.request.state() in {
                QWebEngineDownloadRequest.DownloadState.DownloadRequested,
                QWebEngineDownloadRequest.DownloadState.DownloadInProgress,
            }
            for record in self._records.values()
        )

    def start_download(self, request: QWebEngineDownloadRequest) -> None:
        """Prompt for a destination, then accept only the selected file path."""
        suggested = safe_download_name(request.downloadFileName())
        default_path = nonconflicting_path(Path(self.settings.download_directory) / suggested)
        destination, _ = QFileDialog.getSaveFileName(
            self, "Save download", str(default_path), "All files (*)"
        )
        if not destination:
            request.cancel()
            return

        path = nonconflicting_path(Path(destination).expanduser())
        if path.suffix.lower() in EXECUTABLE_SUFFIXES:
            answer = QMessageBox.warning(
                self,
                "Potentially executable download",
                "This file type may run code. Dash Browser will not open it automatically. "
                "Continue downloading?",
                QMessageBox.StandardButton.Download | QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Cancel,
            )
            if answer != QMessageBox.StandardButton.Download:
                request.cancel()
                return

        try:
            path.parent.mkdir(parents=True, exist_ok=True)
        except OSError as error:
            QMessageBox.critical(self, "Download error", f"Could not use that folder: {error}")
            request.cancel()
            return

        request.setDownloadDirectory(str(path.parent.resolve()))
        request.setDownloadFileName(path.name)
        row = self.table.rowCount()
        self.table.insertRow(row)
        self.table.setItem(row, 0, QTableWidgetItem(path.name))
        self.table.setItem(row, 1, QTableWidgetItem("Starting"))
        self.table.setItem(row, 2, QTableWidgetItem("0%"))
        self.table.setItem(row, 3, QTableWidgetItem(str(path.parent)))
        self._records[id(request)] = DownloadRecord(request, path, row)
        request.receivedBytesChanged.connect(lambda key=id(request): self.update_progress(key))
        request.totalBytesChanged.connect(lambda key=id(request): self.update_progress(key))
        request.stateChanged.connect(lambda _state, key=id(request): self.update_state(key))
        request.accept()
        self.update_state(id(request))
        self.update_actions()

    def _selected_record(self) -> DownloadRecord | None:
        rows = self.table.selectionModel().selectedRows()
        if not rows:
            return None
        selected_row = rows[0].row()
        return next(
            (record for record in self._records.values() if record.row == selected_row),
            None,
        )

    def update_progress(self, key: int) -> None:
        record = self._records.get(key)
        if record is None:
            return
        received, total = record.request.receivedBytes(), record.request.totalBytes()
        progress = f"{received:,} bytes" if total <= 0 else f"{min(100, received * 100 // total)}%"
        self.table.item(record.row, 2).setText(progress)

    def update_state(self, key: int) -> None:
        record = self._records.get(key)
        if record is None:
            return
        state = record.request.state()
        status = {
            QWebEngineDownloadRequest.DownloadState.DownloadRequested: "Starting",
            QWebEngineDownloadRequest.DownloadState.DownloadInProgress: "Downloading",
            QWebEngineDownloadRequest.DownloadState.DownloadCompleted: "Completed",
            QWebEngineDownloadRequest.DownloadState.DownloadCancelled: "Cancelled",
            QWebEngineDownloadRequest.DownloadState.DownloadInterrupted: "Interrupted",
        }.get(state, "Unknown")
        self.table.item(record.row, 1).setText(status)
        if state == QWebEngineDownloadRequest.DownloadState.DownloadCompleted:
            self.table.item(record.row, 2).setText(
                f"{record.request.receivedBytes():,} bytes — not scanned for malware"
            )
        self.update_actions()

    def update_actions(self) -> None:
        record = self._selected_record()
        state = record.request.state() if record else None
        active = state in {
            QWebEngineDownloadRequest.DownloadState.DownloadRequested,
            QWebEngineDownloadRequest.DownloadState.DownloadInProgress,
        }
        complete = state == QWebEngineDownloadRequest.DownloadState.DownloadCompleted
        self.cancel_button.setEnabled(active)
        self.remove_button.setEnabled(record is not None and not active)
        self.open_button.setEnabled(complete and record.path.is_file())
        self.folder_button.setEnabled(complete and record.path.parent.is_dir())

    def cancel_selected(self) -> None:
        record = self._selected_record()
        if record:
            record.request.cancel()

    def cancel_active_downloads(self) -> None:
        for record in tuple(self._records.values()):
            if record.request.state() in {
                QWebEngineDownloadRequest.DownloadState.DownloadRequested,
                QWebEngineDownloadRequest.DownloadState.DownloadInProgress,
            }:
                record.request.cancel()

    def remove_selected(self) -> None:
        record = self._selected_record()
        if record is None or record.request.state() in {
            QWebEngineDownloadRequest.DownloadState.DownloadRequested,
            QWebEngineDownloadRequest.DownloadState.DownloadInProgress,
        }:
            return
        self.table.removeRow(record.row)
        self._records.pop(id(record.request), None)
        for item in self._records.values():
            if item.row > record.row:
                item.row -= 1
        self.update_actions()

    def open_selected(self) -> None:
        record = self._selected_record()
        if record and record.request.state() == QWebEngineDownloadRequest.DownloadState.DownloadCompleted:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(record.path)))

    def open_folder_selected(self) -> None:
        record = self._selected_record()
        if record and record.request.state() == QWebEngineDownloadRequest.DownloadState.DownloadCompleted:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(record.path.parent)))
