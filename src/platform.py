"""
Filebrowser — Abstração Cross-Platform (Strategy Pattern)

Centraliza todo código que depende de sys.platform em um único módulo.
Cada módulo do projeto importa daqui ao invés de verificar a plataforma diretamente.
"""

from __future__ import annotations

import os
import subprocess
import sys
from abc import ABC, abstractmethod
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from PyQt6.QtWidgets import QMainWindow


# ─── Interface Base ──────────────────────────────────────────────────────────


class PlatformBase(ABC):
    """Interface abstrata para operações dependentes de plataforma."""

    @property
    @abstractmethod
    def is_windows(self) -> bool:
        """Retorna True se estiver rodando no Windows."""

    @abstractmethod
    def open_file(self, path: str, reader: str = "") -> None:
        """Abre um arquivo com o leitor configurado."""

    @abstractmethod
    def force_foreground(self, window: QMainWindow | None = None) -> None:
        """Traz a janela para o primeiro plano."""

    @abstractmethod
    def send_notification(self, title: str, body: str) -> None:
        """Envia notificação nativa do SO."""

    @abstractmethod
    def get_default_dirs(self) -> list[str]:
        """Retorna os diretórios padrão de busca."""

    @abstractmethod
    def get_default_ignore(self) -> list[str]:
        """Retorna os padrões de ignore."""

    @abstractmethod
    def get_config_dirs(self) -> tuple[Path, Path]:
        """Retorna (USER_CONFIG_DIR, CACHE_DIR)."""

    @abstractmethod
    def detect_native_clouds(self) -> list[str]:
        """Detecta pastas de nuvem nativas do SO (OneDrive, GDrive, etc.)."""

    @abstractmethod
    def get_extra_disk_paths(self) -> list[Path]:
        """Detecta discos/mídias removíveis montados."""

    @abstractmethod
    def detect_wm(self) -> str:
        """Detecta o Window Manager / SO ativo."""


# ─── Linux ───────────────────────────────────────────────────────────────────


class LinuxPlatform(PlatformBase):
    """Implementação para Linux (X11, Wayland, i3, sway, GNOME, KDE, XFCE)."""

    @property
    def is_windows(self) -> bool:
        return False

    def open_file(self, path: str, reader: str = "") -> None:
        try:
            if reader:
                subprocess.Popen(
                    [reader, path],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                )
            else:
                subprocess.Popen(
                    ["xdg-open", path],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                )
        except FileNotFoundError:
            subprocess.Popen(
                ["xdg-open", path],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            )

    def force_foreground(self, window: QMainWindow | None = None) -> None:
        wm = self.detect_wm()
        try:
            if wm == "i3":
                subprocess.Popen(
                    ["i3-msg", "floating enable, move position center, border pixel 2"],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                )
            elif wm == "sway":
                subprocess.Popen(
                    ["swaymsg", "floating enable, move position center"],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                )
        except FileNotFoundError:
            pass

    def send_notification(self, title: str, body: str) -> None:
        try:
            subprocess.Popen(
                [
                    "notify-send", title, body,
                    "--icon=document-open", "--urgency=low",
                ],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            )
        except (FileNotFoundError, OSError):
            pass

    def get_default_dirs(self) -> list[str]:
        return [
            os.path.expanduser("~/Documentos"),
            os.path.expanduser("~/Documents"),
            os.path.expanduser("~/Downloads"),
            os.path.expanduser("~/Desktop"),
        ]

    def get_default_ignore(self) -> list[str]:
        return [
            ".cache", ".local/share/Trash", "snap",
            ".var/app", "node_modules", "__pycache__",
        ]

    def get_config_dirs(self) -> tuple[Path, Path]:
        config = Path.home() / ".config" / "filebrowser"
        cache = Path.home() / ".cache" / "filebrowser"
        return config, cache

    def detect_native_clouds(self) -> list[str]:
        # Linux não tem nuvens nativas à la OneDrive/GDrive
        return []

    def get_extra_disk_paths(self) -> list[Path]:
        """Detecta mídias externas via /run/media e /mnt."""
        paths: list[Path] = []
        user = os.environ.get("USER", "")

        # /run/media/$USER/ — padrão systemd/udisks2
        media_dir = Path(f"/run/media/{user}")
        if media_dir.is_dir():
            for child in media_dir.iterdir():
                if child.is_dir() and child not in paths:
                    paths.append(child)

        # /mnt/ — montagens manuais
        mnt = Path("/mnt")
        if mnt.is_dir():
            for child in mnt.iterdir():
                if child.is_dir() and child not in paths:
                    paths.append(child)

        return paths

    def detect_wm(self) -> str:
        desktop = os.environ.get("XDG_CURRENT_DESKTOP", "").lower()
        session = os.environ.get("DESKTOP_SESSION", "").lower()
        combined = f"{desktop} {session}"
        if "i3" in combined:
            return "i3"
        if "sway" in combined:
            return "sway"
        if "gnome" in combined:
            return "gnome"
        if "kde" in combined or "plasma" in combined:
            return "kde"
        if "xfce" in combined:
            return "xfce"
        return "generic"


# ─── Windows ─────────────────────────────────────────────────────────────────


