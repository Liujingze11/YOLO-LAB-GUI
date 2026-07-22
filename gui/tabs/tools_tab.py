"""Tools tab — dataset manipulation utilities (split, filter, etc.)."""
from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QTextCursor
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QMessageBox,
    QSpinBox,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from gui.paths import REPO_ROOT
from gui.styles import COMBO_STYLE, SPINNER_STYLE
from gui.widgets import (
    btn,
    card,
    danger_btn,
    field_label,
    log_area,
    path_combo,
    path_combo_get,
    scroll_area,
    section_label,
)
from gui.workers import ToolWorker
from gui.i18n import tr


class ToolsTab(QWidget):
    """Dataset tools tab — run dataset manipulation scripts."""

    TOOL_SCRIPTS = [
        "create_empty_labels.py",
        "split_train_val/split_random_with_labels.py",
        "split_train_val_test/split_random_with_labels.py",
        "split_train_val/split_every_5th_with_labels.py",
        "split_images_only/split_random_images_only.py",
        "split_images_only/split_every_5th_images_only.py",
    ]

    def __init__(self, parent=None, path_history: dict[str, list[str]] | None = None):
        super().__init__(parent)
        self._tool_worker: ToolWorker | None = None
        self._path_history = path_history if path_history is not None else {}
        self._closing = False
        self._build_ui()

    # ── UI construction ─────────────────────────────────────

    def _build_ui(self):
        w = self
        outer = QVBoxLayout(w)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        inner = QWidget()
        inner.setMinimumSize(560, 580)
        il = QVBoxLayout(inner)
        il.setContentsMargins(24, 16, 24, 24)
        il.setSpacing(10)

        # ── 数据集目录卡片 ──
        card1, lay1 = card()
        lay1.addWidget(section_label("数据集目录", i18n_key="tools.card.dataset"))
        lay1.addSpacing(14)

        self._path_history.setdefault("tool_dataset", [])
        self.tool_dataset = path_combo(default=str(REPO_ROOT / "data" / "dataset"),
                                       history=self._path_history["tool_dataset"])
        row = QHBoxLayout()
        row.setSpacing(10)
        row.addWidget(self.tool_dataset, 1)
        b = btn("浏览", primary=False, i18n_key="train.btn.browse")
        b.setFixedWidth(60)
        b.clicked.connect(lambda: self._browse(self.tool_dataset, True, None, "tool_dataset"))
        row.addWidget(b)
        lay1.addLayout(row)
        il.addWidget(card1)

        # ── 工具选择卡片 ──
        card2, lay2 = card()
        lay2.addWidget(section_label("工具", i18n_key="tools.card.tools"))
        lay2.addSpacing(14)

        self.tool_selector = QComboBox()
        self.tool_selector.setProperty("themeClass", "combo")
        self.tool_selector.setStyleSheet(COMBO_STYLE)
        tool_item_keys = [
            "tools.item.empty_labels",
            "tools.item.random_train_val",
            "tools.item.random_train_val_test",
            "tools.item.every_nth_labels",
            "tools.item.random_images_only",
            "tools.item.every_nth_images_only",
        ]
        for i, key in enumerate(tool_item_keys):
            self.tool_selector.addItem(tr(key))
            self.tool_selector.setItemData(i, key, Qt.ItemDataRole.UserRole + 1)
        self.tool_selector.currentIndexChanged.connect(self._on_tool_changed)
        lay2.addWidget(self.tool_selector)
        lay2.addSpacing(16)

        # ── 参数区域（QStackedWidget）──
        self.tool_params = QStackedWidget()
        self._tool_param_spinners: list[dict[str, QSpinBox]] = []
        param_specs = [
            [],                                          # 0: 创建空标签
            [("验证集比例 %", "val_ratio", 20, 1, 99, "tools.param.val_ratio")],   # 1: 随机 train/val
            [("验证集比例 %", "val_ratio", 20, 1, 99, "tools.param.val_ratio"),    # 2: 随机 train/val/test
             ("测试集比例 %", "test_ratio", 10, 1, 99, "tools.param.test_ratio")],
            [("间隔 N (每 N 张取 1 张)", "interval", 5, 1, 100, "tools.param.interval")],  # 3: 每N张含标签
            [("验证集比例 %", "val_ratio", 20, 1, 99, "tools.param.val_ratio")],   # 4: 随机仅图片
            [("间隔 N (每 N 张取 1 张)", "interval", 5, 1, 100, "tools.param.interval")],  # 5: 每N张仅图片
        ]
        for specs in param_specs:
            page = QWidget()
            pl = QVBoxLayout(page)
            pl.setContentsMargins(0, 0, 0, 0)
            pl.setSpacing(8)
            spinner_map = {}
            for label_text, name, default, min_v, max_v, *rest in specs:
                i18n_key = rest[0] if rest else None
                r = QHBoxLayout()
                r.setSpacing(10)
                r.addWidget(field_label(label_text, i18n_key=i18n_key))
                spin = QSpinBox()
                spin.setRange(min_v, max_v)
                spin.setValue(default)
                spin.setMinimumWidth(80)
                spin.setProperty("themeClass", "spinner")
                spin.setStyleSheet(SPINNER_STYLE)
                r.addWidget(spin)
                r.addStretch()
                pl.addLayout(r)
                spinner_map[name] = spin
            pl.addStretch()
            self.tool_params.addWidget(page)
            self._tool_param_spinners.append(spinner_map)

        lay2.addWidget(self.tool_params)
        il.addWidget(card2)

        # ── 操作按钮 ──
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)

        self.btn_tool_run = btn("执行工具", i18n_key="tools.btn.run")
        self.btn_tool_run.setFixedHeight(38)
        self.btn_tool_run.clicked.connect(self._on_run_tool)
        btn_row.addWidget(self.btn_tool_run)

        self.btn_tool_stop = danger_btn("停止", i18n_key="tools.btn.stop")
        self.btn_tool_stop.setFixedHeight(38)
        self.btn_tool_stop.setEnabled(False)
        self.btn_tool_stop.clicked.connect(self._on_stop_tool)
        btn_row.addWidget(self.btn_tool_stop)

        btn_row.addStretch()
        il.addLayout(btn_row)

        # ── 输出 ──
        il.addWidget(field_label("输出", i18n_key="tools.log.output"))
        self.tool_log = log_area()
        il.addWidget(self.tool_log, 1)

        outer.addWidget(scroll_area(inner))

    # ── Shared utility methods (copied from MainWindow) ─────

    MAX_LOG_LINES = 5000

    @staticmethod
    def _log_append(log_widget, html: str, max_lines: int = MAX_LOG_LINES) -> None:
        log_widget.append(html)
        doc = log_widget.document()
        excess = doc.blockCount() - max_lines
        if excess > 0:
            cursor = log_widget.textCursor()
            cursor.movePosition(QTextCursor.MoveOperation.Start)
            for _ in range(excess):
                cursor.select(QTextCursor.SelectionType.BlockUnderCursor)
                cursor.removeSelectedText()
                cursor.deleteChar()
            log_widget.moveCursor(QTextCursor.MoveOperation.End)

    def _add_to_history(self, key, value):
        if not value:
            return
        hist = self._path_history.setdefault(key, [])
        if value in hist:
            hist.remove(value)
        hist.insert(0, value)
        if len(hist) > 20:
            hist.pop()

    def _refresh_combo_history(self, combo, history):
        combo.blockSignals(True)
        combo.clear()
        combo.addItems(history)
        combo.blockSignals(False)

    def _browse(self, combo, directory, filter_str, hist_key):
        start = Path(path_combo_get(combo) or str(REPO_ROOT)).resolve()
        if not start.is_dir() and not start.is_file():
            start = REPO_ROOT
        if directory:
            d = QFileDialog.getExistingDirectory(self, "选择目录", str(start))
            if d:
                combo.setCurrentText(d)
                self._add_to_history(hist_key, d)
                self._refresh_combo_history(combo, self._path_history[hist_key])
        else:
            f, _ = QFileDialog.getOpenFileName(self, "选择文件", str(start), filter_str or "所有文件 (*)")
            if f:
                combo.setCurrentText(f)
                self._add_to_history(hist_key, f)
                self._refresh_combo_history(combo, self._path_history[hist_key])

    # ── Slot methods ────────────────────────────────────────

    def _on_tool_changed(self, idx):
        self.tool_params.setCurrentIndex(idx)

    def _on_run_tool(self):
        if self._tool_worker and self._tool_worker.isRunning():
            QMessageBox.warning(self, tr("msg.title.hint"), tr("msg.tool_running"))
            return

        idx = self.tool_selector.currentIndex()
        dataset_dir = path_combo_get(self.tool_dataset)
        if not dataset_dir:
            QMessageBox.warning(self, tr("msg.title.hint"), tr("msg.select_dataset"))
            return
        if not Path(dataset_dir).is_dir():
            QMessageBox.critical(self, tr("msg.title.error"), f"{tr('msg.dataset_not_found')}\n{dataset_dir}")
            return

        script_rel = self.TOOL_SCRIPTS[idx]
        script = str(REPO_ROOT / "tools" / "dataset_tools" / script_rel)

        if not Path(script).is_file():
            QMessageBox.critical(self, tr("msg.title.error"), f"{tr('msg.tool_not_found')}\n{script}")
            return

        cmd = [sys.executable, script, "--dataset-dir", dataset_dir]

        # 根据参数页提取参数
        spinners = self._tool_param_spinners[idx]
        if idx == 0:
            pass  # 创建空标签，无额外参数
        elif idx == 1:
            cmd.extend(["--val-ratio", str(spinners["val_ratio"].value() / 100)])
        elif idx == 2:
            cmd.extend(["--val-ratio", str(spinners["val_ratio"].value() / 100),
                        "--test-ratio", str(spinners["test_ratio"].value() / 100)])
        elif idx == 3:
            cmd.extend(["--interval", str(spinners["interval"].value())])
        elif idx == 4:
            cmd.extend(["--val-ratio", str(spinners["val_ratio"].value() / 100)])
        elif idx == 5:
            cmd.extend(["--interval", str(spinners["interval"].value())])

        self.tool_log.clear()
        self._log_append(self.tool_log,
                         f'<span style="color:#6ec6ff;">{tr("log.info_prefix")}</span>  {tr("tool.log.running", script=script_rel)}')

        self.btn_tool_run.setEnabled(False)
        self.btn_tool_stop.setEnabled(True)

        self._tool_worker = ToolWorker(cmd)
        self._tool_worker.log_line.connect(self._append_tool_log)
        self._tool_worker.failed.connect(self._on_tool_failed)
        self._tool_worker.finished_ok.connect(self._on_tool_done)
        self._tool_worker.stopped.connect(self._on_tool_stopped)
        self._tool_worker.start()

    def _append_tool_log(self, line):
        self._log_append(self.tool_log, f'<span style="color:#c0c0c0;">{line}</span>')

    def _on_stop_tool(self):
        if self._tool_worker and self._tool_worker.isRunning():
            self._log_append(self.tool_log,
                             f'<span style="color:#ffb86c;">{tr("log.warn_prefix")}</span>  {tr("train.log.tool_stopping")}')
            self._tool_worker.stop()

    def _on_tool_failed(self, msg):
        self._log_append(self.tool_log,
                         f'<span style="color:#ff5555;">{tr("log.err_prefix")}</span>  {tr("tool.log.failed")}')
        self._log_append(self.tool_log, f'<span style="color:#ff6e6e;">{msg[:1500]}</span>')
        self.btn_tool_run.setEnabled(True)
        self.btn_tool_stop.setEnabled(False)
        if not self._closing:
            QMessageBox.critical(self, tr("msg.title.tool_failed"), msg[:2000])

    def _on_tool_done(self):
        self._log_append(self.tool_log,
                         f'<span style="color:#50fa7b;">{tr("log.ok_prefix")}</span>  {tr("tool.log.done")}')
        self.btn_tool_run.setEnabled(True)
        self.btn_tool_stop.setEnabled(False)
        if not self._closing:
            QMessageBox.information(self, tr("msg.title.done"), tr("msg.tool_done"))

    def _on_tool_stopped(self):
        self._log_append(self.tool_log,
                         f'<span style="color:#ffb86c;">{tr("log.warn_prefix")}</span>  {tr("tool.log.cancelled")}')
        self.btn_tool_run.setEnabled(True)
        self.btn_tool_stop.setEnabled(False)
