"""
控件工厂函数 —— 统一创建带 Apple 风格样式的 Qt 控件。
"""
from __future__ import annotations

from PyQt5.QtCore import QEasingCurve, QPropertyAnimation, Qt
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import (
    QComboBox,
    QFrame,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSpinBox,
    QSplitter,
    QTextEdit,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from ISAT.model_development.gui.i18n import tr

from ISAT.model_development.gui.styles import (
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
    _LIGHT_STYLES,
)


def card(parent: QWidget | None = None) -> tuple[QWidget, QVBoxLayout]:
    """带阴影的白色圆角卡片。"""
    w = QWidget(parent)
    w.setProperty("i18nKey", "")
    w.setProperty("themeClass", "card")
    w.setAttribute(Qt.WA_StyledBackground, True)
    w.setStyleSheet(_LIGHT_STYLES['card'])
    shadow = QGraphicsDropShadowEffect()
    shadow.setBlurRadius(18)
    shadow.setColor(QColor(0, 0, 0, 18))
    shadow.setOffset(0, 3)
    w.setGraphicsEffect(shadow)
    lay = QVBoxLayout(w)
    lay.setContentsMargins(*CARD_PADDING)
    lay.setSpacing(0)
    return w, lay


CARD_HEADER_HEIGHT = 40


class FoldableCard(QWidget):
    """A resizable parameter group that keeps its controls alive when folded."""
    def set_expanded(self, expanded):
        self.toggle.setChecked(expanded)

    def _toggle_body(self, expanded):
        wrapper = self.parentWidget()
        splitter = wrapper.parentWidget() if wrapper is not None else None
        splitter = splitter if isinstance(splitter, QSplitter) else None
        sizes = splitter.sizes() if splitter is not None else None
        index = splitter.indexOf(wrapper) if splitter is not None else -1
        if not expanded:
            self._expanded_limits = (self.minimumHeight(), self.maximumHeight())
            if splitter is not None:
                self._expanded_size = sizes[index]
                self._wrapper_limits = (wrapper.minimumHeight(), wrapper.maximumHeight())
            self.body_scroll.hide()
            self.setFixedHeight(CARD_HEADER_HEIGHT)
            if splitter is not None:
                margins = wrapper.layout().contentsMargins()
                wrapper.setFixedHeight(CARD_HEADER_HEIGHT + margins.top() + margins.bottom())
                sizes[index] = wrapper.height()
        else:
            minimum, maximum = getattr(self, '_expanded_limits', (CARD_HEADER_HEIGHT, 16777215))
            self.setMinimumHeight(minimum); self.setMaximumHeight(maximum)
            self.body_scroll.show()
            if splitter is not None and hasattr(self, '_wrapper_limits'):
                minimum, maximum = self._wrapper_limits
                wrapper.setMinimumHeight(minimum); wrapper.setMaximumHeight(maximum)
                sizes[index] = max(self._expanded_size, wrapper.minimumSizeHint().height())
        self.toggle.setArrowType(Qt.DownArrow if expanded else Qt.RightArrow)
        if splitter is not None: splitter.setSizes(sizes)


def resizable_card(title: str = "", parent: QWidget | None = None,
                   i18n_key: str | None = None) -> tuple[QWidget, QHBoxLayout, QVBoxLayout]:
    """可拖拽压缩的卡片：固定标题栏 + 内容滚动区。

    被 QSplitter 挤压时内容区自动出现滚动条，最小可压缩至标题高度。

    Returns (card_widget, header_layout, body_layout)
    """
    w = FoldableCard(parent)
    w.setMinimumHeight(CARD_HEADER_HEIGHT)
    w.setProperty("themeClass", "card")
    w.setAttribute(Qt.WA_StyledBackground, True)
    w.setStyleSheet(_LIGHT_STYLES['card'])
    shadow = QGraphicsDropShadowEffect()
    shadow.setBlurRadius(12)
    shadow.setColor(QColor(0, 0, 0, 10))
    shadow.setOffset(0, 2)
    w.setGraphicsEffect(shadow)

    outer = QVBoxLayout(w)
    outer.setContentsMargins(0, 0, 0, 0)
    outer.setSpacing(0)

    # ── 标题栏（固定高度，始终可见）──
    header = QWidget()
    header.setStyleSheet("background: transparent; border: none;")
    header.setFixedHeight(CARD_HEADER_HEIGHT)
    header_layout = QHBoxLayout(header)
    header_layout.setContentsMargins(CARD_PADDING[0], 4, CARD_PADDING[2], 0)
    w.toggle = QToolButton()
    w.toggle.setText(tr(i18n_key) if i18n_key else title)
    w.toggle.setProperty('i18nKey', i18n_key or '')
    w.toggle.setProperty('themeClass', 'section_toggle')
    w.toggle.setStyleSheet(_LIGHT_STYLES['section_toggle'])
    w.toggle.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
    w.toggle.setArrowType(Qt.DownArrow)
    w.toggle.setCheckable(True); w.toggle.setChecked(True)
    w.toggle.setFocusPolicy(Qt.StrongFocus)
    header_layout.addWidget(w.toggle)
    header_layout.addStretch()
    outer.addWidget(header)

    # ── 内容滚动区 ──
    scroll = QScrollArea()
    w.body_scroll = scroll
    scroll.setWidgetResizable(True)
    scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
    scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
    scroll.setFrameShape(QFrame.NoFrame)
    scroll.setStyleSheet(
        f"QScrollArea {{ background: transparent; border: none; }} "
        f"QScrollBar:vertical {{ width: 6px; }} "
        f"QScrollBar::handle:vertical {{ background: #c0c0c0; border-radius: 3px; min-height: 20px; }} "
        f"QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }} "
        f"QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: none; }}"
    )

    body = QWidget()
    body.setStyleSheet("background: transparent; border: none;")
    body_layout = QVBoxLayout(body)
    body_layout.setContentsMargins(CARD_PADDING[0], 4, CARD_PADDING[2], 4)
    body_layout.setSpacing(0)
    scroll.setWidget(body)
    body.setAutoFillBackground(False)
    scroll.viewport().setAutoFillBackground(False)

    outer.addWidget(scroll, 1)
    w.toggle.toggled.connect(w._toggle_body)

    return w, header_layout, body_layout


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
    scroll = QScrollArea(parent)
    scroll.setWidgetResizable(True)
    scroll.setWidget(widget)
    widget.setAutoFillBackground(False)
    scroll.viewport().setAutoFillBackground(False)
    scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
    scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
    scroll.setProperty("i18nKey", i18n_key or "")
    scroll.setProperty("themeClass", "scroll_area")
    scroll.setStyleSheet(SCROLL_AREA_STYLE)
    return scroll


def simple_combo(min_width: int = 120, font_size: int = 12,
                 parent: QWidget | None = None, i18n_key: str | None = None) -> QComboBox:
    """通用下拉框（无 down-arrow 覆盖）。"""
    from ISAT.model_development.gui.styles import COMBO_SIMPLE_STYLE
    cb = QComboBox(parent)
    cb.setMinimumWidth(min_width)
    cb.setProperty("i18nKey", i18n_key or "")
    cb.setProperty("themeClass", "combo_simple")
    cb.setStyleSheet(COMBO_SIMPLE_STYLE.replace("font-size: 13px", f"font-size: {font_size}px"))
    return cb


def collapsible_section(title: str, i18n_key: str = "",
                        parent: QWidget | None = None) -> tuple[QWidget, QToolButton, QWidget, QVBoxLayout]:
    """Collapsible section with animated expand/collapse."""
    container = QWidget(parent)
    container.setStyleSheet("background: transparent; border: none;")

    outer = QVBoxLayout(container)
    outer.setContentsMargins(0, 0, 0, 0)
    outer.setSpacing(0)

    btn = QToolButton()
    display = tr(i18n_key) if i18n_key else title
    btn.setText(f"▸ {display}")
    btn.setProperty("i18nKey", i18n_key)
    btn.setToolButtonStyle(Qt.ToolButtonTextOnly)
    btn.setStyleSheet(
        "QToolButton { background: transparent; border: none; font-size: 12px; "
        "color: #6e6e73; font-weight: 500; padding: 4px 0; }"
        "QToolButton:hover { color: #0071e3; }"
    )
    btn.setCheckable(True)
    btn.setChecked(False)
    outer.addWidget(btn)

    content = QWidget()
    content.setStyleSheet("background: transparent; border: none;")
    content.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
    content.setMaximumHeight(0)
    content_layout = QVBoxLayout(content)
    content_layout.setContentsMargins(0, 8, 0, 4)
    content_layout.setSpacing(6)
    outer.addWidget(content)

    btn.toggled.connect(lambda checked: _animate_collapse(content, checked, btn))

    return container, btn, content, content_layout


def _animate_collapse(content: QWidget, expand: bool, btn: QToolButton) -> None:
    """Animate maxHeight for smooth expand/collapse."""
    previous = getattr(content, '_collapse_animation', None)
    if previous is not None:
        previous.stop(); previous.deleteLater()
    start_h = content.height()
    target_h = content.layout().sizeHint().height() if expand else 0

    anim = QPropertyAnimation(content, b"maximumHeight", content)
    content._collapse_animation = anim
    anim.setDuration(160)
    anim.setStartValue(start_h)
    anim.setEndValue(target_h)
    anim.setEasingCurve(QEasingCurve.Type.OutCubic)

    display = btn.text()
    if expand:
        btn.setText(display.replace("▸", "▾"))
    else:
        btn.setText(display.replace("▾", "▸"))

    def on_finished():
        content.setMaximumHeight(16777215 if expand else 0)

    anim.finished.connect(on_finished)
    anim.start()


def export_format_card(format_key: str, emoji: str, name: str, desc: str,
                       parent: QWidget | None = None) -> QFrame:
    """Clickable export format card — styled for Apple-like selection UI."""
    card_w = QFrame(parent)
    card_w.setProperty("format_key", format_key)
    card_w.setProperty("themeClass", "export_card")
    card_w.setFixedSize(140, 80)
    card_w.setCursor(Qt.PointingHandCursor)
    card_w.setStyleSheet(_LIGHT_STYLES['export_card'])

    layout = QVBoxLayout(card_w)
    layout.setContentsMargins(12, 10, 12, 10)
    layout.setSpacing(4)

    emoji_lbl = QLabel(f"{emoji}")
    emoji_lbl.setStyleSheet("font-size: 22px; border: none; background: transparent;")
    layout.addWidget(emoji_lbl)

    name_lbl = QLabel(name)
    name_lbl.setProperty('themeClass', 'format_title')
    name_lbl.setStyleSheet(_LIGHT_STYLES['format_title'])
    layout.addWidget(name_lbl)

    desc_lbl = QLabel(desc)
    desc_lbl.setProperty('themeClass', 'format_desc')
    desc_lbl.setStyleSheet(_LIGHT_STYLES['format_desc'])
    desc_lbl.setWordWrap(True)
    layout.addWidget(desc_lbl)

    layout.addStretch()
    return card_w
