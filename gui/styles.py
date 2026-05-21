"""
GUI 样式常量 —— 所有颜色、字体和样式表集中管理。
"""
from __future__ import annotations

from PySide6.QtWidgets import QWidget

# ═══════════════════════════════════════════════════════════
#  亮色主题颜色
# ═══════════════════════════════════════════════════════════

LIGHT = {
    "bg":               "#f5f5f7",
    "card_bg":          "#ffffff",
    "text":             "#1d1d1f",
    "text_secondary":   "#6e6e73",
    "text_muted":       "#8e8e93",
    "border":           "#c7c7cc",
    "border_hover":     "#999999",
    "accent":           "#0071e3",
    "accent_hover":     "#0077ed",
    "accent_pressed":   "#006edb",
    "secondary_bg":     "#e8e8ed",
    "secondary_hover":  "#dedee3",
    "secondary_pressed":"#d4d4d9",
    "danger":           "#ff3b30",
    "danger_hover":     "#ff453a",
    "danger_pressed":   "#d63028",
    "disabled":         "#aeaeb2",
    "log_bg":           "#1e1e1e",
    "log_text":         "#e0e0e0",
    "log_selection":    "#3a3a3a",
    "progress_track":   "#e8e8ed",
}

# ═══════════════════════════════════════════════════════════
#  暗色主题颜色
# ═══════════════════════════════════════════════════════════

DARK = {
    "bg":               "#1e1e1e",
    "card_bg":          "#2d2d2d",
    "text":             "#e0e0e0",
    "text_secondary":   "#8e8e93",
    "text_muted":       "#999999",
    "border":           "#444444",
    "border_hover":     "#666666",
    "accent":           "#4da6ff",
    "accent_hover":     "#5db8ff",
    "accent_pressed":   "#3d96ef",
    "secondary_bg":     "#3a3a3a",
    "secondary_hover":  "#4a4a4a",
    "secondary_pressed":"#333333",
    "danger":           "#ff453a",
    "danger_hover":     "#ff5e55",
    "danger_pressed":   "#d63028",
    "disabled":         "#666666",
    "log_bg":           "#1e1e1e",
    "log_text":         "#e0e0e0",
    "log_selection":    "#3a3a3a",
    "progress_track":   "#444444",
}

# ═══════════════════════════════════════════════════════════
#  字体 & 尺寸
# ═══════════════════════════════════════════════════════════

FONT_FAMILIES = ["-apple-system", "Segoe UI", "Noto Sans CJK SC", "sans-serif"]
FONT_MONO = "'SF Mono', 'JetBrains Mono', 'Consolas', monospace"
FONT_SIZE_SM = 10
FONT_SIZE = 13

CARD_PADDING = (20, 16, 20, 16)
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

# ═══════════════════════════════════════════════════════════
#  样式构建函数
# ═══════════════════════════════════════════════════════════

