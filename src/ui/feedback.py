"""
Filebrowser — Janela de Feedback

Permite ao usuário enviar problemas, sugestões ou elogios
ao desenvolvedor via email (mailto:).
"""

import subprocess
import urllib.parse
import sys
import os

import gi
gi.require_version("Gtk", "4.0")
from gi.repository import Gtk

from src.config.settings import __version__
from src.ui.about import APP_NAME, APP_EMAIL
from src.i18n import t


class FeedbackWindow(Gtk.Window):
    def __init__(self, parent: Gtk.Window):
        super().__init__(
            title=t("fb_title", app=APP_NAME),
            transient_for=parent,
            modal=True,
            default_width=440,
            default_height=380,
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
        title.set_markup(f"<span size='large' weight='bold'>{t('fb_header')}</span>")
        main_box.append(title)

        desc = Gtk.Label(label=t("fb_desc"))
        desc.set_wrap(True)
        main_box.append(desc)

        # Type
        type_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        type_label = Gtk.Label(label=t("fb_type"))
        type_box.append(type_label)

        self._fb_types = [t("fb_bug"), t("fb_suggestion"), t("fb_praise"), t("fb_other")]
        self.type_dropdown = Gtk.DropDown.new_from_strings(self._fb_types)
        self.type_dropdown.set_selected(0)
        self.type_dropdown.set_hexpand(True)
        type_box.append(self.type_dropdown)
        main_box.append(type_box)

        # Email
        email_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        email_label = Gtk.Label(label=t("fb_email"))
        email_box.append(email_label)

        self.email_entry = Gtk.Entry()
        self.email_entry.set_placeholder_text(t("fb_email_placeholder"))
        self.email_entry.set_hexpand(True)
        email_box.append(self.email_entry)
        main_box.append(email_box)

        # Message
        msg_label = Gtk.Label(label=t("fb_message"))
        msg_label.set_halign(Gtk.Align.START)
        main_box.append(msg_label)

        msg_scroll = Gtk.ScrolledWindow()
        msg_scroll.set_min_content_height(120)
        msg_scroll.set_vexpand(True)

        self.msg_view = Gtk.TextView()
        self.msg_view.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        self.msg_view.set_top_margin(8)
        self.msg_view.set_left_margin(8)
        self.msg_view.set_right_margin(8)
        self.msg_view.set_bottom_margin(8)
        msg_scroll.set_child(self.msg_view)
        main_box.append(msg_scroll)

        # Buttons
        btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        btn_box.set_halign(Gtk.Align.END)
        main_box.append(btn_box)

        cancel_btn = Gtk.Button(label=t("fb_cancel"))
        cancel_btn.connect("clicked", lambda b: self.close())
        btn_box.append(cancel_btn)

        send_btn = Gtk.Button(label=t("fb_send"))
        send_btn.add_css_class("suggested-action")
        send_btn.connect("clicked", self._on_send)
        btn_box.append(send_btn)

        self.status_label = Gtk.Label(label="")
        self.status_label.set_wrap(True)
        main_box.append(self.status_label)

    def _on_send(self, button):
        type_idx = self.type_dropdown.get_selected()
        feedback_type = self._fb_types[type_idx] if type_idx < len(self._fb_types) else "?"

        buffer = self.msg_view.get_buffer()
        start, end = buffer.get_bounds()
        message = buffer.get_text(start, end, True).strip()
        user_email = self.email_entry.get_text().strip()

        if not message:
            self.status_label.set_text(t("fb_empty_warning"))
            return

        subject = f"[{APP_NAME} {__version__}] {feedback_type}"
        body = f"Type: {feedback_type}\n"
        if user_email:
            body += f"Reply: {user_email}\n"
        body += f"Version: {__version__}\n\n{'='*40}\n\n{message}"

        mailto = (
            f"mailto:{APP_EMAIL}"
            f"?subject={urllib.parse.quote(subject)}"
            f"&body={urllib.parse.quote(body)}"
        )

        try:
            if sys.platform == "win32":
                os.startfile(mailto)
            else:
                subprocess.Popen(
                    ["xdg-open", mailto],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                )
            self.status_label.set_text(t("fb_success"))
        except (FileNotFoundError, OSError):
            self.status_label.set_text(t("fb_error"))
