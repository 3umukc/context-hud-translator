"""
Styles and color schemes for Context HUD Translator.
Modern dark glass / acrylic aesthetic.
"""

HUD_STYLESHEET = """
QWidget#HudContainer {
    background-color: rgba(22, 24, 29, 0.94);
    border: 1px solid rgba(255, 255, 255, 0.12);
    border-radius: 14px;
}

QLabel#HeaderTitle {
    color: #F3F4F6;
    font-family: 'Segoe UI', sans-serif;
    font-size: 13px;
    font-weight: 600;
    letter-spacing: 0.5px;
}

QLabel#ProviderBadge {
    color: #60A5FA;
    background-color: rgba(37, 99, 235, 0.2);
    border: 1px solid rgba(96, 165, 250, 0.3);
    border-radius: 6px;
    font-family: 'Segoe UI', sans-serif;
    font-size: 11px;
    font-weight: 500;
    padding: 2px 8px;
}

QTextEdit#InputField {
    background-color: rgba(30, 34, 42, 0.85);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 8px;
    color: #E5E7EB;
    font-family: 'Segoe UI', sans-serif;
    font-size: 13px;
    padding: 8px;
    selection-background-color: #3B82F6;
}

QTextEdit#InputField:focus {
    border: 1px solid #3B82F6;
    background-color: rgba(35, 40, 50, 0.95);
}

QTextEdit#OutputField {
    background-color: rgba(18, 20, 24, 0.9);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 8px;
    color: #34D399;
    font-family: 'Segoe UI', sans-serif;
    font-size: 14px;
    font-weight: 500;
    line-height: 1.4;
    padding: 10px;
    selection-background-color: #059669;
}

QPushButton#ToggleInputBtn {
    background-color: rgba(255, 255, 255, 0.05);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 6px;
    color: #9CA3AF;
    font-family: 'Segoe UI', sans-serif;
    font-size: 11px;
    padding: 2px 8px;
}

QPushButton#ToggleInputBtn:hover {
    background-color: rgba(59, 130, 246, 0.2);
    color: #60A5FA;
    border: 1px solid rgba(59, 130, 246, 0.4);
}

QPushButton.ActionButton {
    background-color: rgba(255, 255, 255, 0.06);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 6px;
    color: #9CA3AF;
    font-family: 'Segoe UI', sans-serif;
    font-size: 11px;
    padding: 4px 10px;
}

QPushButton.ActionButton:hover {
    background-color: rgba(255, 255, 255, 0.12);
    color: #F9FAFB;
    border: 1px solid rgba(255, 255, 255, 0.2);
}

QPushButton.ActionButton:pressed {
    background-color: rgba(255, 255, 255, 0.04);
}

QPushButton#CloseBtn {
    background-color: transparent;
    border: none;
    color: #9CA3AF;
    font-size: 14px;
    font-weight: bold;
    padding: 2px 6px;
    border-radius: 4px;
}

QPushButton#CloseBtn:hover {
    background-color: rgba(239, 68, 68, 0.25);
    color: #F87171;
}

QLabel#AnchorTag {
    background-color: rgba(245, 158, 11, 0.15);
    border: 1px solid rgba(245, 158, 11, 0.35);
    border-radius: 4px;
    color: #FBBF24;
    font-size: 10px;
    padding: 1px 6px;
    margin-right: 4px;
}
"""

SETTINGS_STYLESHEET = """
QDialog {
    background-color: #181A20;
    color: #E5E7EB;
    font-family: 'Segoe UI', sans-serif;
}

QLabel {
    color: #D1D5DB;
    font-size: 12px;
}

QLineEdit, QComboBox {
    background-color: #242731;
    border: 1px solid #374151;
    border-radius: 6px;
    color: #F9FAFB;
    padding: 6px 10px;
    font-size: 12px;
}

QLineEdit:focus, QComboBox:focus {
    border: 1px solid #3B82F6;
}

QGroupBox {
    border: 1px solid #2E333D;
    border-radius: 8px;
    margin-top: 10px;
    padding-top: 15px;
    font-weight: 600;
    color: #9CA3AF;
}

QPushButton {
    background-color: #2563EB;
    color: #FFFFFF;
    border: none;
    border-radius: 6px;
    padding: 8px 16px;
    font-size: 12px;
    font-weight: 500;
}

QPushButton:hover {
    background-color: #1D4ED8;
}

QPushButton#SecondaryBtn {
    background-color: #374151;
    color: #D1D5DB;
}

QPushButton#SecondaryBtn:hover {
    background-color: #4B5563;
}
"""
