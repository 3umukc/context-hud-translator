from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QComboBox, QGroupBox, QSpinBox, QMessageBox
)
from PyQt6.QtCore import Qt
from config import config
from ui.styles import SETTINGS_STYLESHEET

SUPPORTED_LANGUAGES = [
    # Основные
    ("Русский (ru)", "ru"),
    ("English (en)", "en"),
    # Европа
    ("Deutsch / Немецкий (de)", "de"),
    ("Français / Французский (fr)", "fr"),
    ("Español / Испанский (es)", "es"),
    ("Italiano / Итальянский (it)", "it"),
    ("Português / Португальский (pt)", "pt"),
    ("Nederlands / Нидерландский (nl)", "nl"),
    ("Polski / Польский (pl)", "pl"),
    ("Українська / Украинский (uk)", "uk"),
    ("Čeština / Чешский (cs)", "cs"),
    ("Slovenčina / Словацкий (sk)", "sk"),
    ("Български / Болгарский (bg)", "bg"),
    ("Српски / Сербский (sr)", "sr"),
    ("Hrvatski / Хорватский (hr)", "hr"),
    ("Svenska / Шведский (sv)", "sv"),
    ("Norsk / Норвежский (no)", "no"),
    ("Dansk / Датский (da)", "da"),
    ("Suomi / Финский (fi)", "fi"),
    ("Ελληνικά / Греческий (el)", "el"),
    ("Magyar / Венгерский (hu)", "hu"),
    ("Română / Румынский (ro)", "ro"),
    ("Lietuvių / Литовский (lt)", "lt"),
    ("Latviešu / Латышский (lv)", "lv"),
    ("Eesti / Эстонский (et)", "et"),
    # СНГ и Кавказ
    ("Қазақша / Казахский (kk)", "kk"),
    ("Беларуская / Белорусский (be)", "be"),
    ("Հայերեն / Армянский (hy)", "hy"),
    ("ქართული / Грузинский (ka)", "ka"),
    ("Azərbaycan / Азербайджанский (az)", "az"),
    ("Oʻzbekcha / Узбекский (uz)", "uz"),
    ("Тоҷикӣ / Таджикский (tg)", "tg"),
    ("Кыргызча / Киргизский (ky)", "ky"),
    # Ближний Восток и Азия
    ("Türkçe / Турецкий (tr)", "tr"),
    ("中文 / Китайский (zh)", "zh"),
    ("日本語 / Японский (ja)", "ja"),
    ("한국어 / Корейский (ko)", "ko"),
    ("العربية / Арабский (ar)", "ar"),
    ("עברית / Иврит (he)", "he"),
    ("فارسی / Персидский (fa)", "fa"),
    ("हिन्दी / Хинди (hi)", "hi"),
    ("Tiếng Việt / Вьетнамский (vi)", "vi"),
    ("ไทย / Тайский (th)", "th"),
    ("Bahasa Indonesia / Индонезийский (id)", "id"),
    ("Bahasa Melayu / Малайский (ms)", "ms"),
    ("Tagalog / Филиппинский (tl)", "tl"),
]

SOURCE_LANGUAGES = [
    ("Автоопределение (auto)", "auto"),
] + SUPPORTED_LANGUAGES

