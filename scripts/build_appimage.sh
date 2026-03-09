#!/bin/bash
# ─────────────────────────────────────────────────────────
# Filebrowser — AppImage Builder
# ─────────────────────────────────────────────────────────
set -e

APP_NAME="Filebrowser"
APP_VERSION="0.2.0"
ARCH="$(uname -m)"
BUILD_DIR="build_appimage"
APPDIR="${BUILD_DIR}/${APP_NAME}.AppDir"

echo "📦 Building AppImage ($APP_NAME-$APP_VERSION-$ARCH.AppImage)..."

# 1. Clean previous build
rm -rf "$BUILD_DIR"
mkdir -p "$APPDIR/usr/bin"
mkdir -p "$APPDIR/usr/share/applications"
mkdir -p "$APPDIR/usr/share/icons/hicolor/scalable/apps"

# 2. Get linuxdeploy and python plugin
echo "  ↳ Downloading linuxdeploy tools..."
if [ ! -f "linuxdeploy-x86_64.AppImage" ]; then
    wget -qO linuxdeploy-x86_64.AppImage https://github.com/linuxdeploy/linuxdeploy/releases/download/continuous/linuxdeploy-x86_64.AppImage
    chmod +x linuxdeploy-x86_64.AppImage
fi

# We use the official python appimage builder tool for Python apps
echo "  ↳ Setting up Python AppImage builder (python-appimage)..."
if ! python3 -m pip show python-appimage &> /dev/null; then
    python3 -m pip install --user python-appimage
fi

export PATH="$HOME/.local/bin:$PATH"

# 3. Prepare AppDir structure
echo "  ↳ Preparing AppDir with python-appimage..."
python3 -m python_appimage build app --python-version 3.10 $APPDIR

echo "  ↳ Copying app source..."
mkdir -p "$APPDIR/opt/filebrowser"
cp -r src "$APPDIR/opt/filebrowser/"

# 4. Create AppRun script
echo "  ↳ Creating AppRun entry point..."
cat > "$APPDIR/AppRun" << 'EOF'
#!/bin/bash
HERE="$(dirname "$(readlink -f "${0}")")"
export PYTHONPATH="${HERE}/opt/filebrowser:${PYTHONPATH}"

# We assume the host system has GTK4 installed (as packaging it makes AppImage HUGE)
# But we use the bundled Python to run our app
exec "${HERE}/opt/python3.10/bin/python3" -m src.main "$@"
EOF
chmod +x "$APPDIR/AppRun"

# 5. Create Desktop Entry and Icon
echo "  ↳ Creating .desktop and icon..."
cat > "$APPDIR/filebrowser.desktop" << EOF
[Desktop Entry]
Name=Filebrowser
Comment=Launcher de PDFs estilo Spotlight para Linux
Exec=AppRun
Icon=filebrowser
Type=Application
Categories=Utility;Office;
EOF
# Just a placeholder icon (we can use the default document icon)
touch "$APPDIR/filebrowser.svg"

# 6. Build the final AppImage using linuxdeploy
echo "  ↳ Generating final AppImage using linuxdeploy..."
./linuxdeploy-x86_64.AppImage --appdir "$APPDIR" --output appimage \
    --desktop-file "$APPDIR/filebrowser.desktop" \
    --icon-file "$APPDIR/filebrowser.svg"

mv Filebrowser*.AppImage "Filebrowser-${APP_VERSION}-${ARCH}.AppImage"

echo ""
echo "✅ Build complete! AppImage is ready at:"
echo "   Filebrowser-${APP_VERSION}-${ARCH}.AppImage"
