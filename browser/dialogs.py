# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Atul Singh Chandel

"""Native dialogs for bookmark management and browser settings."""

from collections.abc import Callable
from datetime import datetime
from pathlib import Path

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QColorDialog,
    QDialog,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QMessageBox,
    QPushButton,
    QPlainTextEdit,
    QScrollArea,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)
from PyQt6.QtWebEngineCore import QWebEngineProfile

from browser.bookmarks import Bookmark, BookmarkStore
from browser.browser_tab import MAX_WALLPAPER_BYTES, _wallpaper_data_uri
from browser.history import HistoryEntry, HistoryStore
from browser.privacy import normalize_site
from browser.settings import (
    MAX_CUSTOM_SEARCH_ENGINES,
    SEARCH_ENGINES,
    BrowserSettings,
    validate_search_engine,
)


class SitePermissionsDialog(QDialog):
    """Review and revoke in-memory website permissions."""

    def __init__(self, profile: QWebEngineProfile, parent=None) -> None:
        super().__init__(parent)
        self.profile = profile
        self._permissions = []
        self.setWindowTitle("Site permissions")
        self.resize(640, 380)

        layout = QVBoxLayout(self)
        layout.addWidget(
            QLabel(
                "Dash asks before granting camera, microphone, location, "
                "notifications, or other supported site permissions. "
                "Choices last only until Dash closes.",
                self,
            )
        )
        self.table = QTableWidget(0, 3, self)
        self.table.setHorizontalHeaderLabels(["Website", "Permission", "Decision"])
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.table)

        actions = QHBoxLayout()
        self.revoke_button = QPushButton("Revoke selected", self)
        self.revoke_all_button = QPushButton("Revoke all", self)
        close = QPushButton("Close", self)
        actions.addWidget(self.revoke_button)
        actions.addWidget(self.revoke_all_button)
        actions.addStretch(1)
        actions.addWidget(close)
        layout.addLayout(actions)
        self.revoke_button.clicked.connect(self.revoke_selected)
        self.revoke_all_button.clicked.connect(self.revoke_all)
        close.clicked.connect(self.accept)
        self.table.itemSelectionChanged.connect(self.update_actions)
        self.refresh()

    def refresh(self) -> None:
        self._permissions = [
            permission
            for permission in self.profile.listAllPermissions()
            if permission.isValid()
        ]
        self.table.setRowCount(0)
        for permission in self._permissions:
            row = self.table.rowCount()
            self.table.insertRow(row)
            decision = permission.state().name.title()
            values = (
                permission.origin().toDisplayString(),
                permission.permissionType().name,
                decision,
            )
            for column, value in enumerate(values):
                self.table.setItem(row, column, QTableWidgetItem(value))
        self.update_actions()

    def update_actions(self) -> None:
        self.revoke_button.setEnabled(bool(self.table.selectionModel().selectedRows()))
        self.revoke_all_button.setEnabled(bool(self._permissions))

    def revoke_selected(self) -> None:
        for index in sorted(
            (item.row() for item in self.table.selectionModel().selectedRows()),
            reverse=True,
        ):
            self._permissions[index].reset()
        self.refresh()

    def revoke_all(self) -> None:
        for permission in self._permissions:
            permission.reset()
        self.refresh()


