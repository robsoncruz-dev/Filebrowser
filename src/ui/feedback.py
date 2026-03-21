"""
Filebrowser — Janela de Feedback

Permite ao usuário enviar problemas, sugestões ou elogios
ao desenvolvedor via email (mailto:).
"""

import subprocess
import urllib.parse
import sys
import os

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, 
    QLineEdit, QTextEdit, QPushButton, QScrollArea
)
from PyQt6.QtCore import Qt

from src.config.settings import __version__
from src.ui.about import APP_NAME, APP_EMAIL
from src.i18n import t

class FeedbackWindow(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(t("fb_title", app=APP_NAME))
        self.setFixedSize(440, 380)
        self.setModal(True)
        self._build_ui()

    def _build_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(24, 20, 24, 20)
        main_layout.setSpacing(12)

        title = QLabel(f"<b>{t('fb_header')}</b>")
        title.setStyleSheet("font-size: 16px;")
        main_layout.addWidget(title)

        desc = QLabel(t("fb_desc"))
        desc.setWordWrap(True)
        main_layout.addWidget(desc)

        # Type
        type_layout = QHBoxLayout()
        type_label = QLabel(t("fb_type"))
        type_layout.addWidget(type_label)

        self._fb_types = [t("fb_bug"), t("fb_suggestion"), t("fb_praise"), t("fb_other")]
        self.type_dropdown = QComboBox()
        self.type_dropdown.addItems(self._fb_types)
        type_layout.addWidget(self.type_dropdown, stretch=1)
        main_layout.addLayout(type_layout)

        # Email
        email_layout = QHBoxLayout()
        email_label = QLabel(t("fb_email"))
        email_layout.addWidget(email_label)

        self.email_entry = QLineEdit()
        self.email_entry.setPlaceholderText(t("fb_email_placeholder"))
        email_layout.addWidget(self.email_entry, stretch=1)
        main_layout.addLayout(email_layout)

        # Message
        msg_label = QLabel(t("fb_message"))
        main_layout.addWidget(msg_label)

        self.msg_view = QTextEdit()
        main_layout.addWidget(self.msg_view)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.setAlignment(Qt.AlignmentFlag.AlignRight)

        cancel_btn = QPushButton(t("fb_cancel"))
        cancel_btn.clicked.connect(self.accept)
        btn_layout.addWidget(cancel_btn)

        send_btn = QPushButton(t("fb_send"))
        send_btn.setProperty("class", "suggested-action")
        send_btn.clicked.connect(self._on_send)
        btn_layout.addWidget(send_btn)

        main_layout.addLayout(btn_layout)

        self.status_label = QLabel("")
        self.status_label.setWordWrap(True)
        main_layout.addWidget(self.status_label)

    def _on_send(self):
        type_idx = self.type_dropdown.currentIndex()
        feedback_type = self._fb_types[type_idx] if type_idx < len(self._fb_types) else "?"

        message = self.msg_view.toPlainText().strip()
        user_email = self.email_entry.text().strip()

        if not message:
            self.status_label.setText(t("fb_empty_warning"))
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
            from PyQt6.QtGui import QDesktopServices
            from PyQt6.QtCore import QUrl
            QDesktopServices.openUrl(QUrl(mailto))
            self.status_label.setText(t("fb_success"))
        except Exception:
            self.status_label.setText(t("fb_error"))
