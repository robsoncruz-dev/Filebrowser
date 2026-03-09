"""
Filebrowser — Janela Principal (Spotlight)

Interface GTK4 flutuante estilo Spotlight para busca e abertura de PDFs.
"""

import json
import os
import signal
import subprocess
import threading
from pathlib import Path

import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")
from gi.repository import Gtk, Gdk, GLib, Pango  # noqa: E402

from src.search.finder import search_pdfs
from src.search.indexer import (
    build_index_local, scan_cloud, save_cloud_results, get_total_count,
    clear_cloud_cache, insert_single_cloud_pdf,
    get_counts_by_source, get_last_indexed_at, get_last_cloud_count,
    save_metadata,
)
from src.search.cloud_mount import mount_all
from src.config.settings import AppConfig
from src.i18n import t, load_saved_language

# Carregar idioma salvo antes de construir a UI
load_saved_language()


CSS_FILE = Path(__file__).resolve().parent / "styles.css"
TRAY_STATE_FILE = Path.home() / ".cache" / "filebrowser" / "tray_state.json"
PID_FILE = Path.home() / ".cache" / "filebrowser" / "app.pid"
TRAY_CMD_FILE = Path.home() / ".cache" / "filebrowser" / "tray_cmd.json"
TRAY_SCRIPT = Path(__file__).resolve().parent / "tray.py"


