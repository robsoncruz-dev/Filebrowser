"""
Filebrowser — Janela de Configurações

Permite ao usuário alterar idioma e configurar atalho de teclado.
O atalho é editável, salvo no metadata, e inserido automaticamente no config do WM.
"""

import os
import subprocess

import sys
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, 
    QLineEdit, QPushButton, QFrame, QApplication
)
from PyQt6.QtCore import Qt

from src.ui.about import APP_NAME
from src.i18n import t
from src.search.indexer import get_metadata, save_metadata


# ─── Idiomas disponíveis ─────────────────────────────────────────────────────

LANGUAGES = [
    ("pt_BR", "🇧🇷 Português (Brasil)"),
    ("en", "🇺🇸 English"),
    ("es", "🇪🇸 Español"),
]

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


def _detect_wm() -> str:
    """Detecta o Window Manager ativo ou SO."""
    if sys.platform == "win32":
        return "windows"
        
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


def apply_shortcut(key: str, wm: str = "", callback=None) -> tuple:
    """
    Aplica o atalho:
    - Windows: Regista global hotkey dinâmico usando módulo keyboard
    - i3/Sway: insere binding no config com marcador, recarrega WM
    - Outros: retorna instruções manuais

    Returns:
        (success: bool, message: str)
    """
    if not wm:
        wm = _detect_wm()
        
    if wm == "windows":
        try:
            # Substitui a lib `keyboard` (que exige privilégios ou falha) por ctypes nativo
            import threading
            import ctypes
            from ctypes import wintypes
            import time

            # Para a thread anterior se ela existir
            global _win32_hotkey_thread, _win32_hotkey_active
            if '_win32_hotkey_active' in globals():
                _win32_hotkey_active = False

            def _listener(key_str, cb):
                user32 = ctypes.windll.user32
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
                    while globals().get('_win32_hotkey_active', False):
                        bRet = user32.PeekMessageW(ctypes.byref(msg), None, 0, 0, 1) # PM_REMOVE
                        if bRet:
                            if msg.message == 0x0312 and msg.wParam == HOTKEY_ID: # WM_HOTKEY
                                if cb:
                                    from PyQt6.QtCore import QTimer
                                    QTimer.singleShot(0, cb)
                            user32.TranslateMessage(ctypes.byref(msg))
                            user32.DispatchMessageW(ctypes.byref(msg))
                        time.sleep(0.01)
                finally:
                    user32.UnregisterHotKey(None, HOTKEY_ID)

            if callback:
                globals()['_win32_hotkey_active'] = True
                _win32_hotkey_thread = threading.Thread(target=_listener, args=(key, callback), daemon=True)
                _win32_hotkey_thread.start()
            
            return True, t("set_shortcut_active", key=key)
        except Exception as e:
            return False, f"Falha ao registrar Hotkey Nativo Win32: {e}"

    if wm in ("i3", "sway"):
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

            binding_line = tmpl["template"].format(key=key)
            lines.append(f"\n{binding_line}  {SHORTCUT_MARKER}\n")

            with open(config_path, "w") as f:
                f.writelines(lines)

            reload_cmd = "i3-msg" if wm == "i3" else "swaymsg"
            subprocess.run(
                [reload_cmd, "reload"],
                capture_output=True, timeout=5,
            )

            return True, t("set_shortcut_active", key=key)

        except Exception as e:
            return False, f"Error: {e}"

    else:
        return False, t("set_shortcut_manual")


def remove_shortcut_from_config():
    """Remove o binding do filebrowser do config do WM (para desinstalação)."""
    wm = _detect_wm()
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


def apply_saved_shortcut(callback=None):
    """Aplica o atalho salvo no WM (chamado no startup do app). Silencioso."""
    try:
        saved = get_metadata("shortcut", "")
        if saved:
            return apply_shortcut(saved, callback=callback)
    except Exception as e:
        return False, str(e)
    return True, ""


