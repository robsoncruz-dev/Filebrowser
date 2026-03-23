"""
Filebrowser — Gerenciamento de Hotkeys

Centraliza toda a lógica de registro e remoção de atalhos globais.
No Windows, usa Win32 RegisterHotKey via ctypes.
No Linux, insere binding no config do WM (i3/sway) com marcador.
"""

from __future__ import annotations

import os
import subprocess
import threading

from src.platform import detect_wm
from src.i18n import t


# ─── Variáveis globais para hotkey Win32 ─────────────────────────────────────

_win32_hotkey_thread: threading.Thread | None = None
_win32_hotkey_active: bool = False


# ─── WM Config Templates ────────────────────────────────────────────────────

WM_TEMPLATES = {
    "i3": {
        "name": "i3wm",
        "file": "~/.config/i3/config",
        "template": "bindsym {key} exec --no-startup-id filebrowser",
    },
    "sway": {
        "name": "Sway",
        "file": "~/.config/sway/config",
        "template": "bindsym {key} exec filebrowser",
    },
    "gnome": {
        "name": "GNOME",
        "file": "Custom Shortcuts",
        "template": "# GNOME: Settings → Keyboard → Custom Shortcuts\n"
                    "# Name: Filebrowser\n"
                    "# Command: filebrowser\n"
                    "# Shortcut: {key}",
    },
    "kde": {
        "name": "KDE Plasma",
        "file": "~/.config/kglobalshortcutsrc",
        "template": "# KDE: System Settings → Shortcuts → Custom Shortcuts\n"
                    "# Name: Filebrowser\n"
                    "# Command: filebrowser\n"
                    "# Shortcut: {key}",
    },
    "xfce": {
        "name": "XFCE",
        "file": "~/.config/xfce4/xfconf/xfce-perchannel-xml/xfce4-keyboard-shortcuts.xml",
        "template": "# XFCE: Settings → Keyboard → Application Shortcuts\n"
                    "# Command: filebrowser\n"
                    "# Shortcut: {key}",
    },
    "windows": {
        "name": "Windows",
        "file": "API nativa",
        "template": "Windows Global Hook ativado: {key}",
    },
    "generic": {
        "name": "Linux",
        "file": "WM config file",
        "template": "# Command: filebrowser\n# Shortcut: {key}",
    },
}

DEFAULT_SHORTCUT = "$mod+Shift+f"
SHORTCUT_MARKER = "# filebrowser-shortcut"


# ─── API Pública ─────────────────────────────────────────────────────────────

def apply_shortcut(shortcut_key: str, wm: str = "", callback=None) -> tuple:
    """
    Aplica o atalho:
    - Windows: Registra global hotkey dinâmico usando ctypes nativo
    - i3/Sway: insere binding no config com marcador, recarrega WM
    - Outros: retorna instruções manuais

    Returns:
        (success: bool, message: str)
    """
    if not wm:
        wm = detect_wm()

    if wm == "windows":
        return _apply_win32_hotkey(shortcut_key, callback)

    if wm in ("i3", "sway"):
        return _apply_wm_hotkey(shortcut_key, wm)

    return False, t("set_shortcut_manual")


def remove_shortcut_from_config() -> None:
    """Remove o binding do filebrowser do config do WM (para desinstalação)."""
    wm = detect_wm()
    if wm in ("i3", "sway"):
        tmpl = WM_TEMPLATES[wm]
        config_path = os.path.expanduser(tmpl["file"])
        if os.path.isfile(config_path):
            try:
                with open(config_path, "r") as f:
                    lines = f.readlines()
                lines = [l for l in lines if SHORTCUT_MARKER not in l]
                with open(config_path, "w") as f:
                    f.writelines(lines)
            except Exception:
                pass


def apply_saved_shortcut(callback=None) -> tuple:
    """Aplica o atalho salvo no WM (chamado no startup do app). Silencioso."""
    try:
        from src.search.indexer import get_metadata, save_metadata
        saved = get_metadata("shortcut", "")
        if not saved:
            saved = "alt+space"
            save_metadata("shortcut", saved)

        if saved:
            return apply_shortcut(saved, callback=callback)
    except Exception as e:
        return False, str(e)
    return True, ""


# ─── Implementações Internas ─────────────────────────────────────────────────

def _apply_win32_hotkey(shortcut_key: str, callback) -> tuple:
    """Registra global hotkey no Windows via ctypes."""
    try:
        import ctypes
        from ctypes import wintypes

        global _win32_hotkey_thread, _win32_hotkey_active
        _win32_hotkey_active = False

        def _listener(key_str: str, cb):
            user32 = ctypes.windll.user32  # type: ignore[attr-defined]
            MOD_ALT = 0x0001
            MOD_CONTROL = 0x0002
            MOD_SHIFT = 0x0004
            MOD_WIN = 0x0008

            modifiers = 0
            vk = 0
            parts = key_str.lower().replace(" ", "").split("+")
            for part in parts:
                if part == "alt": modifiers |= MOD_ALT
                elif part == "ctrl": modifiers |= MOD_CONTROL
                elif part == "shift": modifiers |= MOD_SHIFT
                elif part == "win": modifiers |= MOD_WIN
                elif part == "space": vk = 0x20
                elif len(part) == 1 and 'a' <= part <= 'z':
                    vk = ord(part.upper())

            HOTKEY_ID = 1
            if not user32.RegisterHotKey(None, HOTKEY_ID, modifiers, vk):
                return

            try:
                msg = wintypes.MSG()
                while _win32_hotkey_active:
                    bRet = user32.GetMessageW(ctypes.byref(msg), None, 0, 0)
                    if bRet == 0 or bRet == -1:
                        break
                    if msg.message == 0x0312 and msg.wParam == HOTKEY_ID:
                        if cb:
                            from PyQt6.QtCore import QTimer
                            QTimer.singleShot(0, cb)
                    user32.TranslateMessage(ctypes.byref(msg))
                    user32.DispatchMessageW(ctypes.byref(msg))
            finally:
                user32.UnregisterHotKey(None, HOTKEY_ID)

        if callback:
            _win32_hotkey_active = True
            _win32_hotkey_thread = threading.Thread(
                target=_listener, args=(shortcut_key, callback), daemon=True
            )
            _win32_hotkey_thread.start()

        return True, t("set_shortcut_active", shortcut=shortcut_key)
    except Exception as e:
        return False, f"Falha ao registrar Hotkey Nativo Win32: {e}"


def _apply_wm_hotkey(shortcut_key: str, wm: str) -> tuple:
    """Insere binding no config do WM (i3/sway)."""
    tmpl = WM_TEMPLATES[wm]
    config_path = os.path.expanduser(tmpl["file"])

    if not os.path.isfile(config_path):
        return False, t("set_shortcut_manual")

    try:
        with open(config_path, "r") as f:
            lines = f.readlines()

        lines = [l for l in lines if SHORTCUT_MARKER not in l]

        while lines and lines[-1].strip() == "":
            lines.pop()

        binding_line = tmpl["template"].format(key=shortcut_key)
        lines.append(f"\n{binding_line}  {SHORTCUT_MARKER}\n")

        with open(config_path, "w") as f:
            f.writelines(lines)

        reload_cmd = "i3-msg" if wm == "i3" else "swaymsg"
        subprocess.run(
            [reload_cmd, "reload"],
            capture_output=True, timeout=5,
        )

        return True, t("set_shortcut_active", shortcut=shortcut_key)

    except Exception as e:
        return False, f"Error: {e}"
