"""
Filebrowser — Janela Sobre

Exibe informações sobre o aplicativo: versão, autor, história,
termos de uso e verificação de atualização.
"""

import subprocess
import threading

import gi
gi.require_version("Gtk", "4.0")
from gi.repository import Gtk, GLib

from src.config.settings import __version__
from src.i18n import t


# ─── Constantes ──────────────────────────────────────────────────────────────

APP_NAME = "Filebrowser"
APP_WEBSITE = "https://github.com/robsoncruz-dev/filebrowser"
APP_LICENSE = "MIT"
APP_AUTHOR = "Robson Cruz"
APP_EMAIL = "dev@example.com"  # MOCKUP

HISTORY_TEXT_PT = (
    "O Filebrowser nasceu de uma necessidade pessoal: encontrar PDFs "
    "rapidamente no meu sistema Arch Linux com i3wm.\n\n"
    "Navegar por pastas no gerenciador de arquivos era lento demais. "
    "Eu queria algo como o Spotlight do macOS — pressionar um atalho, "
    "digitar o nome, e pronto.\n\n"
    "O projeto começou como um script simples, evoluiu para uma aplicação "
    "GTK4 com indexação inteligente, suporte a nuvem via rclone, e busca "
    "instantânea.\n\n"
    "Se o Filebrowser facilita sua vida, fico feliz. Se quiser contribuir, "
    "acesse nosso repositório no GitHub. ❤"
)

HISTORY_TEXT_EN = (
    "Filebrowser was born from a personal need: finding PDFs quickly "
    "on my Arch Linux system with i3wm.\n\n"
    "Browsing through folders in the file manager was too slow. "
    "I wanted something like macOS Spotlight — press a shortcut, "
    "type the name, and done.\n\n"
    "The project started as a simple script and evolved into a GTK4 "
    "application with smart indexing, cloud support via rclone, and "
    "instant search.\n\n"
    "If Filebrowser makes your life easier, I'm happy. Want to contribute? "
    "Visit our GitHub repository. ❤"
)

TERMS_TEXT_PT = (
    "TERMOS DE USO\n\n"
    "Licença MIT\n\n"
    f"Copyright (c) 2026 {APP_AUTHOR}\n\n"
    "É concedida permissão, gratuitamente, a qualquer pessoa que obtenha "
    "uma cópia deste software e dos arquivos de documentação associados "
    "(o \"Software\"), para lidar com o Software sem restrições, incluindo "
    "sem limitação os direitos de usar, copiar, modificar, mesclar, publicar, "
    "distribuir, sublicenciar e/ou vender cópias do Software.\n\n"
    "O SOFTWARE É FORNECIDO \"NO ESTADO EM QUE SE ENCONTRA\", SEM GARANTIA "
    "DE QUALQUER TIPO."
)

TERMS_TEXT_EN = (
    "TERMS OF USE\n\n"
    "MIT License\n\n"
    f"Copyright (c) 2026 {APP_AUTHOR}\n\n"
    "Permission is hereby granted, free of charge, to any person obtaining "
    "a copy of this software and associated documentation files (the "
    "\"Software\"), to deal in the Software without restriction, including "
    "without limitation the rights to use, copy, modify, merge, publish, "
    "distribute, sublicense, and/or sell copies of the Software.\n\n"
    "THE SOFTWARE IS PROVIDED \"AS IS\", WITHOUT WARRANTY OF ANY KIND."
)


def _get_history():
    from src.i18n import get_language
    return HISTORY_TEXT_EN if get_language() == "en" else HISTORY_TEXT_PT


def _get_terms():
    from src.i18n import get_language
    return TERMS_TEXT_EN if get_language() == "en" else TERMS_TEXT_PT