def _style(theme: dict) -> dict:
    """返回给定主题的所有样式字符串。"""
    p = theme
    return {
        "card": (
            "QWidget { background: %s; border-radius: %dpx; }"
            % (p["card_bg"], CARD_RADIUS)
        ),
        "section_label": (
            "font-size: 11px; font-weight: 600; color: %s; letter-spacing: 0.4px;"
            % p["text_secondary"]
        ),
        "field_label": "font-size: 13px; color: %s; font-weight: 400;" % p["text"],
        "input": (
            "QLineEdit { background: %s; border: 1px solid %s; border-radius: %dpx; "
            "padding: %s; font-size: 13px; color: %s; }"
            "QLineEdit:focus { border: 1px solid %s; }"
            % (p["card_bg"], p["border"], INPUT_RADIUS, INPUT_PADDING, p["text"], p["accent"])
        ),
        "spinner": (
            "QSpinBox { background: %s; border: 1px solid %s; border-radius: %dpx; "
            "padding: %s; font-size: 13px; color: %s; }"
            "QSpinBox:focus { border: 1px solid %s; }"
            % (p["card_bg"], p["border"], INPUT_RADIUS, INPUT_PADDING, p["text"], p["accent"])
        ),
        "combo": (
            "QComboBox { background: %s; border: 1px solid %s; border-radius: %dpx; "
            "padding: %s; font-size: 13px; color: %s; min-height: 20px; }"
            "QComboBox:hover { border: 1px solid %s; }"
            "QComboBox:focus { border: 1px solid %s; }"
            "QComboBox::drop-down { border: none; width: 22px; }"
            "QComboBox::down-arrow { image: none; border: none; }"
            "QComboBox QAbstractItemView { background: %s; border: 1px solid %s; "
            "border-radius: %dpx; padding: 4px; selection-background-color: %s; "
            "font-size: 13px; outline: none; color: %s; }"
            % (
                p["card_bg"], p["border"], INPUT_RADIUS, INPUT_PADDING, p["text"],
                p["border_hover"], p["accent"],
                p["card_bg"], p["border"], INPUT_RADIUS, p["secondary_bg"], p["text"],
            )
        ),
        "combo_simple": (
            "QComboBox { background: %s; border: 1px solid %s; border-radius: %dpx; "
            "padding: %s; font-size: 13px; min-height: 20px; color: %s; }"
            "QComboBox:hover { border: 1px solid %s; }"
            "QComboBox::drop-down { border: none; width: 20px; }"
            "QComboBox QAbstractItemView { background: %s; border: 1px solid %s; "
            "border-radius: %dpx; padding: 4px; selection-background-color: %s; color: %s; }"
            % (
                p["card_bg"], p["border"], INPUT_RADIUS, INPUT_PADDING, p["text"],
                p["border_hover"],
                p["card_bg"], p["border"], INPUT_RADIUS, p["secondary_bg"], p["text"],
            )
        ),
        "primary_btn": (
            "QPushButton { background: %s; color: #fff; border: none; "
            "border-radius: %dpx; padding: %s; font-size: 13px; font-weight: 500; }"
            "QPushButton:hover { background: %s; }"
            "QPushButton:pressed { background: %s; }"
            "QPushButton:disabled { background: %s; }"
            % (p["accent"], BTN_RADIUS, BTN_PADDING,
               p["accent_hover"], p["accent_pressed"], p["disabled"])
        ),
        "secondary_btn": (
            "QPushButton { background: %s; color: %s; border: none; "
            "border-radius: %dpx; padding: %s; font-size: 13px; font-weight: 400; }"
            "QPushButton:hover { background: %s; }"
            "QPushButton:pressed { background: %s; }"
            % (p["secondary_bg"], p["text"], BTN_RADIUS, BTN_PADDING,
               p["secondary_hover"], p["secondary_pressed"])
        ),
        "tiny_btn": (
            "QPushButton { background: transparent; color: %s; border: none; "
            "padding: 2px 6px; font-size: 12px; }"
            "QPushButton:hover { color: %s; text-decoration: underline; }"
            % (p["accent"], p["accent_hover"])
        ),
        "danger_btn": (
            "QPushButton { background: %s; color: #fff; border: none; "
            "border-radius: %dpx; padding: %s; font-size: 13px; font-weight: 500; }"
            "QPushButton:hover { background: %s; }"
            "QPushButton:pressed { background: %s; }"
            % (p["danger"], BTN_RADIUS, BTN_PADDING,
               p["danger_hover"], p["danger_pressed"])
        ),
        "log_area": (
            "QTextEdit { background: %s; border: none; border-radius: %dpx; "
            "padding: %s; font-family: %s; font-size: 12px; color: %s; "
            "selection-background-color: %s; }"
            % (p["log_bg"], LOG_RADIUS, LOG_PADDING, FONT_MONO,
               p["log_text"], p["log_selection"])
        ),
        "tab_widget": (
            "QTabWidget::pane { border: none; background: %s; padding: 20px 24px; }"
            "QTabBar::tab { background: transparent; color: %s; padding: 8px 16px; "
            "margin-right: 2px; border-bottom: 2px solid transparent; font-size: 14px; font-weight: 500; }"
            "QTabBar::tab:selected { color: %s; border-bottom: 2px solid %s; }"
            "QTabBar::tab:hover:!selected { color: %s; }"
            % (p["bg"], p["text_muted"], p["accent"], p["accent"], p["text"])
        ),
        "radio": "QRadioButton { spacing: 6px; padding: 4px 0; font-size: 13px; color: %s; }" % p["text"],
        "checkbox": "QCheckBox { spacing: 8px; font-size: 13px; color: %s; }" % p["text"],
        "progress": (
            "QProgressBar { background: %s; border: none; border-radius: %dpx; "
            "font-size: %dpx; color: %s; text-align: center; }"
            "QProgressBar::chunk { background: %s; border-radius: %dpx; }"
            % (p["progress_track"], PROGRESS_RADIUS, FONT_SIZE_SM, p["text"],
               p["accent"], PROGRESS_RADIUS)
        ),
        "scroll_area": (
            "QScrollArea { border: none; background: %s; }"
            "QScrollBar:vertical { background: transparent; width: %dpx; margin: 0; }"
            "QScrollBar::handle:vertical { background: %s; border-radius: %dpx; min-height: 30px; }"
            "QScrollBar::handle:vertical:hover { background: %s; }"
            "QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }"
            "QScrollBar:horizontal { background: transparent; height: %dpx; margin: 0; }"
            "QScrollBar::handle:horizontal { background: %s; border-radius: %dpx; min-width: 30px; }"
            "QScrollBar::handle:horizontal:hover { background: %s; }"
            "QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0; }"
            % (p["bg"], SCROLLBAR_WIDTH,
               p["border"], SCROLLBAR_RADIUS, p["border_hover"],
               SCROLLBAR_WIDTH,
               p["border"], SCROLLBAR_RADIUS, p["border_hover"])
        ),
    }


# 预计算两套样式
_LIGHT_STYLES = _style(LIGHT)
_DARK_STYLES = _style(DARK)

# ═══════════════════════════════════════════════════════════
#  向后兼容的亮色样式常量
# ═══════════════════════════════════════════════════════════

