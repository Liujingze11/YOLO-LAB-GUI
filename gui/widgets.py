"""
控件工厂函数 —— 统一创建带 Apple 风格样式的 Qt 控件。
"""
from __future__ import annotations

from PySide6.QtCore import QAbstractAnimation, QEasingCurve, QParallelAnimationGroup, QPropertyAnimation, Qt
from PySide6.QtWidgets import (
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
    QTextEdit,
    QToolButton,
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
    w.setStyleSheet(f"QWidget {{ background: #ffffff; border: 1px solid #e0e0e0; border-radius: {CARD_RADIUS}px; }}")
    shadow = QGraphicsDropShadowEffect()
    shadow.setBlurRadius(24)
    shadow.setColor(Qt.gray)
    shadow.setOffset(0, 1)
    w.setGraphicsEffect(shadow)
    lay = QVBoxLayout(w)
    lay.setContentsMargins(*CARD_PADDING)
    lay.setSpacing(0)
    return w, lay


CARD_HEADER_HEIGHT = 40


def resizable_card(title: str = "", parent: QWidget | None = None,
                   i18n_key: str | None = None) -> tuple[QWidget, QHBoxLayout, QVBoxLayout]:
    """可拖拽压缩的卡片：固定标题栏 + 内容滚动区。

    被 QSplitter 挤压时内容区自动出现滚动条，最小可压缩至标题高度。

    Returns (card_widget, header_layout, body_layout)
    """
    w = QWidget(parent)
    w.setMinimumHeight(CARD_HEADER_HEIGHT)
    w.setProperty("themeClass", "card")
    w.setStyleSheet(f"QWidget {{ background: #ffffff; border: 1px solid #e0e0e0; border-radius: {CARD_RADIUS}px; }}")
    shadow = QGraphicsDropShadowEffect()
    shadow.setBlurRadius(24)
    shadow.setColor(Qt.gray)
    shadow.setOffset(0, 1)
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
    if title:
        header_layout.addWidget(section_label(title, i18n_key=i18n_key))
    header_layout.addStretch()
    outer.addWidget(header)

    # ── 内容滚动区 ──
    scroll = QScrollArea()
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

    outer.addWidget(scroll, 1)

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


def collapsible_section(title: str, i18n_key: str = "",
                        parent: QWidget | None = None) -> tuple[QWidget, QToolButton, QWidget, QVBoxLayout]:
    """可折叠区域：点击标题按钮展开/收起内容区域。

    Returns (container, toggle_button, content_widget, content_layout)
    """
    container = QWidget(parent)
    container.setStyleSheet("background: transparent; border: none;")

    outer = QVBoxLayout(container)
    outer.setContentsMargins(0, 0, 0, 0)
    outer.setSpacing(0)

    # 切换按钮
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

    # 内容区域
    content = QWidget()
    content.setStyleSheet("background: transparent; border: none;")
    content.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
    content.setMaximumHeight(0)
    content_layout = QVBoxLayout(content)
    content_layout.setContentsMargins(0, 8, 0, 4)
    content_layout.setSpacing(6)
    outer.addWidget(content)

    # 动画
    btn.toggled.connect(lambda checked: _animate_collapse(content, checked, btn))

    return container, btn, content, content_layout


def _animate_collapse(content: QWidget, expand: bool, btn: QToolButton) -> None:
    """展开/收起动画：通过 QPropertyAnimation 过渡 maxHeight。"""
    content.setUpdatesEnabled(False)

    # 计算内容实际高度
    content.setMaximumHeight(2000)  # 临时解除限制测量真实高度
    target_h = content.sizeHint().height() if expand else 0

    anim = QPropertyAnimation(content, b"maximumHeight")
    anim.setDuration(250)
    anim.setStartValue(content.maximumHeight() if not expand else 0)
    anim.setEndValue(target_h)
    anim.setEasingCurve(QEasingCurve.Type.OutCubic)

    # 更新按钮文本箭头
    display = btn.text()
    if expand:
        btn.setText(display.replace("▸", "▾"))
    else:
        btn.setText(display.replace("▾", "▸"))

    def on_finished():
        content.setUpdatesEnabled(True)
        if not expand:
            content.setMaximumHeight(0)

    anim.finished.connect(on_finished)
    anim.start()
