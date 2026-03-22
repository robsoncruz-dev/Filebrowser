"""
Filebrowser — Janela Principal (Spotlight)

Interface PyQt6 flutuante estilo Spotlight para busca e abertura de PDFs.
"""

import json
import os
import signal
import subprocess
import threading
from pathlib import Path
import sys

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLineEdit, QListWidget, QListWidgetItem, QProgressBar, QLabel,
    QFrame, QPushButton, QSystemTrayIcon, QMenu
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QObject, QEvent, QPoint
from PyQt6.QtGui import QKeyEvent, QIcon, QAction

from src.search.finder import search_pdfs
from src.search.indexer import (
    build_index_local, scan_cloud, save_cloud_results, get_total_count,
    clear_cloud_cache, insert_single_cloud_pdf,
    get_counts_by_source, get_last_indexed_at, get_last_cloud_count,
    save_metadata,
)

from src.config.settings import AppConfig, CACHE_DIR
from src.i18n import t, load_saved_language

# Carregar idioma salvo antes de construir a UI
load_saved_language()

CSS_FILE = Path(__file__).resolve().parent / "styles.css"

class IndexSignals(QObject):
    local_found = pyqtSignal(int, object)
    cloud_found = pyqtSignal(int, object)
    status_update = pyqtSignal(str)
    refresh_counter = pyqtSignal()
    cloud_slow = pyqtSignal()
    cloud_fail = pyqtSignal()
    done = pyqtSignal(int)
    stop_pulse = pyqtSignal()