class ClearBrowsingDataDialog(QDialog):
    """Choose supported browser data to clear from the persistent profile."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Clear browsing data")
        layout = QVBoxLayout(self)
        layout.addWidget(
            QLabel(
                "Choose what Dash should clear from the regular browser profile. "
                "This does not close tabs or delete downloaded files.",
                self,
            )
        )
        self.history = QCheckBox("Browsing history", self)
        self.cookies = QCheckBox("Cookies (may sign you out of websites)", self)
        self.cache = QCheckBox("Cached web files", self)
        self.permissions = QCheckBox("Saved site-permission decisions", self)
        for checkbox in (self.history, self.cookies, self.cache, self.permissions):
            checkbox.setChecked(True)
            layout.addWidget(checkbox)
        layout.addWidget(
            QLabel(
                "Qt WebEngine does not expose a safe all-sites control for local "
                "storage or service-worker data while this profile is running; "
                "those site data are not included.",
                self,
            )
        )
        actions = QHBoxLayout()
        actions.addStretch(1)
        cancel = QPushButton("Cancel", self)
        self.clear_button = QPushButton("Clear selected data", self)
        cancel.clicked.connect(self.reject)
        self.clear_button.clicked.connect(self.accept)
        actions.addWidget(cancel)
        actions.addWidget(self.clear_button)
        layout.addLayout(actions)

    def selected_data(self) -> frozenset[str]:
        selected = set()
        for key, checkbox in (
            ("history", self.history),
            ("cookies", self.cookies),
            ("cache", self.cache),
            ("permissions", self.permissions),
        ):
            if checkbox.isChecked():
                selected.add(key)
        return frozenset(selected)


class HistoryDialog(QDialog):
    """Show recent pages and let the user reopen or clear history."""

    def __init__(
        self, store: HistoryStore, open_url: Callable[[str], None], parent=None
    ) -> None:
        super().__init__(parent)
        self.store = store
        self.open_url = open_url
        self.setWindowTitle("History")
        self.resize(860, 480)
        self._visible_entries: tuple[HistoryEntry, ...] = ()

        layout = QVBoxLayout(self)
        self.search = QLineEdit(self)
        self.search.setPlaceholderText("Search history")
        self.search.textChanged.connect(self.refresh)
        layout.addWidget(self.search)

        self.table = QTableWidget(0, 3, self)
        self.table.setHorizontalHeaderLabels(["Visited", "Page", "Address"])
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.itemDoubleClicked.connect(self.open_selected)
        layout.addWidget(self.table)

        self.summary = QLabel(self)
        layout.addWidget(self.summary)

        actions = QHBoxLayout()
        self.open_button = QPushButton("Open", self)
        self.delete_button = QPushButton("Delete selected", self)
        self.clear_button = QPushButton("Clear all history", self)
        close_button = QPushButton("Close", self)
        for button in (self.open_button, self.delete_button, self.clear_button, close_button):
            actions.addWidget(button)
        layout.addLayout(actions)
        self.open_button.clicked.connect(self.open_selected)
        self.delete_button.clicked.connect(self.delete_selected)
        self.clear_button.clicked.connect(self.clear_history)
        close_button.clicked.connect(self.accept)
        self.table.itemSelectionChanged.connect(self.update_actions)
        self.refresh()

    def refresh(self, _query: str = "") -> None:
        self.table.setRowCount(0)
        query = self.search.text().strip().casefold()
        self._visible_entries = tuple(
            entry for entry in self.store.entries
            if not query or query in entry.title.casefold() or query in entry.url.casefold()
        )
        for entry in self._visible_entries:
            row = self.table.rowCount()
            self.table.insertRow(row)
            visited = datetime.fromisoformat(
                entry.visited_at.replace("Z", "+00:00")
            ).astimezone().strftime("%Y-%m-%d %H:%M")
            for column, text in enumerate((visited, entry.title, entry.url)):
                self.table.setItem(row, column, QTableWidgetItem(text))
        self.summary.setText(f"{len(self._visible_entries)} of {len(self.store.entries)} visits")
        self.update_actions()

    def selected_entries(self) -> tuple[HistoryEntry, ...]:
        return tuple(
            self._visible_entries[index.row()]
            for index in self.table.selectionModel().selectedRows()
        )

    def update_actions(self) -> None:
        selected = self.selected_entries()
        self.open_button.setEnabled(len(selected) == 1)
        self.delete_button.setEnabled(bool(selected))
        self.clear_button.setEnabled(bool(self.store.entries))

    def open_selected(self, *_args) -> None:
        selected = self.selected_entries()
        if len(selected) == 1:
            self.open_url(selected[0].url)
            self.accept()

    def delete_selected(self) -> None:
        entries = self.selected_entries()
        if not entries:
            return
        answer = QMessageBox.question(
            self,
            "Delete selected history",
            f"Delete {len(entries)} selected visit(s)?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        try:
            removed = self.store.remove_entries(entries)
        except OSError as error:
            QMessageBox.critical(self, "History error", f"Could not delete selected history: {error}")
            return
        self.refresh()
        self.summary.setText(f"Deleted {removed} visit(s). {len(self.store.entries)} remain.")

    def clear_history(self) -> None:
        answer = QMessageBox.question(
            self,
            "Clear history",
            "Remove all browsing history?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        try:
            self.store.clear()
        except OSError as error:
            QMessageBox.critical(self, "History error", f"Could not clear history: {error}")
            return
        self.refresh()
        self.summary.setText("All browsing history cleared.")


class PrivacyPolicyDialog(QDialog):
    """Explain Dash's local data handling and its privacy limitations."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Dash Privacy Policy")
        self.resize(620, 480)
        layout = QVBoxLayout(self)
        policy = QPlainTextEdit(self)
        policy.setReadOnly(True)
        policy.setPlainText(
            "DASH PRIVACY POLICY\n\n"
            "Dash stores browser data on this device. Ordinary browsing history, "
            "bookmarks, settings, cookies, and cache are stored locally in your "
            "user profile. Dash does not send this stored data to a Dash analytics "
            "or account service.\n\n"
            "When you visit a website or use a search engine, that provider and "
            "the network services needed to connect may receive your request, "
            "including your IP address and the information you submit. Their "
            "privacy practices are separate from Dash.\n\n"
            "Tear Tab uses a temporary, off-the-record Qt WebEngine profile. "
            "Dash does not add its visits to ordinary Dash history and discards "
            "the profile when its tabs close. This is not a promise of forensic "
            "erasure or anonymity: websites, network operators, and downloaded "
            "files can retain information independently.\n\n"
            "Downloads are saved where you choose and are not removed when "
            "history or the temporary tab is cleared. Dash does not scan "
            "downloaded files for malware.\n\n"
            "Dash blocks third-party requests to a small built-in set of known "
            "ad and tracker domains when blocking is enabled. This is not a "
            "comprehensive filter list; ads may still appear. You can pause "
            "blocking for selected sites in the Privacy dashboard. Site permission "
            "requests are prompted for and decisions last only until Dash closes.\n\n"
            "Web traffic uses the operating system's configured network.\n\n"
            "Settings can clear Dash history, cookies, cached web files, and "
            "in-memory permission decisions from the regular profile. Qt "
            "WebEngine does not expose a safe all-sites local-storage or "
            "service-worker wipe while that profile is running, so those site "
            "data are not cleared by this control. Downloaded files remain. "
            "Permission grants are kept in memory only and are discarded when "
            "Dash closes.\n\n"
            "Keep Qt WebEngine and your operating system updated. "
            "This policy describes the current application behavior."
        )
        layout.addWidget(policy)
        close = QPushButton("Close", self)
        close.clicked.connect(self.accept)
        layout.addWidget(close)


