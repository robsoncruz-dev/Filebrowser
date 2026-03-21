#!/usr/bin/env python3
"""
Filebrowser — System Tray (subprocess)

Processo separado que exibe ícone na bandeja do sistema.
Comunica com a aplicação principal via arquivo de estado.
Usa PyQt6 (QSystemTrayIcon).
"""

import os
import sys
import signal
import json
import time

# Permitir importar src.i18n
_project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from src.i18n import t, load_saved_language
from src.config.settings import CACHE_DIR

# Carregar idioma salvo
load_saved_language()

from PyQt6.QtWidgets import QApplication, QSystemTrayIcon, QMenu
from PyQt6.QtGui import QIcon, QAction
from PyQt6.QtCore import QTimer

STATE_FILE = CACHE_DIR / "tray_state.json"
PID_FILE = CACHE_DIR / "app.pid"
TRAY_CMD_FILE = CACHE_DIR / "tray_cmd.json"


def read_state() -> dict:
    """Lê o estado atual da aplicação."""
    try:
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"indexing": False, "local": 0, "cloud": 0, "status": ""}


class TrayIcon(QSystemTrayIcon):
    """Ícone na system tray usando PyQt6."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setIcon(QIcon.fromTheme("folder"))
        self.setToolTip("Filebrowser")
        self._build_menu()
        
        # Iniciar polling
        self._timer = QTimer()
        self._timer.timeout.connect(self._poll_state)
        self._timer.start(2000)

    def _build_menu(self):
        menu = QMenu()

        self._item_status = QAction(t("tray_title"), self)
        self._item_status.setEnabled(False)
        menu.addAction(self._item_status)
        menu.addSeparator()

        item_show = QAction(t("tray_show"), self)
        item_show.triggered.connect(self._on_show)
        menu.addAction(item_show)

        item_reindex = QAction(t("tray_reindex"), self)
        item_reindex.triggered.connect(self._on_reindex)
        menu.addAction(item_reindex)

        menu.addSeparator()

        item_settings = QAction(t("tray_settings"), self)
        item_settings.triggered.connect(lambda: self._send_command("settings"))
        menu.addAction(item_settings)

        item_about = QAction(t("tray_about"), self)
        item_about.triggered.connect(lambda: self._send_command("about"))
        menu.addAction(item_about)

        item_feedback = QAction(t("tray_feedback"), self)
        item_feedback.triggered.connect(lambda: self._send_command("feedback"))
        menu.addAction(item_feedback)

        item_donate = QAction(t("tray_donate"), self)
        item_donate.triggered.connect(lambda: self._send_command("donate"))
        menu.addAction(item_donate)

        menu.addSeparator()

        item_quit = QAction(t("tray_quit"), self)
        item_quit.triggered.connect(self._on_quit)
        menu.addAction(item_quit)

        self.setContextMenu(menu)

    def _poll_state(self):
        """Verifica o estado a cada 2s e atualiza o ícone."""
        state = read_state()
        indexing = state.get("indexing", False)
        local = state.get("local", 0)
        cloud = state.get("cloud", 0)

        icon_theme = "folder-download" if indexing else "folder"
        self.setIcon(QIcon.fromTheme(icon_theme))

        if indexing:
            label = t("tray_indexing", local=local, cloud=cloud)
        elif local + cloud > 0:
            label = t("tray_indexed", n=local + cloud)
        else:
            label = t("tray_title")

        self.setToolTip(label)
        self._item_status.setText(label)

    def _on_show(self):
        self._send_command("show")

    def _on_reindex(self):
        self._send_command("reindex")

    def _on_quit(self):
        self._send_command("quit")
        QApplication.quit()

    def _send_command(self, cmd: str):
        try:
            TRAY_CMD_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(TRAY_CMD_FILE, "w") as f:
                json.dump({"command": cmd, "time": time.time()}, f)
        except OSError:
            pass

        if sys.platform != "win32":
            try:
                with open(PID_FILE, "r") as f:
                    pid = int(f.read().strip())
                os.kill(pid, signal.SIGUSR1)
            except (FileNotFoundError, ValueError, ProcessLookupError, PermissionError):
                pass


def main():
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    app = QApplication(sys.argv)
    
    # Prevenir que fechar janela finaliza
    app.setQuitOnLastWindowClosed(False)
    
    tray = TrayIcon()
    tray.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