class WindowsPlatform(PlatformBase):
    """Implementação para Windows (Win32 nativo via ctypes)."""

    @property
    def is_windows(self) -> bool:
        return True

    def open_file(self, path: str, reader: str = "") -> None:
        try:
            if reader and reader.lower() in ["zathura", "evince", "okular"]:
                subprocess.Popen(
                    [reader, path],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                )
            else:
                os.startfile(path)  # type: ignore[attr-defined]
        except FileNotFoundError:
            os.startfile(path)  # type: ignore[attr-defined]

    def force_foreground(self, window: QMainWindow | None = None) -> None:
        if window is None:
            return

        # Raise + activate + focus no nível Qt
        window.raise_()
        window.activateWindow()

        hwnd = int(window.winId())

        import ctypes
        user32 = ctypes.windll.user32  # type: ignore[attr-defined]
        kernel32 = ctypes.windll.kernel32  # type: ignore[attr-defined]

        current_thread_id = kernel32.GetCurrentThreadId()
        foreground_thread_id = user32.GetWindowThreadProcessId(
            user32.GetForegroundWindow(), 0
        )

        SWP_NOMOVE = 0x0002
        SWP_NOSIZE = 0x0001
        SWP_SHOWWINDOW = 0x0040
        HWND_TOPMOST = -1
        SW_SHOW = 5

        flags = SWP_NOMOVE | SWP_NOSIZE | SWP_SHOWWINDOW

        if current_thread_id != foreground_thread_id and foreground_thread_id != 0:
            user32.AttachThreadInput(current_thread_id, foreground_thread_id, True)
            user32.SetWindowPos(hwnd, HWND_TOPMOST, 0, 0, 0, 0, flags)
            user32.SetForegroundWindow(hwnd)
            user32.ShowWindow(hwnd, SW_SHOW)
            user32.AttachThreadInput(current_thread_id, foreground_thread_id, False)
        else:
            user32.SetWindowPos(hwnd, HWND_TOPMOST, 0, 0, 0, 0, flags)
            user32.SetForegroundWindow(hwnd)

    def send_notification(self, title: str, body: str) -> None:
        # Windows: notificações são feitas pelo QSystemTrayIcon (na UI)
        pass

    def get_default_dirs(self) -> list[str]:
        return [
            os.path.expanduser("~/Documents"),
            os.path.expanduser("~/Downloads"),
            os.path.expanduser("~/Desktop"),
        ]

    def get_default_ignore(self) -> list[str]:
        return [
            "AppData", "ProgramData", "$Recycle.Bin",
            "Windows", "Program Files", "node_modules",
        ]

    def get_config_dirs(self) -> tuple[Path, Path]:
        app_data = Path(os.getenv("APPDATA", Path.home() / "AppData" / "Roaming"))
        local_app_data = Path(os.getenv("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
        config = app_data / "Filebrowser"
        cache = local_app_data / "Filebrowser" / "Cache"
        return config, cache

    def detect_native_clouds(self) -> list[str]:
        """Detecta OneDrive e GDrive nativos no Windows."""
        clouds: list[str] = []

        # OneDrive — variáveis de ambiente
        for od_key in ["OneDrive", "OneDriveConsumer", "OneDriveCommercial"]:
            od_val = os.environ.get(od_key)
            if od_val and Path(od_val).exists() and od_val not in clouds:
                clouds.append(od_val)

        # OneDrive — fallbacks físicos
        userprofile = os.environ.get("USERPROFILE", "")
        if userprofile:
            od_base = Path(userprofile) / "OneDrive"
            if od_base.exists() and str(od_base) not in clouds:
                clouds.append(str(od_base))

            # Empresas (OneDrive - NomeDaEmpresa)
            import glob
            for match in glob.glob(str(Path(userprofile) / "OneDrive - *")):
                if str(match) not in clouds:
                    clouds.append(str(match))

        # Google Drive
        gdrive_paths = ["G:\\My Drive", os.path.expanduser("~/Google Drive")]
        for gdir in gdrive_paths:
            if Path(gdir).exists() and gdir not in clouds:
                clouds.append(gdir)

        return clouds

    def get_extra_disk_paths(self) -> list[Path]:
        """Detecta discos extras via psutil no Windows."""
        paths: list[Path] = []
        try:
            import psutil
            for part in psutil.disk_partitions(all=False):
                if not part.mountpoint or "cdrom" in part.opts or part.fstype == "":
                    continue
                mp = Path(part.mountpoint).resolve()
                # Evitar C:\ root (já coberto por ~/Documents etc.)
                if str(mp).upper().startswith("C:\\"):
                    continue
                if mp.exists() and mp.is_dir() and mp not in paths:
                    paths.append(mp)
        except (ImportError, OSError):
            pass
        return paths

    def detect_wm(self) -> str:
        return "windows"


# ─── Singleton & API de Compatibilidade ──────────────────────────────────────


def _get_platform() -> PlatformBase:
    """Instancia a plataforma correta baseado no SO."""
    if sys.platform == "win32":
        return WindowsPlatform()
    return LinuxPlatform()


platform = _get_platform()
"""Singleton global — instância da plataforma atual."""


# ─── Wrappers de compatibilidade ────────────────────────────────────────────


def detect_wm() -> str:
    """Detecta o Window Manager ativo ou SO."""
    return platform.detect_wm()


def open_file(path: str, reader: str = "") -> None:
    """Abre um arquivo com o leitor configurado."""
    platform.open_file(path, reader)


def get_default_dirs() -> list[str]:
    """Retorna os diretórios padrão de busca para a plataforma atual."""
    return platform.get_default_dirs()


def get_default_ignore() -> list[str]:
    """Retorna os padrões de ignore para a plataforma atual."""
    return platform.get_default_ignore()
