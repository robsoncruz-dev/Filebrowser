#!/bin/bash
# ─────────────────────────────────────────────────────────
# Filebrowser — Instalador Local para Linux
# ─────────────────────────────────────────────────────────
set -e

APP_NAME="Filebrowser"
APP_VERSION="0.3.0"
INSTALL_DIR="$HOME/.local/share/filebrowser"
BIN_DIR="$HOME/.local/bin"
CONFIG_DIR="$HOME/.config/filebrowser"
DESKTOP_DIR="$HOME/.local/share/applications"

echo "📄 $APP_NAME $APP_VERSION — Instalador"
echo "════════════════════════════════════════"
echo ""

# ─── 1. Verificar dependências ───────────────────────────

echo "🔍 Verificando dependências..."
ERRORS=0

check_cmd() {
    if command -v "$1" &>/dev/null; then
        echo "  ✅ $2"
    else
        if [ "$3" = "required" ]; then
            echo "  ❌ $2 (OBRIGATÓRIO)"
            ERRORS=$((ERRORS + 1))
        else
            echo "  ⚠️  $2 (opcional)"
        fi
    fi
}

check_cmd python3 "Python 3" required

if python3 -c "import PyQt6" 2>/dev/null; then
    echo "  ✅ PyQt6"
else
    echo "  ❌ PyQt6 (OBRIGATÓRIO)"
    echo "     Instale: sudo pacman -S python-pyqt6           (Arch)"
    echo "              sudo apt install python3-pyqt6          (Ubuntu/Debian)"
    ERRORS=$((ERRORS + 1))
fi

check_cmd zathura "Zathura (leitor PDF)" optional
check_cmd rclone "rclone (nuvem)" optional
check_cmd notify-send "libnotify (notificações)" optional

echo ""

if [ $ERRORS -gt 0 ]; then
    echo "❌ $ERRORS dependência(s) obrigatória(s) faltando."
    echo "   Instale as dependências acima e rode novamente."
    exit 1
fi

echo "✅ Dependências OK"
echo ""

# ─── 2. Detectar diretório fonte ──────────────────────────

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SRC_DIR="$(dirname "$SCRIPT_DIR")"

if [ ! -d "$SRC_DIR/src" ]; then
    echo "❌ Diretório src/ não encontrado em $SRC_DIR"
    echo "   Execute este script de dentro do projeto."
    exit 1
fi

# ─── 3. Instalar arquivos ────────────────────────────────

echo "📦 Instalando em $INSTALL_DIR..."
mkdir -p "$INSTALL_DIR" "$BIN_DIR" "$CONFIG_DIR" "$DESKTOP_DIR"

# Copiar código fonte
rm -rf "$INSTALL_DIR/src"
cp -r "$SRC_DIR/src" "$INSTALL_DIR/"

# Criar launcher
cat > "$BIN_DIR/filebrowser" << 'LAUNCHER'
#!/bin/bash
cd "$HOME/.local/share/filebrowser"
exec python3 -m src.main "$@"
LAUNCHER
chmod +x "$BIN_DIR/filebrowser"

# Copiar config de exemplo (se não existir config do usuário)
if [ ! -f "$CONFIG_DIR/config.toml" ]; then
    cp "$SRC_DIR/config.example.toml" "$CONFIG_DIR/config.toml"
    echo "  📝 Config criado em $CONFIG_DIR/config.toml"
else
    echo "  📝 Config existente preservado"
fi

# ─── 4. Criar .desktop entry ─────────────────────────────

cat > "$DESKTOP_DIR/filebrowser.desktop" << EOF
[Desktop Entry]
Name=Filebrowser
Comment=Launcher de PDFs estilo Spotlight para Linux
Exec=$BIN_DIR/filebrowser
Icon=document-open
Type=Application
Categories=Utility;Office;
Keywords=pdf;search;finder;documents;
StartupNotify=false
Terminal=false
EOF

echo "  🖥️  Atalho criado no menu de aplicativos"

# ─── 5. Verificar PATH ───────────────────────────────────

if [[ ":$PATH:" != *":$BIN_DIR:"* ]]; then
    echo ""
    echo "⚠️  $BIN_DIR não está no seu PATH."
    echo "   Adicione ao seu ~/.bashrc ou ~/.zshrc:"
    echo "   export PATH=\"\$HOME/.local/bin:\$PATH\""
fi

# ─── 6. Concluído ────────────────────────────────────────

echo ""
echo "═══════════════════════════════════════════"
echo "✅ $APP_NAME $APP_VERSION instalado!"
echo ""
echo "   Executar:      filebrowser"
echo "   Configuração:  $CONFIG_DIR/config.toml"
echo "   Desinstalar:   rm -rf $INSTALL_DIR $BIN_DIR/filebrowser"
echo "                  rm -f $DESKTOP_DIR/filebrowser.desktop"
echo "═══════════════════════════════════════════"