class AboutWindow(Gtk.Window):
    def __init__(self, parent: Gtk.Window):
        super().__init__(
            title=t("about_title", app=APP_NAME),
            transient_for=parent,
            modal=True,
            default_width=480,
            default_height=420,
        )
        self.set_resizable(False)
        self._build_ui()

    def _build_ui(self):
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        main_box.set_margin_top(20)
        main_box.set_margin_bottom(20)
        main_box.set_margin_start(24)
        main_box.set_margin_end(24)
        self.set_child(main_box)

        title = Gtk.Label()
        title.set_markup(f"<span size='xx-large' weight='bold'>📄 {APP_NAME}</span>")
        main_box.append(title)

        ver = Gtk.Label(label=t("about_version", v=__version__))
        ver.add_css_class("dim-label")
        main_box.append(ver)

        desc = Gtk.Label(label=t("about_desc"))
        desc.set_wrap(True)
        main_box.append(desc)

        notebook = Gtk.Notebook()
        main_box.append(notebook)

        # Tab: History
        history_scroll = Gtk.ScrolledWindow()
        history_scroll.set_min_content_height(200)
        history_label = Gtk.Label(label=_get_history())
        history_label.set_wrap(True)
        history_label.set_margin_top(12)
        history_label.set_margin_bottom(12)
        history_label.set_margin_start(12)
        history_label.set_margin_end(12)
        history_label.set_valign(Gtk.Align.START)
        history_scroll.set_child(history_label)
        notebook.append_page(history_scroll, Gtk.Label(label=t("about_tab_history")))

        # Tab: Terms
        terms_scroll = Gtk.ScrolledWindow()
        terms_scroll.set_min_content_height(200)
        terms_label = Gtk.Label(label=_get_terms())
        terms_label.set_wrap(True)
        terms_label.set_margin_top(12)
        terms_label.set_margin_bottom(12)
        terms_label.set_margin_start(12)
        terms_label.set_margin_end(12)
        terms_label.set_valign(Gtk.Align.START)
        terms_label.set_selectable(True)
        terms_scroll.set_child(terms_label)
        notebook.append_page(terms_scroll, Gtk.Label(label=t("about_tab_terms")))

        btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        btn_box.set_halign(Gtk.Align.CENTER)
        main_box.append(btn_box)

        help_btn = Gtk.Button(label=t("about_help"))
        help_btn.connect("clicked", self._on_help)
        btn_box.append(help_btn)

        update_btn = Gtk.Button(label=t("about_check_update"))
        update_btn.connect("clicked", self._on_check_update)
        self._update_btn = update_btn
        btn_box.append(update_btn)

        close_btn = Gtk.Button(label=t("about_close"))
        close_btn.connect("clicked", lambda b: self.close())
        btn_box.append(close_btn)

        self.update_label = Gtk.Label(label="")
        self.update_label.set_wrap(True)
        main_box.append(self.update_label)

        author = Gtk.Label()
        author.set_markup(
            f"<span size='small'>{t('about_made_by', author=APP_AUTHOR)}</span>"
        )
        author.add_css_class("dim-label")
        main_box.append(author)

    def _on_help(self, button):
        try:
            subprocess.Popen(
                ["xdg-open", f"{APP_WEBSITE}#readme"],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            )
        except (FileNotFoundError, OSError):
            pass

    def _on_check_update(self, button):
        button.set_sensitive(False)
        self.update_label.set_text(t("about_checking"))

        def _check():
            try:
                import urllib.request
                import json
                url = f"https://api.github.com/repos/robsoncruz-dev/filebrowser/releases/latest"
                req = urllib.request.Request(url, headers={"User-Agent": APP_NAME})
                with urllib.request.urlopen(req, timeout=10) as resp:
                    data = json.loads(resp.read())
                    latest = data.get("tag_name", "").lstrip("v")
                if latest and latest != __version__:
                    GLib.idle_add(
                        self.update_label.set_text,
                        t("about_new_version", v=latest, url=f"{APP_WEBSITE}/releases"),
                    )
                else:
                    GLib.idle_add(
                        self.update_label.set_text,
                        t("about_up_to_date", v=__version__),
                    )
            except Exception:
                GLib.idle_add(self.update_label.set_text, t("about_check_error"))
            finally:
                GLib.idle_add(button.set_sensitive, True)

        threading.Thread(target=_check, daemon=True).start()
