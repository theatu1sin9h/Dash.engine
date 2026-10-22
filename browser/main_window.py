# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Atul Singh Chandel

"""Main Dash Browser window and tab/navigation wiring."""

from pathlib import Path

from dataclasses import replace

from PyQt6.QtCore import QPoint, QSize, Qt, QUrl, pyqtSignal
from PyQt6.QtGui import QAction, QColor, QIcon, QKeySequence, QPainter, QPainterPath, QPen, QPixmap
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QDialog,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QApplication,
    QLabel,
    QSizePolicy,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
    QToolBar,
    QToolButton,
    QWidget,
)
from PyQt6.QtWebEngineCore import QWebEnginePage, QWebEngineProfile

from browser.browser_tab import BrowserTab
from browser.bookmarks import BookmarkStore
from browser.constants import APP_NAME, stylesheet_for_theme, theme_colors
from browser.dialogs import (
    BookmarkManagerDialog,
    ClearBrowsingDataDialog,
    HistoryDialog,
    PrivacyDashboardDialog,
    SettingsDialog,
    SitePermissionsDialog,
)
from browser.downloads import DownloadManagerDialog
from browser.history import HistoryStore
from browser.navigation import AddressError, address_to_url
from browser.privacy import RequestBlocker
from browser.settings import SEARCH_ENGINES, BrowserSettings, SettingsStore
from browser.storage import data_directory
from browser.tear_effect import TearEffect, system_prefers_reduced_motion


