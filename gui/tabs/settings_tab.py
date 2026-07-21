"""Settings tab — panel configuration and preferences."""
from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QLabel,
    QVBoxLayout,
    QWidget,
)

from gui.widgets import (
    btn,
    card,
    scroll_area,
    section_label,
)
from gui.i18n import tr


class SettingsTab(QWidget):
    """Application settings and panel configuration tab."""

    reset_splitter_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self):
        w = self
        outer = QVBoxLayout(w)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        inner = QWidget()
        inner.setMinimumSize(400, 300)
        il = QVBoxLayout(inner)
        il.setContentsMargins(24, 16, 24, 24)
        il.setSpacing(10)

        card1, lay1 = card()
        lay1.addWidget(section_label("面板设置", i18n_key="settings.card.panels"))
        lay1.addSpacing(14)

        desc = QLabel(tr("settings.desc.reset_sizes"))
        desc.setStyleSheet("font-size: 13px; color: #6e6e73;")
        desc.setWordWrap(True)
        lay1.addWidget(desc)
        lay1.addSpacing(12)

        reset_btn = btn("↺ 恢复默认比例", primary=False, i18n_key="train.btn.reset_sizes")
        reset_btn.clicked.connect(self.reset_splitter_requested.emit)
        lay1.addWidget(reset_btn)
        lay1.addStretch()
        il.addWidget(card1)

        il.addStretch()

        outer.addWidget(scroll_area(inner))
