# 📄 Filebrowser

**Launcher estilo Spotlight para busca e abertura de PDFs no Linux.**

Encontre qualquer PDF no seu sistema em milissegundos. Pressione um atalho de teclado, digite o nome, e pronto.

![GTK4](https://img.shields.io/badge/GTK-4.0-blue)
![Python](https://img.shields.io/badge/Python-3.10+-green)
![License](https://img.shields.io/badge/License-MIT-yellow)

## ✨ Features

- 🔍 **Busca instantânea** — encontre PDFs pelo nome, fácil e rápido
- ☁️ **Suporte a nuvem** — indexa OneDrive e Google Drive via rclone
- 🔄 **Indexação inteligente** — delta sync (só atualiza mudanças)
- 📊 **Progresso visual** — barra de progresso e percentual estimado
- 🖥️ **System tray** — roda em segundo plano com ícone na bandeja
- 🌐 **Compatível** — funciona em i3, Sway, GNOME, KDE, XFCE

## 📦 Instalação

### Dependências

| Pacote | Arch Linux | Ubuntu/Debian |
|---|---|---|
| Python 3.10+ | `python` | `python3` |
| PyGObject | `python-gobject` | `python3-gi` |
| GTK 4 | `gtk4` | `gir1.2-gtk-4.0` |
| Zathura *(recomendado)* | `zathura zathura-pdf-mupdf` | `zathura` |
| rclone *(opcional)* | `rclone` | `rclone` |

### Instalar

```bash
git clone https://github.com/robsoncruz-dev/filebrowser.git
cd filebrowser
bash scripts/install.sh
```

### Executar

```bash
filebrowser
```

## ⚙️ Configuração

O arquivo de configuração fica em `~/.config/filebrowser/config.toml`.

```toml
[geral]
leitor = "zathura"           # ou evince, okular, xdg-open
fechar_apos_abrir = true

[busca]
diretorios = ["~/Documentos", "~/Downloads"]
profundidade_local = 5
profundidade_nuvem = 15

# Nuvem (opcional)
[nuvem]
auto_montar = true
[nuvem.remotes]
onedrive = "~/Nuvem/OneDrive"
gdrive = "~/Nuvem/GoogleDrive"
```

## ⌨️ Atalho de Teclado

### i3wm / Sway

Adicione ao seu config:

```
bindsym $mod+Shift+f exec filebrowser
```

### GNOME

```bash
# Configurações → Teclado → Atalhos Personalizados
# Comando: filebrowser
```

## 🤝 Contribuir

Encontrou um bug? Tem uma sugestão? Use o menu **✉ Feedback** dentro do app ou abra uma [Issue](https://github.com/robsoncruz-dev/filebrowser/issues).

## 💝 Apoiar

Se o Filebrowser facilita sua vida, considere uma doação pelo menu **💝 Apoiar** dentro do app.

## 📜 Licença

MIT — veja [LICENSE](LICENSE).

---

*Feito com ❤ por [Robson Cruz](https://github.com/robsoncruz-dev)*
