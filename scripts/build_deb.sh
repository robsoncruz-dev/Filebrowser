#!/bin/bash
# ─────────────────────────────────────────────────────────
# Filebrowser — Debian (.deb) Package Builder
# ─────────────────────────────────────────────────────────
set -e

APP_NAME="filebrowser"
APP_VERSION="0.4.4"
ARCH="all" # Python scripts are architecture independent
DEB_NAME="${APP_NAME}_${APP_VERSION}_${ARCH}"
BUILD_DIR="build_deb"
PKG_DIR="${BUILD_DIR}/${APP_NAME}"

echo "📦 Building Debian Package ($DEB_NAME.deb)..."

# 1. Clean previous build
rm -rf "$BUILD_DIR"
mkdir -p "${PKG_DIR}/usr/bin"
mkdir -p "${PKG_DIR}/usr/share/${APP_NAME}"
mkdir -p "${PKG_DIR}/usr/share/applications"
mkdir -p "${PKG_DIR}/DEBIAN"

# 2. Copy source files
echo "  ↳ Copying source code..."
cp -r src "${PKG_DIR}/usr/share/${APP_NAME}/"

# 3. Create wrapper script in /usr/bin
echo "  ↳ Creating executable binary..."
cat > "${PKG_DIR}/usr/bin/${APP_NAME}" << 'EOF'
#!/bin/bash
export PYTHONPATH="/usr/share/filebrowser"
exec python3 -m src.main "$@"
EOF
chmod +x "${PKG_DIR}/usr/bin/${APP_NAME}"

# 4. Create .desktop entry
echo "  ↳ Generating desktop entry..."
cat > "${PKG_DIR}/usr/share/applications/${APP_NAME}.desktop" << EOF
[Desktop Entry]
Name=Filebrowser
Comment=Launcher de PDFs estilo Spotlight para Linux
Exec=/usr/bin/${APP_NAME}
Icon=document-open
Type=Application
Categories=Utility;Office;
Keywords=pdf;search;finder;documents;
StartupNotify=false
Terminal=false
EOF

# 5. Create Debian Control File
echo "  ↳ Generating DEBIAN/control file..."
# Dependencies: python3, gir1.2-gtk-4.0, python3-gi, zathura is optional but recommended
cat > "${PKG_DIR}/DEBIAN/control" << EOF
Package: ${APP_NAME}
Version: ${APP_VERSION}
Section: utils
Priority: optional
Architecture: ${ARCH}
Depends: python3 (>= 3.10), python3-gi, gir1.2-gtk-4.0
Suggests: zathura, rclone
Maintainer: Robson Cruz <your_email@example.com>
Description: Launcher de PDFs estilo Spotlight para Linux
 Encontra qualquer PDF no seu sistema em milissegundos. Pressione um
 atalho de teclado, digite o nome, e pronto.
EOF

# 6. Build the package
echo "  ↳ Running dpkg-deb --build..."
dpkg-deb --build --root-owner-group "${PKG_DIR}" "${BUILD_DIR}/${DEB_NAME}.deb"

echo ""
echo "✅ Build complete! Package is located at:"
echo "   ${BUILD_DIR}/${DEB_NAME}.deb"
echo ""
echo "📥 Users can install it via: sudo apt install ./${BUILD_DIR}/${DEB_NAME}.deb"
echo "   or double-clicking it in Ubuntu/Mint."
