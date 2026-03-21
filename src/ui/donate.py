"""
Filebrowser — Janela de Doação

Permite ao usuário contribuir com o projeto via PayPal, cripto ou PIX.
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QFrame, QApplication
)
from PyQt6.QtCore import Qt

from src.ui.about import APP_NAME, APP_AUTHOR
from src.i18n import t

# ─── MOCKUP — Substituir antes de publicar ───────────────────────────────────

PAYPAL_URL = "https://paypal.me/seuusuario"          # MOCKUP
BTC_ADDRESS = "bc1qxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"  # MOCKUP
PIX_KEY = "seu@email.com"                             # MOCKUP


class DonateWindow(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(t("don_title", app=APP_NAME))
        self.setFixedSize(420, 380)
        self.setModal(True)
        self._build_ui()

    def _build_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(24, 24, 24, 24)
        main_layout.setSpacing(16)

        title = QLabel(f"<b>{t('don_header')}</b>")
        title.setStyleSheet("font-size: 20px;")
        main_layout.addWidget(title)

        desc = QLabel(t("don_desc", app=APP_NAME))
        desc.setWordWrap(True)
        desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(desc)

        # PayPal
        main_layout.addWidget(self._create_donate_row(
            t("don_paypal"), t("don_paypal_desc"), t("don_paypal_btn"), self._on_paypal
        ))

        # Bitcoin
        main_layout.addWidget(self._create_copy_row(t("don_bitcoin"), BTC_ADDRESS))

        # PIX
        main_layout.addWidget(self._create_copy_row(t("don_pix"), PIX_KEY))

        self.status_label = QLabel("")
        main_layout.addWidget(self.status_label)

        close_btn = QPushButton(t("don_close"))
        close_btn.clicked.connect(self.accept)
        btn_layout = QHBoxLayout()
        btn_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        btn_layout.addWidget(close_btn)
        main_layout.addLayout(btn_layout)

        thanks = QLabel(t("don_thanks", app=APP_NAME))
        thanks.setStyleSheet("font-size: 11px;")
        thanks.setProperty("class", "dim-label")
        main_layout.addWidget(thanks)

    def _create_donate_row(self, label_text, desc_text, btn_text, callback):
        frame = QFrame()
        frame.setFrameShape(QFrame.Shape.StyledPanel)
        box = QHBoxLayout(frame)
        box.setContentsMargins(12, 8, 12, 8)
        box.setSpacing(12)

        info = QVBoxLayout()
        info.setSpacing(2)
        name = QLabel(f"<b>{label_text}</b>")
        info.addWidget(name)
        d = QLabel(desc_text)
        d.setProperty("class", "dim-label")
        info.addWidget(d)
        box.addLayout(info, stretch=1)

        btn = QPushButton(btn_text)
        btn.clicked.connect(callback)
        box.addWidget(btn)

        return frame

    def _create_copy_row(self, label_text, address):
        frame = QFrame()
        frame.setFrameShape(QFrame.Shape.StyledPanel)
        box = QHBoxLayout(frame)
        box.setContentsMargins(12, 8, 12, 8)
        box.setSpacing(12)

        info = QVBoxLayout()
        info.setSpacing(2)
        name = QLabel(f"<b>{label_text}</b>")
        info.addWidget(name)
        addr = QLabel(address)
        addr.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        addr.setProperty("class", "dim-label")
        info.addWidget(addr)
        box.addLayout(info, stretch=1)

        btn = QPushButton(t("don_copy"))
        btn.clicked.connect(lambda: self._copy_to_clipboard(address))
        box.addWidget(btn)

        return frame

    def _on_paypal(self):
        try:
            from PyQt6.QtGui import QDesktopServices
            from PyQt6.QtCore import QUrl
            QDesktopServices.openUrl(QUrl(PAYPAL_URL))
        except Exception:
            self.status_label.setText(t("don_browser_error"))

    def _copy_to_clipboard(self, text):
        clipboard = QApplication.clipboard()
        clipboard.setText(text)
        self.status_label.setText(t("don_copied"))
