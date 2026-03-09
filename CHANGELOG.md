# Changelog

Todas as mudanças notáveis do projeto serão documentadas neste arquivo.

## [0.2.0] — 2026-03-08

### Adicionado
- ☁️ Montagem automática de nuvem via rclone
- 🔄 Indexação delta (compara mtime, sem re-scan total)
- 📊 Progresso percentual durante indexação
- 🕐 Timestamp da última indexação
- 🔔 Notificação desktop ao concluir indexação em 2º plano
- 📂 Profundidade separada para local (5) e nuvem (15)
- ℹ️ Janela "Sobre" com história, termos e verificação de atualização
- ✉ Formulário de feedback via email
- 💝 Janela de doação (PayPal, Bitcoin, PIX)
- 🌐 Detecção de WM (i3, Sway, GNOME, KDE)
- 📦 Instalador local (`scripts/install.sh`)

### Alterado
- Cache persistente: app inicia com dados do SQLite, sem re-scan automático
- Config path: `~/.config/filebrowser/config.toml` com fallback para projeto
- Nuvem não é mais desmontada ao fechar (disponível para Dolphin e outros)

## [0.1.0] — 2026-03-07

### Adicionado
- 🔍 Busca instantânea de PDFs
- 🗂️ Indexação com cache SQLite
- ☁️ Suporte a diretórios de nuvem
- 🖥️ System tray com AppIndicator3
- 🚫 Single instance via D-Bus
