"""
GUI 样式常量 —— 所有颜色、字体和样式表集中管理。
"""
from __future__ import annotations

# ── 颜色 ──────────────────────────────────────────────────

COLOR_BG = "#f5f5f7"
COLOR_CARD_BG = "#ffffff"
COLOR_TEXT = "#1d1d1f"
COLOR_TEXT_SECONDARY = "#6e6e73"
COLOR_TEXT_MUTED = "#8e8e93"
COLOR_BORDER = "#c7c7cc"
COLOR_BORDER_HOVER = "#999"
COLOR_ACCENT = "#0071e3"
COLOR_ACCENT_HOVER = "#0077ed"
COLOR_ACCENT_PRESSED = "#006edb"
COLOR_SECONDARY_BG = "#e8e8ed"
COLOR_SECONDARY_HOVER = "#dedee3"
COLOR_SECONDARY_PRESSED = "#d4d4d9"
COLOR_DANGER = "#ff3b30"
COLOR_DANGER_HOVER = "#ff453a"
COLOR_DANGER_PRESSED = "#d63028"
COLOR_DISABLED = "#aeaeb2"
COLOR_LOG_BG = "#1e1e1e"
COLOR_LOG_TEXT = "#e0e0e0"
COLOR_LOG_SELECTION = "#3a3a3a"
COLOR_PROGRESS_TRACK = "#e8e8ed"

# ── 字体 ──────────────────────────────────────────────────

FONT_FAMILIES = ["-apple-system", "Segoe UI", "Noto Sans CJK SC", "sans-serif"]
FONT_MONO = "'SF Mono', 'JetBrains Mono', 'Consolas', monospace"
FONT_SIZE_SM = 10
FONT_SIZE = 13

# ── 尺寸 ──────────────────────────────────────────────────

CARD_PADDING = (24, 20, 24, 20)
CARD_RADIUS = 12
INPUT_RADIUS = 6
INPUT_PADDING = "7px 10px"
BTN_RADIUS = 6
BTN_PADDING = "8px 20px"
BTN_HEIGHT = 38
LOG_RADIUS = 10
LOG_PADDING = "14px 16px"
PROGRESS_RADIUS = 7
PROGRESS_HEIGHT = 14
SCROLLBAR_WIDTH = 8
SCROLLBAR_RADIUS = 4
FIELD_LABEL_WIDTH = 72
SPINNER_MIN_WIDTH = 96
PATH_COMBO_MIN_WIDTH = 280

# ── 共享样式表 ─────────────────────────────────────────────

CARD_STYLE = (
    "QWidget { background: %s; border-radius: %dpx; }"
    % (COLOR_CARD_BG, CARD_RADIUS)
)

SECTION_LABEL_STYLE = (
    "font-size: 11px; font-weight: 600; color: %s; letter-spacing: 0.4px;"
    % COLOR_TEXT_SECONDARY
)

FIELD_LABEL_STYLE = "font-size: 13px; color: %s; font-weight: 400;" % COLOR_TEXT

INPUT_STYLE = (
    "QLineEdit { background: %s; border: 1px solid %s; border-radius: %dpx; "
    "padding: %s; font-size: 13px; color: %s; }"
    "QLineEdit:focus { border: 1px solid %s; }"
    % (COLOR_CARD_BG, COLOR_BORDER, INPUT_RADIUS, INPUT_PADDING, COLOR_TEXT, COLOR_ACCENT)
)

SPINNER_STYLE = (
    "QSpinBox { background: %s; border: 1px solid %s; border-radius: %dpx; "
    "padding: %s; font-size: 13px; }"
    "QSpinBox:focus { border: 1px solid %s; }"
    % (COLOR_CARD_BG, COLOR_BORDER, INPUT_RADIUS, INPUT_PADDING, COLOR_ACCENT)
)

COMBO_STYLE = (
    "QComboBox { background: %s; border: 1px solid %s; border-radius: %dpx; "
    "padding: %s; font-size: 13px; color: %s; min-height: 20px; }"
    "QComboBox:hover { border: 1px solid %s; }"
    "QComboBox:focus { border: 1px solid %s; }"
    "QComboBox::drop-down { border: none; width: 22px; }"
    "QComboBox::down-arrow { image: none; border: none; }"
    "QComboBox QAbstractItemView { background: %s; border: 1px solid %s; "
    "border-radius: %dpx; padding: 4px; selection-background-color: %s; "
    "font-size: 13px; outline: none; }"
    % (
        COLOR_CARD_BG, COLOR_BORDER, INPUT_RADIUS, INPUT_PADDING, COLOR_TEXT,
        COLOR_BORDER_HOVER, COLOR_ACCENT,
        COLOR_CARD_BG, COLOR_BORDER, INPUT_RADIUS, COLOR_SECONDARY_BG,
    )
)