class SettingsWindow(QDialog):
    """Janela de configurações do app."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(t("set_title", app=APP_NAME))
        self.setFixedSize(500, 460)
        self.setModal(True)
        self._wm = _detect_wm()
        self._tmpl = WM_TEMPLATES.get(self._wm, WM_TEMPLATES["generic"])
        self._build_ui()

    def _build_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(24, 20, 24, 20)
        main_layout.setSpacing(14)

        # ─── Idioma ──────────────────────────────────────────────────
        lang_title = QLabel(f"<b>{t('set_lang_title')}</b>")
        lang_title.setStyleSheet("font-size: 16px;")
        main_layout.addWidget(lang_title)

        lang_desc = QLabel(t("set_lang_desc"))
        lang_desc.setProperty("class", "dim-label")
        main_layout.addWidget(lang_desc)

        self.lang_dropdown = QComboBox()
        for _, name in LANGUAGES:
            self.lang_dropdown.addItem(name)

        from src.i18n import get_language
        current_lang = get_language()
        for i, (code, _) in enumerate(LANGUAGES):
            if code == current_lang:
                self.lang_dropdown.setCurrentIndex(i)
                break

        self.lang_dropdown.currentIndexChanged.connect(self._on_lang_changed)
        main_layout.addWidget(self.lang_dropdown)

        lang_note = QLabel(t('set_lang_note'))
        lang_note.setStyleSheet("font-size: 11px;")
        lang_note.setProperty("class", "dim-label")
        main_layout.addWidget(lang_note)

        # ─── Separador ───────────────────────────────────────────────
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setFrameShadow(QFrame.Shadow.Sunken)
        main_layout.addWidget(sep)

        # ─── Atalho de Teclado ───────────────────────────────────────
        shortcut_title = QLabel(f"<b>{t('set_shortcut_title')}</b>")
        shortcut_title.setStyleSheet("font-size: 16px;")
        main_layout.addWidget(shortcut_title)

        wm_label = QLabel(t("set_wm_detected", wm=self._tmpl["name"]))
        main_layout.addWidget(wm_label)

        file_label = QLabel(t('set_wm_file', file=self._tmpl['file']))
        file_label.setStyleSheet("font-size: 11px;")
        file_label.setProperty("class", "dim-label")
        main_layout.addWidget(file_label)

        # Campo editável
        shortcut_layout = QHBoxLayout()
        shortcut_label = QLabel(t("set_shortcut_label"))
        shortcut_layout.addWidget(shortcut_label)

        saved_shortcut = get_metadata("shortcut", DEFAULT_SHORTCUT)
        self.shortcut_entry = QLineEdit()
        self.shortcut_entry.setText(saved_shortcut)
        self.shortcut_entry.setPlaceholderText(t("set_shortcut_placeholder"))
        self.shortcut_entry.textChanged.connect(self._on_shortcut_edited)
        shortcut_layout.addWidget(self.shortcut_entry)

        save_btn = QPushButton(t("set_save_shortcut"))
        save_btn.clicked.connect(self._on_save_shortcut)
        shortcut_layout.addWidget(save_btn)

        main_layout.addLayout(shortcut_layout)

        # Instrução
        instruction_label = QLabel(t("set_instruction"))
        instruction_label.setWordWrap(True)
        instruction_label.setProperty("class", "dim-label")
        main_layout.addWidget(instruction_label)

        # Comando gerado
        cmd_frame = QFrame()
        cmd_frame.setFrameShape(QFrame.Shape.StyledPanel)
        cmd_layout = QVBoxLayout(cmd_frame)
        cmd_layout.setContentsMargins(10, 8, 10, 8)
        
        gen_label = QLabel(t('set_generated_cmd'))
        gen_label.setStyleSheet("font-size: 11px;")
        gen_label.setProperty("class", "dim-label")
        cmd_layout.addWidget(gen_label)

        self.cmd_label = QLabel()
        self.cmd_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.cmd_label.setWordWrap(True)
        self._update_command_preview(saved_shortcut)
        cmd_layout.addWidget(self.cmd_label)
        main_layout.addWidget(cmd_frame)

        # Botões
        btn_layout = QHBoxLayout()
        btn_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        copy_btn = QPushButton(t("set_copy_cmd"))
        copy_btn.clicked.connect(self._on_copy_cmd)
        btn_layout.addWidget(copy_btn)

        close_btn = QPushButton(t("set_close"))
        close_btn.clicked.connect(self.accept)
        btn_layout.addWidget(close_btn)

        main_layout.addLayout(btn_layout)

        # Status
        self.status_label = QLabel("")
        self.status_label.setWordWrap(True)
        main_layout.addWidget(self.status_label)

    def _update_command_preview(self, shortcut: str):
        cmd = self._tmpl["template"].format(key=shortcut)
        self.cmd_label.setText(cmd)
        self.cmd_label.setStyleSheet("font-family: monospace;")
        self._current_cmd = cmd

    def _on_shortcut_edited(self, text):
        key = text.strip() or DEFAULT_SHORTCUT
        self._update_command_preview(key)

    def _on_save_shortcut(self):
        key = self.shortcut_entry.text().strip() or DEFAULT_SHORTCUT
        
        # Validar em tempo real antes de salvar!
        cb = None
        if hasattr(self, 'parent') and self.parent():
            if hasattr(self.parent(), 'fb_app'):
                cb = self.parent().fb_app._on_tray_show

        success, message = apply_shortcut(key, self._wm, callback=cb)
        
        if success:
            save_metadata("shortcut", key)
            self.status_label.setText(message)
        else:
            self.status_label.setText("⚠ Erro ao salvar: " + message)

    def _on_lang_changed(self, idx):
        if idx < len(LANGUAGES):
            code, name = LANGUAGES[idx]
            from src.i18n import save_language
            save_language(code)
            self.status_label.setText(t("set_lang_changed", name=name))

    def _on_copy_cmd(self):
        clipboard = QApplication.clipboard()
        clipboard.setText(self._current_cmd)
        self.status_label.setText(t("set_copied"))
