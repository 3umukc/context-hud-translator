import sys
import threading
import time
from PyQt6.QtWidgets import QApplication, QSystemTrayIcon, QMenu
from PyQt6.QtGui import QIcon, QPixmap, QColor, QPainter, QFont
from PyQt6.QtCore import Qt, QTimer

from config import config
from core.context_buffer import ContextBuffer
from core.wsd_engine import WSDEngine
from services.translation_manager import TranslationManager
from windows.hooks import WinHookWorker, get_cursor_position, simulate_copy, simulate_paste
from ui.hud_window import HudWindow
from ui.settings_dialog import SettingsDialog

def create_tray_icon():
    pixmap = QPixmap(32, 32)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    # Circle background
    painter.setBrush(QColor(37, 99, 235))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawRoundedRect(2, 2, 28, 28, 6, 6)
    # Text
    painter.setPen(QColor(255, 255, 255))
    font = QFont("Segoe UI", 13, QFont.Weight.Bold)
    painter.setFont(font)
    painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, "T")
    painter.end()
    return QIcon(pixmap)

class ContextHudApp:
    def __init__(self):
        self.app = QApplication(sys.argv)
        self.app.setQuitOnLastWindowClosed(False)

        # Core logic components
        self.context_buffer = ContextBuffer(max_sentences=config.get("wsd.max_context_sentences", 3))
        self.wsd_engine = WSDEngine(self.context_buffer)
        self.translation_mgr = TranslationManager()

        # UI HUD Window
        self.hud = HudWindow(self.context_buffer, self.wsd_engine, self.translation_mgr)

        # Win32 Global Hooks Worker with Live Inline Translation
        self.hook_worker = WinHookWorker(self.context_buffer, self.wsd_engine)
        self.hook_worker.double_ctrl_c_detected.connect(self.on_double_ctrl_c)
        self.hook_worker.toggle_hud_triggered.connect(self.on_toggle_hud)
        self.hook_worker.in_place_replace_triggered.connect(self.on_in_place_replace)
        self.hook_worker.live_typing_toggled.connect(self.on_live_typing_toggled)

        self.hook_thread = threading.Thread(target=self.hook_worker.start_hook, daemon=True)
        self.hook_thread.start()

        # System Tray
        self.tray = QSystemTrayIcon(create_tray_icon(), self.app)
        self.tray.setToolTip("Context HUD Translator (WSD)")
        self.setup_tray_menu()
        self.tray.show()

    def setup_tray_menu(self):
        menu = QMenu()
        
        self.live_action = menu.addAction("Прямой перевод при вводе (Alt+T)")
        self.live_action.setCheckable(True)
        self.live_action.setChecked(self.hook_worker.live_typing_enabled)
        self.live_action.triggered.connect(self.toggle_live_typing)

        menu.addSeparator()

        show_action = menu.addAction("Показать HUD (Ctrl+Space)")
        show_action.triggered.connect(self.on_toggle_hud)

        clear_ctx_action = menu.addAction("Очистить контекст WSD")
        clear_ctx_action.triggered.connect(self.hud.clear_context)

        settings_action = menu.addAction("Настройки...")
        settings_action.triggered.connect(self.hud.open_settings)

        menu.addSeparator()
        quit_action = menu.addAction("Выход")
        quit_action.triggered.connect(self.quit_app)

        self.tray.setContextMenu(menu)
        self.tray.activated.connect(self._on_tray_activated)

    def toggle_live_typing(self):
        self.hook_worker.live_typing_enabled = not self.hook_worker.live_typing_enabled
        self.on_live_typing_toggled(self.hook_worker.live_typing_enabled)

    def on_live_typing_toggled(self, enabled: bool):
        self.live_action.setChecked(enabled)
        src = config.get("source_lang", "ru").upper()
        tgt = config.get("target_lang", "en").upper()
        status_msg = f"Прямой ввод {src} → {tgt} ВКЛЮЧЕН (Alt+T)" if enabled else "Прямой ввод ВЫКЛЮЧЕН"
        self.tray.showMessage("Синхронный переводчик", status_msg, QSystemTrayIcon.MessageIcon.Information, 1500)

    def _on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self.on_toggle_hud()

    def on_double_ctrl_c(self, x: int, y: int):
        clipboard = QApplication.clipboard()
        text = clipboard.text().strip()
        if text:
            self.hud.show_at_cursor(x, y, text)
        else:
            self.hud.show_at_cursor(x, y)

    def on_toggle_hud(self):
        if self.hud.isVisible():
            self.hud.hide()
        else:
            x, y = get_cursor_position()
            self.hud.show_at_cursor(x, y)

    def on_in_place_replace(self):
        # 1. Copy selected text
        simulate_copy()
        time.sleep(0.08)
        clipboard = QApplication.clipboard()
        text = clipboard.text().strip()
        if not text:
            return

        # 2. Update anchors and translate
        self.wsd_engine.infer_and_update_anchors(text)
        target_lang = config.get("target_lang", "ru")
        prompts = self.wsd_engine.build_llm_prompt(text, target_lang=target_lang)

        provider, _ = self.translation_mgr.get_preferred_provider()

        # Run translation in background thread to avoid freezing target window
        def _replace_worker():
            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                translated = loop.run_until_complete(
                    provider.translate(text, prompts, target_lang)
                )
                if translated and not translated.startswith("["):
                    # Update context buffer
                    self.context_buffer.add_text_chunks(text)
                    # Put back on clipboard and paste
                    QTimer.singleShot(0, lambda: self._paste_translation(translated))
            finally:
                loop.close()

        threading.Thread(target=_replace_worker, daemon=True).start()

    def _paste_translation(self, translated: str):
        clipboard = QApplication.clipboard()
        clipboard.setText(translated)
        time.sleep(0.05)
        simulate_paste()

    def quit_app(self):
        self.hook_worker.stop_hook()
        self.hud.close()
        self.app.quit()

    def run(self):
        # Run in background with tray notification
        self.tray.showMessage(
            "Синхронный переводчик",
            "Активен прямой ввод: печатайте в любом поле — текст сразу переводится (Alt+T для переключения)!",
            QSystemTrayIcon.MessageIcon.Information,
            3000
        )
        sys.exit(self.app.exec())

if __name__ == "__main__":
    app = ContextHudApp()
    app.run()
