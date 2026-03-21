#!/usr/bin/env python3
"""
Filebrowser — Ponto de Entrada

Launcher estilo Spotlight para busca e abertura de arquivos PDF no Zathura.
"""

import sys
import os

# PyInstaller PyQt6 handles paths automatically, no MSYS2 injections needed.

from src.config.settings import load_config
from src.ui.window import FilebrowserApp


def main():
    """Inicia a aplicação Filebrowser."""
    config = load_config()
    app = FilebrowserApp(config)
    return app.run(sys.argv)


if __name__ == "__main__":
    sys.exit(main())
