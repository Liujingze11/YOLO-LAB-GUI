"""
控件工厂函数 —— 统一创建带 Apple 风格样式的 Qt 控件。
"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QGraphicsDropShadowEffect,
    QLabel,
    QLineEdit,
    QProgressBar,
    QPushButton,
    QSpinBox,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from gui.i18n import tr

from gui.styles import (
    CARD_PADDING,
    CARD_RADIUS,
    DANGER_BTN_STYLE,
    FIELD_LABEL_STYLE,
    INPUT_STYLE,
    LOG_AREA_STYLE,
    PATH_COMBO_MIN_WIDTH,
    PRIMARY_BTN_STYLE,
    PROGRESS_HEIGHT,
    PROGRESS_STYLE,
    SCROLL_AREA_STYLE,
    SECONDARY_BTN_STYLE,
    SECTION_LABEL_STYLE,
    SPINNER_MIN_WIDTH,
    SPINNER_STYLE,
    TINY_BTN_STYLE,
    COMBO_STYLE,
)


def card(parent: QWidget | None = None) -> tuple[QWidget, QVBoxLayout]:
    """带阴影的白色圆角卡片。"""
    w = QWidget(parent)
    w.setProperty("i18nKey", "")
    w.setProperty("themeClass", "card")
    w.setStyleSheet(f"QWidget {{ background: #ffffff; border-radius: {CARD_RADIUS}px; }}")
    shadow = QGraphicsDropShadowEffect()
    shadow.setBlurRadius(24)
    shadow.setColor(Qt.gray)
    shadow.setOffset(0, 1)
    w.setGraphicsEffect(shadow)
    lay = QVBoxLayout(w)
    lay.setContentsMargins(*CARD_PADDING)
    lay.setSpacing(0)
    return w, lay


def section_label(text: str, parent: QWidget | None = None,
                  i18n_key: str | None = None) -> QLabel:
    """大写灰色区域标题。"""
    display = tr(i18n_key) if i18n_key else text.upper()
    lbl = QLabel(display, parent)
    lbl.setProperty("i18nKey", i18n_key or "")
    lbl.setProperty("themeClass", "section_label")
    lbl.setStyleSheet(SECTION_LABEL_STYLE)
    lbl.setTextInteractionFlags(Qt.TextSelectableByMouse)
    return lbl


def field_label(text: str, parent: QWidget | None = None,
                i18n_key: str | None = None) -> QLabel:
    """常规字段标签。"""
    display = tr(i18n_key) if i18n_key else text
    lbl = QLabel(display, parent)
    lbl.setProperty("i18nKey", i18n_key or "")
    lbl.setProperty("themeClass", "field_label")
    lbl.setStyleSheet(FIELD_LABEL_STYLE)
    lbl.setTextInteractionFlags(Qt.TextSelectableByMouse)
    return lbl


def input_(placeholder: str = "", default: str = "", min_width: int = 0,
           parent: QWidget | None = None, i18n_key: str | None = None) -> QLineEdit:
    """带焦点高亮的文本输入框。"""
    e = QLineEdit(default, parent)
    e.setPlaceholderText(tr(i18n_key) if i18n_key else placeholder)
    e.setProperty("i18nKey", i18n_key or "")
    e.setProperty("themeClass", "input")
    e.setStyleSheet(INPUT_STYLE)
    if min_width:
        e.setMinimumWidth(min_width)
    return e


def path_combo(default: str = "", history: list[str] | None = None,
               parent: QWidget | None = None, i18n_key: str | None = None) -> QComboBox:
    """可编辑路径下拉框：输入框 + 下拉历史。"""
    cb = QComboBox(parent)
    cb.setEditable(True)
    cb.setInsertPolicy(QComboBox.NoInsert)
    cb.setMinimumWidth(PATH_COMBO_MIN_WIDTH)
    cb.setProperty("i18nKey", i18n_key or "")
    cb.setProperty("themeClass", "combo")
    cb.setStyleSheet(COMBO_STYLE)
    if history:
        cb.addItems(history)
    cb.setCurrentText(default)
    cb.setSizePolicy(cb.sizePolicy().horizontalPolicy(), cb.sizePolicy().verticalPolicy())
    return cb


def path_combo_get(cb: QComboBox) -> str:
    """从路径下拉框获取当前文本。"""
    return cb.currentText().strip()


def spinner(min_val: int, max_val: int, default: int, min_width: int = SPINNER_MIN_WIDTH,
            parent: QWidget | None = None, i18n_key: str | None = None) -> QSpinBox:
    """数值微调框。"""
    s = QSpinBox(parent)
    s.setRange(min_val, max_val)
    s.setValue(default)
    s.setMinimumWidth(min_width)
    s.setProperty("i18nKey", i18n_key or "")
    s.setProperty("themeClass", "spinner")
    s.setStyleSheet(SPINNER_STYLE)
    return s


def btn(text: str, primary: bool = True, parent: QWidget | None = None,
        i18n_key: str | None = None) -> QPushButton:
    """主要（蓝色）或次要（灰色）按钮。"""
    display = tr(i18n_key) if i18n_key else text
    b = QPushButton(display, parent)
    b.setProperty("i18nKey", i18n_key or "")
    tc = "primary_btn" if primary else "secondary_btn"
    b.setProperty("themeClass", tc)
    b.setStyleSheet(PRIMARY_BTN_STYLE if primary else SECONDARY_BTN_STYLE)
    return b


def tiny_btn(text: str, parent: QWidget | None = None,
             i18n_key: str | None = None) -> QPushButton:
    """透明蓝色链接按钮。"""
    display = tr(i18n_key) if i18n_key else text
    b = QPushButton(display, parent)
    b.setProperty("i18nKey", i18n_key or "")
    b.setProperty("themeClass", "tiny_btn")
    b.setStyleSheet(TINY_BTN_STYLE)
    return b


def danger_btn(text: str, parent: QWidget | None = None,
               i18n_key: str | None = None) -> QPushButton:
    """红色危险按钮。"""
    display = tr(i18n_key) if i18n_key else text
    b = QPushButton(display, parent)
    b.setProperty("i18nKey", i18n_key or "")
    b.setProperty("themeClass", "danger_btn")
    b.setStyleSheet(DANGER_BTN_STYLE)
    return b


def log_area(parent: QWidget | None = None, i18n_key: str | None = None) -> QTextEdit:
    """深色主题只读日志区域。"""
    e = QTextEdit(parent)
    e.setReadOnly(True)
    e.setProperty("i18nKey", i18n_key or "")
    e.setProperty("themeClass", "log_area")
    e.setStyleSheet(LOG_AREA_STYLE)
    e.setMinimumHeight(130)
    return e


def progress_bar(parent: QWidget | None = None, i18n_key: str | None = None) -> QProgressBar:
    """圆角蓝色进度条。"""
    p = QProgressBar(parent)
    p.setRange(0, 100)
    p.setValue(0)
    p.setFixedHeight(PROGRESS_HEIGHT)
    p.setTextVisible(True)
    p.setFormat(tr("train.progress.format"))
    p.setProperty("i18nKey", i18n_key or "")
    p.setProperty("themeClass", "progress")
    p.setStyleSheet(PROGRESS_STYLE)
    return p


def scroll_area(widget: QWidget, parent: QWidget | None = None,
                i18n_key: str | None = None) -> QScrollArea:
    """包裹一个 widget 的可滚动区域（细滚动条）。"""
    from PySide6.QtWidgets import QScrollArea
    scroll = QScrollArea(parent)
    scroll.setWidgetResizable(True)
    scroll.setWidget(widget)
    scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
    scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
    scroll.setProperty("i18nKey", i18n_key or "")
    scroll.setProperty("themeClass", "scroll_area")
    scroll.setStyleSheet(SCROLL_AREA_STYLE)
    return scroll


def simple_combo(min_width: int = 120, font_size: int = 12,
                 parent: QWidget | None = None, i18n_key: str | None = None) -> QComboBox:
    """通用下拉框（无 down-arrow 覆盖）。"""
    from gui.styles import COMBO_SIMPLE_STYLE
    cb = QComboBox(parent)
    cb.setMinimumWidth(min_width)
    cb.setProperty("i18nKey", i18n_key or "")
    cb.setProperty("themeClass", "combo_simple")
    cb.setStyleSheet(COMBO_SIMPLE_STYLE.replace("font-size: 13px", f"font-size: {font_size}px"))
    return cb
