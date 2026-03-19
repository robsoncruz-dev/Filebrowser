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

### Método 1: O Mais Fácil (Recomendado)

Se você quer a experiência mais simples possível, baixe os pacotes prontos na página de **Releases** do GitHub:

#### 🟢 Ubuntu, Linux Mint, Pop!_OS, Debian
Baixe o arquivo **`.deb`** e dê um clique duplo. A loja de aplicativos do seu sistema vai abrir e você só precisa clicar em **"Instalar"**.

#### 🪟 Windows
Baixe o arquivo **`-Installer.exe`** na página de Releases. Basta executar o instalador e seguir as instruções. Ele criará atalhos no Menu Iniciar e na Área de Trabalho para você.

#### 🔵 Qualquer outro Linux (Fedora, Arch Linux, etc)
Baixe o arquivo **`.AppImage`**. Clique com o botão direito nele, vá em **Propriedades → Permissões** e marque "Permitir execução como programa". Depois, basta dar dois cliques para abrir!

---

### Método 2: Instalação Manual via Terminal (Avançado)

Se preferir instalar direto do código fonte:

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

## 🪟 Windows (Compilação)

O Filebrowser é compatível com Windows via **MSYS2**. Para compilar seu próprio executável `.exe`:

### Pré-requisitos

1. Instale o [MSYS2](https://www.msys2.org/).
2. Abra o terminal **MSYS2 UCRT64** e instale as dependências:
   ```bash
   pacman -S mingw-w64-ucrt-x86_64-gcc mingw-w64-ucrt-x86_64-gtk4 \
             mingw-w64-ucrt-x86_64-python3 mingw-w64-ucrt-x86_64-python-gobject \
             mingw-w64-ucrt-x86_64-python-pip
   ```
3. Instale o PyInstaller:
   ```bash
   pip install pyinstaller
   ```

### Compilando

No terminal MSYS2 (ou PowerShell com o PATH do MSYS2 configurado), execute:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/build_windows.ps1
```

O executável será gerado na pasta `dist/filebrowser/` e um arquivo `.zip` será criado na raiz do projeto.

---

## 🤝 Contribuir

Encontrou um bug? Tem uma sugestão? Use o menu **✉ Feedback** dentro do app ou abra uma [Issue](https://github.com/robsoncruz-dev/filebrowser/issues).

## 💝 Apoiar

Se o Filebrowser facilita sua vida, considere uma doação pelo menu **💝 Apoiar** dentro do app.

## 📜 Licença

MIT — veja [LICENSE](LICENSE).

---

*Feito com ❤ por [Robson Cruz](https://github.com/robsoncruz-dev)*
