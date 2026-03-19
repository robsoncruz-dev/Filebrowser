# ─────────────────────────────────────────────────────────
# Filebrowser — Windows Builder (PyInstaller + MSYS2)
# ─────────────────────────────────────────────────────────
# Este script deve ser executado em um terminal PowerShell
# Requisitos: MSYS2 instalado com ambiente UCRT64 configurado

$APP_NAME = "filebrowser"
$VERSION = "0.2.0"

Write-Host "📦 Iniciando build para Windows ($APP_NAME $VERSION)..." -ForegroundColor Cyan

# 1. Verificar se o PyInstaller está disponível (no ambiente MSYS2/Python)
# Nota: Supomos que o usuário já tenha configurado o ambiente conforme o README.md

if (!(Get-Command "pyinstaller" -ErrorAction SilentlyContinue)) {
    Write-Warning "⚠️ PyInstaller não encontrado no PATH. Tente instalar com: pip install pyinstaller"
    exit 1
}

# 2. Limpar builds anteriores
if (Test-Path "dist\") { Remove-Item -Recurse -Force "dist\" }
if (Test-Path "build\") { Remove-Item -Recurse -Force "build\" }

# 3. Executar o PyInstaller
# --windowed: Não abre terminal ao rodar (GUI)
# --add-data: Inclui arquivos de estilo e traduções
# --hidden-import: Garante que módulos dinâmicos sejam incluídos
Write-Host "  ↳ Rodando PyInstaller..." -ForegroundColor Yellow

pyinstaller --name "$APP_NAME" `
  --windowed `
  --noconfirm `
  --add-data "src/ui/styles.css;src/ui" `
  --add-data "src/locale;src/locale" `
  --hidden-import "src.i18n" `
  src/main.py

if ($LASTEXITCODE -ne 0) {
    Write-Error "❌ Falha na compilação do PyInstaller."
    exit $LASTEXITCODE
}

# 4. Tentar gerar o instalador (Inno Setup)
$ISCC = "C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
if (Test-Path $ISCC) {
    Write-Host "  ↳ Gerando instalador com Inno Setup..." -ForegroundColor Yellow
    & $ISCC scripts/installer.iss
} else {
    Write-Warning "⚠️ Inno Setup (ISCC.exe) não encontrado em $ISCC. O instalador .exe não será gerado."
}

# 5. Criar o arquivo compactado (como backup/alternativa)
$ZIP_NAME = "Filebrowser-$VERSION-Windows.zip"
Write-Host "  ↳ Criando arquivo $ZIP_NAME..." -ForegroundColor Yellow
Compress-Archive -Path dist\$APP_NAME\* -DestinationPath $ZIP_NAME -Force

Write-Host ""
Write-Host "✅ Build concluído com sucesso!" -ForegroundColor Green
Write-Host "📂 Arquivos disponíveis:"
if (Test-Path "scripts\Output\Filebrowser-$VERSION-Installer.exe") {
    Write-Host "   🚀 Instalador: scripts\Output\Filebrowser-$VERSION-Installer.exe"
}
Write-Host "   📦 Arquivo ZIP: $ZIP_NAME"
Write-Host "🚀 O executável portátil está em dist\$APP_NAME\"
