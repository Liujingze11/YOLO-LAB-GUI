"""Inference tab — model prediction on images/video."""
from __future__ import annotations

import sys
import time
from pathlib import Path

from PySide6.QtCore import Qt, Slot
from PySide6.QtGui import QTextCursor
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QVBoxLayout,
    QWidget,
)

from gui.paths import REPO_ROOT, BEST_SEG_MODEL, PREDICT_DIR, TEST_IMAGES_DIR, PRETRAINED_DIR
from gui.styles import SPINNER_STYLE
from gui.widgets import (
    btn,
    card,
    danger_btn,
    field_label,
    input_,
    log_area,
    path_combo,
    path_combo_get,
    progress_bar,
    scroll_area,
    section_label,
    spinner,
)
from gui.workers import InferWorker
from gui.i18n import tr, current_lang


class InferTab(QWidget):
    """Inference configuration and execution tab."""

    def __init__(self, parent=None, path_history: dict[str, list[str]] | None = None):
        super().__init__(parent)
        self._infer_worker: InferWorker | None = None
        self._infer_defaults_done = False
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

        card1, lay1 = card()
        lay1.addWidget(section_label("推理配置", i18n_key="infer.card.config"))
        lay1.addSpacing(14)

        for key in ["ir_model", "ir_source", "ir_save"]:
            self._path_history.setdefault(key, [])

        self.ir_model = path_combo(default="", history=self._path_history["ir_model"])
        self.ir_source = path_combo(default="", history=self._path_history["ir_source"])
        self.ir_save = path_combo(default="", history=self._path_history["ir_save"])
        self.ir_conf = input_(default="0.406", min_width=96)
        self.ir_imgsz = spinner(32, 4096, 640, 96)

        ir_rows = [
            ("模型 .pt", self.ir_model, "ir_model", False, "权重 (*.pt *.pth *.onnx)", "infer.field.model"),
            ("输入源", self.ir_source, "ir_source", True, None, "infer.field.source"),
            ("保存目录", self.ir_save, "ir_save", True, None, "infer.field.save"),
        ]
        for label, cb, hist_key, is_dir, flt, i18n_key in ir_rows:
            row = QHBoxLayout()
            row.setSpacing(10)
            lbl = field_label(label, i18n_key=i18n_key)
            lbl.setFixedWidth(72)
            row.addWidget(lbl)
            row.addWidget(cb, 1)
            b = btn("浏览", primary=False, i18n_key="train.btn.browse")
            b.setFixedWidth(60)
            b.clicked.connect(lambda checked, c=cb, d=is_dir, f=flt, k=hist_key: self._browse(c, d, f, k))
            row.addWidget(b)
            lay1.addLayout(row)
            lay1.addSpacing(8)

        conf_row = QHBoxLayout()
        conf_row.setSpacing(10)
        conf_row.addWidget(field_label("Conf", i18n_key="infer.field.conf"))
        conf_row.addWidget(self.ir_conf)
        conf_row.addSpacing(24)
        conf_row.addWidget(field_label("Imgsz", i18n_key="infer.field.imgsz"))
        conf_row.addWidget(self.ir_imgsz)
        conf_row.addStretch()
        lay1.addLayout(conf_row)
        il.addWidget(card1)

        ir_btn_row = QHBoxLayout()
        ir_btn_row.setSpacing(10)

        self.btn_infer = btn("开始推理", i18n_key="infer.btn.start")
        self.btn_infer.setFixedHeight(38)
        self.btn_infer.clicked.connect(self._on_start_infer)
        ir_btn_row.addWidget(self.btn_infer)

        self.btn_stop_ir = danger_btn("停止推理", i18n_key="infer.btn.stop")
        self.btn_stop_ir.setFixedHeight(38)
        self.btn_stop_ir.setVisible(False)
        self.btn_stop_ir.clicked.connect(self._on_stop_infer)
        ir_btn_row.addWidget(self.btn_stop_ir)

        ir_btn_row.addStretch()
        il.addLayout(ir_btn_row)

        il.addSpacing(4)
        self.ir_progress = progress_bar(i18n_key="infer.progress.format")
        self.ir_progress.setFormat(tr("infer.progress.format"))
        self.ir_progress.setVisible(False)
        il.addWidget(self.ir_progress)
        self.ir_eta_label = QLabel("")
        self.ir_eta_label.setStyleSheet("font-size:11px; color:#8e8e93;")
        self.ir_eta_label.setVisible(False)
        il.addWidget(self.ir_eta_label)

        il.addWidget(field_label("输出", i18n_key="infer.log.output"))
        self.ir_log = log_area()
        il.addWidget(self.ir_log, 1)

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
    def _model_file_ok(path: str) -> bool:
        if Path(path).is_file():
            return True
        if path and "/" not in path and "\\" not in path:
            return (PRETRAINED_DIR / path).is_file()
        return False

    # ── Slot methods ────────────────────────────────────────

    def _log_info_ir(self, msg):
        self._log_append(self.ir_log, f'<span style="color:#6ec6ff;">{tr("log.info_prefix")}</span>  {msg}')

    def _set_infer_ui_state(self, state: str) -> None:
        if state == "running":
            self.btn_infer.setVisible(False)
            self.btn_stop_ir.setVisible(True)
            self.ir_progress.setVisible(True)
            self.ir_progress.setValue(0)
            self.ir_eta_label.setVisible(True)
            self.ir_eta_label.setText("")
            self._infer_start_time = time.time()
        else:  # idle
            self.btn_infer.setVisible(True)
            self.btn_stop_ir.setVisible(False)
            self.ir_progress.setVisible(False)
            self.ir_eta_label.setVisible(False)

    def showEvent(self, e):
        super().showEvent(e)
        if self._infer_defaults_done:
            return
        self._infer_defaults_done = True
        self.ir_model.setCurrentText(BEST_SEG_MODEL)
        self.ir_source.setCurrentText(TEST_IMAGES_DIR)
        self.ir_save.setCurrentText(str(Path(PREDICT_DIR) / "predict_result"))

    @Slot()
    def _on_start_infer(self):
        if self._infer_worker and self._infer_worker.isRunning():
            QMessageBox.warning(self, tr("msg.title.hint"), tr("msg.infer_running"))
            return

        model_path = path_combo_get(self.ir_model)
        source = path_combo_get(self.ir_source)
        save_dir = path_combo_get(self.ir_save)
        conf = self.ir_conf.text().strip()
        try:
            conf_val = float(conf) if conf else 0.25
        except ValueError:
            QMessageBox.critical(self, tr("msg.title.error"), f"{tr('msg.invalid_conf')} {conf}")
            return
        imgsz_val = int(self.ir_imgsz.value())

        if not self._model_file_ok(model_path):
            QMessageBox.critical(self, tr("msg.title.error"), f"{tr('msg.infer_model_not_found')}\n{model_path}")
            return
        if not Path(source).exists():
            QMessageBox.critical(self, tr("msg.title.error"), f"{tr('msg.infer_source_not_found')}\n{source}")
            return

        self.ir_log.clear()
        self._log_info_ir(tr("infer.log.starting", model=model_path))

        cmd = [
            sys.executable, str(REPO_ROOT / "gui" / "infer_engine.py"),
            "--lang", current_lang(),
            "--model", model_path,
            "--source", source,
            "--save-dir", save_dir,
            "--conf", str(conf_val),
            "--imgsz", str(imgsz_val),
        ]

        self.btn_infer.setVisible(False)
        self.btn_stop_ir.setVisible(True)
        self._set_infer_ui_state("running")
        self._infer_worker = InferWorker(cmd)
        self._infer_worker.log_line.connect(self._append_infer_log)
        self._infer_worker.progress.connect(self._on_infer_progress)
        self._infer_worker.failed.connect(self._on_infer_failed)
        self._infer_worker.finished_ok.connect(self._on_infer_done)
        self._infer_worker.stopped.connect(self._on_infer_stopped)
        self._infer_worker.finished.connect(self._on_infer_thread_finished)
        self._infer_worker.start()

    @Slot(str)
    def _append_infer_log(self, line: str) -> None:
        self._log_append(self.ir_log, f'<span style="color:#c0c0c0;">{line}</span>')

    @Slot(int, int)
    def _on_infer_progress(self, cur: int, total: int) -> None:
        self.ir_progress.setRange(0, total)
        self.ir_progress.setValue(cur)
        self.ir_progress.setFormat(tr("infer.progress.format"))
        elapsed = time.time() - getattr(self, "_infer_start_time", time.time())
        if cur > 0 and total > 0:
            eta = (elapsed / cur) * (total - cur)
            self.ir_eta_label.setText(
                tr("infer.eta", elapsed=elapsed, eta=eta, total=total)
            )

    @Slot()
    def _on_stop_infer(self):
        if self._infer_worker and self._infer_worker.isRunning():
            self._log_append(self.ir_log, f'<span style="color:#ffb86c;">{tr("log.warn_prefix")}</span>  {tr("infer.log.stopping")}')
            self._infer_worker.stop()

    @Slot(str)
    def _on_infer_failed(self, msg):
        self._log_append(self.ir_log, f'<span style="color:#ff5555;">{tr("log.err_prefix")}</span>  {tr("msg.title.infer_failed")}')
        self._log_append(self.ir_log, f'<span style="color:#ff6e6e;">{msg[:1500]}</span>')
        self._set_infer_ui_state("idle")
        if not self._closing:
            QMessageBox.critical(self, tr("msg.title.infer_failed"), msg[:2000])

    @Slot()
    def _on_infer_done(self):
        self._log_append(self.ir_log, f'<span style="color:#50fa7b;">{tr("log.ok_prefix")}</span>  {tr("msg.infer_done")}')
        self._set_infer_ui_state("idle")
        if not self._closing:
            QMessageBox.information(self, tr("msg.title.done"), tr("msg.infer_done"))

    @Slot()
    def _on_infer_stopped(self):
        self._log_append(self.ir_log, f'<span style="color:#ffb86c;">{tr("log.warn_prefix")}</span>  {tr("infer.log.stopped")}')
        self._set_infer_ui_state("idle")

    @Slot()
    def _on_infer_thread_finished(self):
        if self._closing:
            from PySide6.QtWidgets import QApplication
            QApplication.quit()
