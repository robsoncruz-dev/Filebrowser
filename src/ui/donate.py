"""
Filebrowser — Janela de Doação

Permite ao usuário contribuir com o projeto via PayPal, cripto ou PIX.
"""

import subprocess

import gi
gi.require_version("Gtk", "4.0")
from gi.repository import Gtk, Gdk

from src.ui.about import APP_NAME, APP_AUTHOR
from src.i18n import t


# ─── MOCKUP — Substituir antes de publicar ───────────────────────────────────

PAYPAL_URL = "https://paypal.me/seuusuario"          # MOCKUP
BTC_ADDRESS = "bc1qxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"  # MOCKUP
PIX_KEY = "seu@email.com"                             # MOCKUP


class DonateWindow(Gtk.Window):
    def __init__(self, parent: Gtk.Window):
        super().__init__(
            title=t("don_title", app=APP_NAME),
            transient_for=parent,
            modal=True,
            default_width=420,
            default_height=380,
        )
        self.set_resizable(False)
        self._build_ui()

    def _build_ui(self):
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        main_box.set_margin_top(24)
        main_box.set_margin_bottom(24)
        main_box.set_margin_start(24)
        main_box.set_margin_end(24)
        self.set_child(main_box)

        title = Gtk.Label()
        title.set_markup(f"<span size='x-large' weight='bold'>{t('don_header')}</span>")
        main_box.append(title)

        desc = Gtk.Label(label=t("don_desc", app=APP_NAME))
        desc.set_wrap(True)
        desc.set_justify(Gtk.Justification.CENTER)
        main_box.append(desc)

        # PayPal
        main_box.append(self._create_donate_row(
            t("don_paypal"), t("don_paypal_desc"), t("don_paypal_btn"), self._on_paypal,
        ))

        # Bitcoin
        main_box.append(self._create_copy_row(t("don_bitcoin"), BTC_ADDRESS))

        # PIX
        main_box.append(self._create_copy_row(t("don_pix"), PIX_KEY))

        self.status_label = Gtk.Label(label="")
        main_box.append(self.status_label)

        close_btn = Gtk.Button(label=t("don_close"))
        close_btn.set_halign(Gtk.Align.CENTER)
        close_btn.connect("clicked", lambda b: self.close())
        main_box.append(close_btn)

        thanks = Gtk.Label()
        thanks.set_markup(f"<span size='small'>{t('don_thanks', app=APP_NAME)}</span>")
        thanks.add_css_class("dim-label")
        main_box.append(thanks)

    def _create_donate_row(self, label_text, desc_text, btn_text, callback):
        frame = Gtk.Frame()
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        box.set_margin_top(8)
        box.set_margin_bottom(8)
        box.set_margin_start(12)
        box.set_margin_end(12)

        info = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        info.set_hexpand(True)
        name = Gtk.Label()
        name.set_halign(Gtk.Align.START)
        name.set_markup(f"<b>{label_text}</b>")
        info.append(name)
        d = Gtk.Label(label=desc_text)
        d.set_halign(Gtk.Align.START)
        d.add_css_class("dim-label")
        info.append(d)
        box.append(info)

        btn = Gtk.Button(label=btn_text)
        btn.set_valign(Gtk.Align.CENTER)
        btn.connect("clicked", callback)
        box.append(btn)

        frame.set_child(box)
        return frame

    def _create_copy_row(self, label_text, address):
        frame = Gtk.Frame()
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        box.set_margin_top(8)
        box.set_margin_bottom(8)
        box.set_margin_start(12)
        box.set_margin_end(12)

        info = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        info.set_hexpand(True)
        name = Gtk.Label()
        name.set_halign(Gtk.Align.START)
        name.set_markup(f"<b>{label_text}</b>")
        info.append(name)
        addr = Gtk.Label(label=address)
        addr.set_halign(Gtk.Align.START)
        addr.set_selectable(True)
        addr.set_ellipsize(2)
        addr.add_css_class("dim-label")
        info.append(addr)
        box.append(info)

        btn = Gtk.Button(label=t("don_copy"))
        btn.set_valign(Gtk.Align.CENTER)
        btn.connect("clicked", lambda b: self._copy_to_clipboard(address))
        box.append(btn)

        frame.set_child(box)
        return frame

    def _on_paypal(self, button):
        try:
            subprocess.Popen(
                ["xdg-open", PAYPAL_URL],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            )
        except (FileNotFoundError, OSError):
            self.status_label.set_text(t("don_browser_error"))

    def _copy_to_clipboard(self, text):
        display = Gdk.Display.get_default()
        clipboard = display.get_clipboard()
        clipboard.set(text)
        self.status_label.set_text(t("don_copied"))
