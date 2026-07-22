"""Settings tab — panel configuration and preferences."""
from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from gui.widgets import (
    btn,
    card,
    field_label,
    path_combo,
    scroll_area,
    section_label,
)
from gui.i18n import tr
from gui.paths import REPO_ROOT


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

        # ── 默认路径 ──
        card2, lay2 = card()
        lay2.addWidget(section_label("默认路径", i18n_key="settings.card.defaults"))
        lay2.addSpacing(12)

        # 数据集默认目录
        ds_row = QHBoxLayout()
        ds_row.setSpacing(10)
        ds_row.addWidget(field_label("数据集", i18n_key="settings.field.dataset_dir"))
        self.default_dataset = path_combo(default=str(REPO_ROOT / "data" / "dataset"))
        ds_row.addWidget(self.default_dataset, 1)
        lay2.addLayout(ds_row)

        # 模型缓存目录
        model_row = QHBoxLayout()
        model_row.setSpacing(10)
        model_row.addWidget(field_label("模型缓存", i18n_key="settings.field.model_dir"))
        self.default_model_dir = path_combo(default=str(REPO_ROOT / "pretrained_models"))
        model_row.addWidget(self.default_model_dir, 1)
        lay2.addLayout(model_row)

        lay2.addSpacing(12)
        save_defaults_btn = btn("保存默认值", primary=False, i18n_key="settings.btn.save_defaults")
        save_defaults_btn.clicked.connect(self._save_defaults)
        lay2.addWidget(save_defaults_btn)

        il.addWidget(card2)

        il.addStretch()

        outer.addWidget(scroll_area(inner))

    # ── slots ──

    def _save_defaults(self):
        """Save current path defaults to settings store."""
        _ = self