def _brand_icon() -> QIcon:
    image_path = Path(__file__).parent / "assets" / "dash-mark.png"
    mark = QPixmap(str(image_path))
    if mark.isNull():
        raise RuntimeError(f"Could not load Dash logo asset: {image_path}")

    return QIcon(
        mark.scaled(
            QSize(34, 34),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
    )


def _navigation_icon(direction: str, theme: str) -> QIcon:
    icon = QPixmap(24, 24)
    icon.fill(Qt.GlobalColor.transparent)
    painter = QPainter(icon)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setPen(
        QPen(
            QColor(theme_colors(theme)["secondary"]),
            2,
            Qt.PenStyle.SolidLine,
            Qt.PenCapStyle.RoundCap,
            Qt.PenJoinStyle.RoundJoin,
        )
    )
    if direction == "left":
        painter.drawLine(18, 12, 6, 12)
        painter.drawLine(6, 12, 12, 6)
        painter.drawLine(6, 12, 12, 18)
    else:
        painter.drawLine(6, 12, 18, 12)
        painter.drawLine(18, 12, 12, 6)
        painter.drawLine(18, 12, 12, 18)
    painter.end()
    return QIcon(icon)


class AddressBar(QLineEdit):
    """Address field with a dedicated Escape-to-restore signal."""

    escapePressed = pyqtSignal()

    def keyPressEvent(self, event) -> None:
        if event.key() == Qt.Key.Key_Escape:
            self.escapePressed.emit()
            event.accept()
            return
        super().keyPressEvent(event)


class SidebarButton(QToolButton):
    """Compact, accessible line-icon button for Dash's persistent sidebar."""

    def __init__(self, name: str, parent=None) -> None:
        super().__init__(parent)
        self.icon_name = name
        self.setAccessibleName(name)
        self.setToolTip(name)
        self.setFixedSize(40, 38)
        self.setAutoRaise(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    def paintEvent(self, _event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        if self.underMouse() or self.hasFocus():
            painter.setPen(Qt.PenStyle.NoPen)
            colors = getattr(self.window(), "theme_colors", theme_colors("dark"))
            painter.setBrush(QColor(colors["active_tab"]))
            painter.drawRoundedRect(self.rect().adjusted(1, 1, -1, -1), 6, 6)

        colors = getattr(self.window(), "theme_colors", theme_colors("dark"))
        painter.setPen(QPen(QColor(colors["secondary"]), 1.7, Qt.PenStyle.SolidLine,
                            Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        cx, cy = self.width() / 2, self.height() / 2

        if self.icon_name == "New tab":
            painter.drawLine(int(cx - 6), int(cy), int(cx + 6), int(cy))
            painter.drawLine(int(cx), int(cy - 6), int(cx), int(cy + 6))
        elif self.icon_name == "Downloads":
            painter.drawLine(int(cx), int(cy - 8), int(cx), int(cy + 2))
            painter.drawLine(int(cx - 4), int(cy - 2), int(cx), int(cy + 2))
            painter.drawLine(int(cx + 4), int(cy - 2), int(cx), int(cy + 2))
            painter.drawLine(int(cx - 7), int(cy + 5), int(cx - 7), int(cy + 8))
            painter.drawLine(int(cx - 7), int(cy + 8), int(cx + 7), int(cy + 8))
            painter.drawLine(int(cx + 7), int(cy + 8), int(cx + 7), int(cy + 5))
        elif self.icon_name == "Bookmarks":
            path = QPainterPath()
            path.moveTo(cx - 6, cy - 8)
            path.lineTo(cx + 6, cy - 8)
            path.lineTo(cx + 6, cy + 8)
            path.lineTo(cx, cy + 4)
            path.lineTo(cx - 6, cy + 8)
            path.closeSubpath()
            painter.drawPath(path)
        elif self.icon_name == "History":
            painter.drawArc(int(cx - 8), int(cy - 8), 16, 16, 35 * 16, 300 * 16)
            painter.drawLine(int(cx), int(cy), int(cx), int(cy - 5))
            painter.drawLine(int(cx), int(cy), int(cx + 4), int(cy + 2))
        elif self.icon_name == "Privacy":
            path = QPainterPath()
            path.moveTo(cx, cy - 9)
            path.lineTo(cx + 7, cy - 6)
            path.lineTo(cx + 6, cy + 1)
            path.cubicTo(cx + 5, cy + 5, cx + 2, cy + 8, cx, cy + 9)
            path.cubicTo(cx - 2, cy + 8, cx - 5, cy + 5, cx - 6, cy + 1)
            path.lineTo(cx - 7, cy - 6)
            path.closeSubpath()
            painter.drawPath(path)
        elif self.icon_name == "Tear tab":
            path = QPainterPath()
            path.moveTo(cx, cy + 9)
            path.cubicTo(cx - 9, cy + 5, cx - 5, cy - 1, cx - 2, cy - 8)
            path.cubicTo(cx + 1, cy - 4, cx + 6, cy - 3, cx + 5, cy + 2)
            path.cubicTo(cx + 9, cy + 1, cx + 9, cy + 7, cx, cy + 9)
            painter.drawPath(path)
            painter.drawArc(int(cx - 3), int(cy + 1), 6, 6, 190 * 16, 160 * 16)
        elif self.icon_name == "Settings":
            painter.drawEllipse(int(cx - 3), int(cy - 3), 6, 6)
            for angle in range(0, 360, 45):
                painter.save()
                painter.translate(cx, cy)
                painter.rotate(angle)
                painter.drawLine(0, -6, 0, -9)
                painter.restore()


class BrowserWindow(QMainWindow):
    """Minimal multi-tab browser window backed by Qt WebEngine."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(APP_NAME)
        self.resize(1180, 780)
        self.setMinimumSize(640, 420)
        self.settings_store = SettingsStore()
        self.settings = self.settings_store.load()
        self.theme_colors = theme_colors(self.settings.theme)
        self.setStyleSheet(stylesheet_for_theme(self.settings.theme))
        self.bookmarks = BookmarkStore()
        self.history = HistoryStore()
        self._data_directory = data_directory()
        profile_directory = self._data_directory / "profile"
        cache_directory = self._data_directory / "cache"
        profile_directory.mkdir(mode=0o700, parents=True, exist_ok=True)
        cache_directory.mkdir(mode=0o700, parents=True, exist_ok=True)
        self._profile = QWebEngineProfile(APP_NAME, QApplication.instance())
        self.request_blocker = RequestBlocker(
            self.settings.ad_blocking_enabled,
            tuple(self.settings.ad_allowlist),
            self._profile,
        )
        self._profile_blockers: dict[QWebEngineProfile, RequestBlocker] = {
            self._profile: self.request_blocker
        }
        self._profile.setPersistentStoragePath(str(profile_directory))
        self._profile.setCachePath(str(cache_directory))
        self._profile.setPersistentCookiesPolicy(
            QWebEngineProfile.PersistentCookiesPolicy.ForcePersistentCookies
        )
        self._profile.setPersistentPermissionsPolicy(
            QWebEngineProfile.PersistentPermissionsPolicy.StoreInMemory
        )
        self._profile.setUrlRequestInterceptor(self.request_blocker)
        self._profile.clearHttpCacheCompleted.connect(self._http_cache_cleared)
        self._cache_clear_pending = False
        self._profile.setDownloadPath(self.settings.download_directory)
        self.downloads = DownloadManagerDialog(self.settings, self)
        self._profile.downloadRequested.connect(self.downloads.start_download)
        self._burn_profiles: dict[BrowserTab, QWebEngineProfile] = {}
        self._burn_tabs: set[BrowserTab] = set()
        self._burn_sessions: dict[QWebEngineProfile, set[BrowserTab]] = {}
        self._tear_effects: set[TearEffect] = set()
        self.tabs = QTabWidget(self)
        self.tabs.setDocumentMode(True)
        self.tabs.setMovable(True)
        self.tabs.setTabsClosable(True)
        self.tabs.tabCloseRequested.connect(self.close_tab)
        self.tabs.currentChanged.connect(self.update_address_bar)

        self.address_bar = AddressBar(self)
        self.address_bar.setPlaceholderText("Search or enter address")
        self.address_bar.setAccessibleName("Address and search")
        self.address_bar.setClearButtonEnabled(True)
        self.address_bar.returnPressed.connect(self.navigate)
        self.address_bar.escapePressed.connect(self.restore_address)

        self._build_window_layout()
        self._build_toolbar()
        self._build_bookmarks_bar()
        self._build_sidebar()
        self._build_shortcuts()
        self.progress = QProgressBar(self)
        self.progress.setRange(0, 100)
        self.progress.setTextVisible(False)
        self.progress.setFixedWidth(110)
        self.progress.setFixedHeight(5)
        self.progress.hide()
        self.statusBar().setFixedHeight(18)
        self.statusBar().addPermanentWidget(self.progress)
        self.statusBar().showMessage("Ready")
        self.new_tab()
        self._build_zoom_actions()

    def _build_window_layout(self) -> None:
        root = QWidget(self)
        root_layout = QHBoxLayout(root)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        self.sidebar = QWidget(root)
        self.sidebar.setObjectName("sidebar")
        self.sidebar.setFixedWidth(56)
        self.sidebar_layout = QVBoxLayout(self.sidebar)
        self.sidebar_layout.setContentsMargins(8, 10, 8, 10)
        self.sidebar_layout.setSpacing(6)
        root_layout.addWidget(self.sidebar)

        self.bookmarks_panel = QWidget(root)
        self.bookmarks_panel.setObjectName("bookmarksPanel")
        self.bookmarks_panel.setFixedWidth(260)
        self.bookmarks_panel.hide()
        self.bookmarks_panel_layout = QVBoxLayout(self.bookmarks_panel)
        self.bookmarks_panel_layout.setContentsMargins(12, 12, 12, 12)
        self.bookmarks_panel_layout.setSpacing(8)
        root_layout.addWidget(self.bookmarks_panel)

        self.browser_area = QWidget(root)
        self.browser_layout = QVBoxLayout(self.browser_area)
        self.browser_layout.setContentsMargins(0, 0, 0, 0)
        self.browser_layout.setSpacing(0)
        self.browser_layout.addWidget(self.tabs)
        root_layout.addWidget(self.browser_area, 1)
        self.setCentralWidget(root)

    def _build_sidebar(self) -> None:
        self._sidebar_dividers: list[QWidget] = []
        brand = QToolButton(self.sidebar)
        brand.setText("")
        brand.setAccessibleName("DASH logo")
        brand.setToolTip("Dash Browser")
        brand.setFixedSize(40, 38)
        brand.setIconSize(QSize(36, 30))
        brand.setIcon(_brand_icon())
        brand.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        brand.setStyleSheet(
            "QToolButton { border: 0; background: transparent; }"
        )
        self.brand_button = brand
        self.sidebar_layout.addWidget(brand, 0, Qt.AlignmentFlag.AlignHCenter)

        new_tab = SidebarButton("New tab", self.sidebar)
        new_tab.clicked.connect(self.new_tab)
        self.sidebar_layout.addWidget(new_tab, 0, Qt.AlignmentFlag.AlignHCenter)
        self._add_sidebar_divider()

        downloads = SidebarButton("Downloads", self.sidebar)
        downloads.clicked.connect(self.show_downloads)
        self.sidebar_layout.addWidget(downloads, 0, Qt.AlignmentFlag.AlignHCenter)

        bookmarks = SidebarButton("Bookmarks", self.sidebar)
        bookmarks.clicked.connect(self.toggle_bookmarks_panel)
        self.sidebar_layout.addWidget(bookmarks, 0, Qt.AlignmentFlag.AlignHCenter)

        history = SidebarButton("History", self.sidebar)
        history.clicked.connect(self.show_history)
        self.sidebar_layout.addWidget(history, 0, Qt.AlignmentFlag.AlignHCenter)

        privacy = SidebarButton("Privacy", self.sidebar)
        privacy.clicked.connect(self.show_privacy_dashboard)
        self.sidebar_layout.addWidget(privacy, 0, Qt.AlignmentFlag.AlignHCenter)

        self.sidebar_layout.addStretch(1)
        self._add_sidebar_divider()
        settings = SidebarButton("Settings", self.sidebar)
        settings.clicked.connect(self.show_settings)
        self.sidebar_layout.addWidget(settings, 0, Qt.AlignmentFlag.AlignHCenter)
        self._build_bookmarks_panel()

    def _build_bookmarks_panel(self) -> None:
        header = QHBoxLayout()
        title = QLabel("Bookmarks", self.bookmarks_panel)
        title.setStyleSheet(f"font-weight: 600; color: {self.theme_colors['text']};")
        header.addWidget(title)
        header.addStretch(1)
        close = QToolButton(self.bookmarks_panel)
        close.setText("×")
        close.setAccessibleName("Close bookmarks panel")
        close.setToolTip("Close")
        close.clicked.connect(self.bookmarks_panel.hide)
        header.addWidget(close)
        self.bookmarks_panel_layout.addLayout(header)

        self.bookmark_search = QLineEdit(self.bookmarks_panel)
        self.bookmark_search.setPlaceholderText("Search bookmarks")
        self.bookmark_search.textChanged.connect(self.filter_bookmarks_panel)
        self.bookmarks_panel_layout.addWidget(self.bookmark_search)

        self.bookmark_list = QListWidget(self.bookmarks_panel)
        self.bookmark_list.itemDoubleClicked.connect(self.open_bookmark_item)
        self.bookmarks_panel_layout.addWidget(self.bookmark_list, 1)

        actions = QHBoxLayout()
        self.bookmark_open_button = QPushButton("Open", self.bookmarks_panel)
        manage = QPushButton("Manage bookmarks…", self.bookmarks_panel)
        self.bookmark_open_button.clicked.connect(self.open_selected_bookmark)
        manage.clicked.connect(self.manage_bookmarks_from_panel)
        actions.addWidget(self.bookmark_open_button)
        actions.addWidget(manage)
        self.bookmarks_panel_layout.addLayout(actions)
        self.bookmark_list.itemSelectionChanged.connect(
            lambda: self.bookmark_open_button.setEnabled(self.bookmark_list.currentItem() is not None)
        )
        self.refresh_bookmarks_panel()

    def toggle_bookmarks_panel(self) -> None:
        self.refresh_bookmarks_panel()
        self.bookmarks_panel.setVisible(not self.bookmarks_panel.isVisible())
        if self.bookmarks_panel.isVisible():
            self.bookmark_search.setFocus(Qt.FocusReason.ShortcutFocusReason)

    def refresh_bookmarks_panel(self) -> None:
        if not hasattr(self, "bookmark_list"):
            return
        self.bookmark_list.clear()
        for bookmark in self.bookmarks.bookmarks:
            item = QListWidgetItem(bookmark.title)
            item.setToolTip(bookmark.url)
            item.setData(Qt.ItemDataRole.UserRole, bookmark.url)
            self.bookmark_list.addItem(item)
        self.filter_bookmarks_panel(self.bookmark_search.text())
        self.bookmark_open_button.setEnabled(False)

    def filter_bookmarks_panel(self, query: str) -> None:
        normalized = query.strip().casefold()
        for row in range(self.bookmark_list.count()):
            item = self.bookmark_list.item(row)
            item.setHidden(
                bool(normalized)
                and normalized not in item.text().casefold()
                and normalized not in item.toolTip().casefold()
            )

    def open_bookmark_item(self, item: QListWidgetItem) -> None:
        self.open_bookmark(item.data(Qt.ItemDataRole.UserRole))

    def open_selected_bookmark(self) -> None:
        item = self.bookmark_list.currentItem()
        if item is not None:
            self.open_bookmark_item(item)

    def manage_bookmarks_from_panel(self) -> None:
        self.show_bookmarks()
        self.refresh_bookmarks_panel()

    def _add_sidebar_divider(self) -> None:
        divider = QWidget(self.sidebar)
        divider.setFixedHeight(1)
        divider.setStyleSheet(f"background: {self.theme_colors['border']};")
        self._sidebar_dividers.append(divider)
        self.sidebar_layout.addWidget(divider)

    def _build_toolbar(self) -> None:
        toolbar = QToolBar("Navigation", self)
        toolbar.setMovable(False)
        toolbar.setFloatable(False)
        toolbar.setContextMenuPolicy(Qt.ContextMenuPolicy.PreventContextMenu)
        self.browser_layout.insertWidget(0, toolbar)

        self.back_action = QAction(self)
        self.back_action.setIcon(_navigation_icon("left", self.settings.theme))
        self.back_action.setToolTip("Back")
        self.back_action.setStatusTip("Go back one page")
        self.back_action.setShortcut(QKeySequence.StandardKey.Back)
        self.back_action.triggered.connect(self.go_back)
        toolbar.addAction(self.back_action)

        self.home_action = QAction("Home", self)
        self.home_action.setToolTip("Home / new tab")
        self.home_action.setStatusTip("Open Dash Browser's home page")
        self.home_action.triggered.connect(self.go_home)
        toolbar.addAction(self.home_action)

        self.forward_action = QAction(self)
        self.forward_action.setIcon(_navigation_icon("right", self.settings.theme))
        self.forward_action.setToolTip("Forward")
        self.forward_action.setStatusTip("Go forward one page")
        self.forward_action.setShortcut(QKeySequence.StandardKey.Forward)
        self.forward_action.triggered.connect(self.go_forward)
        toolbar.addAction(self.forward_action)

        self.reload_action = QAction("Reload", self)
        self.reload_action.setStatusTip("Reload the current page")
        self.reload_action.setShortcut(QKeySequence.StandardKey.Refresh)
        self.reload_action.triggered.connect(lambda: self._current_view_action("reload"))
        toolbar.addAction(self.reload_action)

        self.stop_action = QAction("Stop", self)
        self.stop_action.setStatusTip("Stop loading the current page")
        self.stop_action.triggered.connect(lambda: self._current_view_action("stop"))
        self.stop_action.setVisible(False)
        toolbar.addAction(self.stop_action)

        toolbar.addWidget(self.address_bar)
        self.address_bar.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        self.bookmark_action = QAction("Bookmark", self)
        self.bookmark_action.setToolTip("Add or remove bookmark")
        self.bookmark_action.triggered.connect(self.toggle_current_bookmark)
        toolbar.addAction(self.bookmark_action)

        self.tear_button = SidebarButton("Tear tab", toolbar)
        self.tear_button.setAccessibleName("Tear Page / Burn Tab")
        self.tear_button.setToolTip("Tear Page / Burn Tab")
        self.tear_button.clicked.connect(self.tear_current_tab)
        toolbar.addWidget(self.tear_button)

        self.privacy_button = SidebarButton("Privacy", toolbar)
        self.privacy_button.setAccessibleName("Privacy dashboard")
        self.privacy_button.setToolTip("Privacy dashboard")
        self.privacy_button.clicked.connect(self.show_privacy_dashboard)
        toolbar.addWidget(self.privacy_button)

        add_tab = QToolButton(self)
        add_tab.setText("+")
        add_tab.setToolTip("New tab")
        add_tab.clicked.connect(self.new_tab)
        self.tabs.setCornerWidget(add_tab, Qt.Corner.TopRightCorner)

    def _build_bookmarks_bar(self) -> None:
        self.bookmarks_bar = QToolBar("Bookmarks", self)
        self.bookmarks_bar.setMovable(False)
        self.bookmarks_bar.setFloatable(False)
        self.bookmarks_bar.setContextMenuPolicy(Qt.ContextMenuPolicy.PreventContextMenu)
        self.browser_layout.insertWidget(1, self.bookmarks_bar)
        self.bookmarks_bar.setVisible(self.settings.show_bookmarks_bar)
        self.refresh_bookmarks_bar()

    def _build_shortcuts(self) -> None:
        self._add_shortcut("Ctrl+T", self.new_tab)
        self._add_shortcut("Ctrl+W", lambda: self.close_tab(self.tabs.currentIndex()))
        self._add_shortcut("Ctrl+Tab", lambda: self._switch_tab(1))
        self._add_shortcut("Ctrl+Shift+Tab", lambda: self._switch_tab(-1))
        self._add_shortcut("Ctrl+L", self.focus_address_bar)
        self._add_shortcut("Alt+D", self.focus_address_bar)
        self._add_shortcut("Ctrl+J", self.show_downloads)
        self._add_shortcut("Ctrl+B", self.toggle_bookmarks_panel)
        self._add_shortcut("Ctrl+H", self.show_history)
        self._add_shortcut("Ctrl+,", self.show_settings)
        self._add_shortcut("Ctrl+Shift+N", self.open_tear_tab)

    def _build_zoom_actions(self) -> None:
        self._add_shortcut(QKeySequence.StandardKey.ZoomIn, lambda: self.adjust_zoom(0.1))
        self._add_shortcut(QKeySequence.StandardKey.ZoomOut, lambda: self.adjust_zoom(-0.1))
        self._add_shortcut("Ctrl+0", lambda: self.set_zoom(1.0))

    def _add_shortcut(self, sequence, callback) -> None:
        action = QAction(self)
        action.setShortcut(QKeySequence(sequence))
        action.triggered.connect(callback)
        self.addAction(action)

    def adjust_zoom(self, amount: float) -> None:
        view = self.current_view()
        if view is not None:
            self.set_zoom(view.zoomFactor() + amount)

    def set_zoom(self, factor: float) -> None:
        view = self.current_view()
        if view is None:
            return
        factor = max(0.25, min(5.0, round(factor, 2)))
        view.setZoomFactor(factor)
        self.statusBar().showMessage(f"Page zoom: {round(factor * 100)}%", 2000)

    def _switch_tab(self, offset: int) -> None:
        count = self.tabs.count()
        if count:
            self.tabs.setCurrentIndex((self.tabs.currentIndex() + offset) % count)

    def new_tab(
        self, burnable: bool = False, profile: QWebEngineProfile | None = None
    ) -> QWebEnginePage:
        if profile is None:
            profile = QWebEngineProfile(self) if burnable else self._profile
        burnable = profile is not self._profile
        if profile is not self._profile:
            if profile not in self._profile_blockers:
                blocker = RequestBlocker(
                    self.settings.ad_blocking_enabled,
                    tuple(self.settings.ad_allowlist),
                    profile,
                )
                profile.setUrlRequestInterceptor(blocker)
                self._profile_blockers[profile] = blocker
        create_tab = lambda: self.new_tab(burnable=burnable, profile=profile if burnable else None)
        tab = BrowserTab(
            profile,
            create_tab,
            self,
            self.settings.theme,
            self._selected_search_url(),
            self.settings.new_tab_background,
            self.settings.new_tab_solid_color,
            self.settings.new_tab_gradient_start,
            self.settings.new_tab_gradient_end,
            self.settings.new_tab_wallpaper,
        )
        if burnable:
            self._burn_tabs.add(tab)
            self._burn_profiles[tab] = profile
            tab.destroyed.connect(lambda _obj=None, item=tab: self._burn_tabs.discard(item))
            session_tabs = self._burn_sessions.setdefault(profile, set())
            first_session_tab = not session_tabs
            session_tabs.add(tab)
            if first_session_tab:
                profile.downloadRequested.connect(self.downloads.start_download)
            if not profile.isOffTheRecord():
                raise RuntimeError("Qt did not create a disposable browsing profile")
        tab.titleChanged.connect(lambda title, view=tab: self.update_tab_title(view, title))
        tab.iconChanged.connect(lambda _icon, view=tab: self.update_tab_icon(view))
        tab.urlChanged.connect(lambda url, view=tab: self.update_tab_url(view, url))
        tab.loadStarted.connect(lambda view=tab: self.load_started(view))
        tab.loadProgress.connect(lambda value, view=tab: self.load_progress(view, value))
        tab.loadFinished.connect(lambda ok, view=tab: self.load_finished(view, ok))
        tab.page().urlRejected.connect(self.rejected_url)
        tab.page().customizeRequested.connect(self.show_settings)
        tab.page().permissionRequested.connect(self.handle_permission_request)
        tab.page().renderProcessTerminated.connect(
            lambda status, exit_code, view=tab: self.renderer_terminated(view, status, exit_code)
        )
        index = self.tabs.addTab(tab, "Tear · New Tab" if burnable else "New Tab")
        if burnable:
            self.tabs.setTabToolTip(index, "Disposable session — not recorded in Dash history")
        self.tabs.setCurrentIndex(index)
        return tab.page()

    def close_tab(self, index: int) -> None:
        if index < 0 or index >= self.tabs.count():
            return
        tab = self.tabs.widget(index)
        if isinstance(tab, BrowserTab) and tab in self._burn_profiles:
            profile = self._burn_profiles.pop(tab)
            remaining = self._burn_sessions.get(profile)
            if remaining is not None:
                remaining.discard(tab)
                if not remaining:
                    self._burn_sessions.pop(profile, None)
                    self._profile_blockers.pop(profile, None)
                    profile.cookieStore().deleteAllCookies()
                    profile.clearHttpCache()
                    profile.clearAllVisitedLinks()
                    tab.page().destroyed.connect(profile.deleteLater)
            tab.stop()
        self.tabs.removeTab(index)
        if tab is not None:
            tab.deleteLater()
        if self.tabs.count() == 0:
            self.new_tab()

    def open_tear_tab(self) -> None:
        self.new_tab(burnable=True)
        self.statusBar().showMessage(
            "Tear Tab: this disposable session is excluded from Dash history. "
            "Tear it closed to discard its temporary profile; downloads are retained.",
            9000,
        )

    def tear_current_tab(self) -> None:
        view = self.current_view()
        if view is not None and view in self._burn_profiles:
            index = self.tabs.indexOf(view)
            snapshot = view.grab()
            if snapshot.isNull():
                self.close_tab(index)
                self.statusBar().showMessage(
                    "Page capture was unavailable; the temporary tab was closed.",
                    5000,
                )
                return
            geometry = view.rect()
            geometry.moveTopLeft(view.mapTo(self.tabs, QPoint(0, 0)))
            view.stop()
            view.setEnabled(False)
            effect = TearEffect(
                self.tabs,
                snapshot,
                geometry,
                self.theme_colors["background"],
                system_prefers_reduced_motion(),
            )
            self._tear_effects.add(effect)
            effect.destroyed.connect(
                lambda _obj=None, item=effect: self._tear_effects.discard(item)
            )
            self.close_tab(index)
            effect.raise_()
            self.statusBar().showMessage(
                "Temporary tab closed; its isolated profile is being discarded.",
                5000,
            )
            return
        self.open_tear_tab()

    def _current_view_action(self, action: str) -> None:
        view = self.current_view()
        if view is not None:
            getattr(view, action)()

    def current_view(self) -> BrowserTab | None:
        view = self.tabs.currentWidget()
        return view if isinstance(view, BrowserTab) else None

    def update_navigation_actions(self, view: BrowserTab | None = None) -> None:
        view = view or self.current_view()
        if view is None or view is not self.current_view():
            return
        self.back_action.setEnabled(view.history().canGoBack())
        self.forward_action.setEnabled(view.history().canGoForward())

    def go_back(self) -> None:
        view = self.current_view()
        if view is not None and view.history().canGoBack():
            view.back()

    def go_forward(self) -> None:
        view = self.current_view()
        if view is not None and view.history().canGoForward():
            view.forward()

    def go_home(self) -> None:
        view = self.current_view()
        if isinstance(view, BrowserTab):
            view.show_new_tab()

    def navigate(self) -> None:
        self._navigate_text(self.address_bar.text())

    def _selected_search_url(self) -> str:
        search_engines = {**SEARCH_ENGINES, **(self.settings.custom_search_engines or {})}
        return search_engines[self.settings.search_engine]

    def _navigate_text(self, text: str, view: BrowserTab | None = None) -> None:
        view = view or self.current_view()
        if view is None:
            return
        try:
            url = address_to_url(text, self._selected_search_url())
        except AddressError as error:
            self.statusBar().showMessage(str(error), 5000)
            if view is self.current_view():
                self.restore_address()
            return
        if view is self.current_view():
            self.address_bar.setText(text)
        view.setUrl(url)
        if view is self.current_view():
            self.address_bar.clearFocus()

    def restore_address(self) -> None:
        view = self.current_view()
        self.address_bar.setText(view.url().toDisplayString() if view and view.url().scheme() else "")
        self.address_bar.clearFocus()

    def focus_address_bar(self) -> None:
        self.address_bar.setFocus(Qt.FocusReason.ShortcutFocusReason)
        self.address_bar.selectAll()

    def update_address_bar(self, _index: int = -1) -> None:
        view = self.current_view()
        if view is None:
            self.address_bar.clear()
            self.back_action.setEnabled(False)
            self.forward_action.setEnabled(False)
            return
        url = view.url()
        self.address_bar.setText(url.toDisplayString() if url.scheme() in {"http", "https"} else "")
        self.setWindowTitle(f"{self.tabs.tabText(self.tabs.currentIndex())} — {APP_NAME}")
        self.update_navigation_actions(view)
        self.progress.hide()
        self.update_bookmark_action()

    def update_tab_title(self, view: BrowserTab, title: str) -> None:
        index = self.tabs.indexOf(view)
        if index >= 0:
            label = title or "New Tab"
            if view in self._burn_profiles:
                label = f"Tear · {label}"
            self.tabs.setTabText(index, label[:36])
        if view is self.current_view():
            self.setWindowTitle(f"{title or 'New Tab'} — {APP_NAME}")

    def update_tab_icon(self, view: BrowserTab) -> None:
        index = self.tabs.indexOf(view)
        if index >= 0 and not view.icon().isNull():
            self.tabs.setTabIcon(index, view.icon())

    def update_tab_url(self, view: BrowserTab, url: QUrl) -> None:
        self.update_navigation_actions(view)
        if view is self.current_view():
            self.address_bar.setText(url.toDisplayString() if url.scheme() in {"http", "https"} else "")
            self.update_bookmark_action()

    def load_started(self, view: BrowserTab) -> None:
        if view is self.current_view():
            self.progress.setValue(0)
            self.progress.show()
            self.reload_action.setVisible(False)
            self.stop_action.setVisible(True)
            self.statusBar().showMessage("Loading")

    def load_progress(self, view: BrowserTab, value: int) -> None:
        if view is self.current_view():
            self.progress.setValue(value)

    def load_finished(self, view: BrowserTab, succeeded: bool) -> None:
        self.update_navigation_actions(view)
        history_error = None
        url = view.url()
        if (
            view not in self._burn_tabs
            and succeeded
            and url.scheme().lower() in {"http", "https"}
            and url.host()
        ):
            try:
                self.history.add(view.title(), url.toString())
            except (OSError, ValueError) as error:
                history_error = error
        if view is self.current_view():
            self.progress.hide()
            self.reload_action.setVisible(True)
            self.stop_action.setVisible(False)
            if history_error:
                self.statusBar().showMessage(f"Could not save browsing history: {history_error}", 8000)
            else:
                self.statusBar().showMessage(
                    "Page loaded" if succeeded else "Page failed to load", 5000
                )

    def rejected_url(self, url: str) -> None:
        self.statusBar().showMessage(f"Blocked unsupported address: {url[:160]}", 6000)

    def handle_permission_request(self, permission) -> None:
        if not permission.isValid():
            return
        feature = permission.permissionType().name
        feature_names = {
            "ClipboardReadWrite": "clipboard access",
            "DesktopAudioVideoCapture": "desktop audio and video capture",
            "DesktopVideoCapture": "desktop video capture",
            "Geolocation": "your location",
            "LocalFontsAccess": "local fonts access",
            "MediaAudioCapture": "your microphone",
            "MediaAudioVideoCapture": "your camera and microphone",
            "MediaVideoCapture": "your camera",
            "MouseLock": "mouse lock",
            "Notifications": "notifications",
        }
        feature_name = feature_names.get(feature)
        if feature_name is None:
            permission.deny()
            self.statusBar().showMessage(
                f"Denied unsupported site permission ({feature}).", 5000
            )
            return

        origin = permission.origin().toDisplayString()
        if self.confirm_site_permission(origin, feature_name):
            permission.grant()
            decision = "allowed in memory"
        else:
            permission.deny()
            decision = "denied"
        self.statusBar().showMessage(
            f"Permission {decision} for {origin}: {feature_name}.", 6000
        )

    def confirm_site_permission(self, origin: str, feature: str) -> bool:
        answer = QMessageBox.question(
            self,
            "Website permission request",
            f"{origin} wants access to {feature}.\n\n"
            "Allow this site for the current Dash session?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        return answer == QMessageBox.StandardButton.Yes

    def show_site_permissions(self) -> None:
        SitePermissionsDialog(self._profile, self).exec()

    def show_clear_browsing_data(self) -> None:
        dialog = ClearBrowsingDataDialog(self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        selected = dialog.selected_data()
        self._clear_browsing_data(selected)

    def _clear_browsing_data(self, selected: frozenset[str]) -> None:
        cleared = []
        if "history" in selected:
            try:
                self.history.clear()
            except OSError as error:
                QMessageBox.critical(
                    self, "Clear browsing data", f"Could not clear history: {error}"
                )
                return
            cleared.append("Dash history")
        if "cookies" in selected:
            self._profile.cookieStore().deleteAllCookies()
            cleared.append("cookies")
        if "permissions" in selected:
            for permission in self._profile.listAllPermissions():
                if permission.isValid():
                    permission.reset()
            cleared.append("site permissions")
        if "cache" in selected:
            self._cache_clear_pending = True
            self._profile.clearHttpCache()
            cleared.append("cached web files")
        if cleared:
            self.statusBar().showMessage(
                f"Clear requested for {', '.join(cleared)}. "
                "Local site storage, service workers, and downloaded files are not cleared.",
                9000,
            )

    def _http_cache_cleared(self) -> None:
        if self._cache_clear_pending:
            self._cache_clear_pending = False
            self.statusBar().showMessage("Cached web files cleared.", 5000)

    def renderer_terminated(self, view: BrowserTab, status, exit_code: int) -> None:
        if view is self.current_view():
            self.statusBar().showMessage(
                f"Page renderer stopped ({status.name}, exit code {exit_code}). Reload to try again.",
                10000,
            )

    def update_bookmark_action(self) -> None:
        view = self.current_view()
        url = view.url().toString() if view else ""
        bookmarked = any(bookmark.url == url for bookmark in self.bookmarks.bookmarks)
        self.bookmark_action.setText("Bookmarked" if bookmarked else "Bookmark")
        self.bookmark_action.setEnabled(bool(view and view.url().scheme() in {"http", "https"}))

    def toggle_current_bookmark(self) -> None:
        view = self.current_view()
        if view is None or view.url().scheme() not in {"http", "https"}:
            return
        url = view.url().toString()
        try:
            existing = next(
                (bookmark for bookmark in self.bookmarks.bookmarks if bookmark.url == url), None
            )
            if existing:
                self.bookmarks.remove(url)
            else:
                self.bookmarks.add(view.title(), url)
        except (OSError, ValueError) as error:
            QMessageBox.critical(self, "Bookmark error", f"Could not save bookmark: {error}")
            return
        self.refresh_bookmarks_bar()
        self.refresh_bookmarks_panel()
        self.update_bookmark_action()

    def refresh_bookmarks_bar(self) -> None:
        self.bookmarks_bar.clear()
        for bookmark in self.bookmarks.bookmarks:
            action = QAction(bookmark.title[:28], self)
            action.setToolTip(f"{bookmark.title}\n{bookmark.url}")
            action.triggered.connect(
                lambda _checked=False, url=bookmark.url: self.open_bookmark(url)
            )
            self.bookmarks_bar.addAction(action)
        self.bookmarks_bar.setVisible(self.settings.show_bookmarks_bar)

    def open_bookmark(self, url: str) -> None:
        view = self.current_view()
        if view is None:
            self.new_tab()
            view = self.current_view()
        if view is not None:
            view.setUrl(QUrl(url))

    def show_bookmarks(self) -> None:
        dialog = BookmarkManagerDialog(self.bookmarks, self)
        dialog.exec()
        self.refresh_bookmarks_bar()
        self.refresh_bookmarks_panel()
        self.update_bookmark_action()

    def show_history(self) -> None:
        HistoryDialog(self.history, self.open_bookmark, self).exec()

    def show_downloads(self) -> None:
        self.downloads.show()
        self.downloads.raise_()
        self.downloads.activateWindow()

    def show_settings(self) -> None:
        dialog = SettingsDialog(self.settings, self)
        dialog.manageSitePermissions.connect(self.show_site_permissions)
        dialog.clearBrowsingData.connect(self.show_clear_browsing_data)
        dialog.openPrivacyDashboard.connect(
            lambda: self._show_privacy_dashboard_from_settings(dialog)
        )
        if not dialog.exec():
            return
        try:
            updated = dialog.updated_settings(self.settings)
            self.settings_store.save(updated)
        except (OSError, ValueError) as error:
            QMessageBox.critical(self, "Settings error", f"Could not save settings: {error}")
            return
        self.settings = updated
        for blocker in self._profile_blockers.values():
            blocker.configure(
                self.settings.ad_blocking_enabled, tuple(self.settings.ad_allowlist)
            )
        self.apply_theme()
        self._profile.setDownloadPath(self.settings.download_directory)
        self.downloads.settings = self.settings
        self.refresh_bookmarks_bar()
        self.refresh_bookmarks_panel()

    def show_privacy_dashboard(self) -> None:
        view = self.current_view()
        current_site = ""
        if view is not None and view.url().scheme().lower() in {"http", "https"}:
            current_site = view.url().host().rstrip(".").lower()
        dialog = PrivacyDashboardDialog(
            self.settings,
            self.request_blocker,
            current_site,
            self,
        )
        dialog.settingsChanged.connect(self.apply_privacy_settings)
        dialog.exec()

    def _show_privacy_dashboard_from_settings(self, settings_dialog: SettingsDialog) -> None:
        self.show_privacy_dashboard()
        settings_dialog.ad_blocking.setChecked(self.settings.ad_blocking_enabled)
        settings_dialog.ad_allowlist.setPlainText("\n".join(self.settings.ad_allowlist))

    def apply_privacy_settings(self, blocking_enabled: bool, allowlist: list[str]) -> None:
        try:
            updated = replace(
                self.settings,
                ad_blocking_enabled=blocking_enabled,
                ad_allowlist=allowlist,
            )
            self.settings_store.save(updated)
        except (OSError, ValueError, TypeError) as error:
            QMessageBox.critical(
                self, "Privacy settings error", f"Could not save privacy settings: {error}"
            )
            return
        self.settings = updated
        for blocker in self._profile_blockers.values():
            blocker.configure(
                updated.ad_blocking_enabled, tuple(updated.ad_allowlist)
            )

    def apply_theme(self) -> None:
        self.theme_colors = theme_colors(self.settings.theme)
        self.setStyleSheet(stylesheet_for_theme(self.settings.theme))
        self.brand_button.setIcon(_brand_icon())
        self.back_action.setIcon(_navigation_icon("left", self.settings.theme))
        self.forward_action.setIcon(_navigation_icon("right", self.settings.theme))
        for divider in self._sidebar_dividers:
            divider.setStyleSheet(f"background: {self.theme_colors['border']};")
        self.bookmarks_panel.update()
        for index in range(self.tabs.count()):
            view = self.tabs.widget(index)
            if isinstance(view, BrowserTab):
                view.set_appearance(
                    self.settings.theme,
                    self._selected_search_url(),
                    self.settings.new_tab_background,
                    self.settings.new_tab_solid_color,
                    self.settings.new_tab_gradient_start,
                    self.settings.new_tab_gradient_end,
                    self.settings.new_tab_wallpaper,
                )
        for button in self.sidebar.findChildren(SidebarButton):
            button.update()

    def closeEvent(self, event) -> None:
        if self.downloads.has_active_downloads:
            answer = QMessageBox.question(
                self,
                "Downloads in progress",
                "Downloads are still active. Close Dash Browser and cancel them?",
                QMessageBox.StandardButton.Close | QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Cancel,
            )
            if answer != QMessageBox.StandardButton.Close:
                event.ignore()
                return
            self.downloads.cancel_active_downloads()
        super().closeEvent(event)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        if hasattr(self, "bookmarks_panel"):
            self.bookmarks_panel.setFixedWidth(
                min(260, max(200, round(self.width() * 0.24)))
            )