class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Настройки Context HUD Translator")
        self.setFixedSize(480, 490)
        self.setStyleSheet(SETTINGS_STYLESHEET)
        self.init_ui()
        self.load_values()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        # 1. API Keys Group
        api_group = QGroupBox("API Ключи (Облачные провайдеры)")
        api_layout = QVBoxLayout(api_group)
        api_layout.setSpacing(8)

        # Gemini
        api_layout.addWidget(QLabel("Google Gemini API Key (Бесплатный):"))
        self.gemini_key_edit = QLineEdit()
        self.gemini_key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.gemini_key_edit.setPlaceholderText("AIzaSy...")
        api_layout.addWidget(self.gemini_key_edit)

        # Groq
        api_layout.addWidget(QLabel("Groq Cloud API Key (Ультрабыстрый Llama 3.3):"))
        self.groq_key_edit = QLineEdit()
        self.groq_key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.groq_key_edit.setPlaceholderText("gsk_...")
        api_layout.addWidget(self.groq_key_edit)

        # DeepL
        api_layout.addWidget(QLabel("DeepL Free API Key:"))
        self.deepl_key_edit = QLineEdit()
        self.deepl_key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.deepl_key_edit.setPlaceholderText("xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx:fx")
        api_layout.addWidget(self.deepl_key_edit)

        layout.addWidget(api_group)

        # 2. General Preferences Group
        pref_group = QGroupBox("Параметры языков и работы")
        pref_layout = QVBoxLayout(pref_group)
        pref_layout.setSpacing(8)

        # Active Provider
        prov_row = QHBoxLayout()
        prov_row.addWidget(QLabel("Основной провайдер:"))
        self.provider_combo = QComboBox()
        self.provider_combo.addItems(["auto", "groq", "gemini", "deepl", "offline"])
        prov_row.addWidget(self.provider_combo)
        pref_layout.addLayout(prov_row)

        # Source language (С какого)
        src_row = QHBoxLayout()
        src_row.addWidget(QLabel("С какого языка:"))
        self.src_lang_combo = QComboBox()
        self.src_lang_combo.setMaxVisibleItems(15)
        for label, code in SOURCE_LANGUAGES:
            self.src_lang_combo.addItem(label, code)
        src_row.addWidget(self.src_lang_combo)
        pref_layout.addLayout(src_row)

        # Target language (На какой)
        tgt_row = QHBoxLayout()
        tgt_row.addWidget(QLabel("На какой язык:"))
        self.tgt_lang_combo = QComboBox()
        self.tgt_lang_combo.setMaxVisibleItems(15)
        for label, code in SUPPORTED_LANGUAGES:
            self.tgt_lang_combo.addItem(label, code)
        tgt_row.addWidget(self.tgt_lang_combo)
        pref_layout.addLayout(tgt_row)

        # Debounce
        debounce_row = QHBoxLayout()
        debounce_row.addWidget(QLabel("Debounce задержка ввода (мс):"))
        self.debounce_spin = QSpinBox()
        self.debounce_spin.setRange(200, 1500)
        self.debounce_spin.setSingleStep(50)
        debounce_row.addWidget(self.debounce_spin)
        pref_layout.addLayout(debounce_row)

        layout.addWidget(pref_group)

        # Hotkeys info
        info_label = QLabel("Горячие клавиши: [Ctrl+Space] — HUD | [2x Ctrl+C] — Quick Select | [Ctrl+Shift+T] — Замена")
        info_label.setStyleSheet("color: #6B7280; font-size: 11px;")
        layout.addWidget(info_label)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        cancel_btn = QPushButton("Отмена")
        cancel_btn.setObjectName("SecondaryBtn")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        save_btn = QPushButton("Сохранить")
        save_btn.clicked.connect(self.save_values)
        btn_layout.addWidget(save_btn)

        layout.addLayout(btn_layout)

    def load_values(self):
        keys = config.get("api_keys", {})
        self.gemini_key_edit.setText(keys.get("gemini", ""))
        self.groq_key_edit.setText(keys.get("groq", ""))
        self.deepl_key_edit.setText(keys.get("deepl", ""))

        provider = config.get("provider", "auto")
        idx = self.provider_combo.findText(provider)
        if idx >= 0:
            self.provider_combo.setCurrentIndex(idx)

        s_lang = config.get("source_lang", "ru")
        s_idx = self.src_lang_combo.findData(s_lang)
        if s_idx >= 0:
            self.src_lang_combo.setCurrentIndex(s_idx)

        t_lang = config.get("target_lang", "en")
        t_idx = self.tgt_lang_combo.findData(t_lang)
        if t_idx >= 0:
            self.tgt_lang_combo.setCurrentIndex(t_idx)

        self.debounce_spin.setValue(config.get("debounce_ms", 400))

    def save_values(self):
        config.set("api_keys.gemini", self.gemini_key_edit.text().strip())
        config.set("api_keys.groq", self.groq_key_edit.text().strip())
        config.set("api_keys.deepl", self.deepl_key_edit.text().strip())
        config.set("provider", self.provider_combo.currentText())
        config.set("source_lang", self.src_lang_combo.currentData())
        config.set("target_lang", self.tgt_lang_combo.currentData())
        config.set("debounce_ms", self.debounce_spin.value())
        self.accept()
