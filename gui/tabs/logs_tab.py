"""Logs viewer tab — browse training logs, CSV files, and experiment results."""
from __future__ import annotations

import csv
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QTextCursor
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QVBoxLayout,
    QWidget,
)

from gui.paths import REPO_ROOT, LOG_DIR, RESULTS_DIR, PREDICT_DIR
from gui.widgets import (
    btn,
    card,
    field_label,
    log_area,
    path_combo,
    path_combo_get,
    scroll_area,
    section_label,
    simple_combo,
    tiny_btn,
)
from gui.i18n import tr


class LogsTab(QWidget):
    """Training logs and experiment results viewer tab."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._path_history: dict[str, list[str]] = {}
        self._build_ui()

    # ── UI construction ─────────────────────────────────────

    def _build_ui(self):
        w = self
        outer = QVBoxLayout(w)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        inner = QWidget()
        inner.setMinimumSize(560, 520)
        il = QVBoxLayout(inner)
        il.setContentsMargins(24, 16, 24, 24)
        il.setSpacing(10)

        # ── 日志目录 ──
        card1, lay1 = card()
        lay1.addWidget(section_label("日志目录", i18n_key="logs.card.logdir"))
        lay1.addSpacing(14)
        self._path_history.setdefault("lv_logs", [])
        self.lv_log_dir = path_combo(default=LOG_DIR, history=self._path_history["lv_logs"])
        row1 = QHBoxLayout()
        row1.setSpacing(10)
        row1.addWidget(self.lv_log_dir, 1)
        b1 = btn("浏览", primary=False, i18n_key="train.btn.browse")
        b1.setFixedWidth(60)
        b1.clicked.connect(lambda: self._browse(self.lv_log_dir, True, None, "lv_logs"))
        row1.addWidget(b1)
        lay1.addLayout(row1)
        il.addWidget(card1)

        # ── 日志文件选择 ──
        card2, lay2 = card()
        lay2.addWidget(section_label("历史日志文件", i18n_key="logs.card.files"))
        lay2.addSpacing(14)
        row2 = QHBoxLayout()
        row2.setSpacing(10)
        self.lv_csv_combo = simple_combo(min_width=280, font_size=13)
        self.lv_csv_combo.addItem(tr("logs.combo.csv_placeholder"))
        self.lv_csv_combo.activated.connect(self._on_lv_csv_selected)
        row2.addWidget(self.lv_csv_combo, 1)
        refresh_btn = tiny_btn("⟳")
        refresh_btn.clicked.connect(self._refresh_lv_csv_list)
        row2.addWidget(refresh_btn)
        lay2.addLayout(row2)
        il.addWidget(card2)

        # ── 日志内容 ──
        self.lv_log = log_area()
        il.addWidget(self.lv_log, 1)

        # ── 实验结果 ──
        card3, lay3 = card()
        lay3.addWidget(section_label("实验 & 结果", i18n_key="logs.card.experiments"))
        lay3.addSpacing(14)

        exp_sel_row = QHBoxLayout()
        exp_sel_row.setSpacing(10)
        exp_sel_row.addWidget(field_label("实验", i18n_key="logs.field.experiment"))
        self.lv_exp_combo = simple_combo(min_width=200, font_size=13)
        self.lv_exp_combo.addItem(tr("logs.combo.exp_placeholder"))
        self.lv_exp_combo.activated.connect(self._on_lv_exp_selected)
        exp_sel_row.addWidget(self.lv_exp_combo, 1)
        exp_refresh = tiny_btn("⟳")
        exp_refresh.clicked.connect(self._refresh_lv_exp_list)
        exp_sel_row.addWidget(exp_refresh)
        lay3.addLayout(exp_sel_row)
        lay3.addSpacing(10)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)
        self.lv_btn_exp_dir = btn("打开实验目录", primary=False, i18n_key="logs.btn.exp_dir")
        self.lv_btn_exp_dir.clicked.connect(self._open_lv_exp_dir)
        btn_row.addWidget(self.lv_btn_exp_dir)
        self.lv_btn_weights = btn("打开权重目录", primary=False, i18n_key="logs.btn.weights")
        self.lv_btn_weights.clicked.connect(self._open_lv_weights)
        btn_row.addWidget(self.lv_btn_weights)
        self.lv_btn_plot = btn("查看训练图表", primary=False, i18n_key="logs.btn.plot")
        self.lv_btn_plot.clicked.connect(self._open_lv_plot)
        btn_row.addWidget(self.lv_btn_plot)
        btn_row.addStretch()
        lay3.addLayout(btn_row)
        il.addWidget(card3)

        # ── 快捷目录 ──
        card4, lay4 = card()
        lay4.addWidget(section_label("快捷目录", i18n_key="logs.card.quick"))
        lay4.addSpacing(14)
        quick_row = QHBoxLayout()
        quick_row.setSpacing(10)
        btn_specs = [
            ("训练结果", RESULTS_DIR, "logs.btn.results"),
            ("推理结果", str(Path(PREDICT_DIR) / "predict_result"), "logs.btn.predictions"),
            ("数据集", str(REPO_ROOT / "data" / "dataset"), "logs.btn.dataset"),
        ]
        for label, path, i18n_key in btn_specs:
            b = btn(label, primary=False, i18n_key=i18n_key)
            b.clicked.connect(lambda checked, p=path: LogsTab._open_dir_safe(p))
            quick_row.addWidget(b)
        quick_row.addStretch()
        lay4.addLayout(quick_row)
        il.addWidget(card4)

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

    @staticmethod
    def _open_file_with_default_app(path: str) -> None:
        """Cross-platform: open file with default application."""
        import os
        import platform
        import subprocess
        system = platform.system()
        if system == "Windows":
            os.startfile(path)
        elif system == "Darwin":
            subprocess.Popen(["open", path])
        else:
            subprocess.Popen(["xdg-open", path])

    @staticmethod
    def _open_dir_safe(path_str: str) -> None:
        p = Path(path_str)
        if p.is_dir():
            LogsTab._open_file_with_default_app(str(p))
        elif p.parent.is_dir():
            LogsTab._open_file_with_default_app(str(p.parent))

    @staticmethod
    def _load_csv_log(log_widget, csv_path: Path):
        log_widget.clear()
        with open(csv_path, encoding="utf-8-sig") as f:
            reader = csv.reader(f)
            rows = list(reader)
        if not rows:
            LogsTab._log_append(log_widget,
                f'<span style="color:#6ec6ff;">{tr("log.info_prefix")}</span>  {tr("msg.log_empty")}')
            return
        LogsTab._log_append(log_widget,
            f'<span style="color:#6ec6ff;">{tr("log.info_prefix")}</span>  {tr("msg.log_loaded")}: {csv_path.name}  ({len(rows)} {tr("msg.log_rows")})')
        html = '<table style="font-size:11px; border-collapse:collapse; width:100%;">'
        for i, row in enumerate(rows):
            tag = "th" if i == 0 else "td"
            color = "#8ab4f8" if i == 0 else "#c0c0c0"
            html += f'<tr style="color:{color};">'
            for cell in row:
                html += f"<{tag} style='padding:2px 8px; border-bottom:1px solid #333;'>{cell}</{tag}>"
            html += "</tr>"
        html += "</table>"
        LogsTab._log_append(log_widget, html)

    # ── Slot methods ────────────────────────────────────────

    def _refresh_lv_csv_list(self):
        combo = self.lv_csv_combo
        combo.blockSignals(True)
        combo.clear()
        combo.addItem(tr("logs.combo.csv_placeholder"))
        log_dir = path_combo_get(self.lv_log_dir)
        if Path(log_dir).is_dir():
            for f in sorted(Path(log_dir).glob("*.csv"), reverse=True):
                combo.addItem(f.name)
        combo.blockSignals(False)

    def _on_lv_csv_selected(self, idx: int):
        if idx <= 0:
            return
        text = self.lv_csv_combo.currentText()
        log_dir = path_combo_get(self.lv_log_dir)
        csv_path = Path(log_dir) / text
        if not csv_path.is_file():
            QMessageBox.warning(self, tr("msg.title.hint"), f"{tr('msg.yaml_not_found')}\n{csv_path}")
            return
        try:
            self._load_csv_log(self.lv_log, csv_path)
        except Exception as e:
            self._log_append(self.lv_log,
                f'<span style="color:#ff5555;">{tr("log.err_prefix")}</span>  {tr("msg.csv_read_failed")} {e}')

    def _refresh_lv_exp_list(self):
        combo = self.lv_exp_combo
        combo.blockSignals(True)
        combo.clear()
        combo.addItem(tr("logs.combo.exp_placeholder"))
        if Path(RESULTS_DIR).is_dir():
            for d in sorted(Path(RESULTS_DIR).iterdir(), reverse=True):
                if d.is_dir():
                    combo.addItem(d.name)
        combo.blockSignals(False)

    def _on_lv_exp_selected(self, idx: int):
        pass  # selecting experiment does nothing by itself; buttons below use it

    def _lv_exp_path(self):
        name = self.lv_exp_combo.currentText()
        placeholder = tr("logs.combo.exp_placeholder")
        if not name or name == placeholder:
            QMessageBox.warning(self, tr("msg.title.hint"), tr("msg.select_experiment"))
            return None
        return Path(RESULTS_DIR) / name

    def _open_lv_exp_dir(self):
        p = self._lv_exp_path()
        if p and p.is_dir():
            LogsTab._open_file_with_default_app(str(p))

    def _open_lv_weights(self):
        p = self._lv_exp_path()
        if p:
            wp = p / "weights"
            if wp.is_dir():
                LogsTab._open_file_with_default_app(str(wp))
            else:
                QMessageBox.warning(self, tr("msg.title.hint"), f"{tr('msg.weights_dir_not_found')}\n{wp}")

    def _open_lv_plot(self):
        p = self._lv_exp_path()
        if p:
            rp = p / "results.png"
            if rp.is_file():
                LogsTab._open_file_with_default_app(str(rp))
            else:
                QMessageBox.warning(self, tr("msg.title.hint"), tr("msg.plot_not_found"))
                if p.is_dir():
                    LogsTab._open_file_with_default_app(str(p))
