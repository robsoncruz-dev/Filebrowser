#!/usr/bin/env python3
"""
Filebrowser — System Tray (subprocess)

Processo separado que exibe ícone na bandeja do sistema.
Comunica com a aplicação principal via arquivo de estado.
Usa GTK3 + AppIndicator3 (separado do GTK4 da app principal).
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

# Carregar idioma salvo
load_saved_language()

import gi
gi.require_version("Gtk", "3.0")
gi.require_version("AppIndicator3", "0.1")
from gi.repository import Gtk, GLib, AppIndicator3


STATE_FILE = os.path.expanduser("~/.cache/filebrowser/tray_state.json")
PID_FILE = os.path.expanduser("~/.cache/filebrowser/app.pid")


def read_state() -> dict:
    """Lê o estado atual da aplicação."""
    try:
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"indexing": False, "local": 0, "cloud": 0, "status": ""}


class TrayIcon:
    """Ícone na system tray com AppIndicator3."""

    ICON_IDLE = "folder"
    ICON_INDEXING = "folder-download"

    def __init__(self):
        self._indicator = AppIndicator3.Indicator.new(
            "filebrowser-pdf",
            self.ICON_IDLE,
            AppIndicator3.IndicatorCategory.APPLICATION_STATUS,
        )
        self._indicator.set_status(AppIndicator3.IndicatorStatus.ACTIVE)
        self._indicator.set_title("Filebrowser")
        self._build_menu()
        self._poll_timer = GLib.timeout_add(2000, self._poll_state)

    def _build_menu(self):
        menu = Gtk.Menu()

        self._item_status = Gtk.MenuItem(label=t("tray_title"))
        self._item_status.set_sensitive(False)
        menu.append(self._item_status)

        menu.append(Gtk.SeparatorMenuItem())

        item_show = Gtk.MenuItem(label=t("tray_show"))
        item_show.connect("activate", self._on_show)
        menu.append(item_show)

        item_reindex = Gtk.MenuItem(label=t("tray_reindex"))
        item_reindex.connect("activate", self._on_reindex)
        menu.append(item_reindex)

        menu.append(Gtk.SeparatorMenuItem())

        item_settings = Gtk.MenuItem(label=t("tray_settings"))
        item_settings.connect("activate", lambda i: self._send_command("settings"))
        menu.append(item_settings)

        item_about = Gtk.MenuItem(label=t("tray_about"))
        item_about.connect("activate", lambda i: self._send_command("about"))
        menu.append(item_about)

        item_feedback = Gtk.MenuItem(label=t("tray_feedback"))
        item_feedback.connect("activate", lambda i: self._send_command("feedback"))
        menu.append(item_feedback)

        item_donate = Gtk.MenuItem(label=t("tray_donate"))
        item_donate.connect("activate", lambda i: self._send_command("donate"))
        menu.append(item_donate)

        menu.append(Gtk.SeparatorMenuItem())

        item_quit = Gtk.MenuItem(label=t("tray_quit"))
        item_quit.connect("activate", self._on_quit)
        menu.append(item_quit)

        menu.show_all()
        self._indicator.set_menu(menu)

    def _poll_state(self) -> bool:
        """Verifica o estado a cada 2s e atualiza o ícone."""
        state = read_state()
        indexing = state.get("indexing", False)
        local = state.get("local", 0)
        cloud = state.get("cloud", 0)

        icon = self.ICON_INDEXING if indexing else self.ICON_IDLE
        self._indicator.set_icon_full(icon, "Filebrowser")

        if indexing:
            label = t("tray_indexing", local=local, cloud=cloud)
        elif local + cloud > 0:
            label = t("tray_indexed", n=local + cloud)
        else:
            label = t("tray_title")

        self._item_status.set_label(label)
        self._indicator.set_title(label)
        return True

    def _on_show(self, item):
        self._send_command("show")

    def _on_reindex(self, item):
        self._send_command("reindex")

    def _on_quit(self, item):
        self._send_command("quit")
        Gtk.main_quit()

    def _send_command(self, cmd: str):
        cmd_file = os.path.expanduser("~/.cache/filebrowser/tray_cmd.json")
        try:
            with open(cmd_file, "w") as f:
                json.dump({"command": cmd, "time": time.time()}, f)
        except OSError:
            pass

        try:
            with open(PID_FILE, "r") as f:
                pid = int(f.read().strip())
            os.kill(pid, signal.SIGUSR1)
        except (FileNotFoundError, ValueError, ProcessLookupError, PermissionError):
            pass


def main():
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    tray = TrayIcon()
    Gtk.main()


if __name__ == "__main__":
    main()
