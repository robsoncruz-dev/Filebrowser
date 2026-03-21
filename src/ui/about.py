"""
Filebrowser — Janela Sobre

Exibe informações sobre o aplicativo: versão, autor, história,
termos de uso e verificação de atualização.
"""

import subprocess
import sys
import os
import threading

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QTabWidget, QScrollArea, QWidget
)
from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtGui import QDesktopServices

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
    "altamente responsiva, com suporte a nuvem via rclone e busca "
    "instantânea nativa.\n\n"
    "Se o Filebrowser facilita sua vida, fico feliz. Se quiser contribuir, "
    "acesse nosso repositório no GitHub. ❤"
)

HISTORY_TEXT_EN = (
    "Filebrowser was born from a personal need: finding PDFs quickly "
    "on my Arch Linux system with i3wm.\n\n"
    "Browsing through folders in the file manager was too slow. "
    "I wanted something like macOS Spotlight — press a shortcut, "
    "type the name, and done.\n\n"
    "The project started as a simple script and evolved into a robust "
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


class AboutWindow(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(t("about_title", app=APP_NAME))
        self.setFixedSize(480, 420)
        self.setModal(True)
        self._build_ui()

    def _build_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(24, 20, 24, 20)
        main_layout.setSpacing(12)

        title = QLabel(f"📄 {APP_NAME}")
        title.setStyleSheet("font-size: 24px; font-weight: bold;")
        main_layout.addWidget(title)

        ver = QLabel(t("about_version", v=__version__))
        ver.setProperty("class", "dim-label")
        main_layout.addWidget(ver)

        desc = QLabel(t("about_desc"))
        desc.setWordWrap(True)
        main_layout.addWidget(desc)

        tabs = QTabWidget()
        main_layout.addWidget(tabs)

        history_widget = QWidget()
        history_layout = QVBoxLayout(history_widget)
        history_label = QLabel(_get_history())
        history_label.setWordWrap(True)
        history_label.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        history_scroll = QScrollArea()
        history_scroll.setWidgetResizable(True)
        history_scroll.setWidget(history_label)
        history_layout.addWidget(history_scroll)
        history_layout.setContentsMargins(0, 0, 0, 0)
        tabs.addTab(history_widget, t("about_tab_history"))

        terms_widget = QWidget()
        terms_layout = QVBoxLayout(terms_widget)
        terms_label = QLabel(_get_terms())
        terms_label.setWordWrap(True)
        terms_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        terms_label.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        terms_scroll = QScrollArea()
        terms_scroll.setWidgetResizable(True)
        terms_scroll.setWidget(terms_label)
        terms_layout.addWidget(terms_scroll)
        terms_layout.setContentsMargins(0, 0, 0, 0)
        tabs.addTab(terms_widget, t("about_tab_terms"))

        btn_layout = QHBoxLayout()
        btn_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addLayout(btn_layout)

        help_btn = QPushButton(t("about_help"))
        help_btn.clicked.connect(self._on_help)
        btn_layout.addWidget(help_btn)

        self.update_btn = QPushButton(t("about_check_update"))
        self.update_btn.clicked.connect(self._on_check_update)
        btn_layout.addWidget(self.update_btn)

        close_btn = QPushButton(t("about_close"))
        close_btn.clicked.connect(self.accept)
        btn_layout.addWidget(close_btn)

        self.update_label = QLabel("")
        self.update_label.setWordWrap(True)
        main_layout.addWidget(self.update_label)

        author = QLabel(t("about_made_by", author=APP_AUTHOR))
        author.setStyleSheet("font-size: 11px;")
        author.setProperty("class", "dim-label")
        main_layout.addWidget(author)

    def _on_help(self):
        QDesktopServices.openUrl(QUrl(f"{APP_WEBSITE}#readme"))

    def _on_check_update(self):
        self.update_btn.setEnabled(False)
        self.update_label.setText(t("about_checking"))

        def _check():
            try:
                import urllib.request
                import json
                url = f"https://api.github.com/repos/robsoncruz-dev/filebrowser/releases/latest"
                req = urllib.request.Request(url, headers={"User-Agent": APP_NAME})
                with urllib.request.urlopen(req, timeout=10) as resp:
                    data = json.loads(resp.read())
                    latest = data.get("tag_name", "").lstrip("v")
                
                from PyQt6.QtCore import QMetaObject, Q_ARG
                if latest and latest != __version__:
                    QMetaObject.invokeMethod(self.update_label, "setText", 
                        Qt.ConnectionType.QueuedConnection, 
                        Q_ARG(str, t("about_new_version", v=latest, url=f"{APP_WEBSITE}/releases"))
                    )
                else:
                    QMetaObject.invokeMethod(self.update_label, "setText", 
                        Qt.ConnectionType.QueuedConnection, 
                        Q_ARG(str, t("about_up_to_date", v=__version__))
                    )
            except Exception:
                from PyQt6.QtCore import QMetaObject, Q_ARG
                QMetaObject.invokeMethod(self.update_label, "setText", 
                    Qt.ConnectionType.QueuedConnection, 
                    Q_ARG(str, t("about_check_error"))
                )
            finally:
                from PyQt6.QtCore import QMetaObject, Q_ARG
                QMetaObject.invokeMethod(self.update_btn, "setEnabled", 
                    Qt.ConnectionType.QueuedConnection, 
                    Q_ARG(bool, True)
                )

        threading.Thread(target=_check, daemon=True).start()