CARD_STYLE         = _LIGHT_STYLES["card"]
SECTION_LABEL_STYLE = _LIGHT_STYLES["section_label"]
FIELD_LABEL_STYLE  = _LIGHT_STYLES["field_label"]
INPUT_STYLE        = _LIGHT_STYLES["input"]
SPINNER_STYLE      = _LIGHT_STYLES["spinner"]
COMBO_STYLE        = _LIGHT_STYLES["combo"]
COMBO_SIMPLE_STYLE = _LIGHT_STYLES["combo_simple"]
PRIMARY_BTN_STYLE  = _LIGHT_STYLES["primary_btn"]
SECONDARY_BTN_STYLE = _LIGHT_STYLES["secondary_btn"]
TINY_BTN_STYLE     = _LIGHT_STYLES["tiny_btn"]
DANGER_BTN_STYLE   = _LIGHT_STYLES["danger_btn"]
LOG_AREA_STYLE     = _LIGHT_STYLES["log_area"]
TAB_WIDGET_STYLE   = _LIGHT_STYLES["tab_widget"]
RADIO_STYLE        = _LIGHT_STYLES["radio"]
CHECKBOX_STYLE     = _LIGHT_STYLES["checkbox"]
PROGRESS_STYLE     = _LIGHT_STYLES["progress"]
SCROLL_AREA_STYLE  = _LIGHT_STYLES["scroll_area"]

# 亮色模式颜色常量 (向后兼容)
COLOR_BG              = LIGHT["bg"]
COLOR_CARD_BG         = LIGHT["card_bg"]
COLOR_TEXT            = LIGHT["text"]
COLOR_TEXT_SECONDARY  = LIGHT["text_secondary"]
COLOR_TEXT_MUTED      = LIGHT["text_muted"]
COLOR_BORDER          = LIGHT["border"]
COLOR_BORDER_HOVER    = LIGHT["border_hover"]
COLOR_ACCENT          = LIGHT["accent"]
COLOR_ACCENT_HOVER    = LIGHT["accent_hover"]
COLOR_ACCENT_PRESSED  = LIGHT["accent_pressed"]
COLOR_SECONDARY_BG    = LIGHT["secondary_bg"]
COLOR_SECONDARY_HOVER = LIGHT["secondary_hover"]
COLOR_SECONDARY_PRESSED = LIGHT["secondary_pressed"]
COLOR_DANGER          = LIGHT["danger"]
COLOR_DANGER_HOVER    = LIGHT["danger_hover"]
COLOR_DANGER_PRESSED  = LIGHT["danger_pressed"]
COLOR_DISABLED        = LIGHT["disabled"]
COLOR_LOG_BG          = LIGHT["log_bg"]
COLOR_LOG_TEXT        = LIGHT["log_text"]
COLOR_LOG_SELECTION   = LIGHT["log_selection"]
COLOR_PROGRESS_TRACK  = LIGHT["progress_track"]

# ═══════════════════════════════════════════════════════════
#  旧版全局暗色样式 (已废弃，保留兼容)
# ═══════════════════════════════════════════════════════════

DARK_STYLE = """
QWidget {
    background-color: #1e1e1e;
    color: #e0e0e0;
}
"""

DARK_TOGGLE_STYLE = (
    "QPushButton { background: transparent; color: %s; border: none; "
    "font-size: 16px; padding: 2px 8px; }"
    "QPushButton:hover { color: %s; }"
    % (COLOR_TEXT_MUTED, COLOR_ACCENT)
)

# ═══════════════════════════════════════════════════════════
#  主题切换
# ═══════════════════════════════════════════════════════════

THEME_CLASS_TO_KEY: dict[str, str] = {
    "card":           "card",
    "section_label":  "section_label",
    "field_label":    "field_label",
    "input":          "input",
    "spinner":        "spinner",
    "combo":          "combo",
    "combo_simple":   "combo_simple",
    "primary_btn":    "primary_btn",
    "secondary_btn":  "secondary_btn",
    "tiny_btn":       "tiny_btn",
    "danger_btn":     "danger_btn",
    "log_area":       "log_area",
    "tab_widget":     "tab_widget",
    "radio":          "radio",
    "checkbox":       "checkbox",
    "progress":       "progress",
    "scroll_area":    "scroll_area",
}


def apply_theme_to_widgets(root: QWidget, is_dark: bool) -> None:
    """递归遍历 widget 树，根据 themeClass 属性重新应用样式。"""
    from PySide6.QtCore import Qt as QtCore
    from PySide6.QtGui import QColor
    styles = _DARK_STYLES if is_dark else _LIGHT_STYLES
    stack = [root]
    while stack:
        w = stack.pop()
        tc = w.property("themeClass")
        if tc and tc in THEME_CLASS_TO_KEY:
            key = THEME_CLASS_TO_KEY[tc]
            w.setStyleSheet(styles[key])
        # 更新卡片阴影
        if tc == "card":
            effect = w.graphicsEffect()
            if effect is not None:
                effect.setColor(QColor("#000000" if is_dark else QtCore.gray))
        for child in w.children():
            if isinstance(child, QWidget):
                stack.append(child)