# 通用下拉框（无 down-arrow 定制，用于 cb_history / cb_presets）
COMBO_SIMPLE_STYLE = (
    "QComboBox { background: %s; border: 1px solid %s; border-radius: %dpx; "
    "padding: %s; font-size: 13px; min-height: 20px; }"
    "QComboBox:hover { border: 1px solid %s; }"
    "QComboBox::drop-down { border: none; width: 20px; }"
    "QComboBox QAbstractItemView { background: %s; border: 1px solid %s; "
    "border-radius: %dpx; padding: 4px; selection-background-color: %s; }"
    % (
        COLOR_CARD_BG, COLOR_BORDER, INPUT_RADIUS, INPUT_PADDING,
        COLOR_BORDER_HOVER,
        COLOR_CARD_BG, COLOR_BORDER, INPUT_RADIUS, COLOR_SECONDARY_BG,
    )
)

PRIMARY_BTN_STYLE = (
    "QPushButton { background: %s; color: #fff; border: none; "
    "border-radius: %dpx; padding: %s; font-size: 13px; font-weight: 500; }"
    "QPushButton:hover { background: %s; }"
    "QPushButton:pressed { background: %s; }"
    "QPushButton:disabled { background: %s; }"
    % (COLOR_ACCENT, BTN_RADIUS, BTN_PADDING,
       COLOR_ACCENT_HOVER, COLOR_ACCENT_PRESSED, COLOR_DISABLED)
)

SECONDARY_BTN_STYLE = (
    "QPushButton { background: %s; color: %s; border: none; "
    "border-radius: %dpx; padding: %s; font-size: 13px; font-weight: 400; }"
    "QPushButton:hover { background: %s; }"
    "QPushButton:pressed { background: %s; }"
    % (COLOR_SECONDARY_BG, COLOR_TEXT, BTN_RADIUS, BTN_PADDING,
       COLOR_SECONDARY_HOVER, COLOR_SECONDARY_PRESSED)
)

TINY_BTN_STYLE = (
    "QPushButton { background: transparent; color: %s; border: none; "
    "padding: 2px 6px; font-size: 12px; }"
    "QPushButton:hover { color: %s; text-decoration: underline; }"
    % (COLOR_ACCENT, COLOR_ACCENT_HOVER)
)

DANGER_BTN_STYLE = (
    "QPushButton { background: %s; color: #fff; border: none; "
    "border-radius: %dpx; padding: %s; font-size: 13px; font-weight: 500; }"
    "QPushButton:hover { background: %s; }"
    "QPushButton:pressed { background: %s; }"
    % (COLOR_DANGER, BTN_RADIUS, BTN_PADDING,
       COLOR_DANGER_HOVER, COLOR_DANGER_PRESSED)
)

LOG_AREA_STYLE = (
    "QTextEdit { background: %s; border: none; border-radius: %dpx; "
    "padding: %s; font-family: %s; font-size: 12px; color: %s; "
    "selection-background-color: %s; }"
    % (COLOR_LOG_BG, LOG_RADIUS, LOG_PADDING, FONT_MONO,
       COLOR_LOG_TEXT, COLOR_LOG_SELECTION)
)

TAB_WIDGET_STYLE = (
    "QTabWidget::pane { border: none; background: %s; padding: 20px 24px; }"
    "QTabBar::tab { background: transparent; color: %s; padding: 8px 16px; "
    "margin-right: 2px; border-bottom: 2px solid transparent; font-size: 14px; font-weight: 500; }"
    "QTabBar::tab:selected { color: %s; border-bottom: 2px solid %s; }"
    "QTabBar::tab:hover:!selected { color: #515154; }"
    % (COLOR_BG, COLOR_TEXT_MUTED, COLOR_ACCENT, COLOR_ACCENT)
)

RADIO_STYLE = "QRadioButton { spacing: 6px; padding: 4px 0; font-size: 13px; }"
CHECKBOX_STYLE = "QCheckBox { spacing: 8px; font-size: 13px; }"

PROGRESS_STYLE = (
    "QProgressBar { background: %s; border: none; border-radius: %dpx; "
    "font-size: %dpx; color: %s; text-align: center; }"
    "QProgressBar::chunk { background: %s; border-radius: %dpx; }"
    % (COLOR_PROGRESS_TRACK, PROGRESS_RADIUS, FONT_SIZE_SM, COLOR_TEXT,
       COLOR_ACCENT, PROGRESS_RADIUS)
)

SCROLL_AREA_STYLE = (
    "QScrollArea { border: none; background: %s; }"
    "QScrollBar:vertical { background: transparent; width: %dpx; margin: 0; }"
    "QScrollBar::handle:vertical { background: #c0c0c0; border-radius: %dpx; min-height: 30px; }"
    "QScrollBar::handle:vertical:hover { background: #a0a0a0; }"
    "QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }"
    "QScrollBar:horizontal { background: transparent; height: %dpx; margin: 0; }"
    "QScrollBar::handle:horizontal { background: #c0c0c0; border-radius: %dpx; min-width: 30px; }"
    "QScrollBar::handle:horizontal:hover { background: #a0a0a0; }"
    "QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0; }"
    % (COLOR_BG, SCROLLBAR_WIDTH, SCROLLBAR_RADIUS,
       SCROLLBAR_WIDTH, SCROLLBAR_RADIUS)
)