class FilebrowserWindow(Gtk.ApplicationWindow):
    """Janela spotlight para busca de PDFs."""

    def __init__(self, app: Gtk.Application, config: AppConfig):
        super().__init__(application=app, title="Filebrowser")
        self.config = config
        self._selected_index = -1
        self._results: list[dict] = []
        self._local_count = 0
        self._cloud_count = 0
        self._last_cloud_ref = 0  # Referência histórica para progresso %
        self._prompt_visible = False  # Prompt de fechamento visível
        self._cloud_thread = None     # Referência para thread de nuvem

        self._setup_window()
        self._load_css()
        self._build_ui()
        self._connect_signals()

        # Forçar floating + centralizar após a janela ser mapeada
        self.connect("realize", self._on_realize)
        self._indexing = False  # Flag para evitar indexações simultâneas

        # Carregar cache existente (instantâneo) — SEM scan automático
        self._load_from_cache()

    def _setup_window(self):
        """Configura propriedades da janela."""
        self.set_default_size(self.config.interface.largura, -1)
        self.set_resizable(False)
        self.set_decorated(False)  # Remove bordas do WM

        # Configurar nome e classe da janela
        self.set_name("filebrowser-window")
        self.add_css_class("filebrowser-window")

    def _load_from_cache(self):
        """Carrega contadores do cache SQLite existente (instantâneo)."""
        counts = get_counts_by_source()
        self._local_count = counts["local"]
        self._cloud_count = counts["nuvem"]
        self._last_cloud_ref = get_last_cloud_count()
        total = self._local_count + self._cloud_count

        if total > 0:
            last_ts = get_last_indexed_at()
            ts_part = f"  ·  {t('last')}: {last_ts}" if last_ts else ""
            self.status_label.set_text(
                t("counter", local=self._local_count, cloud=self._cloud_count) + ts_part
            )
        else:
            self.status_label.set_text(t("no_indexed"))

    def _on_realize(self, widget):
        """Após a janela ser criada, forçar floating e centralizar."""
        GLib.timeout_add(50, self._force_floating)

    @staticmethod
    def _detect_wm() -> str:
        """Detecta o Window Manager ativo."""
        desktop = os.environ.get("XDG_CURRENT_DESKTOP", "").lower()
        session = os.environ.get("DESKTOP_SESSION", "").lower()
        combined = f"{desktop} {session}"
        if "i3" in combined:
            return "i3"
        if "sway" in combined:
            return "sway"
        return "generic"  # GNOME, KDE, XFCE, etc.

    def _force_floating(self) -> bool:
        """Força floating e centraliza a janela no WM ativo."""
        wm = self._detect_wm()
        try:
            if wm == "i3":
                subprocess.Popen(
                    ["i3-msg", "floating enable, move position center, border pixel 2"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
            elif wm == "sway":
                subprocess.Popen(
                    ["swaymsg", "floating enable, move position center"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
            # Generic: GTK4 handles positioning natively
        except FileNotFoundError:
            pass  # WM command not available
        return False  # Não repetir

    def _load_css(self):
        """Carrega o CSS customizado."""
        if not CSS_FILE.exists():
            return

        css_provider = Gtk.CssProvider()
        css_provider.load_from_path(str(CSS_FILE))
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(),
            css_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
        )

    def _build_ui(self):
        """Constrói os widgets da interface."""
        # Container principal
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        main_box.add_css_class("main-container")
        self.set_child(main_box)

        # Campo de busca
        self.search_entry = Gtk.Entry()
        self.search_entry.set_placeholder_text(t("search_placeholder"))
        self.search_entry.add_css_class("search-entry")
        self.search_entry.set_hexpand(True)
        main_box.append(self.search_entry)

        # ScrolledWindow para resultados
        self.scroll = Gtk.ScrolledWindow()
        self.scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.scroll.set_max_content_height(400)
        self.scroll.set_propagate_natural_height(True)
        self.scroll.add_css_class("results-scroll")
        self.scroll.set_visible(False)
        main_box.append(self.scroll)

        # Lista de resultados
        self.results_list = Gtk.ListBox()
        self.results_list.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.results_list.add_css_class("results-list")
        self.scroll.set_child(self.results_list)

        # Barra de progresso (pulse mode)
        self.progress_bar = Gtk.ProgressBar()
        self.progress_bar.add_css_class("index-progress")
        self.progress_bar.set_visible(False)
        main_box.append(self.progress_bar)
        self._pulse_timer_id = None

        # Contador de arquivos indexados
        self.counter_label = Gtk.Label(label="")
        self.counter_label.add_css_class("counter-text")
        self.counter_label.set_halign(Gtk.Align.START)
        self.counter_label.set_visible(False)
        main_box.append(self.counter_label)

        # Prompt de fechamento durante indexação
        self.prompt_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        self.prompt_box.add_css_class("close-prompt")
        self.prompt_box.set_visible(False)
        main_box.append(self.prompt_box)

        prompt_label = Gtk.Label(label="⚠ Indexação em andamento.")
        prompt_label.add_css_class("prompt-text")
        prompt_label.set_halign(Gtk.Align.START)
        self.prompt_box.append(prompt_label)

        prompt_buttons = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        prompt_buttons.set_halign(Gtk.Align.END)
        self.prompt_box.append(prompt_buttons)

        bg_btn = Gtk.Button(label="Continuar em 2º plano")
        bg_btn.add_css_class("prompt-btn-bg")
        bg_btn.connect("clicked", self._on_continue_background)
        prompt_buttons.append(bg_btn)

        exit_btn = Gtk.Button(label="Sair")
        exit_btn.add_css_class("prompt-btn-exit")
        exit_btn.connect("clicked", self._on_force_close)
        prompt_buttons.append(exit_btn)

        # Barra de status (label + botão re-indexar)
        status_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        status_box.add_css_class("status-bar")
        main_box.append(status_box)

        self.status_label = Gtk.Label(label="Indexando...")
        self.status_label.add_css_class("status-text")
        self.status_label.set_halign(Gtk.Align.START)
        self.status_label.set_hexpand(True)
        status_box.append(self.status_label)

        self.reindex_btn = Gtk.Button(label="🔄")
        self.reindex_btn.add_css_class("reindex-btn")
        self.reindex_btn.set_tooltip_text(t("reindex_tooltip"))
        self.reindex_btn.connect("clicked", self._on_reindex_clicked)
        status_box.append(self.reindex_btn)

        # Focar no campo de busca
        self.search_entry.grab_focus()

    def _connect_signals(self):
        """Conecta sinais de eventos."""
        # Buscar ao digitar
        self.search_entry.connect("changed", self._on_search_changed)

        # Enter no campo de busca → abrir PDF selecionado
        self.search_entry.connect("activate", lambda e: self._open_selected_pdf())

        # Teclas especiais
        key_controller = Gtk.EventControllerKey()
        key_controller.connect("key-pressed", self._on_key_pressed)
        self.add_controller(key_controller)

        # Ativar item ao clicar
        self.results_list.connect("row-activated", self._on_row_activated)

        # Foco perdido → fechar
        focus_controller = Gtk.EventControllerFocus()
        focus_controller.connect("leave", self._on_focus_leave)
        self.add_controller(focus_controller)

    def _start_pulse(self):
        """Inicia a animação pulse da barra de progresso."""
        self.progress_bar.set_visible(True)
        if self._pulse_timer_id is None:
            self._pulse_timer_id = GLib.timeout_add(80, self._do_pulse)

    def _do_pulse(self) -> bool:
        """Avança a animação pulse."""
        self.progress_bar.pulse()
        return True  # Repetir

    def _stop_pulse(self) -> bool:
        """Para a animação pulse e oculta a barra (chamado via GLib.idle_add)."""
        if self._pulse_timer_id is not None:
            GLib.source_remove(self._pulse_timer_id)
            self._pulse_timer_id = None
        self.progress_bar.set_visible(False)
        return False

    def _start_background_index(self) -> bool:
        """Inicia indexação em thread separada."""
        if self._indexing:
            return False
        self._indexing = True
        self._local_count = 0
        self._cloud_count = 0
        self._last_cloud_ref = get_last_cloud_count()
        self.reindex_btn.set_sensitive(False)
        self._start_pulse()
        self.counter_label.set_text(t("counter", local=0, cloud=0))
        self.counter_label.set_visible(True)
        self.status_label.set_text(t("indexing_local"))
        self._hide_prompt()
        thread = threading.Thread(target=self._index_thread, daemon=True)
        thread.start()
        return False

    def _on_local_found(self, count: int, pdf: dict = None):
        """Callback chamado a cada PDF local encontrado."""
        self._local_count = count
        GLib.idle_add(self._refresh_counter)

    def _on_cloud_found(self, count: int, pdf: dict = None):
        """Callback chamado a cada PDF de nuvem encontrado."""
        self._cloud_count = count
        if pdf:
            insert_single_cloud_pdf(pdf)
        GLib.idle_add(self._refresh_counter)

    def _refresh_counter(self) -> bool:
        """Atualiza o label do contador com progresso % se disponível."""
        if self._indexing and self._last_cloud_ref > 0 and self._cloud_count > 0:
            pct = min(int(self._cloud_count / self._last_cloud_ref * 100), 99)
            self.counter_label.set_text(
                t("counter_progress", local=self._local_count, cloud=self._cloud_count, ref=self._last_cloud_ref, pct=pct)
            )
        else:
            self.counter_label.set_text(
                t("counter", local=self._local_count, cloud=self._cloud_count)
            )
        return False

    def _index_thread(self):
        """Thread de indexação: locais primeiro, nuvem depois."""
        # Fase 1: Pastas locais (delta sync — rápido)
        local_count = build_index_local(self.config, on_found=self._on_local_found)
        self._local_count = local_count
        GLib.idle_add(self._refresh_counter)
        GLib.idle_add(self._update_status, f"✅ {local_count} PDFs locais")

        # Fase 2: Montar nuvens + indexar
        cloud_dirs = self.config.busca.diretorios_nuvem
        if cloud_dirs:
            # Auto-montar nuvens se configurado
            if self.config.nuvem.auto_montar and self.config.nuvem.remotes:
                GLib.idle_add(self._update_status, "☁ Montando nuvem...")
                mount_results = mount_all(self.config.nuvem.remotes)
                mounted = sum(1 for ok in mount_results.values() if ok)
                total_remotes = len(mount_results)
                if mounted == 0:
                    GLib.idle_add(self._update_status, f"⚠ Nuvem indisponível ({local_count} PDFs locais)")
                    GLib.idle_add(self._update_counter_cloud_fail)
                    self._indexing = False
                    GLib.idle_add(self._stop_pulse)
                    GLib.idle_add(self._enable_reindex_btn)
                    return
                elif mounted < total_remotes:
                    failed = [r for r, ok in mount_results.items() if not ok]
                    GLib.idle_add(self._update_status, f"⚠ {', '.join(failed)} falhou · montando restante...")

            ref_str = f" / ~{self._last_cloud_ref}" if self._last_cloud_ref > 0 else ""
            GLib.idle_add(self._update_status, f"☁ Indexando nuvem...{ref_str} (pode demorar)")

            cloud_done = {"value": False, "count": 0}

            def _cloud_scan():
                """Scan de nuvem com persistência incremental (delta sync)."""
                try:
                    pdfs = scan_cloud(
                        self.config, on_found=self._on_cloud_found
                    )
                    # Delta sync: salvar resultados (compara mtime, não deleta tudo)
                    save_cloud_results(pdfs)
                    cloud_done["count"] = len(pdfs)
                    cloud_done["value"] = True

                    # Atualizar UI
                    total = self._local_count + len(pdfs)
                    GLib.idle_add(self._refresh_counter)

                    last_ts = get_last_indexed_at()
                    ts_part = f"  ·  Última: {last_ts}" if last_ts else ""
                    if len(pdfs) > 0:
                        GLib.idle_add(self._update_status, f"✅ {total} PDFs (☁ nuvem incluída){ts_part}")
                    else:
                        GLib.idle_add(self._update_status, f"✅ {total} PDFs indexados{ts_part}")
                    GLib.idle_add(self._stop_pulse)
                    GLib.idle_add(self._enable_reindex_btn)
                    GLib.idle_add(self._hide_prompt)

                    # Notificação desktop se app está em 2º plano
                    self._send_notification(total)
                except Exception:
                    pass

            self._cloud_thread = threading.Thread(target=_cloud_scan, daemon=True)
            self._cloud_thread.start()

            # Esperar 30s — se concluir rápido, ótimo
            self._cloud_thread.join(timeout=30)

            if cloud_done["value"]:
                pass  # Já tratado dentro de _cloud_scan
            else:
                GLib.idle_add(self._update_status, "☁ Nuvem lenta... (aguardando)")

                # Esperar mais 30s (60s total)
                self._cloud_thread.join(timeout=30)

                if not cloud_done["value"]:
                    # 60s sem conclusão — informar usuário mas NÃO desistir
                    GLib.idle_add(self._update_status, f"⚠ Nuvem lenta — indexando em 2º plano ({local_count} PDFs locais disponíveis)")
                    GLib.idle_add(self._update_counter_cloud_slow)
        else:
            last_ts = get_last_indexed_at()
            ts_part = f"  ·  Última: {last_ts}" if last_ts else ""
            GLib.idle_add(self._update_status, f"✅ {local_count} PDFs indexados{ts_part}")

        self._indexing = False
        self._cloud_thread = None
        GLib.idle_add(self._stop_pulse)
        GLib.idle_add(self._enable_reindex_btn)
        GLib.idle_add(self._hide_prompt)

    def _send_notification(self, total: int):
        """Envia notificação desktop se a janela está oculta (2º plano)."""
        try:
            if not self.get_visible():
                subprocess.Popen(
                    [
                        "notify-send",
                        "📄 Filebrowser",
                        f"Indexação concluída — {total} PDFs encontrados",
                        "--icon=document-open",
                        "--urgency=low",
                    ],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
        except (FileNotFoundError, OSError):
            pass

    def _cloud_success(self, pdfs: list[dict], local_count: int):
        """Processa resultado de nuvem com sucesso."""
        count = save_cloud_results(pdfs)
        self._cloud_count = count
        GLib.idle_add(self._refresh_counter)
        total = local_count + count
        if count > 0:
            GLib.idle_add(self._update_status, f"✅ {total} PDFs (☁ nuvem incluída)")
        else:
            GLib.idle_add(self._update_status, f"✅ {total} PDFs indexados")

    def _update_counter_cloud_slow(self) -> bool:
        """Atualiza contador indicando nuvem lenta."""
        self.counter_label.set_text(
            f"📂 {self._local_count} locais  ·  ☁ aguardando..."
        )
        return False

    def _update_counter_cloud_fail(self) -> bool:
        """Atualiza contador indicando falha na nuvem."""
        self.counter_label.set_text(
            f"📂 {self._local_count} locais  ·  ☁ — indisponível"
        )
        return False

    def _update_status(self, text: str) -> bool:
        """Atualiza o label de status (chamado via GLib.idle_add)."""
        self.status_label.set_text(text)
        return False

    def _enable_reindex_btn(self) -> bool:
        """Re-habilita o botão de re-indexação."""
        self.reindex_btn.set_sensitive(True)
        return False

    def _on_reindex_clicked(self, button):
        """Callback: botão de re-indexação clicado."""
        self._start_background_index()
        self.search_entry.grab_focus()

    def _on_search_changed(self, entry: Gtk.Entry):
        """Callback: texto de busca alterado."""
        query = entry.get_text()
        self._update_results(query)

    def _update_results(self, query: str):
        """Atualiza a lista de resultados com base no query."""
        # Limpar lista atual
        while True:
            row = self.results_list.get_row_at_index(0)
            if row is None:
                break
            self.results_list.remove(row)

        self._selected_index = -1

        if not query.strip():
            self.scroll.set_visible(False)
            self._results = []
            return

        # Buscar PDFs
        self._results = search_pdfs(
            query,
            max_results=self.config.interface.max_resultados,
        )

        if not self._results:
            self.scroll.set_visible(True)
            no_results = Gtk.Label(label=t("no_results"))
            no_results.add_css_class("no-results")
            self.results_list.append(no_results)
            return

        # Adicionar resultados
        self.scroll.set_visible(True)
        for pdf in self._results:
            row = self._create_result_row(pdf)
            self.results_list.append(row)

        # Selecionar primeiro resultado
        first_row = self.results_list.get_row_at_index(0)
        if first_row:
            self.results_list.select_row(first_row)
            self._selected_index = 0

        # Atualizar status
        self.status_label.set_text(
            t("results_found", n=len(self._results))
        )
        self.status_label.set_visible(True)

    def _create_result_row(self, pdf: dict) -> Gtk.Widget:
        """Cria um widget para um resultado de PDF."""
        row_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        row_box.add_css_class("result-item")

        # Ícone PDF
        icon = Gtk.Label(label="📄")
        icon.add_css_class("pdf-icon")
        row_box.append(icon)

        # Info do arquivo
        info_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        info_box.set_hexpand(True)

        # Nome do arquivo
        name_label = Gtk.Label(label=pdf["nome"])
        name_label.add_css_class("result-filename")
        name_label.set_halign(Gtk.Align.START)
        name_label.set_ellipsize(Pango.EllipsizeMode.MIDDLE)
        info_box.append(name_label)

        # Caminho (abreviado)
        path_display = pdf["caminho"].replace(str(Path.home()), "~")
        path_label = Gtk.Label(label=path_display)
        path_label.add_css_class("result-path")
        path_label.set_halign(Gtk.Align.START)
        path_label.set_ellipsize(Pango.EllipsizeMode.START)
        info_box.append(path_label)

        row_box.append(info_box)
        return row_box

    def _on_key_pressed(self, controller, keyval, keycode, state) -> bool:
        """Callback: tecla pressionada."""
        # Escape → fechar (com smart close)
        if keyval == Gdk.KEY_Escape:
            if self._prompt_visible:
                self._hide_prompt()
                self.search_entry.grab_focus()
            elif self._indexing:
                self._show_prompt()
            else:
                self._hide_window()
            return True

        # Enter → abrir PDF selecionado
        if keyval in (Gdk.KEY_Return, Gdk.KEY_KP_Enter):
            self._open_selected_pdf()
            return True

        # Setas ↑ ↓ → navegar resultados
        if keyval == Gdk.KEY_Down:
            self._navigate_results(1)
            return True

        if keyval == Gdk.KEY_Up:
            self._navigate_results(-1)
            return True

        # Tab → navegar para baixo (como seta)
        if keyval == Gdk.KEY_Tab:
            self._navigate_results(1)
            return True

        return False

    def _navigate_results(self, direction: int):
        """Navega pelos resultados (direction: 1 = baixo, -1 = cima)."""
        if not self._results:
            return

        total = len(self._results)
        new_index = self._selected_index + direction

        # Wrap around
        if new_index < 0:
            new_index = total - 1
        elif new_index >= total:
            new_index = 0

        row = self.results_list.get_row_at_index(new_index)
        if row:
            self.results_list.select_row(row)
            self._selected_index = new_index

    def _on_row_activated(self, listbox, row):
        """Callback: item da lista ativado (clicado ou Enter)."""
        index = row.get_index()
        if 0 <= index < len(self._results):
            self._selected_index = index
            self._open_selected_pdf()

    def _open_selected_pdf(self):
        """Abre o PDF selecionado no leitor configurado."""
        if self._selected_index < 0 or self._selected_index >= len(self._results):
            return

        pdf = self._results[self._selected_index]
        caminho = pdf["caminho"]
        leitor = self.config.geral.leitor

        try:
            subprocess.Popen(
                [leitor, caminho],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except FileNotFoundError:
            # Leitor não encontrado — tentar xdg-open como fallback
            subprocess.Popen(
                ["xdg-open", caminho],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )

        if self.config.geral.fechar_apos_abrir:
            self._hide_window()

    def _on_focus_leave(self, controller):
        """Callback: janela perde o foco → fechar ou prompt."""
        GLib.timeout_add(150, self._check_and_close)

    def _check_and_close(self) -> bool:
        """Verifica se a janela ainda está sem foco e decide."""
        if not self.is_active():
            if self._indexing:
                self._show_prompt()
                self.present()  # Trazer de volta ao foco
            else:
                self._hide_window()
        return False

    def _hide_window(self):
        """Esconde a janela (sem encerrar o app — tray continua)."""
        self.search_entry.set_text("")  # Limpar busca
        self.set_visible(False)

    def _show_prompt(self):
        """Mostra prompt de fechamento durante indexação."""
        self._prompt_visible = True
        self.prompt_box.set_visible(True)

    def _hide_prompt(self) -> bool:
        """Esconde prompt de fechamento."""
        self._prompt_visible = False
        self.prompt_box.set_visible(False)
        return False

    def _on_continue_background(self, button):
        """Callback: continuar indexação em segundo plano (minimizar)."""
        self._hide_prompt()
        self.set_visible(False)  # Esconder janela
        self._update_tray_state()  # Atualizar tray
        self.get_application()._ensure_tray()  # Garantir tray rodando

    def _on_force_close(self, button):
        """Callback: fechar tudo mesmo durante indexação."""
        self._indexing = False
        self.get_application()._kill_tray()
        self.close()

    def _update_tray_state(self):
        """Atualiza o arquivo de estado para o tray ler."""
        try:
            TRAY_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
            state = {
                "indexing": self._indexing,
                "local": self._local_count,
                "cloud": self._cloud_count,
                "status": self.status_label.get_text(),
            }
            TRAY_STATE_FILE.write_text(json.dumps(state))
        except OSError:
            pass


class FilebrowserApp(Gtk.Application):
    """Aplicação GTK4 principal — instância única via D-Bus."""

    def __init__(self, config: AppConfig):
        super().__init__(application_id="com.filebrowser.pdflaunch")
        self.config = config
        self._win = None
        self._tray_process = None
        self._cmd_poll_id = None

    def do_activate(self):
        """Cria ou re-exibe a janela principal."""
        if self._win is not None:
            # Instância já existe — trazer de volta
            self._win.set_visible(True)
            self._win.present()
            GLib.timeout_add(50, self._win._force_floating)
            return

        # Primeira ativação — criar janela
        self._win = FilebrowserWindow(self, self.config)
        self._win.present()

        # Salvar PID para comunicação com tray
        self._write_pid()

        # Iniciar system tray
        self._ensure_tray()

        # Ativar atalho salvo (via WM IPC, temporário)
        from src.ui.settings_ui import apply_saved_shortcut
        apply_saved_shortcut()

        # Monitorar comandos do tray
        self._cmd_poll_id = GLib.timeout_add(1000, self._poll_tray_commands)

        # Registrar handler SIGUSR1 para com tray
        signal.signal(signal.SIGUSR1, self._on_sigusr1)

    def do_shutdown(self):
        """Limpa recursos ao encerrar."""
        self._kill_tray()
        self._cleanup_files()
        Gtk.Application.do_shutdown(self)

    def _write_pid(self):
        """Salva o PID do processo principal."""
        try:
            PID_FILE.parent.mkdir(parents=True, exist_ok=True)
            PID_FILE.write_text(str(os.getpid()))
        except OSError:
            pass

    def _cleanup_files(self):
        """Remove arquivos temporários."""
        for f in (PID_FILE, TRAY_STATE_FILE, TRAY_CMD_FILE):
            try:
                f.unlink(missing_ok=True)
            except OSError:
                pass

    def _ensure_tray(self):
        """Garante que o processo de tray está rodando."""
        if self._tray_process and self._tray_process.poll() is None:
            return  # Já está rodando

        try:
            import sys
            tray_log = Path.home() / ".cache" / "filebrowser" / "tray.log"
            log_file = open(str(tray_log), "w")
            self._tray_process = subprocess.Popen(
                [sys.executable, str(TRAY_SCRIPT)],
                stdout=log_file,
                stderr=log_file,
            )
        except (FileNotFoundError, OSError):
            pass

    def _kill_tray(self):
        """Encerra o processo de tray."""
        if self._tray_process and self._tray_process.poll() is None:
            self._tray_process.terminate()
            self._tray_process = None

    def _on_sigusr1(self, signum, frame):
        """Handler SIGUSR1 — tray enviou um comando."""
        GLib.idle_add(self._process_tray_command)

    def _poll_tray_commands(self) -> bool:
        """Verifica se há comandos pendentes do tray."""
        self._process_tray_command()
        # Atualizar estado do tray
        if self._win:
            self._win._update_tray_state()
        return True  # Continuar polling

    def _process_tray_command(self):
        """Processa comando enviado pelo tray."""
        try:
            if not TRAY_CMD_FILE.exists():
                return
            data = json.loads(TRAY_CMD_FILE.read_text())
            TRAY_CMD_FILE.unlink(missing_ok=True)

            cmd = data.get("command", "")
            if cmd == "show" and self._win:
                self._win.set_visible(True)
                self._win.present()
                GLib.timeout_add(50, self._win._force_floating)
            elif cmd == "reindex" and self._win:
                self._win.set_visible(True)
                self._win.present()
                GLib.timeout_add(50, self._win._force_floating)
                GLib.idle_add(self._win._start_background_index)
            elif cmd == "about" and self._win:
                from src.ui.about import AboutWindow
                win = AboutWindow(self._win)
                win.present()
            elif cmd == "feedback" and self._win:
                from src.ui.feedback import FeedbackWindow
                win = FeedbackWindow(self._win)
                win.present()
            elif cmd == "donate" and self._win:
                from src.ui.donate import DonateWindow
                win = DonateWindow(self._win)
                win.present()
            elif cmd == "settings" and self._win:
                from src.ui.settings_ui import SettingsWindow
                win = SettingsWindow(self._win)
                win.present()
            elif cmd == "quit":
                if self._win:
                    self._win._indexing = False
                    self._win.close()
                self.quit()
        except (json.JSONDecodeError, OSError):
            pass