class FilebrowserWindow(QMainWindow):
    """Janela spotlight para busca de PDFs."""

    def __init__(self, app: QApplication, config: AppConfig, fb_app):
        super().__init__()
        self.app = app
        self.fb_app = fb_app
        self.config = config
        self._selected_index = -1
        self._results: list[dict] = []
        self._local_count = 0
        self._cloud_count = 0
        self._last_cloud_ref = 0
        self._prompt_visible = False
        self._cloud_thread = None
        self._indexing = False

        self._signals = IndexSignals()
        self._signals.local_found.connect(self._on_local_found_signal)
        self._signals.cloud_found.connect(self._on_cloud_found_signal)
        self._signals.status_update.connect(self._update_status)
        self._signals.refresh_counter.connect(self._refresh_counter)
        self._signals.cloud_slow.connect(self._update_counter_cloud_slow)
        self._signals.cloud_fail.connect(self._update_counter_cloud_fail)
        self._signals.done.connect(self._on_index_done)
        self._signals.stop_pulse.connect(self._stop_pulse)

        self._setup_window()
        self._build_ui()
        self._load_css()
        self._load_from_cache()

    def _setup_window(self):
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedWidth(self.config.interface.largura)
        self.setObjectName("filebrowser-window")

    def _load_css(self):
        if CSS_FILE.exists():
            self.setStyleSheet(CSS_FILE.read_text())

    def _load_from_cache(self):
        counts = get_counts_by_source()
        self._local_count = counts["local"]
        self._cloud_count = counts["nuvem"]
        self._last_cloud_ref = get_last_cloud_count()
        total = self._local_count + self._cloud_count

        if total > 0:
            last_ts = get_last_indexed_at()
            ts_part = f"  ·  {t('last')}: {last_ts}" if last_ts else ""
            self.status_label.setText(
                t("counter", local=self._local_count, cloud=self._cloud_count) + ts_part
            )
        else:
            self.status_label.setText(t("no_indexed"))

    def showEvent(self, event):
        super().showEvent(event)
        QTimer.singleShot(50, self._force_floating)

    def changeEvent(self, event):
        if event.type() == QEvent.Type.ActivationChange:
            if not self.isActiveWindow():
                self._check_and_close()
        super().changeEvent(event)

    @staticmethod
    def _detect_wm() -> str:
        desktop = os.environ.get("XDG_CURRENT_DESKTOP", "").lower()
        session = os.environ.get("DESKTOP_SESSION", "").lower()
        combined = f"{desktop} {session}"
        if "i3" in combined: return "i3"
        if "sway" in combined: return "sway"
        return "generic"

    def _force_floating(self):
        # Center the window
        screen = QApplication.primaryScreen().geometry()
        x = (screen.width() - self.width()) // 2
        y = (screen.height() - self.height()) // 2
        self.move(x, y)

        if sys.platform != "win32":
            wm = self._detect_wm()
            try:
                if wm == "i3":
                    subprocess.Popen(
                        ["i3-msg", "floating enable, move position center, border pixel 2"],
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                    )
                elif wm == "sway":
                    subprocess.Popen(
                        ["swaymsg", "floating enable, move position center"],
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                    )
            except FileNotFoundError:
                pass
        else:
            try:
                import ctypes
                self.raise_()
                self.activateWindow()
                self.search_entry.setFocus()
                
                hwnd = int(self.winId())
                user32 = ctypes.windll.user32
                kernel32 = ctypes.windll.kernel32
                
                current_thread_id = kernel32.GetCurrentThreadId()
                foreground_thread_id = user32.GetWindowThreadProcessId(user32.GetForegroundWindow(), 0)
                
                if current_thread_id != foreground_thread_id and foreground_thread_id != 0:
                    user32.AttachThreadInput(current_thread_id, foreground_thread_id, True)
                    user32.SetWindowPos(hwnd, -1, 0, 0, 0, 0, 0x0001 | 0x0002 | 0x0040)
                    user32.SetForegroundWindow(hwnd)
                    user32.ShowWindow(hwnd, 5) # SW_SHOW
                    user32.AttachThreadInput(current_thread_id, foreground_thread_id, False)
                else:
                    user32.SetWindowPos(hwnd, -1, 0, 0, 0, 0, 0x0001 | 0x0002 | 0x0040)
                    user32.SetForegroundWindow(hwnd)
                    user32.ShowWindow(hwnd, 5)
            except Exception:
                pass

    def _build_ui(self):
        central = QWidget()
        central.setObjectName("filebrowser-window")
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(0)
        self.setCentralWidget(central)

        # Search Entry
        self.search_entry = QLineEdit()
        self.search_entry.setObjectName("search-entry")
        self.search_entry.setPlaceholderText(t("search_placeholder"))
        self.search_entry.textChanged.connect(self._on_search_changed)
        self.search_entry.returnPressed.connect(self._open_selected_pdf)
        self.search_entry.installEventFilter(self)
        main_layout.addWidget(self.search_entry)

        # Results List
        self.results_list = QListWidget()
        self.results_list.setObjectName("results-list")
        self.results_list.setMaximumHeight(400)
        self.results_list.hide()
        self.results_list.itemActivated.connect(self._on_row_activated)
        self.results_list.itemClicked.connect(self._on_row_activated)
        main_layout.addWidget(self.results_list)

        # Progress Bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setObjectName("index-progress")
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setRange(0, 0) # Pulse mode
        self.progress_bar.hide()
        main_layout.addWidget(self.progress_bar)

        # Counter Label
        self.counter_label = QLabel()
        self.counter_label.setObjectName("counter-text")
        self.counter_label.hide()
        main_layout.addWidget(self.counter_label)

        # Prompt Box
        self.prompt_box = QFrame()
        self.prompt_box.setObjectName("close-prompt")
        self.prompt_box.hide()
        prompt_layout = QVBoxLayout(self.prompt_box)
        prompt_layout.setContentsMargins(14, 8, 14, 8)
        prompt_layout.setSpacing(4)
        
        prompt_label = QLabel("⚠ Indexação em andamento.")
        prompt_label.setObjectName("prompt-text")
        prompt_layout.addWidget(prompt_label)

        prompt_btns = QHBoxLayout()
        prompt_btns.setAlignment(Qt.AlignmentFlag.AlignRight)
        
        bg_btn = QPushButton("Continuar em 2º plano")
        bg_btn.setObjectName("prompt-btn-bg")
        bg_btn.clicked.connect(self._on_continue_background)
        prompt_btns.addWidget(bg_btn)

        exit_btn = QPushButton("Sair")
        exit_btn.setObjectName("prompt-btn-exit")
        exit_btn.clicked.connect(self._on_force_close)
        prompt_btns.addWidget(exit_btn)

        prompt_layout.addLayout(prompt_btns)
        main_layout.addWidget(self.prompt_box)

        # Status Bar
        status_box = QFrame()
        status_box.setObjectName("status-bar")
        status_layout = QHBoxLayout(status_box)
        status_layout.setContentsMargins(14, 6, 14, 6)
        status_layout.setSpacing(6)
        
        self.status_label = QLabel("Indexando...")
        self.status_label.setObjectName("status-text")
        status_layout.addWidget(self.status_label, stretch=1)

        self.reindex_btn = QPushButton("🔄")
        self.reindex_btn.setObjectName("reindex-btn")
        self.reindex_btn.setToolTip(t("reindex_tooltip"))
        self.reindex_btn.clicked.connect(self._on_reindex_clicked)
        status_layout.addWidget(self.reindex_btn)

        self.settings_btn = QPushButton("⚙️")
        self.settings_btn.setObjectName("settings-btn")
        self.settings_btn.setToolTip(t("tray_settings"))
        self.settings_btn.clicked.connect(self._on_settings_clicked)
        status_layout.addWidget(self.settings_btn)

        main_layout.addWidget(status_box)

    def eventFilter(self, obj, event):
        if obj == self.search_entry and event.type() == QEvent.Type.KeyPress:
            if event.key() == Qt.Key.Key_Escape:
                if self._prompt_visible:
                    self._hide_prompt()
                    self.search_entry.setFocus()
                elif self._indexing:
                    self._show_prompt()
                else:
                    self._hide_window()
                return True
            elif event.key() == Qt.Key.Key_Down:
                self._navigate_results(1)
                return True
            elif event.key() == Qt.Key.Key_Up:
                self._navigate_results(-1)
                return True
            elif event.key() == Qt.Key.Key_Tab:
                self._navigate_results(1)
                return True
        return super().eventFilter(obj, event)

    def _navigate_results(self, direction: int):
        if not self._results:
            return
        total = len(self._results)
        new_index = self._selected_index + direction
        if new_index < 0:
            new_index = total - 1
        elif new_index >= total:
            new_index = 0
            
        self.results_list.setCurrentRow(new_index)
        self._selected_index = new_index

    def _start_pulse(self):
        self.progress_bar.show()

    def _stop_pulse(self):
        self.progress_bar.hide()

    def _start_background_index(self):
        if self._indexing:
            return
        self._indexing = True
        self._local_count = 0
        self._cloud_count = 0
        self._last_cloud_ref = get_last_cloud_count()
        self.reindex_btn.setEnabled(False)
        self._start_pulse()
        self.counter_label.setText(t("counter", local=0, cloud=0))
        self.counter_label.show()
        self.status_label.setText(t("indexing_local"))
        self._hide_prompt()
        self._cloud_thread = threading.Thread(target=self._index_thread, daemon=True)
        self._cloud_thread.start()

    def _on_local_found(self, count: int, pdf: dict = None):
        self._signals.local_found.emit(count, pdf)

    def _on_cloud_found(self, count: int, pdf: dict = None):
        self._signals.cloud_found.emit(count, pdf)

    def _on_local_found_signal(self, count, pdf):
        self._local_count = count
        self._refresh_counter()

    def _on_cloud_found_signal(self, count, pdf):
        self._cloud_count = count
        if pdf:
            insert_single_cloud_pdf(pdf)
        self._refresh_counter()

    def _refresh_counter(self):
        if self._indexing and self._last_cloud_ref > 0 and self._cloud_count > 0:
            pct = min(int(self._cloud_count / self._last_cloud_ref * 100), 99)
            self.counter_label.setText(
                t("counter_progress", local=self._local_count, cloud=self._cloud_count, ref=self._last_cloud_ref, pct=pct)
            )
        else:
            self.counter_label.setText(
                t("counter", local=self._local_count, cloud=self._cloud_count)
            )

    def _index_thread(self):
        local_count = build_index_local(self.config, on_found=self._on_local_found)
        self._signals.local_found.emit(local_count, None)
        self._signals.status_update.emit(f"✅ {local_count} PDFs locais")

        remotes = self.config.nuvem.remotes
        if remotes:
            ref_str = f" / ~{self._last_cloud_ref}" if self._last_cloud_ref > 0 else ""
            self._signals.status_update.emit(f"☁ Indexando nuvem...{ref_str} (pode demorar)")

            cloud_done = {"value": False, "count": 0}
            def _cloud_scan():
                try:
                    pdfs = scan_cloud(self.config, on_found=self._on_cloud_found)
                    save_cloud_results(pdfs)
                    cloud_done["count"] = len(pdfs)
                    cloud_done["value"] = True

                    total = local_count + len(pdfs)
                    self._signals.refresh_counter.emit()

                    last_ts = get_last_indexed_at()
                    ts_part = f"  ·  Última: {last_ts}" if last_ts else ""
                    msg = f"✅ {total} PDFs (☁ nuvem incluída){ts_part}" if len(pdfs) > 0 else f"✅ {total} PDFs indexados{ts_part}"
                    
                    self._signals.status_update.emit(msg)
                    self._signals.done.emit(total)
                except Exception:
                    pass

            scan_th = threading.Thread(target=_cloud_scan, daemon=True)
            scan_th.start()
            scan_th.join(timeout=30)

            if not cloud_done["value"]:
                self._signals.status_update.emit("☁ Nuvem lenta... (aguardando)")
                scan_th.join(timeout=30)
                if not cloud_done["value"]:
                    self._signals.status_update.emit(f"⚠ Nuvem lenta — indexando em 2º plano ({local_count} PDFs locais disponíveis)")
                    self._signals.cloud_slow.emit()
        else:
            last_ts = get_last_indexed_at()
            ts_part = f"  ·  Última: {last_ts}" if last_ts else ""
            self._signals.status_update.emit(f"✅ {local_count} PDFs indexados{ts_part}")
            self._signals.done.emit(local_count)

    def _on_index_done(self, total):
        self._indexing = False
        self._cloud_thread = None
        self._stop_pulse()
        self.reindex_btn.setEnabled(True)
        self._hide_prompt()
        self._send_notification(total)
        self._update_tray_state()

    def _send_notification(self, total: int):
        if sys.platform == "win32": return
        try:
            if not self.isVisible():
                subprocess.Popen(
                    [
                        "notify-send", "📄 Filebrowser",
                        f"Indexação concluída — {total} PDFs encontrados",
                        "--icon=document-open", "--urgency=low"
                    ],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                )
        except (FileNotFoundError, OSError):
            pass

    def _update_counter_cloud_slow(self):
        self.counter_label.setText(f"📂 {self._local_count} locais  ·  ☁ aguardando...")

    def _update_counter_cloud_fail(self):
        self.counter_label.setText(f"📂 {self._local_count} locais  ·  ☁ — indisponível")

    def _update_status(self, text: str):
        self.status_label.setText(text)

    def _on_reindex_clicked(self):
        self._start_background_index()
        self.search_entry.setFocus()

    def _on_settings_clicked(self):
        from src.ui.settings_ui import SettingsWindow
        self._settings_win = SettingsWindow(self)
        self._settings_win.show()

    def _on_search_changed(self, query: str):
        self._update_results(query)

    def _update_results(self, query: str):
        self.results_list.clear()
        self._selected_index = -1

        if not query.strip():
            self.results_list.hide()
            self._results = []
            return

        self._results = search_pdfs(query, max_results=self.config.interface.max_resultados)

        if not self._results:
            self.results_list.show()
            item = QListWidgetItem()
            widget = QLabel(t("no_results"))
            widget.setProperty("class", "no-results")
            widget.setStyleSheet("color: rgba(160, 160, 200, 125); padding: 20px; font-size: 13px;")
            item.setSizeHint(widget.sizeHint())
            self.results_list.addItem(item)
            self.results_list.setItemWidget(item, widget)
            return

        self.results_list.show()
        for pdf in self._results:
            item = QListWidgetItem()
            widget = self._create_result_row(pdf)
            item.setSizeHint(widget.sizeHint())
            self.results_list.addItem(item)
            self.results_list.setItemWidget(item, widget)

        self.results_list.setCurrentRow(0)
        self._selected_index = 0

        self.status_label.setText(t("results_found", n=len(self._results)))

    def _create_result_row(self, pdf: dict) -> QWidget:
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(10)

        # Usar a propriedade real `fonte` do SQLite para definir o ícone
        fonte = pdf.get("fonte", "local")
        is_cloud = fonte in ["nuvem", "nuvem_nativa"] or pdf["caminho"].startswith("cloud://")

        icon_char = "☁️" if is_cloud else "📄"
        icon_color = "#60a0e0" if is_cloud else "#e06060"

        icon = QLabel(icon_char)
        icon.setStyleSheet(f"font-size: 22px; color: {icon_color};")
        layout.addWidget(icon)

        info_box = QVBoxLayout()
        info_box.setSpacing(2)
        
        name_label = QLabel(pdf["nome"])
        name_label.setStyleSheet("font-size: 14px; font-weight: 600; color: #d8d8f0;")
        info_box.addWidget(name_label)

        path_display = pdf["caminho"].replace(str(Path.home()), "~")
        if len(path_display) > 60:
            path_display = path_display[:20] + "..." + path_display[-35:]
        path_label = QLabel(path_display)
        path_label.setStyleSheet("font-size: 11px; color: rgba(160, 160, 200, 180);")
        info_box.addWidget(path_label)

        layout.addLayout(info_box, stretch=1)
        return widget

    def _on_row_activated(self, item):
        index = self.results_list.row(item)
        if 0 <= index < len(self._results):
            self._selected_index = index
            self._open_selected_pdf()

    def _open_selected_pdf(self):
        if self._selected_index < 0 or self._selected_index >= len(self._results):
            return

        pdf = self._results[self._selected_index]
        caminho = pdf["caminho"]
        leitor = self.config.geral.leitor

        if caminho.startswith("cloud://"):
            import tempfile
            from PyQt6.QtCore import Qt
            from PyQt6.QtWidgets import QApplication
            
            parts = caminho[8:].split("/", 1)
            remote = parts[0]
            cloud_path = parts[1] if len(parts) > 1 else ""
            
            safe_name = os.path.basename(cloud_path)
            tmp_dir = os.path.join(tempfile.gettempdir(), f"filebrowser_cloud_{remote}")
            os.makedirs(tmp_dir, exist_ok=True)
            tmp_path = os.path.join(tmp_dir, safe_name)
            
            QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
            try:
                subprocess.run(
                    ["rclone", "copyto", f"{remote}:{cloud_path}", tmp_path],
                    check=True, capture_output=True
                )
                caminho = tmp_path
            except Exception:
                QApplication.restoreOverrideCursor()
                return
            finally:
                QApplication.restoreOverrideCursor()

        try:
            if sys.platform == "win32" and leitor.lower() not in ["zathura", "evince", "okular"]:
                os.startfile(caminho)
            else:
                subprocess.Popen(
                    [leitor, caminho],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                )
        except FileNotFoundError:
            if sys.platform == "win32":
                os.startfile(caminho)
            else:
                subprocess.Popen(
                    ["xdg-open", caminho],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                )

        if self.config.geral.fechar_apos_abrir:
            self._hide_window()

    def _check_and_close(self):
        if not self.isActiveWindow():
            if self._indexing:
                self._show_prompt()
                self.activateWindow()
            else:
                self._hide_window()

    def _hide_window(self):
        self.search_entry.setText("")
        self.hide()

    def _show_prompt(self):
        self._prompt_visible = True
        self.prompt_box.show()

    def _hide_prompt(self):
        self._prompt_visible = False
        self.prompt_box.hide()

    def _on_continue_background(self):
        self._hide_prompt()
        self.hide()
        self._update_tray_state()
        self.fb_app._ensure_tray()

    def _on_force_close(self):
        self._indexing = False
        self.close()
        QApplication.quit()

    def _update_tray_state(self):
        if hasattr(self.fb_app, 'update_tray_state'):
            self.fb_app.update_tray_state(
                self._indexing, 
                self._local_count, 
                self._cloud_count, 
                self.status_label.text()
            )


