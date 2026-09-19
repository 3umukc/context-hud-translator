import asyncio
import threading
from typing import Optional

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTextEdit,
    QPushButton, QApplication, QFrame
)
from PyQt6.QtCore import Qt, QPoint, QTimer, pyqtSignal, QObject
from PyQt6.QtGui import QGuiApplication, QClipboard

from config import config
from core.context_buffer import ContextBuffer
from core.wsd_engine import WSDEngine
from services.translation_manager import TranslationManager
from ui.styles import HUD_STYLESHEET
from ui.settings_dialog import SettingsDialog

class AsyncStreamWorker(QObject):
    chunk_received = pyqtSignal(str, str)  # chunk, provider_name
    finished = pyqtSignal()
    error = pyqtSignal(str)

    def __init__(self, translation_mgr: TranslationManager, text: str, prompts: dict, target_lang: str):
        super().__init__()
        self.translation_mgr = translation_mgr
        self.text = text
        self.prompts = prompts
        self.target_lang = target_lang
        self._is_cancelled = False

    def cancel(self):
        self._is_cancelled = True

    def run(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(self._execute())
        finally:
            loop.close()

    async def _execute(self):
        try:
            async for chunk, prov_name in self.translation_mgr.translate_stream(
                self.text, self.prompts, self.target_lang
            ):
                if self._is_cancelled:
                    break
                self.chunk_received.emit(chunk, prov_name)
        except Exception as e:
            self.error.emit(str(e))
        finally:
            self.finished.emit()


class HudInputEdit(QTextEdit):
    enter_pressed = pyqtSignal()
    escape_pressed = pyqtSignal()

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            if event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
                super().keyPressEvent(event)
            else:
                self.enter_pressed.emit()
                event.accept()
        elif event.key() == Qt.Key.Key_Escape:
            self.escape_pressed.emit()
            event.accept()
        else:
            super().keyPressEvent(event)

class HudWindow(QWidget):
    def __init__(self, context_buffer: ContextBuffer, wsd_engine: WSDEngine, translation_mgr: TranslationManager):
        super().__init__()
        self.context_buffer = context_buffer
        self.wsd_engine = wsd_engine
        self.translation_mgr = translation_mgr

        self._drag_pos = QPoint()
        self._active_worker: Optional[AsyncStreamWorker] = None
        self._worker_thread: Optional[threading.Thread] = None
        self._current_translating_text = ""

        # Debounce timer for user typing
        self.debounce_timer = QTimer(self)
        self.debounce_timer.setSingleShot(True)
        self.debounce_timer.timeout.connect(self._on_debounce_timeout)

        self.init_window_flags()
        self.init_ui()
        self.update_provider_badge()
        self.update_anchor_tags()

    def init_window_flags(self):
        self.setWindowFlags(
            Qt.WindowType.Window |
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.resize(config.get("hud.width", 460), config.get("hud.height", 280))

    def init_ui(self):
        # Outer container for dark glass border styling
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(4, 4, 4, 4)

        self.container = QWidget()
        self.container.setObjectName("HudContainer")
        self.container.setStyleSheet(HUD_STYLESHEET)
        container_layout = QVBoxLayout(self.container)
        container_layout.setContentsMargins(12, 10, 12, 10)
        container_layout.setSpacing(8)

        # 1. Header Bar (draggable)
        header = QHBoxLayout()
        header.setSpacing(8)

        self.title_label = QLabel("Context HUD")
        self.title_label.setObjectName("HeaderTitle")
        header.addWidget(self.title_label)

        self.provider_badge = QLabel("Auto")
        self.provider_badge.setObjectName("ProviderBadge")
        header.addWidget(self.provider_badge)

        header.addStretch()

        self.toggle_input_btn = QPushButton("Ввод")
        self.toggle_input_btn.setObjectName("ToggleInputBtn")
        self.toggle_input_btn.setToolTip("Показать/скрыть поле прямого ввода")
        self.toggle_input_btn.clicked.connect(self.toggle_input_visibility)
        header.addWidget(self.toggle_input_btn)

        self.settings_btn = QPushButton("Настройки")
        self.settings_btn.setObjectName("ActionButton")
        self.settings_btn.setToolTip("Настройки API и языков")
        self.settings_btn.clicked.connect(self.open_settings)
        header.addWidget(self.settings_btn)

        self.close_btn = QPushButton("x")
        self.close_btn.setObjectName("CloseBtn")
        self.close_btn.setToolTip("Скрыть HUD (Ctrl+Space или Esc)")
        self.close_btn.clicked.connect(self.hide)
        header.addWidget(self.close_btn)

        container_layout.addLayout(header)

        # 2. Input Text Field
        self.input_field = HudInputEdit()
        self.input_field.setObjectName("InputField")
        self.input_field.setPlaceholderText("Введите текст здесь (Enter — перевести) или выделите в любой программе (2x Ctrl+C)...")
        self.input_field.setFixedHeight(65)
        self.input_field.textChanged.connect(self._on_input_text_changed)
        self.input_field.enter_pressed.connect(self._on_enter_pressed)
        self.input_field.escape_pressed.connect(self.hide)
        container_layout.addWidget(self.input_field)

        # 3. Output Translation Field (Streaming)
        self.output_field = QTextEdit()
        self.output_field.setObjectName("OutputField")
        self.output_field.setReadOnly(True)
        self.output_field.setPlaceholderText("Перевод появится здесь...")
        container_layout.addWidget(self.output_field)

        # 4. Anchors display row
        self.anchors_layout = QHBoxLayout()
        self.anchors_layout.setSpacing(4)
        self.anchors_label = QLabel("Якоря WSD:")
        self.anchors_label.setStyleSheet("color: #6B7280; font-size: 11px;")
        self.anchors_layout.addWidget(self.anchors_label)
        self.anchors_container = QHBoxLayout()
        self.anchors_layout.addLayout(self.anchors_container)
        self.anchors_layout.addStretch()
        container_layout.addLayout(self.anchors_layout)

        # 5. Footer Actions Bar
        footer = QHBoxLayout()
        
        self.context_info = QLabel("Контекст: 0 предложений")
        self.context_info.setStyleSheet("color: #6B7280; font-size: 11px;")
        footer.addWidget(self.context_info)

        footer.addStretch()

        self.clear_ctx_btn = QPushButton("Сброс контекста")
        self.clear_ctx_btn.setObjectName("ActionButton")
        self.clear_ctx_btn.clicked.connect(self.clear_context)
        footer.addWidget(self.clear_ctx_btn)

        self.copy_btn = QPushButton("Копировать")
        self.copy_btn.setObjectName("ActionButton")
        self.copy_btn.clicked.connect(self.copy_translation)
        footer.addWidget(self.copy_btn)

        container_layout.addLayout(footer)
        outer_layout.addWidget(self.container)

    # Window Dragging support
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton and not self._drag_pos.isNull():
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.hide()
        else:
            super().keyPressEvent(event)

    def _on_input_text_changed(self):
        debounce_ms = config.get("debounce_ms", 400)
        self.debounce_timer.start(debounce_ms)

    def _on_enter_pressed(self):
        self.debounce_timer.stop()
        text = self.input_field.toPlainText().strip()
        if text:
            self.start_translation(text)

    def _on_debounce_timeout(self):
        text = self.input_field.toPlainText().strip()
        if text:
            self.start_translation(text)

    def showEvent(self, event):
        super().showEvent(event)
        self.input_field.setFocus()

    def toggle_input_visibility(self):
        if self.input_field.isVisible():
            self.input_field.hide()
            self.resize(config.get("hud.width", 460), 185)
        else:
            self.input_field.show()
            self.resize(config.get("hud.width", 460), 280)
            self.input_field.setFocus()

    def start_translation(self, text: str):
        if not text:
            return

        self._current_translating_text = text

        # Cancel any running worker
        if self._active_worker:
            self._active_worker.cancel()

        # Update WSD anchors based on input and context
        self.wsd_engine.infer_and_update_anchors(text)
        self.update_anchor_tags()

        # Build prompt
        target_lang = config.get("target_lang", "ru")
        prompts = self.wsd_engine.build_llm_prompt(text, target_lang=target_lang)

        # Clear output field
        self.output_field.clear()

        # Start streaming in thread
        self._active_worker = AsyncStreamWorker(self.translation_mgr, text, prompts, target_lang)
        self._active_worker.chunk_received.connect(self._on_chunk_received)
        self._active_worker.finished.connect(self._on_stream_finished)
        self._active_worker.error.connect(self._on_stream_error)

        self._worker_thread = threading.Thread(target=self._active_worker.run, daemon=True)
        self._worker_thread.start()

    def _on_chunk_received(self, chunk: str, provider_name: str):
        self.output_field.moveCursor(self.output_field.textCursor().MoveOperation.End)
        self.output_field.insertPlainText(chunk)
        self.provider_badge.setText(provider_name)

    def _on_stream_finished(self):
        # Once translation completes, add sentence to context buffer
        text = self._current_translating_text.strip()
        if text:
            self.context_buffer.add_text_chunks(text)
            n_ctx = len(self.context_buffer.history_sentences)
            self.context_info.setText(f"Контекст: {n_ctx} предл.")

    def _on_stream_error(self, err: str):
        self.output_field.setPlainText(f"[Ошибка перевода: {err}]")

    def show_at_cursor(self, cursor_x: int, cursor_y: int, initial_text: Optional[str] = None):
        """Displays HUD near cursor, adjusting to screen boundaries."""
        if initial_text:
            # Quick Select mode: hide input field so source text NEVER appears
            self.input_field.hide()
            self.input_field.clear()
            target_h = 185
        else:
            # Manual typing mode: show input field for direct entry
            self.input_field.show()
            self.input_field.clear()
            target_h = 280

        self.resize(config.get("hud.width", 460), target_h)

        screen = QGuiApplication.primaryScreen()
        if screen:
            geom = screen.availableGeometry()
            w, h = self.width(), target_h
            x = min(max(cursor_x + 15, geom.left() + 10), geom.right() - w - 10)
            y = min(max(cursor_y + 15, geom.top() + 10), geom.bottom() - h - 10)
            self.move(x, y)

        if initial_text:
            self.start_translation(initial_text)

        self.show()
        self.raise_()
        self.activateWindow()
        if not initial_text:
            self.input_field.setFocus()

    def copy_translation(self):
        text = self.output_field.toPlainText().strip()
        if text:
            clipboard = QApplication.clipboard()
            clipboard.setText(text)
            self.copy_btn.setText("Скопировано")
            QTimer.singleShot(1500, lambda: self.copy_btn.setText("Копировать"))

    def clear_context(self):
        self.context_buffer.clear()
        self.context_info.setText("Контекст: 0 предл.")
        self.update_anchor_tags()

    def update_anchor_tags(self):
        # Clear existing tags
        while self.anchors_container.count():
            item = self.anchors_container.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        anchors = self.context_buffer.term_anchors.get_anchors()
        if not anchors:
            empty_lbl = QLabel("нет")
            empty_lbl.setStyleSheet("color: #4B5563; font-size: 10px;")
            self.anchors_container.addWidget(empty_lbl)
            return

        for term, data in list(anchors.items())[:4]:  # Show top 4
            tag = QLabel(f"{term} → {data['translation']}")
            tag.setObjectName("AnchorTag")
            tag.setStyleSheet(HUD_STYLESHEET)
            self.anchors_container.addWidget(tag)

    def update_provider_badge(self):
        _, name = self.translation_mgr.get_preferred_provider()
        self.provider_badge.setText(name)

    def open_settings(self):
        dlg = SettingsDialog(self)
        if dlg.exec():
            self.translation_mgr.reload_config()
            self.update_provider_badge()
