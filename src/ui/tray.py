"""
Filebrowser — System Tray + App Orchestrator

Classe FilebrowserApp: ponto central da aplicação.
Gerencia a criação da janela, tray icon, e atalhos globais.
"""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING

from PyQt6.QtWidgets import (
    QApplication, QSystemTrayIcon, QMenu,
)
from PyQt6.QtCore import QTimer
from PyQt6.QtGui import QIcon, QAction

from src.config.settings import AppConfig
from src.i18n import t, load_saved_language
from src.platform import platform as plat

if TYPE_CHECKING:
    from src.ui.window import FilebrowserWindow

# Carregar idioma salvo antes de construir a UI
load_saved_language()


class FilebrowserApp:
    """Orquestrador principal da aplicação."""

    def __init__(self, config: AppConfig):
        self.config = config
        self.app = QApplication(sys.argv)
        self.app.setQuitOnLastWindowClosed(False)
        self._win: FilebrowserWindow | None = None
        self._tray: QSystemTrayIcon | None = None
        self._item_status: QAction | None = None

    def run(self, argv) -> int:
        from src.ui.window import FilebrowserWindow

        # Create Main Window
        self._win = FilebrowserWindow(self.app, self.config, self)

        # Build tray icon natively
        self._build_tray()

        from src.hotkeys import apply_saved_shortcut
        success, msg = apply_saved_shortcut(callback=self._on_tray_show)

        if success is False and plat.is_windows:
            self._on_tray_settings()

        return self.app.exec()

    def _build_tray(self) -> None:
        self._tray = QSystemTrayIcon(self._win)
        self._tray.setIcon(QIcon.fromTheme("folder"))
        self._tray.setToolTip("Filebrowser")

        menu = QMenu()
        self._item_status = QAction(t("tray_title"), self._win)
        self._item_status.setEnabled(False)
        menu.addAction(self._item_status)
        menu.addSeparator()

        item_show = QAction(t("tray_show"), self._win)
        item_show.triggered.connect(self._on_tray_show)
        menu.addAction(item_show)

        item_reindex = QAction(t("tray_reindex"), self._win)
        item_reindex.triggered.connect(self._on_tray_reindex)
        menu.addAction(item_reindex)

        menu.addSeparator()

        item_settings = QAction(t("tray_settings"), self._win)
        item_settings.triggered.connect(self._on_tray_settings)
        menu.addAction(item_settings)

        item_about = QAction(t("tray_about"), self._win)
        item_about.triggered.connect(self._on_tray_about)
        menu.addAction(item_about)

        item_feedback = QAction(t("tray_feedback"), self._win)
        item_feedback.triggered.connect(self._on_tray_feedback)
        menu.addAction(item_feedback)

        item_donate = QAction(t("tray_donate"), self._win)
        item_donate.triggered.connect(self._on_tray_donate)
        menu.addAction(item_donate)

        menu.addSeparator()

        item_quit = QAction(t("tray_quit"), self._win)
        item_quit.triggered.connect(self._on_tray_quit)
        menu.addAction(item_quit)

        self._tray.setContextMenu(menu)
        self._tray.activated.connect(self._on_tray_activated)
        self._tray.show()

    def _ensure_tray(self) -> None:
        """Garante que o tray icon está visível."""
        if self._tray is not None:
            self._tray.show()

    def _on_tray_activated(self, reason) -> None:
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self._on_tray_show()

    def _on_tray_show(self) -> None:
        if self._win is None:
            return
        self._win.show()
        self._win.activateWindow()
        QTimer.singleShot(50, self._win._force_floating)

    def _on_tray_reindex(self) -> None:
        if self._win is None:
            return
        self._win.show()
        self._win.activateWindow()
        QTimer.singleShot(50, self._win._force_floating)
        QTimer.singleShot(50, self._win._start_background_index)

    def _on_tray_settings(self) -> None:
        from src.ui.settings_ui import SettingsWindow
        win = SettingsWindow(self._win)
        win.show()

    def _on_tray_about(self) -> None:
        from src.ui.about import AboutWindow
        win = AboutWindow(self._win)
        win.show()

    def _on_tray_feedback(self) -> None:
        from src.ui.feedback import FeedbackWindow
        win = FeedbackWindow(self._win)
        win.show()

    def _on_tray_donate(self) -> None:
        from src.ui.donate import DonateWindow
        win = DonateWindow(self._win)
        win.show()

    def _on_tray_quit(self) -> None:
        QApplication.quit()

    def update_tray_state(self, indexing: bool, local_count: int, cloud_count: int, status_text: str) -> None:
        if not self._tray or not self._item_status:
            return

        icon_theme = "folder-download" if indexing else "folder"
        self._tray.setIcon(QIcon.fromTheme(icon_theme))

        if indexing:
            label = t("tray_indexing", local=local_count, cloud=cloud_count)
        elif local_count + cloud_count > 0:
            label = t("tray_indexed", n=local_count + cloud_count)
        else:
            label = t("tray_title")

        self._tray.setToolTip(label)
        self._item_status.setText(label)