class FilebrowserApp:
    def __init__(self, config: AppConfig):
        self.config = config
        self.app = QApplication(sys.argv)
        self.app.setQuitOnLastWindowClosed(False)
        self._win = None
        self._tray = None
        self._item_status = None

    def run(self, argv):
        # Create Main Window
        self._win = FilebrowserWindow(self.app, self.config, self)

        # Build tray icon natively
        self._build_tray()

        from src.ui.settings_ui import apply_saved_shortcut, _detect_wm
        success, msg = apply_saved_shortcut(callback=self._on_tray_show)
        
        if success is False and _detect_wm() == "windows":
            self._on_tray_settings()

        return self.app.exec()

    def _build_tray(self):
        self._tray = QSystemTrayIcon(self._win)
        self._tray.setIcon(QIcon.fromTheme("folder"))
        self._tray.setToolTip("Filebrowser")
        
        menu = QMenu()
        self._item_status = QAction(t("tray_title"), self._win)
        self._item_status.setEnabled(False)
        menu.addAction(self._item_status)
        menu.addSeparator()

        item_show = QAction(t("tray_show"), self._win)
        item_show.triggered.connect(self._on_tray_show)
        menu.addAction(item_show)

        item_reindex = QAction(t("tray_reindex"), self._win)
        item_reindex.triggered.connect(self._on_tray_reindex)
        menu.addAction(item_reindex)

        menu.addSeparator()

        item_settings = QAction(t("tray_settings"), self._win)
        item_settings.triggered.connect(self._on_tray_settings)
        menu.addAction(item_settings)

        item_about = QAction(t("tray_about"), self._win)
        item_about.triggered.connect(self._on_tray_about)
        menu.addAction(item_about)

        item_feedback = QAction(t("tray_feedback"), self._win)
        item_feedback.triggered.connect(self._on_tray_feedback)
        menu.addAction(item_feedback)

        item_donate = QAction(t("tray_donate"), self._win)
        item_donate.triggered.connect(self._on_tray_donate)
        menu.addAction(item_donate)

        menu.addSeparator()

        item_quit = QAction(t("tray_quit"), self._win)
        item_quit.triggered.connect(self._on_tray_quit)
        menu.addAction(item_quit)

        self._tray.setContextMenu(menu)
        self._tray.activated.connect(self._on_tray_activated)
        self._tray.show()

    def _on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self._on_tray_show()

    def _on_tray_show(self):
        self._win.show()
        self._win.activateWindow()
        QTimer.singleShot(50, self._win._force_floating)

    def _on_tray_reindex(self):
        self._win.show()
        self._win.activateWindow()
        QTimer.singleShot(50, self._win._force_floating)
        QTimer.singleShot(50, self._win._start_background_index)

    def _on_tray_settings(self):
        from src.ui.settings_ui import SettingsWindow
        win = SettingsWindow(self._win)
        win.show()

    def _on_tray_about(self):
        from src.ui.about import AboutWindow
        win = AboutWindow(self._win)
        win.show()

    def _on_tray_feedback(self):
        from src.ui.feedback import FeedbackWindow
        win = FeedbackWindow(self._win)
        win.show()

    def _on_tray_donate(self):
        from src.ui.donate import DonateWindow
        win = DonateWindow(self._win)
        win.show()

    def _on_tray_quit(self):
        QApplication.quit()

    def update_tray_state(self, indexing, local_count, cloud_count, status_text):
        if not self._tray or not self._item_status:
            return
            
        icon_theme = "folder-download" if indexing else "folder"
        self._tray.setIcon(QIcon.fromTheme(icon_theme))

        if indexing:
            label = t("tray_indexing", local=local_count, cloud=cloud_count)
        elif local_count + cloud_count > 0:
            label = t("tray_indexed", n=local_count + cloud_count)
        else:
            label = t("tray_title")

        self._tray.setToolTip(label)
        self._item_status.setText(label)
