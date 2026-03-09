"""
Filebrowser — Internacionalização (i18n)

Sistema de tradução baseado em dicionários.
Idiomas suportados: pt_BR (padrão), en.
"""

# ─── Dicionários de Tradução ─────────────────────────────────────────────────

TRANSLATIONS = {
    "pt_BR": {
        # ── Window ──
        "search_placeholder": "  Buscar PDF...",
        "no_indexed": "Nenhum PDF indexado — clique 🔄 para indexar",
        "indexing_local": "⚡ Indexando pastas locais...",
        "mounting_cloud": "☁ Montando nuvem...",
        "indexing_cloud": "☁ Indexando nuvem... (pode demorar)",
        "cloud_slow": "☁ Nuvem lenta... (aguardando)",
        "cloud_unavailable": "⚠ Nuvem indisponível",
        "cloud_background": "⚠ Nuvem lenta — indexando em 2º plano",
        "last": "Última",
        "counter": "📂 {local} locais  ·  ☁ {cloud} nuvem",
        "counter_progress": "📂 {local} locais  ·  ☁ {cloud} / ~{ref} nuvem ({pct}%)",
        "results_found": "  {n} resultado(s) encontrado(s)",
        "no_results": "Nenhum PDF encontrado",
        "reindex_tooltip": "Re-indexar PDFs",
        "indexing_warning": "⚠ Indexação em andamento.",
        "continue_bg": "Continuar em 2º plano",
        "exit_prompt": "Sair",
        "notification_title": "📄 Filebrowser",
        "notification_body": "Indexação concluída — {n} PDFs encontrados",
        "pdfs_available": "{n} PDFs locais disponíveis",

        # ── Tray ──
        "tray_title": "📂 Filebrowser",
        "tray_show": "Mostrar janela",
        "tray_reindex": "🔄 Re-indexar",
        "tray_settings": "⚙ Configurações",
        "tray_about": "ℹ️ Sobre",
        "tray_feedback": "✉ Feedback",
        "tray_donate": "💝 Apoiar",
        "tray_quit": "Fechar FileBrowser-pdf",
        "tray_indexing": "⏳ Indexando... ({local}L / {cloud}N)",
        "tray_indexed": "📂 {n} PDFs indexados",

        # ── About ──
        "about_title": "Sobre — {app}",
        "about_version": "Versão {v}",
        "about_desc": "Launcher de PDFs estilo Spotlight para Linux",
        "about_tab_history": "📖 História",
        "about_tab_terms": "📄 Termos",
        "about_help": "❓ Ajuda",
        "about_check_update": "🔄 Verificar Atualização",
        "about_close": "Fechar",
        "about_checking": "Verificando...",
        "about_new_version": "🆕 Nova versão disponível: {v}\nBaixar em: {url}",
        "about_up_to_date": "✅ Você está na versão mais recente ({v})",
        "about_check_error": "⚠ Não foi possível verificar. Verifique sua conexão.",
        "about_made_by": "Feito com ❤ por {author}",

        # ── Feedback ──
        "fb_title": "Feedback — {app}",
        "fb_header": "✉ Enviar Feedback",
        "fb_desc": "Encontrou um problema? Tem uma sugestão?\nPreencha o formulário e enviaremos por email.",
        "fb_type": "Tipo:",
        "fb_bug": "🐛 Problema",
        "fb_suggestion": "💡 Sugestão",
        "fb_praise": "⭐ Elogio",
        "fb_other": "❓ Outro",
        "fb_email": "Seu email (opcional):",
        "fb_email_placeholder": "usuario@exemplo.com",
        "fb_message": "Mensagem:",
        "fb_cancel": "Cancelar",
        "fb_send": "✉ Enviar",
        "fb_empty_warning": "⚠ Escreva uma mensagem antes de enviar.",
        "fb_success": "✅ Cliente de email aberto. Envie a mensagem!",
        "fb_error": "⚠ Não foi possível abrir o cliente de email.",

        # ── Donate ──
        "don_title": "Apoie o Projeto — {app}",
        "don_header": "💝 Apoie o Projeto",
        "don_desc": "Se o {app} facilita sua vida, considere uma doação.\nSua contribuição ajuda a manter o projeto ativo. ❤",
        "don_paypal": "💳 PayPal",
        "don_paypal_desc": "Doação via PayPal",
        "don_paypal_btn": "Abrir PayPal",
        "don_bitcoin": "₿ Bitcoin",
        "don_pix": "🇧🇷 PIX",
        "don_copy": "📋 Copiar",
        "don_close": "Fechar",
        "don_copied": "✅ Copiado para a área de transferência!",
        "don_thanks": "Obrigado por usar o {app}! 🙏",
        "don_browser_error": "⚠ Não foi possível abrir o navegador.",

        # ── Settings ──
        "set_title": "Configurações — {app}",
        "set_lang_title": "🌐 Idioma",
        "set_lang_desc": "Selecione o idioma da interface. Requer reiniciar o app.",
        "set_lang_note": "⚠ Tradução para Español estará disponível em breve.",
        "set_shortcut_title": "⌨ Atalho de Teclado",
        "set_wm_detected": "WM detectado: <b>{wm}</b>",
        "set_shortcut_label": "Seu atalho:",
        "set_shortcut_placeholder": "Ex: $mod+Shift+f",
        "set_instruction": "Cole o comando abaixo no arquivo de configuração do seu WM:",
        "set_generated_cmd": "Comando gerado:",
        "set_copy_cmd": "📋 Copiar comando",
        "set_save_shortcut": "💾 Salvar atalho",
        "set_close": "Fechar",
        "set_lang_changed": "✅ Idioma alterado para {name}.\nFeche e reabra o FileBrowser-pdf para aplicar.",
        "set_shortcut_saved": "✅ Atalho salvo: {key}",
        "set_shortcut_active": "✅ Atalho {key} ativado! Funciona nesta sessão.",
        "set_shortcut_manual": "ℹ️ Seu WM não suporta atalhos via IPC.\nCopie o comando e cole no arquivo de configuração.",
        "set_copied": "✅ Comando copiado!",
        "set_wm_file": "Arquivo: {file}",
    },
    "en": {
        # ── Window ──
        "search_placeholder": "  Search PDF...",
        "no_indexed": "No PDFs indexed — click 🔄 to index",
        "indexing_local": "⚡ Indexing local folders...",
        "mounting_cloud": "☁ Mounting cloud...",
        "indexing_cloud": "☁ Indexing cloud... (may take a while)",
        "cloud_slow": "☁ Cloud slow... (waiting)",
        "cloud_unavailable": "⚠ Cloud unavailable",
        "cloud_background": "⚠ Cloud slow — indexing in background",
        "last": "Last",
        "counter": "📂 {local} local  ·  ☁ {cloud} cloud",
        "counter_progress": "📂 {local} local  ·  ☁ {cloud} / ~{ref} cloud ({pct}%)",
        "results_found": "  {n} result(s) found",
        "no_results": "No PDFs found",
        "reindex_tooltip": "Re-index PDFs",
        "indexing_warning": "⚠ Indexing in progress.",
        "continue_bg": "Continue in background",
        "exit_prompt": "Exit",
        "notification_title": "📄 Filebrowser",
        "notification_body": "Indexing complete — {n} PDFs found",
        "pdfs_available": "{n} local PDFs available",

        # ── Tray ──
        "tray_title": "📂 Filebrowser",
        "tray_show": "Show window",
        "tray_reindex": "🔄 Re-index",
        "tray_settings": "⚙ Settings",
        "tray_about": "ℹ️ About",
        "tray_feedback": "✉ Feedback",
        "tray_donate": "💝 Donate",
        "tray_quit": "Close FileBrowser-pdf",
        "tray_indexing": "⏳ Indexing... ({local}L / {cloud}N)",
        "tray_indexed": "📂 {n} PDFs indexed",

        # ── About ──
        "about_title": "About — {app}",
        "about_version": "Version {v}",
        "about_desc": "Spotlight-style PDF launcher for Linux",
        "about_tab_history": "📖 History",
        "about_tab_terms": "📄 Terms",
        "about_help": "❓ Help",
        "about_check_update": "🔄 Check for Updates",
        "about_close": "Close",
        "about_checking": "Checking...",
        "about_new_version": "🆕 New version available: {v}\nDownload at: {url}",
        "about_up_to_date": "✅ You are on the latest version ({v})",
        "about_check_error": "⚠ Could not check. Verify your connection.",
        "about_made_by": "Made with ❤ by {author}",

        # ── Feedback ──
        "fb_title": "Feedback — {app}",
        "fb_header": "✉ Send Feedback",
        "fb_desc": "Found a bug? Have a suggestion?\nFill out the form and we'll send it via email.",
        "fb_type": "Type:",
        "fb_bug": "🐛 Bug",
        "fb_suggestion": "💡 Suggestion",
        "fb_praise": "⭐ Praise",
        "fb_other": "❓ Other",
        "fb_email": "Your email (optional):",
        "fb_email_placeholder": "user@example.com",
        "fb_message": "Message:",
        "fb_cancel": "Cancel",
        "fb_send": "✉ Send",
        "fb_empty_warning": "⚠ Write a message before sending.",
        "fb_success": "✅ Email client opened. Send the message!",
        "fb_error": "⚠ Could not open email client.",

        # ── Donate ──
        "don_title": "Support the Project — {app}",
        "don_header": "💝 Support the Project",
        "don_desc": "If {app} makes your life easier, consider a donation.\nYour contribution helps keep the project alive. ❤",
        "don_paypal": "💳 PayPal",
        "don_paypal_desc": "Donate via PayPal",
        "don_paypal_btn": "Open PayPal",
        "don_bitcoin": "₿ Bitcoin",
        "don_pix": "🇧🇷 PIX",
        "don_copy": "📋 Copy",
        "don_close": "Close",
        "don_copied": "✅ Copied to clipboard!",
        "don_thanks": "Thank you for using {app}! 🙏",
        "don_browser_error": "⚠ Could not open browser.",

        # ── Settings ──
        "set_title": "Settings — {app}",
        "set_lang_title": "🌐 Language",
        "set_lang_desc": "Select interface language. Requires restarting the app.",
        "set_lang_note": "⚠ Spanish translation is coming soon.",
        "set_shortcut_title": "⌨ Keyboard Shortcut",
        "set_wm_detected": "WM detected: <b>{wm}</b>",
        "set_shortcut_label": "Your shortcut:",
        "set_shortcut_placeholder": "E.g.: $mod+Shift+f",
        "set_instruction": "Paste the command below in your WM config file:",
        "set_generated_cmd": "Generated command:",
        "set_copy_cmd": "📋 Copy command",
        "set_save_shortcut": "💾 Save shortcut",
        "set_close": "Close",
        "set_lang_changed": "✅ Language changed to {name}.\nClose and reopen FileBrowser-pdf to apply.",
        "set_shortcut_saved": "✅ Shortcut saved: {key}",
        "set_shortcut_active": "✅ Shortcut {key} activated! Works this session.",
        "set_shortcut_manual": "ℹ️ Your WM doesn't support IPC shortcuts.\nCopy the command and paste it in your config file.",
        "set_copied": "✅ Command copied!",
        "set_wm_file": "File: {file}",
    },
}

# ─── Estado Global ───────────────────────────────────────────────────────────

_current_lang = "pt_BR"
_strings = TRANSLATIONS["pt_BR"]


def set_language(lang: str):
    """Define o idioma ativo."""
    global _current_lang, _strings
    if lang in TRANSLATIONS:
        _current_lang = lang
        _strings = TRANSLATIONS[lang]


def get_language() -> str:
    """Retorna o código do idioma ativo."""
    return _current_lang


def t(key: str, **kwargs) -> str:
    """
    Retorna a string traduzida para a chave dada.
    Suporta formatação com kwargs: t("counter", local=5, cloud=10)
    """
    text = _strings.get(key, key)
    if kwargs:
        try:
            return text.format(**kwargs)
        except (KeyError, IndexError):
            return text
    return text


def load_saved_language():
    """Carrega o idioma salvo no banco de dados."""
    try:
        from src.search.indexer import get_metadata
        lang = get_metadata("language", "pt_BR")
        set_language(lang)
    except Exception:
        pass


def save_language(lang: str):
    """Salva o idioma escolhido no banco de dados."""
    try:
        from src.search.indexer import save_metadata
        save_metadata("language", lang)
        set_language(lang)
    except Exception:
        pass
