#!/usr/bin/env python3
"""
Filebrowser — Ponto de Entrada

Launcher estilo Spotlight para busca e abertura de arquivos PDF no Zathura.
"""

import sys
import os

# ─── Configuração de Caminhos para Windows (Frozen/PyInstaller) ──────────────
if sys.platform == "win32" and getattr(sys, "frozen", False):
    base_path = sys._MEIPASS
    
    # Caminho para typelibs (Introspection)
    typelib_path = os.path.join(base_path, "lib", "girepository-1.0")
    if os.path.exists(typelib_path):
        os.environ["GI_TYPELIB_PATH"] = typelib_path
        
    # Caminho para GSettings Schemas
    schema_dir = os.path.join(base_path, "share", "glib-2.0", "schemas")
    if os.path.exists(schema_dir):
        os.environ["GSETTINGS_SCHEMA_DIR"] = schema_dir

from src.config.settings import load_config
from src.ui.window import FilebrowserApp


def main():
    """Inicia a aplicação Filebrowser."""
    config = load_config()
    app = FilebrowserApp(config)
    return app.run(sys.argv)


if __name__ == "__main__":
    sys.exit(main())