class SettingsDialog(QDialog):
    """Edit the settings currently implemented by Dash Browser."""

    manageSitePermissions = pyqtSignal()
    clearBrowsingData = pyqtSignal()
    openPrivacyDashboard = pyqtSignal()

    def __init__(self, settings: BrowserSettings, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Dash Browser Settings")
        self.resize(640, 680)
        self.custom_search_engines = dict(settings.custom_search_engines or {})

        dialog_layout = QVBoxLayout(self)
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        content = QWidget(scroll)
        dialog_layout.addWidget(scroll, 1)
        layout = QVBoxLayout(content)
        scroll.setWidget(content)
        form = QFormLayout()
        self.theme = QComboBox(self)
        self.theme.addItem("Dark", "dark")
        self.theme.addItem("Light", "light")
        self.theme.setCurrentIndex(self.theme.findData(settings.theme))
        form.addRow("Appearance", self.theme)

        self.search_engine = QComboBox(self)
        self.search_engine.addItems([*SEARCH_ENGINES, *self.custom_search_engines])
        self.search_engine.setCurrentText(settings.search_engine)
        form.addRow("Search engine", self.search_engine)

        download_row = QHBoxLayout()
        self.download_directory = QLineEdit(settings.download_directory, self)
        browse = QPushButton("Choose…", self)
        browse.clicked.connect(self.choose_download_directory)
        download_row.addWidget(self.download_directory)
        download_row.addWidget(browse)
        form.addRow("Download folder", download_row)

        self.bookmarks_bar = QCheckBox("Show bookmarks bar", self)
        self.bookmarks_bar.setChecked(settings.show_bookmarks_bar)
        form.addRow("", self.bookmarks_bar)

        self.new_tab_background = QComboBox(self)
        self.new_tab_background.addItem("Built-in ambient background", "ambient")
        self.new_tab_background.addItem("Single color", "solid")
        self.new_tab_background.addItem("Two-color gradient", "gradient")
        self.new_tab_background.addItem("Wallpaper image", "image")
        self.new_tab_background.setCurrentIndex(
            self.new_tab_background.findData(settings.new_tab_background)
        )
        form.addRow("New-tab background", self.new_tab_background)

        self.solid_color = QLineEdit(settings.new_tab_solid_color, self)
        self.solid_color_row = self._color_row(self.solid_color, "Choose color…")
        form.addRow("Background color", self.solid_color_row)
        self.solid_color_label = form.labelForField(self.solid_color_row)

        self.gradient_start = QLineEdit(settings.new_tab_gradient_start, self)
        self.gradient_start_row = self._color_row(
            self.gradient_start, "Choose first…"
        )
        form.addRow("Gradient start", self.gradient_start_row)
        self.gradient_start_label = form.labelForField(self.gradient_start_row)
        self.gradient_end = QLineEdit(settings.new_tab_gradient_end, self)
        self.gradient_end_row = self._color_row(self.gradient_end, "Choose second…")
        form.addRow("Gradient end", self.gradient_end_row)
        self.gradient_end_label = form.labelForField(self.gradient_end_row)

        wallpaper_row = QHBoxLayout()
        self.wallpaper_path = QLineEdit(settings.new_tab_wallpaper, self)
        self.wallpaper_path.setReadOnly(True)
        self.wallpaper_path.setPlaceholderText("Choose PNG, JPEG, WebP, or BMP (up to 5 MiB)")
        self.wallpaper_button = QPushButton("Choose image…", self)
        self.wallpaper_button.clicked.connect(self.choose_wallpaper)
        wallpaper_row.addWidget(self.wallpaper_path, 1)
        wallpaper_row.addWidget(self.wallpaper_button)
        self.wallpaper_row = QWidget(self)
        self.wallpaper_row.setLayout(wallpaper_row)
        form.addRow("Wallpaper", self.wallpaper_row)
        self.wallpaper_label = form.labelForField(self.wallpaper_row)
        self.new_tab_background.currentIndexChanged.connect(
            self.update_background_controls
        )
        self.update_background_controls()

        self.ad_blocking = QCheckBox("Block known third-party ad/tracker domains", self)
        self.ad_blocking.setChecked(settings.ad_blocking_enabled)
        form.addRow("", self.ad_blocking)
        layout.addLayout(form)

        layout.addWidget(QLabel("Ad-blocker allowlist (one website host per line):", self))
        self.ad_allowlist = QPlainTextEdit(self)
        self.ad_allowlist.setMaximumHeight(84)
        self.ad_allowlist.setPlainText("\n".join(settings.ad_allowlist))
        layout.addWidget(self.ad_allowlist)
        layout.addWidget(
            QLabel(
                "Blocking uses a small built-in list of known third-party domains. "
                "It is not a full filter-list engine and does not block every ad.",
                self,
                wordWrap=True,
            )
        )

        layout.addWidget(QLabel("Add a search engine (use {query} in its HTTPS URL):", self))
        engine_form = QFormLayout()
        self.engine_name = QLineEdit(self)
        self.engine_template = QLineEdit(self)
        self.engine_template.setPlaceholderText("https://example.com/search?q={query}")
        engine_form.addRow("Name", self.engine_name)
        engine_form.addRow("Search URL", self.engine_template)
        layout.addLayout(engine_form)
        engine_actions = QHBoxLayout()
        self.add_engine_button = QPushButton("Add / update", self)
        self.remove_engine_button = QPushButton("Remove custom engine", self)
        self.engine_status = QLabel(self)
        engine_actions.addWidget(self.add_engine_button)
        engine_actions.addWidget(self.remove_engine_button)
        engine_actions.addWidget(self.engine_status, 1)
        layout.addLayout(engine_actions)
        self.search_engine.currentTextChanged.connect(self.load_selected_engine)
        self.add_engine_button.clicked.connect(self.add_search_engine)
        self.remove_engine_button.clicked.connect(self.remove_search_engine)
        self.load_selected_engine(settings.search_engine)

        data_actions = QHBoxLayout()
        self.permissions_button = QPushButton("Site permissions…", self)
        self.clear_data_button = QPushButton("Clear browsing data…", self)
        self.privacy_dashboard_button = QPushButton("Privacy dashboard…", self)
        self.permissions_button.clicked.connect(self.manageSitePermissions)
        self.clear_data_button.clicked.connect(self.clearBrowsingData)
        self.privacy_dashboard_button.clicked.connect(self.openPrivacyDashboard)
        data_actions.addWidget(self.permissions_button)
        data_actions.addWidget(self.clear_data_button)
        data_actions.addWidget(self.privacy_dashboard_button)
        data_actions.addStretch(1)
        layout.addLayout(data_actions)
        layout.addWidget(
            QLabel(
                "Site decisions last until Dash closes. Clearing data does not "
                "remove local storage, service workers, or downloaded files.",
                self,
            )
        )

        actions = QHBoxLayout()
        actions.addStretch()
        cancel = QPushButton("Cancel", self)
        save = QPushButton("Save", self)
        privacy = QPushButton("Privacy policy", self)
        cancel.clicked.connect(self.reject)
        save.clicked.connect(self.accept)
        privacy.clicked.connect(lambda: PrivacyPolicyDialog(self).exec())
        actions.addWidget(privacy)
        actions.addWidget(cancel)
        actions.addWidget(save)
        dialog_layout.addLayout(actions)

    def _color_row(self, field: QLineEdit, button_text: str) -> QWidget:
        row = QHBoxLayout()
        choose = QPushButton(button_text, self)
        choose.clicked.connect(lambda: self.choose_color(field))
        row.addWidget(field, 1)
        row.addWidget(choose)
        container = QWidget(self)
        container.setLayout(row)
        return container

    def choose_color(self, field: QLineEdit) -> None:
        from PyQt6.QtGui import QColor

        color = QColorDialog.getColor(QColor(field.text()), self)
        if color.isValid():
            field.setText(color.name())

    def choose_wallpaper(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Choose new-tab wallpaper",
            self.wallpaper_path.text(),
            "Images (*.png *.jpg *.jpeg *.webp *.bmp)",
        )
        if not path:
            return
        try:
            if Path(path).stat().st_size > MAX_WALLPAPER_BYTES:
                raise ValueError("Choose an image no larger than 5 MiB.")
        except OSError as error:
            QMessageBox.warning(self, "Wallpaper error", f"Could not read the image: {error}")
            return
        if not _wallpaper_data_uri(path):
            QMessageBox.warning(
                self,
                "Wallpaper error",
                "Choose a valid PNG, JPEG, WebP, or BMP image up to 5 MiB "
                "and 24 megapixels. Dash optimizes it for the new-tab page.",
            )
            return
        self.wallpaper_path.setText(path)

    def update_background_controls(self, _index: int = -1) -> None:
        mode = self.new_tab_background.currentData()
        self.solid_color_row.setVisible(mode == "solid")
        self.solid_color_label.setVisible(mode == "solid")
        self.gradient_start_row.setVisible(mode == "gradient")
        self.gradient_start_label.setVisible(mode == "gradient")
        self.gradient_end_row.setVisible(mode == "gradient")
        self.gradient_end_label.setVisible(mode == "gradient")
        self.wallpaper_row.setVisible(mode == "image")
        self.wallpaper_label.setVisible(mode == "image")

    def load_selected_engine(self, name: str) -> None:
        self.engine_name.setText(name)
        template = self.custom_search_engines.get(name, SEARCH_ENGINES.get(name, ""))
        self.engine_template.setText(template)
        self.remove_engine_button.setEnabled(name in self.custom_search_engines)

    def add_search_engine(self) -> None:
        try:
            name, template = validate_search_engine(
                self.engine_name.text(), self.engine_template.text()
            )
        except ValueError as error:
            self.engine_status.setText(str(error))
            return
        if name not in self.custom_search_engines and len(self.custom_search_engines) >= MAX_CUSTOM_SEARCH_ENGINES:
            self.engine_status.setText("Custom search engine limit reached.")
            return
        self.custom_search_engines[name] = template
        if name not in [self.search_engine.itemText(i) for i in range(self.search_engine.count())]:
            self.search_engine.addItem(name)
        self.search_engine.setCurrentText(name)
        self.engine_status.setText("Search engine saved in settings.")

    def remove_search_engine(self) -> None:
        name = self.search_engine.currentText()
        if name not in self.custom_search_engines:
            return
        del self.custom_search_engines[name]
        self.search_engine.removeItem(self.search_engine.findText(name))
        if self.search_engine.currentText() == name or self.search_engine.count() == 0:
            self.search_engine.setCurrentText("DuckDuckGo")
        self.load_selected_engine(self.search_engine.currentText())
        self.engine_status.setText("Custom search engine removed.")

    def choose_download_directory(self) -> None:
        path = QFileDialog.getExistingDirectory(
            self, "Choose download folder", self.download_directory.text()
        )
        if path:
            self.download_directory.setText(path)

    def updated_settings(self, _existing: BrowserSettings) -> BrowserSettings:
        path = Path(self.download_directory.text()).expanduser()
        if not path.is_absolute():
            raise ValueError("Choose an absolute download folder.")
        from PyQt6.QtGui import QColor

        colors = {
            "New-tab color": self.solid_color.text(),
            "Gradient start": self.gradient_start.text(),
            "Gradient end": self.gradient_end.text(),
        }
        if any(not QColor(value).isValid() for value in colors.values()):
            invalid = next(
                label for label, value in colors.items() if not QColor(value).isValid()
            )
            raise ValueError(f"{invalid} must be a valid color.")
        return BrowserSettings(
            search_engine=self.search_engine.currentText(),
            download_directory=str(path),
            show_bookmarks_bar=self.bookmarks_bar.isChecked(),
            theme=self.theme.currentData(),
            custom_search_engines=self.custom_search_engines,
            ad_blocking_enabled=self.ad_blocking.isChecked(),
            ad_allowlist=self.ad_allowlist.toPlainText().splitlines(),
            new_tab_background=self.new_tab_background.currentData(),
            new_tab_solid_color=QColor(self.solid_color.text()).name(),
            new_tab_gradient_start=QColor(self.gradient_start.text()).name(),
            new_tab_gradient_end=QColor(self.gradient_end.text()).name(),
            new_tab_wallpaper=self.wallpaper_path.text(),
        )


class PrivacyDashboardDialog(QDialog):
    """Show controls for implemented privacy features."""

    settingsChanged = pyqtSignal(bool, list)

    def __init__(
        self,
        settings: BrowserSettings,
        blocker,
        current_site: str,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.settings = settings
        self.blocker = blocker
        self.current_site = current_site
        self.setWindowTitle("Privacy dashboard")
        self.resize(540, 500)

        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        layout.addWidget(QLabel("AD AND TRACKER REQUEST BLOCKING", self))
        self.blocking_toggle = QCheckBox(
            "Block the built-in set of known third-party domains", self
        )
        self.blocking_toggle.setChecked(settings.ad_blocking_enabled)
        layout.addWidget(self.blocking_toggle)
        self.current_site_toggle = QCheckBox(
            f"Pause blocking for {current_site}" if current_site else
            "Open an HTTP(S) website to manage its protection",
            self,
        )
        self.current_site_toggle.setEnabled(bool(current_site))
        self.current_site_toggle.setChecked(
            bool(current_site and self._site_is_allowlisted(current_site))
        )
        layout.addWidget(self.current_site_toggle)
        self.blocked_counts = QLabel(self)
        layout.addWidget(self.blocked_counts)
        self.filter_status = QLabel(
            "Built-in local list: 12 known domains. No remote filter-list updates; "
            "coverage is limited and ads may still appear."
        )
        self.filter_status.setWordWrap(True)
        layout.addWidget(self.filter_status)

        allowlist_row = QHBoxLayout()
        self.allowlist_entry = QLineEdit(self)
        self.allowlist_entry.setPlaceholderText("example.com")
        self.add_allowlist_button = QPushButton("Allow site", self)
        allowlist_row.addWidget(self.allowlist_entry, 1)
        allowlist_row.addWidget(self.add_allowlist_button)
        layout.addLayout(allowlist_row)
        self.allowlist = QListWidget(self)
        self.allowlist.addItems(settings.ad_allowlist)
        self.allowlist.setMaximumHeight(100)
        layout.addWidget(self.allowlist)
        remove_row = QHBoxLayout()
        self.remove_allowlist_button = QPushButton("Remove selected site", self)
        self.remove_allowlist_button.setEnabled(False)
        remove_row.addWidget(self.remove_allowlist_button)
        self.restore_defaults_button = QPushButton("Restore defaults", self)
        remove_row.addWidget(self.restore_defaults_button)
        remove_row.addStretch(1)
        layout.addLayout(remove_row)

        close_button = QPushButton("Close", self)
        close_button.clicked.connect(self.accept)
        layout.addWidget(close_button)

        self.blocking_toggle.toggled.connect(self._emit_settings)
        self.current_site_toggle.toggled.connect(self._toggle_current_site)
        self.add_allowlist_button.clicked.connect(self.add_site)
        self.allowlist_entry.returnPressed.connect(self.add_site)
        self.remove_allowlist_button.clicked.connect(self.remove_selected_site)
        self.restore_defaults_button.clicked.connect(self.restore_defaults)
        self.allowlist.itemSelectionChanged.connect(
            lambda: self.remove_allowlist_button.setEnabled(
                self.allowlist.currentItem() is not None
            )
        )
        self.blocker.countsChanged.connect(self.update_counts)
        self.update_counts(self.blocker.ads_blocked, self.blocker.trackers_blocked)

    def _site_is_allowlisted(self, site: str) -> bool:
        entries = (
            self._allowlist_values()
            if hasattr(self, "allowlist")
            else self.settings.ad_allowlist
        )
        return any(
            site == allowed or site.endswith(f".{allowed}")
            for allowed in entries
        )

    def _sync_current_site_toggle(self) -> None:
        if self.current_site:
            self.current_site_toggle.setChecked(
                self._site_is_allowlisted(self.current_site)
            )

    def _emit_settings(self, *_args) -> None:
        self.settingsChanged.emit(
            self.blocking_toggle.isChecked(), self._allowlist_values()
        )

    def _allowlist_values(self) -> list[str]:
        return [self.allowlist.item(i).text() for i in range(self.allowlist.count())]

    def _toggle_current_site(self, allow: bool) -> None:
        if not self.current_site:
            return
        covering_entries = [
            index
            for index in range(self.allowlist.count())
            if self.current_site == self.allowlist.item(index).text()
            or self.current_site.endswith(f".{self.allowlist.item(index).text()}")
        ]
        if allow and not covering_entries:
            self.allowlist.addItem(self.current_site)
        elif not allow:
            for index in reversed(covering_entries):
                self.allowlist.takeItem(index)
        self._emit_settings()

    def add_site(self) -> None:
        try:
            host = normalize_site(self.allowlist_entry.text())
        except (ValueError, UnicodeError) as error:
            QMessageBox.warning(self, "Website allowlist", str(error))
            return
        if host not in self._allowlist_values():
            self.allowlist.addItem(host)
            self._emit_settings()
        self._sync_current_site_toggle()
        self.allowlist_entry.clear()

    def remove_selected_site(self) -> None:
        row = self.allowlist.currentRow()
        if row >= 0:
            removed = self.allowlist.takeItem(row).text()
            self._emit_settings()
            self._sync_current_site_toggle()

    def restore_defaults(self) -> None:
        self.allowlist.clear()
        self.blocking_toggle.setChecked(True)
        self._sync_current_site_toggle()
        self._emit_settings()

    def update_counts(self, ads: int, trackers: int) -> None:
        self.blocked_counts.setText(
            f"Regular-profile requests blocked this session: "
            f"{ads} ad, {trackers} tracker"
        )


class BookmarkManagerDialog(QDialog):
    """List, remove, import, and export bookmarks."""

    def __init__(self, store: BookmarkStore, parent=None) -> None:
        super().__init__(parent)
        self.store = store
        self.setWindowTitle("Bookmarks")
        self.resize(620, 400)
        layout = QVBoxLayout(self)
        self.list = QListWidget(self)
        self.list.itemDoubleClicked.connect(self.open_selected)
        layout.addWidget(self.list)

        actions = QHBoxLayout()
        self.open_button = QPushButton("Open", self)
        self.remove_button = QPushButton("Remove", self)
        self.import_button = QPushButton("Import…", self)
        self.export_button = QPushButton("Export…", self)
        for button in (self.open_button, self.remove_button, self.import_button, self.export_button):
            actions.addWidget(button)
        layout.addLayout(actions)
        self.open_button.clicked.connect(self.open_selected)
        self.remove_button.clicked.connect(self.remove_selected)
        self.import_button.clicked.connect(self.import_bookmarks)
        self.export_button.clicked.connect(self.export_bookmarks)
        self.list.currentRowChanged.connect(self.update_actions)
        self.refresh()

    def refresh(self) -> None:
        self.list.clear()
        for bookmark in self.store.bookmarks:
            self.list.addItem(f"{bookmark.title}   —   {bookmark.url}")
        self.update_actions()

    def selected_bookmark(self) -> Bookmark | None:
        row = self.list.currentRow()
        return self.store.bookmarks[row] if 0 <= row < len(self.store.bookmarks) else None

    def update_actions(self, _row: int = -1) -> None:
        selected = self.selected_bookmark() is not None
        self.open_button.setEnabled(selected)
        self.remove_button.setEnabled(selected)
        self.export_button.setEnabled(bool(self.store.bookmarks))

    def open_selected(self, *_args) -> None:
        bookmark = self.selected_bookmark()
        if bookmark:
            self.parent().open_bookmark(bookmark.url)

    def remove_selected(self) -> None:
        bookmark = self.selected_bookmark()
        if bookmark:
            try:
                self.store.remove(bookmark.url)
            except OSError as error:
                QMessageBox.critical(self, "Bookmark error", f"Could not save bookmarks: {error}")
                return
            self.refresh()

    def import_bookmarks(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Import bookmarks", "", "Dash bookmarks (*.json);;All files (*)"
        )
        if not path:
            return
        try:
            count = self.store.import_file(Path(path))
        except (OSError, ValueError) as error:
            QMessageBox.critical(self, "Import failed", str(error))
            return
        self.refresh()
        QMessageBox.information(self, "Bookmarks imported", f"Processed {count} bookmarks.")

    def export_bookmarks(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self, "Export bookmarks", "dash-bookmarks.json", "Dash bookmarks (*.json)"
        )
        if not path:
            return
        try:
            self.store.export_file(Path(path))
        except OSError as error:
            QMessageBox.critical(self, "Export failed", f"Could not export bookmarks: {error}")
