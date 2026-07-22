"""Model export / format conversion tab."""
from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtWidgets import (
    QFileDialog, QFrame, QHBoxLayout, QLabel, QMessageBox, QSizePolicy,
    QSpacerItem, QStackedWidget, QVBoxLayout, QWidget, QCheckBox,
)
from PySide6.QtGui import QFont

from core.export import EXPORT_FORMATS, ExportConfig
from gui.paths import REPO_ROOT
from gui.styles import CHECKBOX_STYLE, COMBO_STYLE, SPINNER_STYLE
from gui.widgets import (
    btn, card, danger_btn, export_format_card, field_label, log_area,
    path_combo, path_combo_get, progress_bar, scroll_area,
    section_label, simple_combo, spinner,
)
from gui.workers import ExportWorker
from gui.i18n import tr

ROOT = Path(__file__).resolve().parent.parent.parent


class ExportTab(QWidget):
    """Data conversion tab for model export to various formats."""

    def __init__(self, parent=None, path_history: dict[str, list[str]] | None = None):
        super().__init__(parent)
        self._export_worker: ExportWorker | None = None
        self._selected_format: str = "onnx"
        self._path_history = path_history if path_history is not None else {}
        self._format_cards: dict[str, QFrame] = {}
        self._build_ui()

    def _build_ui(self):
        w = self
        outer = QVBoxLayout(w)
        outer.setContentsMargins(0, 0, 0, 0)

        inner = QWidget()
        inner.setMinimumSize(560, 580)
        il = QVBoxLayout(inner)
        il.setContentsMargins(24, 16, 24, 24)
        il.setSpacing(10)

        # ── 源模型卡片 ──
        card_src, lay_src = card()
        lay_src.addWidget(section_label("源模型", i18n_key="export.card.source"))
        lay_src.addSpacing(12)

        self._path_history.setdefault("export_model", [])
        self.export_model = path_combo(default="", history=self._path_history["export_model"])

        src_row = QHBoxLayout()
        src_row.setSpacing(10)
        lbl = field_label("模型文件", i18n_key="export.field.model")
        lbl.setFixedWidth(72)
        src_row.addWidget(lbl)
        src_row.addWidget(self.export_model, 1)
        b = btn("浏览", primary=False, i18n_key="train.btn.browse")
        b.setFixedWidth(60)
        b.clicked.connect(lambda: self._browse(self.export_model, False,
                                                "权重 (*.pt *.pth)", "export_model"))
        src_row.addWidget(b)
        lay_src.addLayout(src_row)

        self.export_model_info = QLabel("")
        self.export_model_info.setStyleSheet("font-size: 12px; color: #8e8e93; padding-left: 82px;")
        lay_src.addWidget(self.export_model_info)
        il.addWidget(card_src)

        # ── 导出格式卡片 ──
        card_fmt, lay_fmt = card()
        lay_fmt.addWidget(section_label("导出格式", i18n_key="export.card.format"))
        lay_fmt.addSpacing(12)

        fmt_grid = QHBoxLayout()
        fmt_grid.setSpacing(10)
        for fmt_key, meta in EXPORT_FORMATS.items():
            card_w = export_format_card(
                fmt_key, meta["emoji"], fmt_key.upper(),
                tr(meta["desc_key"]),
            )
            card_w.mousePressEvent = lambda e, k=fmt_key: self._select_format(k)
            self._format_cards[fmt_key] = card_w
            fmt_grid.addWidget(card_w)
        fmt_grid.addStretch()
        lay_fmt.addLayout(fmt_grid)
        il.addWidget(card_fmt)

        # ── 导出选项 ──
        card_opt, lay_opt = card()
        lay_opt.addWidget(section_label("导出选项", i18n_key="export.card.options"))
        lay_opt.addSpacing(12)

        self.option_stack = QStackedWidget()
        self._build_option_pages()
        lay_opt.addWidget(self.option_stack)
        il.addWidget(card_opt)

        # ── 输出目录 ──
        card_out, lay_out = card()
        lay_out.addWidget(section_label("输出目录", i18n_key="export.card.output"))
        lay_out.addSpacing(12)

        self._path_history.setdefault("export_output", [])
        self.export_output = path_combo(default=str(REPO_ROOT / "outputs" / "export"),
                                         history=self._path_history["export_output"])
        out_row = QHBoxLayout()
        out_row.setSpacing(10)
        out_row.addWidget(self.export_output, 1)
        b = btn("浏览", primary=False, i18n_key="train.btn.browse")
        b.setFixedWidth(60)
        b.clicked.connect(lambda: self._browse(self.export_output, True, None, "export_output"))
        out_row.addWidget(b)
        lay_out.addLayout(out_row)
        il.addWidget(card_out)

        # ── 操作 ──
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)
        self.btn_export = btn("导出模型", i18n_key="export.btn.start")
        self.btn_export.setFixedHeight(38)
        self.btn_export.clicked.connect(self._on_start_export)
        btn_row.addWidget(self.btn_export)

        self.btn_stop_export = danger_btn("取消", i18n_key="export.btn.stop")
        self.btn_stop_export.setFixedHeight(38)
        self.btn_stop_export.setEnabled(False)
        self.btn_stop_export.clicked.connect(self._on_stop_export)
        btn_row.addWidget(self.btn_stop_export)
        btn_row.addStretch()
        il.addLayout(btn_row)

        self.export_progress = progress_bar()
        self.export_progress.setVisible(False)
        il.addWidget(self.export_progress)

        self.export_log = log_area()
        il.addWidget(self.export_log, 1)

        outer.addWidget(scroll_area(inner))

        # 初始化选中第一个格式
        self._select_format("onnx")

    def _build_option_pages(self):
        """Build QStackedWidget pages for each format's options."""

        # ONNX page
        onnx_page = QWidget()
        onnx_lay = QVBoxLayout(onnx_page)
        onnx_lay.setContentsMargins(0, 0, 0, 0)
        onnx_lay.setSpacing(6)
        r1 = QHBoxLayout()
        r1.addWidget(field_label("imgsz", i18n_key="export.opt.imgsz"))
        self.onnx_imgsz = spinner(32, 4096, 640, 96)
        r1.addWidget(self.onnx_imgsz)
        r1.addSpacing(20)
        r1.addWidget(field_label("opset", i18n_key="export.opt.opset"))
        self.onnx_opset = spinner(9, 19, 12, 80)
        r1.addWidget(self.onnx_opset)
        r1.addStretch()
        onnx_lay.addLayout(r1)
        r2 = QHBoxLayout()
        self.onnx_dynamic = QCheckBox(tr("export.opt.dynamic"))
        self.onnx_dynamic.setChecked(True)
        self.onnx_dynamic.setStyleSheet(CHECKBOX_STYLE)
        r2.addWidget(self.onnx_dynamic)
        self.onnx_simplify = QCheckBox(tr("export.opt.simplify"))
        self.onnx_simplify.setChecked(True)
        self.onnx_simplify.setStyleSheet(CHECKBOX_STYLE)
        r2.addWidget(self.onnx_simplify)
        self.onnx_nms = QCheckBox(tr("export.opt.nms"))
        self.onnx_nms.setStyleSheet(CHECKBOX_STYLE)
        r2.addWidget(self.onnx_nms)
        r2.addStretch()
        onnx_lay.addLayout(r2)
        self.option_stack.addWidget(onnx_page)  # index 0

        # TensorRT page
        engine_page = QWidget()
        engine_lay = QVBoxLayout(engine_page)
        engine_lay.setContentsMargins(0, 0, 0, 0)
        engine_lay.setSpacing(6)
        r3 = QHBoxLayout()
        r3.addWidget(field_label("imgsz", i18n_key="export.opt.imgsz"))
        self.engine_imgsz = spinner(32, 4096, 640, 96)
        r3.addWidget(self.engine_imgsz)
        r3.addSpacing(20)
        r3.addWidget(field_label("Workspace (GB)", i18n_key="export.opt.workspace"))
        self.engine_workspace = spinner(1, 32, 4, 80)
        r3.addWidget(self.engine_workspace)
        r3.addStretch()
        engine_lay.addLayout(r3)
        r4 = QHBoxLayout()
        self.engine_fp16 = QCheckBox("FP16")
        self.engine_fp16.setStyleSheet(CHECKBOX_STYLE)
        r4.addWidget(self.engine_fp16)
        self.engine_int8 = QCheckBox("INT8")
        self.engine_int8.setStyleSheet(CHECKBOX_STYLE)
        r4.addWidget(self.engine_int8)
        r4.addStretch()
        engine_lay.addLayout(r4)
        self.option_stack.addWidget(engine_page)  # index 1

        # OpenVINO page
        ov_page = QWidget()
        ov_lay = QVBoxLayout(ov_page)
        ov_lay.setContentsMargins(0, 0, 0, 0)
        r5 = QHBoxLayout()
        r5.addWidget(field_label("imgsz", i18n_key="export.opt.imgsz"))
        self.ov_imgsz = spinner(32, 4096, 640, 96)
        r5.addWidget(self.ov_imgsz)
        r5.addStretch()
        ov_lay.addLayout(r5)
        r6 = QHBoxLayout()
        self.ov_int8 = QCheckBox("INT8")
        self.ov_int8.setStyleSheet(CHECKBOX_STYLE)
        r6.addWidget(self.ov_int8)
        r6.addStretch()
        ov_lay.addLayout(r6)
        self.option_stack.addWidget(ov_page)  # index 2

        # CoreML page
        cm_page = QWidget()
        cm_lay = QVBoxLayout(cm_page)
        cm_lay.setContentsMargins(0, 0, 0, 0)
        r7 = QHBoxLayout()
        r7.addWidget(field_label("imgsz", i18n_key="export.opt.imgsz"))
        self.cm_imgsz = spinner(32, 4096, 640, 96)
        r7.addWidget(self.cm_imgsz)
        r7.addStretch()
        cm_lay.addLayout(r7)
        r8 = QHBoxLayout()
        self.cm_nms = QCheckBox("NMS")
        self.cm_nms.setStyleSheet(CHECKBOX_STYLE)
        r8.addWidget(self.cm_nms)
        r8.addStretch()
        cm_lay.addLayout(r8)
        self.option_stack.addWidget(cm_page)  # index 3

        # TFLite page
        tl_page = QWidget()
        tl_lay = QVBoxLayout(tl_page)
        tl_lay.setContentsMargins(0, 0, 0, 0)
        r9 = QHBoxLayout()
        r9.addWidget(field_label("imgsz", i18n_key="export.opt.imgsz"))
        self.tl_imgsz = spinner(32, 4096, 640, 96)
        r9.addWidget(self.tl_imgsz)
        r9.addStretch()
        tl_lay.addLayout(r9)
        r10 = QHBoxLayout()
        self.tl_int8 = QCheckBox("INT8")
        self.tl_int8.setStyleSheet(CHECKBOX_STYLE)
        r10.addWidget(self.tl_int8)
        self.tl_fp16 = QCheckBox("FP16")
        self.tl_fp16.setStyleSheet(CHECKBOX_STYLE)
        r10.addWidget(self.tl_fp16)
        r10.addStretch()
        tl_lay.addLayout(r10)
        self.option_stack.addWidget(tl_page)  # index 4

    def _select_format(self, fmt_key: str):
        """Handle format card selection — update card styles and option page."""
        self._selected_format = fmt_key

        import re
        for key, card_w in self._format_cards.items():
            if key == fmt_key:
                card_w.setStyleSheet(
                    "QFrame { background: rgba(0,113,227,0.08); "
                    "border: 2px solid #0071e3; border-radius: 10px; }"
                )
            else:
                card_w.setStyleSheet(
                    "QFrame { background: #ffffff; border: 1px solid #d0d0d0; border-radius: 10px; }"
                    "QFrame:hover { border: 1px solid #0071e3; }"
                )

        page_map = {"onnx": 0, "engine": 1, "openvino": 2, "coreml": 3, "tflite": 4}
        self.option_stack.setCurrentIndex(page_map.get(fmt_key, 0))

    # ── Browse / Log helpers (same pattern as other tabs) ──

    def _browse(self, combo, directory, filter_str, hist_key):
        start = Path(path_combo_get(combo) or str(ROOT)).resolve()
        if not start.is_dir() and not start.is_file():
            start = ROOT
        if directory:
            d = QFileDialog.getExistingDirectory(self, "选择目录", str(start))
            if d:
                combo.setCurrentText(d)
                self._add_to_history(hist_key, d)
        else:
            f, _ = QFileDialog.getOpenFileName(self, "选择文件", str(start), filter_str or "所有文件 (*)")
            if f:
                combo.setCurrentText(f)
                self._add_to_history(hist_key, f)
                # 自动检测模型信息
                self._detect_model_info(f)

    def _add_to_history(self, key, value):
        if not value:
            return
        hist = self._path_history.setdefault(key, [])
        if value in hist:
            hist.remove(value)
        hist.insert(0, value)
        if len(hist) > 20:
            hist.pop()

    def _detect_model_info(self, model_path: str):
        """Auto-detect model task type and input size."""
        try:
            from ultralytics import YOLO
            model = YOLO(model_path)
            task = getattr(model, "task", "detect")
            self.export_model_info.setText(
                f"任务类型: {task}  |  文件: {Path(model_path).name}"
            )
        except Exception:
            self.export_model_info.setText("")

    # ── Log ──

    MAX_LOG_LINES = 3000

    def _log_append(self, html: str):
        self.export_log.append(html)
        doc = self.export_log.document()
        excess = doc.blockCount() - self.MAX_LOG_LINES
        if excess > 0:
            from PySide6.QtGui import QTextCursor
            cursor = self.export_log.textCursor()
            cursor.movePosition(QTextCursor.MoveOperation.Start)
            for _ in range(excess):
                cursor.select(QTextCursor.SelectionType.BlockUnderCursor)
                cursor.removeSelectedText()
                cursor.deleteChar()
            self.export_log.moveCursor(QTextCursor.MoveOperation.End)

    def _log_info(self, msg):
        self._log_append(f'<span style="color:#6ec6ff;">{tr("log.info_prefix")}</span>  {msg}')

    def _log_good(self, msg):
        self._log_append(f'<span style="color:#50fa7b;">{tr("log.ok_prefix")}</span>  {msg}')

    def _log_err(self, msg):
        self._log_append(f'<span style="color:#ff5555;">{tr("log.err_prefix")}</span>  {msg}')

    # ── Export execution ──

    def _build_export_config(self) -> ExportConfig:
        cfg = ExportConfig()
        cfg.model_path = path_combo_get(self.export_model)
        cfg.format = self._selected_format
        cfg.output_dir = path_combo_get(self.export_output)

        if self._selected_format == "onnx":
            cfg.imgsz = self.onnx_imgsz.value()
            cfg.opset = self.onnx_opset.value()
            cfg.dynamic = self.onnx_dynamic.isChecked()
            cfg.simplify = self.onnx_simplify.isChecked()
            cfg.nms = self.onnx_nms.isChecked()
        elif self._selected_format == "engine":
            cfg.imgsz = self.engine_imgsz.value()
            cfg.fp16 = self.engine_fp16.isChecked()
            cfg.int8 = self.engine_int8.isChecked()
            cfg.workspace = self.engine_workspace.value()
        elif self._selected_format == "openvino":
            cfg.imgsz = self.ov_imgsz.value()
            cfg.int8 = self.ov_int8.isChecked()
        elif self._selected_format == "coreml":
            cfg.imgsz = self.cm_imgsz.value()
            cfg.nms = self.cm_nms.isChecked()
        elif self._selected_format == "tflite":
            cfg.imgsz = self.tl_imgsz.value()
            cfg.int8 = self.tl_int8.isChecked()
            cfg.fp16 = self.tl_fp16.isChecked()

        return cfg

    @Slot()
    def _on_start_export(self):
        if self._export_worker and self._export_worker.isRunning():
            QMessageBox.warning(self, tr("msg.title.hint"), "已有导出任务在运行")
            return

        cfg = self._build_export_config()
        if not cfg.model_path or not Path(cfg.model_path).is_file():
            QMessageBox.critical(self, tr("msg.title.error"),
                                 f"模型文件不存在:\n{cfg.model_path}")
            return

        self.export_log.clear()
        self._log_info(f"开始导出: {cfg.model_path} → {cfg.format.upper()}")

        cmd = [
            sys.executable, str(ROOT / "gui" / "export_engine.py"),
            "--model", cfg.model_path,
            "--format", cfg.format,
            "--imgsz", str(cfg.imgsz),
            "--output-dir", cfg.output_dir,
        ]
        if cfg.format == "onnx":
            cmd.extend(["--opset", str(cfg.opset)])
            if cfg.dynamic: cmd.append("--dynamic")
            if cfg.simplify: cmd.append("--simplify")
            if cfg.nms: cmd.append("--nms")
        elif cfg.format == "engine":
            if cfg.fp16: cmd.append("--fp16")
            if cfg.int8: cmd.append("--int8")
            cmd.extend(["--workspace", str(cfg.workspace)])
        elif cfg.format == "openvino":
            if cfg.int8: cmd.append("--int8")
        elif cfg.format == "coreml":
            if cfg.nms: cmd.append("--nms")
        elif cfg.format == "tflite":
            if cfg.int8: cmd.append("--int8")
            if cfg.fp16: cmd.append("--fp16")

        self.btn_export.setEnabled(False)
        self.btn_stop_export.setEnabled(True)

        self._export_worker = ExportWorker(cmd)
        self._export_worker.log_line.connect(self._append_export_log)
        self._export_worker.failed.connect(self._on_export_failed)
        self._export_worker.finished_ok.connect(self._on_export_done)
        self._export_worker.stopped.connect(self._on_export_stopped)
        self._export_worker.start()

    @Slot(str)
    def _append_export_log(self, line: str):
        self._log_append(f'<span style="color:#c0c0c0;">{line}</span>')

    @Slot()
    def _on_stop_export(self):
        if self._export_worker and self._export_worker.isRunning():
            self._export_worker.stop()

    @Slot(str)
    def _on_export_failed(self, msg: str):
        self._log_err(f"导出失败")
        self._log_append(f'<span style="color:#ff6e6e;">{msg[:1500]}</span>')
        self.btn_export.setEnabled(True)
        self.btn_stop_export.setEnabled(False)

    @Slot()
    def _on_export_done(self):
        self._log_good("导出完成 ✓")
        self.btn_export.setEnabled(True)
        self.btn_stop_export.setEnabled(False)

    @Slot()
    def _on_export_stopped(self):
        self._log_append(f'<span style="color:#ffb86c;">{tr("log.warn_prefix")}</span>  导出已取消')
        self.btn_export.setEnabled(True)
        self.btn_stop_export.setEnabled(False)
