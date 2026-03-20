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
    
    # 1. Typelibs (Introspection)
    os.environ["GI_TYPELIB_PATH"] = os.path.join(base_path, "lib", "girepository-1.0")

    # 2. GSettings Schemas
    os.environ["GSETTINGS_SCHEMA_DIR"] = os.path.join(base_path, "share", "glib-2.0", "schemas")

    # 3. GdkPixbuf (Loaders)
    # Procurar o loaders.cache dinamicamente na pasta lib/gdk-pixbuf-2.0
    pixbuf_path = os.path.join(base_path, "lib", "gdk-pixbuf-2.0")
    if os.path.exists(pixbuf_path):
        for root, dirs, files in os.walk(pixbuf_path):
            if "loaders.cache" in files:
                os.environ["GDK_PIXBUF_MODULE_FILE"] = os.path.join(root, "loaders.cache")
                break
        os.environ["GDK_PIXBUF_MODULEDIR"] = pixbuf_path

    # 4. Icones e Temas (XDG)
    os.environ["XDG_DATA_DIRS"] = os.path.join(base_path, "share")
    
    # 5. GTK Base Path
    os.environ["GTK_EXE_PREFIX"] = base_path
    os.environ["GTK_DATA_PREFIX"] = base_path

from src.config.settings import load_config
from src.ui.window import FilebrowserApp


def main():
    """Inicia a aplicação Filebrowser."""
    config = load_config()
    app = FilebrowserApp(config)
    return app.run(sys.argv)


if __name__ == "__main__":
    sys.exit(main())
