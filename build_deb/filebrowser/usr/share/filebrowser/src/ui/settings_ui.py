"""
Filebrowser — Janela de Configurações

Permite ao usuário alterar idioma e configurar atalho de teclado.
O atalho é editável, salvo no metadata, e inserido automaticamente no config do WM.
"""

import os
import subprocess

import gi
gi.require_version("Gtk", "4.0")
from gi.repository import Gtk, Gdk

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
    "generic": {
        "name": "Linux",
        "file": "WM config file",
        "template": "# Command: filebrowser\n# Shortcut: {key}",
    },
}

DEFAULT_SHORTCUT = "$mod+Shift+f"
SHORTCUT_MARKER = "# filebrowser-shortcut"


def _detect_wm() -> str:
    """Detecta o Window Manager ativo."""
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


def apply_shortcut(key: str, wm: str = "") -> tuple:
    """
    Aplica o atalho no WM:
    - i3/Sway: insere binding no config com marcador, recarrega WM
    - Outros: retorna instruções manuais

    Returns:
        (success: bool, message: str)
    """
    if not wm:
        wm = _detect_wm()

    if wm in ("i3", "sway"):
        tmpl = WM_TEMPLATES[wm]
        config_path = os.path.expanduser(tmpl["file"])

        if not os.path.isfile(config_path):
            return False, t("set_shortcut_manual")

        try:
            with open(config_path, "r") as f:
                lines = f.readlines()

            # Remover binding anterior do filebrowser (se existir)
            lines = [l for l in lines if SHORTCUT_MARKER not in l]

            # Remover linhas em branco extras no final
            while lines and lines[-1].strip() == "":
                lines.pop()

            # Adicionar novo binding com marcador
            binding_line = tmpl["template"].format(key=key)
            lines.append(f"\n{binding_line}  {SHORTCUT_MARKER}\n")

            with open(config_path, "w") as f:
                f.writelines(lines)

            # Recarregar WM para aplicar
            reload_cmd = "i3-msg" if wm == "i3" else "swaymsg"
            subprocess.run(
                [reload_cmd, "reload"],
                capture_output=True, timeout=5,
            )

            return True, t("set_shortcut_active", key=key)

        except Exception as e:
            return False, f"Error: {e}"

    else:
        # GNOME, KDE, XFCE — instruções manuais
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


def apply_saved_shortcut():
    """Aplica o atalho salvo no WM (chamado no startup do app). Silencioso."""
    try:
        saved = get_metadata("shortcut", "")
        if saved:
            apply_shortcut(saved)
    except Exception:
        pass


