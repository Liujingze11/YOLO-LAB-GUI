"""
GUI 样式常量 —— 所有颜色、字体和样式表集中管理。
"""
from __future__ import annotations

from PyQt5.QtWidgets import QWidget

from yolo_backprop.ui_theme import LIGHT, DARK, surface

# ═══════════════════════════════════════════════════════════
#  字体 & 尺寸
# ═══════════════════════════════════════════════════════════

FONT_FAMILIES = ["-apple-system", "Segoe UI", "Noto Sans CJK SC", "sans-serif"]
FONT_MONO = "'SF Mono', 'JetBrains Mono', 'Consolas', monospace"
FONT_SIZE_SM = 12
FONT_SIZE = 14

CARD_PADDING = (16, 14, 16, 14)
CARD_RADIUS = 12
INPUT_RADIUS = 8
INPUT_PADDING = "6px 10px"
BTN_RADIUS = 9
BTN_PADDING = "6px 14px"
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
            'QWidget[themeClass="card"] { background: %s; border: 1px solid %s; border-radius: %dpx; }'
            % (p['card_bg'], p["border"], CARD_RADIUS)
        ),
        "export_card": (
            'QFrame[themeClass="export_card"] { background: %s; border: 1px solid %s; border-radius: 10px; }'
            'QFrame[themeClass="export_card"]:hover { border-color: %s; }'
            'QFrame[themeClass="export_card"][selected="true"] { background: %s; border: 2px solid %s; }'
            % (surface(theme is DARK), p['border'], p['accent'], p['secondary_pressed'], p['accent'])
        ),
        "format_title": "font-size: 13px; font-weight: 600; background: transparent; border: none; color: %s;" % p['text'],
        "format_desc": "font-size: 10px; background: transparent; border: none; color: %s;" % p['text_muted'],
        "section_label": (
            "font-size: 14px; font-weight: 600; color: %s;"
            % p["text"]
        ),
        "field_label": "font-size: 13px; color: %s; font-weight: 400;" % p["text"],
        "muted_label": "font-size: 13px; color: %s;" % p["text_secondary"],
        "input": (
            "QLineEdit { background: %s; border: 1px solid %s; border-radius: %dpx; "
            "padding: %s; font-size: 13px; color: %s; }"
            "QLineEdit:focus { border: 1px solid %s; }"
            % (p["card_bg"], p["border"], INPUT_RADIUS, INPUT_PADDING, p["text"], p["accent"])
        ),
        "spinner": (
            "QSpinBox, QDoubleSpinBox { background: %s; border: 1px solid %s; border-radius: %dpx; "
            "padding: %s; font-size: 13px; color: %s; }"
            "QSpinBox:focus, QDoubleSpinBox:focus { border: 1px solid %s; }"
            % (p["card_bg"], p["border"], INPUT_RADIUS, INPUT_PADDING, p["text"], p["accent"])
        ),
        "combo": (
            "QComboBox { background: %s; border: 1px solid %s; border-radius: %dpx; "
            "padding: %s; font-size: 13px; color: %s; min-height: 20px; }"
            "QComboBox:hover { border: 1px solid %s; }"
            "QComboBox:focus { border: 1px solid %s; }"
            "QComboBox::drop-down { border: none; width: 22px; }"
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
            "QPushButton:disabled { color: #98989d; }"
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
            "QTabWidget::pane { border: none; background: %s; padding: 8px 0 0 0; }"
            "QTabBar { background: %s; border-radius: 12px; }"
            "QTabBar::tab { background: transparent; color: %s; padding: 7px 18px; "
            "margin: 3px; border: 1px solid transparent; border-radius: 9px; font-size: 14px; font-weight: 500; }"
            "QTabBar::tab:selected { color: %s; border-color: %s; background: %s; }"
            "QTabBar::tab:hover:!selected { color: %s; background: %s; }"
            % (p["bg"], p['progress_track'], p["text_secondary"], p["text"], p['border'], p['card_bg'], p["text"], p['secondary_bg'])
        ),
        "section_toggle": (
            'QToolButton { color: %s; font-size: 14px; font-weight: 600; padding: 2px; border: none; background: transparent; }'
            'QToolButton:hover { color: %s; } QToolButton:focus { border: 1px solid %s; border-radius: 5px; }'
            % (p['text'], p['accent'], p['accent'])
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

SECTION_LABEL_STYLE = _LIGHT_STYLES["section_label"]
FIELD_LABEL_STYLE  = _LIGHT_STYLES["field_label"]
MUTED_LABEL_STYLE = _LIGHT_STYLES['muted_label']
INPUT_STYLE        = _LIGHT_STYLES["input"]
SPINNER_STYLE      = _LIGHT_STYLES["spinner"]
COMBO_STYLE        = _LIGHT_STYLES["combo"]
COMBO_SIMPLE_STYLE = _LIGHT_STYLES["combo_simple"]

EXPORT_CARD_STYLE = (
    "QFrame { background: #ffffff; border: 1px solid #d0d0d0; border-radius: 8px; }"
    "QFrame:hover { border: 1px solid #0071e3; }"
)

EXPORT_CARD_SELECTED_STYLE = (
    "QFrame { background: rgba(0,113,227,0.08); border: 2px solid #0071e3; border-radius: 8px; }"
)
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

# 亮色模式颜色常量 (仅保留被引用的)
COLOR_TEXT            = LIGHT["text"]
COLOR_TEXT_MUTED      = LIGHT["text_muted"]
COLOR_ACCENT          = LIGHT["accent"]
COLOR_DISABLED        = LIGHT["disabled"]

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
    "export_card":    "export_card",
    "format_title":   "format_title",
    "format_desc":    "format_desc",
    "section_label":  "section_label",
    "section_toggle": "section_toggle",
    "field_label":    "field_label",
    "muted_label":    "muted_label",
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
    from PyQt5.QtGui import QColor
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
                effect.setColor(QColor(0, 0, 0, 50) if is_dark else QColor(0, 0, 0, 18))
        for child in w.children():
            if isinstance(child, QWidget):
                stack.append(child)