class SettingsWindow(Gtk.Window):
    """Janela de configurações do app."""

    def __init__(self, parent: Gtk.Window):
        super().__init__(
            title=t("set_title", app=APP_NAME),
            transient_for=parent,
            modal=True,
            default_width=500,
            default_height=460,
        )
        self.set_resizable(False)
        self._wm = _detect_wm()
        self._tmpl = WM_TEMPLATES.get(self._wm, WM_TEMPLATES["generic"])
        self._build_ui()

    def _build_ui(self):
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14)
        main_box.set_margin_top(20)
        main_box.set_margin_bottom(20)
        main_box.set_margin_start(24)
        main_box.set_margin_end(24)
        self.set_child(main_box)

        # ─── Idioma ──────────────────────────────────────────────────

        lang_title = Gtk.Label()
        lang_title.set_markup(
            f"<span weight='bold' size='large'>{t('set_lang_title')}</span>"
        )
        lang_title.set_halign(Gtk.Align.START)
        main_box.append(lang_title)

        lang_desc = Gtk.Label(label=t("set_lang_desc"))
        lang_desc.set_halign(Gtk.Align.START)
        lang_desc.add_css_class("dim-label")
        main_box.append(lang_desc)

        lang_names = [name for _, name in LANGUAGES]
        self.lang_dropdown = Gtk.DropDown.new_from_strings(lang_names)

        from src.i18n import get_language
        current_lang = get_language()
        for i, (code, _) in enumerate(LANGUAGES):
            if code == current_lang:
                self.lang_dropdown.set_selected(i)
                break

        self.lang_dropdown.connect("notify::selected", self._on_lang_changed)
        main_box.append(self.lang_dropdown)

        lang_note = Gtk.Label()
        lang_note.set_markup(
            f"<span size='small'>{t('set_lang_note')}</span>"
        )
        lang_note.set_halign(Gtk.Align.START)
        lang_note.add_css_class("dim-label")
        main_box.append(lang_note)

        # ─── Separador ───────────────────────────────────────────────

        main_box.append(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL))

        # ─── Atalho de Teclado ───────────────────────────────────────

        shortcut_title = Gtk.Label()
        shortcut_title.set_markup(
            f"<span weight='bold' size='large'>{t('set_shortcut_title')}</span>"
        )
        shortcut_title.set_halign(Gtk.Align.START)
        main_box.append(shortcut_title)

        wm_label = Gtk.Label()
        wm_label.set_markup(t("set_wm_detected", wm=self._tmpl["name"]))
        wm_label.set_halign(Gtk.Align.START)
        main_box.append(wm_label)

        file_label = Gtk.Label()
        file_label.set_markup(
            f"<span size='small'>{t('set_wm_file', file=self._tmpl['file'])}</span>"
        )
        file_label.set_halign(Gtk.Align.START)
        file_label.add_css_class("dim-label")
        main_box.append(file_label)

        # Campo editável para o atalho
        shortcut_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)

        shortcut_label = Gtk.Label(label=t("set_shortcut_label"))
        shortcut_box.append(shortcut_label)

        saved_shortcut = get_metadata("shortcut", DEFAULT_SHORTCUT)
        self.shortcut_entry = Gtk.Entry()
        self.shortcut_entry.set_text(saved_shortcut)
        self.shortcut_entry.set_placeholder_text(t("set_shortcut_placeholder"))
        self.shortcut_entry.set_hexpand(True)
        self.shortcut_entry.connect("changed", self._on_shortcut_edited)
        shortcut_box.append(self.shortcut_entry)

        save_btn = Gtk.Button(label=t("set_save_shortcut"))
        save_btn.connect("clicked", self._on_save_shortcut)
        shortcut_box.append(save_btn)

        main_box.append(shortcut_box)

        # Instrução
        instruction_label = Gtk.Label(label=t("set_instruction"))
        instruction_label.set_halign(Gtk.Align.START)
        instruction_label.set_wrap(True)
        instruction_label.add_css_class("dim-label")
        main_box.append(instruction_label)

        # Comando gerado (frame)
        cmd_frame = Gtk.Frame()
        cmd_inner = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        cmd_inner.set_margin_top(8)
        cmd_inner.set_margin_bottom(8)
        cmd_inner.set_margin_start(10)
        cmd_inner.set_margin_end(10)

        gen_label = Gtk.Label()
        gen_label.set_markup(
            f"<span size='small'>{t('set_generated_cmd')}</span>"
        )
        gen_label.set_halign(Gtk.Align.START)
        gen_label.add_css_class("dim-label")
        cmd_inner.append(gen_label)

        self.cmd_label = Gtk.Label()
        self.cmd_label.set_halign(Gtk.Align.START)
        self.cmd_label.set_selectable(True)
        self.cmd_label.set_wrap(True)
        self._update_command_preview(saved_shortcut)
        cmd_inner.append(self.cmd_label)

        cmd_frame.set_child(cmd_inner)
        main_box.append(cmd_frame)

        # Botões
        btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        btn_box.set_halign(Gtk.Align.CENTER)

        copy_btn = Gtk.Button(label=t("set_copy_cmd"))
        copy_btn.connect("clicked", self._on_copy_cmd)
        btn_box.append(copy_btn)

        close_btn = Gtk.Button(label=t("set_close"))
        close_btn.connect("clicked", lambda b: self.close())
        btn_box.append(close_btn)

        main_box.append(btn_box)

        # Status
        self.status_label = Gtk.Label(label="")
        self.status_label.set_wrap(True)
        main_box.append(self.status_label)

    def _update_command_preview(self, shortcut: str):
        """Atualiza o preview do comando com o atalho atual."""
        cmd = self._tmpl["template"].format(key=shortcut)
        self.cmd_label.set_markup(f"<tt>{cmd}</tt>")
        self._current_cmd = cmd

    def _on_shortcut_edited(self, entry):
        """Atualiza preview quando o atalho é editado."""
        key = entry.get_text().strip() or DEFAULT_SHORTCUT
        self._update_command_preview(key)

    def _on_save_shortcut(self, button):
        """Salva o atalho escolhido e aplica no WM."""
        key = self.shortcut_entry.get_text().strip() or DEFAULT_SHORTCUT
        save_metadata("shortcut", key)

        # Aplicar no WM (insere no config e recarrega)
        success, message = apply_shortcut(key, self._wm)
        self.status_label.set_text(message)

    def _on_lang_changed(self, dropdown, _pspec):
        """Salva o idioma escolhido."""
        idx = dropdown.get_selected()
        if idx < len(LANGUAGES):
            code, name = LANGUAGES[idx]
            from src.i18n import save_language
            save_language(code)
            self.status_label.set_text(t("set_lang_changed", name=name))

    def _on_copy_cmd(self, button):
        """Copia o comando gerado para a área de transferência."""
        display = Gdk.Display.get_default()
        clipboard = display.get_clipboard()
        clipboard.set(self._current_cmd)
        self.status_label.set_text(t("set_copied"))
