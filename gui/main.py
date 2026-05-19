"""
YOLO 分割训练 / 推理桌面界面 — Apple 风格简约设计
启动：在项目根目录执行  python gui/main.py
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

PRESET_FILE = ROOT / "gui" / "presets.json"

from PySide6.QtCore import Qt, Slot
from PySide6.QtGui import QFont, QTextCursor
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QRadioButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from gui.config import TrainConfig
from gui.device import get_available_devices, get_default_device
from gui.train_engine import list_experiments

from gui.styles import (
    CHECKBOX_STYLE,
    COLOR_ACCENT,
    COLOR_BG,
    COLOR_CARD_BG,
    COLOR_LOG_BG,
    COLOR_TEXT,
    COLOR_TEXT_MUTED,
    COMBO_STYLE,
    FONT_FAMILIES,
    FONT_SIZE,
    RADIO_STYLE,
    SCROLL_AREA_STYLE,
    TAB_WIDGET_STYLE,
)
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
    simple_combo,
    spinner,
    tiny_btn,
)
from gui.workers import InferWorker, TrainWorker


# ── 预设管理 ──────────────────────────────────────────────

def load_presets() -> dict:
    if PRESET_FILE.is_file():
        try:
            return json.loads(PRESET_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def save_presets(presets: dict) -> None:
    PRESET_FILE.parent.mkdir(parents=True, exist_ok=True)
    PRESET_FILE.write_text(
        json.dumps(presets, ensure_ascii=False, indent=2), encoding="utf-8"
    )


# ── 主窗口 ──────────────────────────────────────────────────

class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("YOLO Lab")
        self._closing = False
        self.resize(820, 700)
        self.setMinimumSize(720, 520)

        self._train_worker: TrainWorker | None = None
        self._infer_worker: InferWorker | None = None
        self._infer_defaults_done = False
        self._presets = load_presets()
        self._path_history: dict[str, list[str]] = {}

        tabs = QTabWidget()
        tabs.setStyleSheet(TAB_WIDGET_STYLE)
        tabs.addTab(self._build_train_tab(), "训练")
        tabs.addTab(self._build_infer_tab(), "推理")

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.addWidget(tabs)

        self._load_train_defaults()

    # ═══════════════════════════════════════════════════════
    #  训练页
    # ═══════════════════════════════════════════════════════

    def _build_train_tab(self):
        w = QWidget()
        w.setMinimumSize(640, 920)
        outer = QVBoxLayout(w)
        outer.setContentsMargins(24, 16, 24, 24)
        outer.setSpacing(10)

        # ── 路径卡片 ──
        card1, lay1 = card()
        header1 = QHBoxLayout()
        header1.addWidget(section_label("路径"))
        header1.addStretch()
        edit_yaml_btn = tiny_btn("编辑 data.yaml")
        edit_yaml_btn.clicked.connect(self._open_data_yaml)
        header1.addWidget(edit_yaml_btn)
        lay1.addLayout(header1)
        lay1.addSpacing(14)

        for key in ["data_yaml", "model", "results", "logs"]:
            self._path_history.setdefault(key, [])

        self.tr_data_yaml = path_combo(default="", history=self._path_history["data_yaml"])
        self.tr_model     = path_combo(default="", history=self._path_history["model"])
        self.tr_results   = path_combo(default="", history=self._path_history["results"])
        self.tr_logs      = path_combo(default="", history=self._path_history["logs"])

        rows_data = [
            ("data.yaml", self.tr_data_yaml, "data_yaml", False, "YAML (*.yaml *.yml)"),
            ("初始权重", self.tr_model,     "model",      False, "权重 (*.pt *.pth *.onnx)"),
            ("结果目录", self.tr_results,   "results",    True,  None),
            ("日志目录", self.tr_logs,      "logs",       True,  None),
        ]
        for label, cb, hist_key, is_dir, flt in rows_data:
            row = QHBoxLayout()
            row.setSpacing(10)
            lbl = field_label(label)
            lbl.setFixedWidth(72)
            row.addWidget(lbl)
            row.addWidget(cb, 1)
            b = btn("浏览", primary=False)
            b.setFixedWidth(60)
            b.clicked.connect(lambda checked, c=cb, d=is_dir, f=flt, k=hist_key: self._browse(c, d, f, k))
            row.addWidget(b)
            lay1.addLayout(row)
            lay1.addSpacing(8)

        outer.addWidget(card1)

        # ── 超参数卡片 ──
        card2, lay2 = card()
        lay2.addWidget(section_label("超参数"))
        lay2.addSpacing(14)

        self.tr_epochs = spinner(1, 100000, 150, 100)
        self.tr_imgsz  = spinner(32, 4096, 640, 100)
        self.tr_batch  = spinner(1, 1024, 16, 100)
        self.tr_device = QComboBox()
        self.tr_device.setEditable(True)
        self.tr_device.setMinimumWidth(100)
        self.tr_device.setStyleSheet(COMBO_STYLE)

        grid = QHBoxLayout()
        grid.setSpacing(28)
        for lbl, wgt in [
            ("Epochs", self.tr_epochs), ("Imgsz", self.tr_imgsz),
            ("Batch", self.tr_batch), ("Device", self.tr_device),
        ]:
            col = QVBoxLayout()
            col.setSpacing(4)
            col.addWidget(field_label(lbl))
            col.addWidget(wgt)
            grid.addLayout(col)
        grid.addStretch()
        lay2.addLayout(grid)
        lay2.addSpacing(12)

        exp_row = QHBoxLayout()
        exp_row.setSpacing(10)
        exp_row.addWidget(field_label("实验名称"))
        self.tr_exp = input_(min_width=320)
        exp_row.addWidget(self.tr_exp, 1)
        lay2.addLayout(exp_row)
        outer.addWidget(card2)

        # ── 训练模式卡片 ──
        card3, lay3 = card()
        lay3.addWidget(section_label("训练模式"))
        lay3.addSpacing(12)

        self.rb_new = QRadioButton("新训练 — 从初始权重开始")
        self.rb_resume = QRadioButton("续训 — 从上一次 last.pt 继续")
        self.rb_best = QRadioButton("微调 — 基于历史实验的 best.pt")
        self.rb_new.setChecked(True)
        for rb in [self.rb_new, self.rb_resume, self.rb_best]:
            rb.setStyleSheet(RADIO_STYLE)
            lay3.addWidget(rb)

        hist_row = QHBoxLayout()
        hist_row.setSpacing(10)
        hist_row.addWidget(field_label("历史实验"))
        self.cb_history = simple_combo(min_width=300, font_size=13)
        hist_row.addWidget(self.cb_history, 1)
        refresh = btn("刷新", primary=False)
        refresh.clicked.connect(self._refresh_history)
        hist_row.addWidget(refresh)
        lay3.addSpacing(8)
        lay3.addLayout(hist_row)
        outer.addWidget(card3)

        # ── 数据增强 ──
        self.tr_augment = QCheckBox("启用数据增强")
        self.tr_augment.setChecked(True)
        self.tr_augment.setStyleSheet(CHECKBOX_STYLE)
        outer.addWidget(self.tr_augment)

        # ── 操作按钮行 ──
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)

        self.btn_start = btn("开始训练")
        self.btn_start.setFixedHeight(38)
        self.btn_start.clicked.connect(self._on_start_train)
        btn_row.addWidget(self.btn_start)

        self.btn_stop = danger_btn("停止训练")
        self.btn_stop.setFixedHeight(38)
        self.btn_stop.setEnabled(False)
        self.btn_stop.clicked.connect(self._on_stop_train)
        btn_row.addWidget(self.btn_stop)

        self.btn_reset = btn("恢复默认", primary=False)
        self.btn_reset.setFixedHeight(38)
        self.btn_reset.clicked.connect(self._reset_train_defaults)
        btn_row.addWidget(self.btn_reset)

        self.cb_presets = simple_combo(min_width=120)
        self._refresh_preset_combo()
        self.cb_presets.currentTextChanged.connect(self._on_preset_selected)
        btn_row.addWidget(self.cb_presets)

        save_btn = btn("保存预设", primary=False)
        save_btn.setFixedHeight(38)
        save_btn.clicked.connect(self._save_preset)
        btn_row.addWidget(save_btn)

        del_btn = btn("删除预设", primary=False)
        del_btn.setFixedHeight(38)
        del_btn.clicked.connect(self._delete_preset)
        btn_row.addWidget(del_btn)

        btn_row.addStretch()
        outer.addLayout(btn_row)

        # ── 进度条 ──
        outer.addSpacing(4)
        self.tr_progress = progress_bar()
        outer.addWidget(self.tr_progress)

        # ── 日志 ──
        outer.addWidget(field_label("输出"))
        self.tr_log = log_area()
        outer.addWidget(self.tr_log, 1)

        return scroll_area(w)

    def _add_to_history(self, key, value):
        if not value:
            return
        hist = self._path_history.setdefault(key, [])
        if value in hist:
            hist.remove(value)
        hist.insert(0, value)
        if len(hist) > 20:
            hist.pop()

    def _browse(self, combo, directory, filter_str, hist_key):
        start = Path(path_combo_get(combo) or str(ROOT)).resolve()
        if not start.is_dir() and not start.is_file():
            start = ROOT
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

    def _refresh_combo_history(self, combo, history):
        combo.blockSignals(True)
        combo.clear()
        combo.addItems(history)
        combo.blockSignals(False)

    @staticmethod
    def _model_file_ok(path: str) -> bool:
        """本地文件存在，或是一个 YOLO 模型短名称（ultralytics 自动下载）。"""
        if Path(path).is_file():
            return True
        # 短名称如 yolov8n-seg.pt — 不含路径分隔符，ultralytics 会自动下载
        return bool(path) and os.sep not in path and "/" not in path

    def _open_data_yaml(self):
        p = Path(path_combo_get(self.tr_data_yaml))
        if not p.is_file():
            QMessageBox.warning(self, "提示", f"文件不存在：\n{p}")
            return
        try:
            self._open_file_with_default_app(str(p))
        except Exception:
            QMessageBox.critical(self, "错误", "无法打开文件，请手动打开。")

    @staticmethod
    def _open_file_with_default_app(path: str) -> None:
        """跨平台用默认程序打开文件。"""
        import platform
        system = platform.system()
        if system == "Windows":
            os.startfile(path)
        elif system == "Darwin":
            subprocess.Popen(["open", path])
        else:
            subprocess.Popen(["xdg-open", path])

    def _load_train_defaults(self):
        self._refresh_devices()
        self._apply_config(TrainConfig())

    def _refresh_devices(self):
        """刷新 Device 下拉框的可用设备列表。"""
        current = self.tr_device.currentText().strip()
        self.tr_device.clear()
        self.tr_device.addItems(get_available_devices())
        if current:
            idx = self.tr_device.findText(current)
            if idx >= 0:
                self.tr_device.setCurrentIndex(idx)
            else:
                self.tr_device.setCurrentText(current)

    def _apply_config(self, c):
        self.tr_data_yaml.setCurrentText(c.data_yaml)
        self.tr_model.setCurrentText(c.model_file)
        self.tr_results.setCurrentText(c.results_dir)
        self.tr_logs.setCurrentText(c.log_dir)
        self.tr_epochs.setValue(int(c.epochs))
        self.tr_imgsz.setValue(int(c.imgsz))
        self.tr_batch.setValue(int(c.batch))
        self.tr_device.setCurrentText(str(c.device))
        self.tr_exp.setText(c.experiment_name)
        self.tr_augment.setChecked(bool(c.use_augment))
        self._refresh_history()

    def _reset_train_defaults(self):
        self._apply_config(TrainConfig())
        self._log_info("已恢复默认配置")

    def _refresh_history(self):
        self.cb_history.clear()
        res = Path(path_combo_get(self.tr_results) or ".")
        if not res.is_dir():
            return
        for name in sorted(list_experiments(str(res))):
            self.cb_history.addItem(name)

    # ── 预设 ──

    def _get_current_config_dict(self):
        return {
            "data_yaml": path_combo_get(self.tr_data_yaml),
            "model_file": path_combo_get(self.tr_model),
            "results_dir": path_combo_get(self.tr_results),
            "log_dir": path_combo_get(self.tr_logs),
            "epochs": self.tr_epochs.value(),
            "imgsz": self.tr_imgsz.value(),
            "batch": self.tr_batch.value(),
            "device": self.tr_device.currentText().strip(),
            "experiment_name": self.tr_exp.text().strip(),
            "use_augment": self.tr_augment.isChecked(),
        }

    def _apply_config_dict(self, d):
        self.tr_data_yaml.setCurrentText(d.get("data_yaml", ""))
        self.tr_model.setCurrentText(d.get("model_file", ""))
        self.tr_results.setCurrentText(d.get("results_dir", ""))
        self.tr_logs.setCurrentText(d.get("log_dir", ""))
        self.tr_epochs.setValue(d.get("epochs", 150))
        self.tr_imgsz.setValue(d.get("imgsz", 640))
        self.tr_batch.setValue(d.get("batch", 16))
        self.tr_device.setCurrentText(d.get("device", get_default_device()))
        self.tr_exp.setText(d.get("experiment_name", ""))
        self.tr_augment.setChecked(d.get("use_augment", True))
        self._refresh_history()

    def _refresh_preset_combo(self):
        self.cb_presets.blockSignals(True)
        self.cb_presets.clear()
        self.cb_presets.addItem("— 预设 —")
        self._presets = load_presets()
        for name in sorted(self._presets.keys()):
            self.cb_presets.addItem(name)
        self.cb_presets.blockSignals(False)

    def _on_preset_selected(self, name):
        if not name or name == "— 预设 —" or name not in self._presets:
            return
        self._apply_config_dict(self._presets[name])
        self._log_info(f"已加载预设：「{name}」")

    def _save_preset(self):
        name = self.tr_exp.text().strip()
        if not name:
            name = "default"
        self._presets[name] = self._get_current_config_dict()
        save_presets(self._presets)
        self._refresh_preset_combo()
        idx = self.cb_presets.findText(name)
        if idx >= 0:
            self.cb_presets.setCurrentIndex(idx)
        self._log_info(f"预设已保存：「{name}」")

    def _delete_preset(self):
        name = self.cb_presets.currentText()
        if not name or name == "— 预设 —":
            QMessageBox.warning(self, "提示", "请先选择要删除的预设。")
            return
        if name in self._presets:
            del self._presets[name]
            save_presets(self._presets)
            self._refresh_preset_combo()
            self._log_info(f"已删除预设：「{name}」")

    # ── 日志 ──

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

    def _log_info(self, msg):
        self._log_append(self.tr_log, f'<span style="color:#6ec6ff;">[info]</span>  {msg}')

    def _log_good(self, msg):
        self._log_append(self.tr_log, f'<span style="color:#50fa7b;">[ ok ]</span>  {msg}')

    def _log_warn(self, msg):
        self._log_append(self.tr_log, f'<span style="color:#ffb86c;">[warn]</span>  {msg}')

    def _log_err(self, msg):
        self._log_append(self.tr_log, f'<span style="color:#ff5555;">[err!]</span>  {msg}')

    # ── 训练 ──

    def _set_train_ui_state(self, state: str) -> None:
        if state == "running":
            self.btn_start.setEnabled(False)
            self.btn_stop.setText("停止训练")
            self.btn_stop.setEnabled(True)
            self.btn_stop.clicked.disconnect()
            self.btn_stop.clicked.connect(self._on_stop_train)
            self.tr_progress.setValue(0)
        elif state == "stopped":
            self.btn_start.setText("继续训练")
            self.btn_start.setEnabled(True)
            self.btn_stop.setText("结束训练")
            self.btn_stop.setEnabled(True)
            self.rb_resume.setChecked(True)
            self.btn_stop.clicked.disconnect()
            self.btn_stop.clicked.connect(self._on_end_train)
        else:  # idle
            self.btn_start.setText("开始训练")
            self.btn_start.setEnabled(True)
            self.btn_stop.setText("停止训练")
            self.btn_stop.setEnabled(False)
            self.rb_new.setChecked(True)
            self.btn_stop.clicked.disconnect()
            self.btn_stop.clicked.connect(self._on_stop_train)
            self.tr_progress.setRange(0, 100)
            self.tr_progress.setValue(0)
            self.tr_progress.setFormat("%p%")

    def _build_config_from_train_ui(self):
        c = TrainConfig()
        c.data_yaml = path_combo_get(self.tr_data_yaml)
        c.model_file = path_combo_get(self.tr_model)
        c.results_dir = path_combo_get(self.tr_results)
        c.log_dir = path_combo_get(self.tr_logs)
        c.epochs = int(self.tr_epochs.value())
        c.imgsz = int(self.tr_imgsz.value())
        c.batch = int(self.tr_batch.value())
        c.device = self.tr_device.currentText().strip() or get_default_device()
        c.experiment_name = self.tr_exp.text().strip() or c.experiment_name
        c.use_augment = self.tr_augment.isChecked()
        return c

    @Slot()
    def _on_start_train(self):
        if self._train_worker and self._train_worker.isRunning():
            QMessageBox.warning(self, "提示", "训练正在进行中。")
            return

        cfg = self._build_config_from_train_ui()
        use_aug = self.tr_augment.isChecked()

        if self.rb_new.isChecked():
            mode = 1
            if not self._model_file_ok(cfg.model_file):
                QMessageBox.critical(self, "错误", f"找不到初始权重：\n{cfg.model_file}")
                return
            selected = None
            summary = f"模式 1 — 新训练\n权重: {cfg.model_file}\ndata: {cfg.data_yaml}\n实验: {cfg.experiment_name}"
        elif self.rb_resume.isChecked():
            mode = 2
            if not Path(cfg.last_pt).is_file():
                r = QMessageBox.question(
                    self, "未找到 last.pt",
                    f"未找到续训权重：\n{cfg.last_pt}\n\n是否改为模式 1 新训练？",
                    QMessageBox.Yes | QMessageBox.No,
                )
                if r != QMessageBox.Yes:
                    return
                mode = 1
                if not self._model_file_ok(cfg.model_file):
                    QMessageBox.critical(self, "错误", f"找不到初始权重：\n{cfg.model_file}")
                    return
            selected = None
            summary = f"模式 2 — 续训\nlast.pt: {cfg.last_pt}" if mode == 2 else f"已改为模式 1\n权重: {cfg.model_file}"
        else:
            mode = 3
            selected = self.cb_history.currentText().strip()
            if not selected:
                QMessageBox.warning(self, "提示", "请在「历史实验」下拉框中选择一项。")
                return
            best = Path(cfg.results_dir) / selected / "weights" / "best.pt"
            if not best.is_file():
                QMessageBox.critical(self, "错误", f"找不到：\n{best}")
                return
            summary = f"模式 3 — 基于历史 best\n实验: {selected}\n{best}"

        r = QMessageBox.question(
            self, "确认训练",
            summary + f"\n\nepochs={cfg.epochs}  imgsz={cfg.imgsz}  batch={cfg.batch}  device={cfg.device}\n"
            f"数据增强={'开' if use_aug else '关'}\n\n是否开始？",
            QMessageBox.Yes | QMessageBox.No,
        )
        if r != QMessageBox.Yes:
            return

        self.tr_log.clear()
        self._log_info(f"开始训练 — {cfg.experiment_name}")
        self._log_info(f"epochs={cfg.epochs}  imgsz={cfg.imgsz}  batch={cfg.batch}  device={cfg.device}")

        cmd = [
            sys.executable, str(ROOT / "gui" / "train_engine.py"),
            "--no-interactive",
            "--mode", str(mode),
            "--data-yaml", cfg.data_yaml,
            "--model-file", cfg.model_file,
            "--results-dir", cfg.results_dir,
            "--log-dir", cfg.log_dir,
            "--epochs", str(cfg.epochs),
            "--imgsz", str(cfg.imgsz),
            "--batch", str(cfg.batch),
            "--device", cfg.device,
            "--name", cfg.experiment_name,
        ]
        if use_aug:
            cmd.append("--use-augment")
        else:
            cmd.append("--no-augment")
        if mode == 3 and selected:
            cmd.extend(["--selected-exp", selected])

        self._set_train_ui_state("running")
        self.tr_progress.setRange(0, cfg.epochs)
        self.tr_progress.setValue(0)
        self.tr_progress.setFormat(f"Epoch %v / {cfg.epochs}")

        self._train_worker = TrainWorker(cmd)
        self._train_worker.log_line.connect(self._append_train_log)
        self._train_worker.progress.connect(self._on_train_progress)
        self._train_worker.failed.connect(self._on_train_failed)
        self._train_worker.finished_ok.connect(self._on_train_done)
        self._train_worker.stopped.connect(self._on_train_stopped)
        self._train_worker.finished.connect(self._on_train_thread_finished)
        self._train_worker.start()

    @Slot(str)
    def _append_train_log(self, line):
        self._log_append(self.tr_log, f'<span style="color:#c0c0c0;">{line}</span>')

    @Slot(int)
    def _on_train_progress(self, pct: int) -> None:
        self.tr_progress.setValue(pct)

    @Slot()
    def _on_stop_train(self):
        if self._train_worker and self._train_worker.isRunning():
            self._log_warn("正在停止训练...")
            self._train_worker.stop()

    @Slot(str)
    def _on_train_failed(self, msg):
        self._log_err("训练失败")
        self._log_append(self.tr_log, f'<span style="color:#ff6e6e;">{msg[:1500]}</span>')
        if not self._closing:
            QMessageBox.critical(self, "训练失败", msg[:2000])
        self._set_train_ui_state("idle")
        self._refresh_history()

    @Slot()
    def _on_train_done(self):
        self._log_good("训练完成")
        if not self._closing:
            QMessageBox.information(self, "完成", "训练流程已结束。")
        self._set_train_ui_state("idle")
        self._refresh_history()

    @Slot()
    def _on_train_stopped(self):
        self._log_warn("训练已暂停 — 可点击「继续训练」恢复，或点击「结束训练」终止本次会话")
        self._set_train_ui_state("stopped")

    @Slot()
    def _on_end_train(self):
        self._log_info("本次训练会话已结束")
        self._set_train_ui_state("idle")

    @Slot()
    def _on_train_thread_finished(self):
        if self._closing:
            QApplication.quit()

    # ═══════════════════════════════════════════════════════
    #  推理页
    # ═══════════════════════════════════════════════════════

    def _build_infer_tab(self):
        w = QWidget()
        w.setMinimumSize(560, 580)
        outer = QVBoxLayout(w)
        outer.setContentsMargins(24, 16, 24, 24)
        outer.setSpacing(10)

        card1, lay1 = card()
        lay1.addWidget(section_label("推理配置"))
        lay1.addSpacing(14)

        for key in ["ir_model", "ir_source", "ir_save"]:
            self._path_history.setdefault(key, [])

        self.ir_model  = path_combo(default="", history=self._path_history["ir_model"])
        self.ir_source = path_combo(default="", history=self._path_history["ir_source"])
        self.ir_save   = path_combo(default="", history=self._path_history["ir_save"])
        self.ir_conf   = input_(default="0.406", min_width=96)
        self.ir_imgsz  = spinner(32, 4096, 640, 96)

        ir_rows = [
            ("模型 .pt", self.ir_model,  "ir_model",  False, "权重 (*.pt *.pth *.onnx)"),
            ("输入源",   self.ir_source, "ir_source", True,  None),
            ("保存目录", self.ir_save,   "ir_save",   True,  None),
        ]
        for label, cb, hist_key, is_dir, flt in ir_rows:
            row = QHBoxLayout()
            row.setSpacing(10)
            lbl = field_label(label)
            lbl.setFixedWidth(72)
            row.addWidget(lbl)
            row.addWidget(cb, 1)
            b = btn("浏览", primary=False)
            b.setFixedWidth(60)
            b.clicked.connect(lambda checked, c=cb, d=is_dir, f=flt, k=hist_key: self._browse(c, d, f, k))
            row.addWidget(b)
            lay1.addLayout(row)
            lay1.addSpacing(8)

        conf_row = QHBoxLayout()
        conf_row.setSpacing(10)
        conf_row.addWidget(field_label("Conf"))
        conf_row.addWidget(self.ir_conf)
        conf_row.addSpacing(24)
        conf_row.addWidget(field_label("Imgsz"))
        conf_row.addWidget(self.ir_imgsz)
        conf_row.addStretch()
        lay1.addLayout(conf_row)
        outer.addWidget(card1)

        ir_btn_row = QHBoxLayout()
        ir_btn_row.setSpacing(10)

        self.btn_infer = btn("开始推理")
        self.btn_infer.setFixedHeight(38)
        self.btn_infer.clicked.connect(self._on_start_infer)
        ir_btn_row.addWidget(self.btn_infer)

        self.btn_stop_ir = danger_btn("停止推理")
        self.btn_stop_ir.setFixedHeight(38)
        self.btn_stop_ir.setVisible(False)
        self.btn_stop_ir.clicked.connect(self._on_stop_infer)
        ir_btn_row.addWidget(self.btn_stop_ir)

        ir_btn_row.addStretch()
        outer.addLayout(ir_btn_row)

        # ── 进度条 ──
        outer.addSpacing(4)
        self.ir_progress = progress_bar()
        self.ir_progress.setFormat("Image %v / %m")
        self.ir_progress.setVisible(False)
        outer.addWidget(self.ir_progress)

        outer.addWidget(field_label("输出"))
        self.ir_log = log_area()
        outer.addWidget(self.ir_log, 1)

        return scroll_area(w)

    def _log_info_ir(self, msg):
        self._log_append(self.ir_log, f'<span style="color:#6ec6ff;">[info]</span>  {msg}')

    def _set_infer_ui_state(self, state: str) -> None:
        if state == "running":
            self.btn_infer.setVisible(False)
            self.btn_stop_ir.setVisible(True)
            self.ir_progress.setVisible(True)
            self.ir_progress.setValue(0)
        else:  # idle
            self.btn_infer.setVisible(True)
            self.btn_stop_ir.setVisible(False)
            self.ir_progress.setVisible(False)

    def closeEvent(self, event):
        if self._closing:
            event.accept()
            return
        self._closing = True
        self.hide()
        self._log_info("正在退出，终止训练/推理进程...")
        workers_running = False
        if self._train_worker and self._train_worker.isRunning():
            self._train_worker.stop()
            workers_running = True
        if self._infer_worker and self._infer_worker.isRunning():
            self._infer_worker.stop()
            workers_running = True
        if not workers_running:
            QApplication.quit()
        event.ignore()

    def showEvent(self, e):
        super().showEvent(e)
        if self._infer_defaults_done:
            return
        self._infer_defaults_done = True
        from gui.paths import BEST_SEG_MODEL, PREDICT_DIR, TEST_IMAGES_DIR
        self.ir_model.setCurrentText(BEST_SEG_MODEL)
        self.ir_source.setCurrentText(TEST_IMAGES_DIR)
        self.ir_save.setCurrentText(str(Path(PREDICT_DIR) / "predict_result"))

    @Slot()
    def _on_start_infer(self):
        if self._infer_worker and self._infer_worker.isRunning():
            QMessageBox.warning(self, "提示", "推理正在进行中。")
            return

        model_path = path_combo_get(self.ir_model)
        source = path_combo_get(self.ir_source)
        save_dir = path_combo_get(self.ir_save)
        conf = self.ir_conf.text().strip()
        try:
            conf_val = float(conf) if conf else 0.25
        except ValueError:
            QMessageBox.critical(self, "错误", f"Conf 值无效: {conf}")
            return
        imgsz_val = int(self.ir_imgsz.value())

        if not self._model_file_ok(model_path):
            QMessageBox.critical(self, "错误", f"找不到模型：\n{model_path}")
            return
        if not Path(source).exists():
            QMessageBox.critical(self, "错误", f"找不到输入：\n{source}")
            return

        self.ir_log.clear()
        self._log_info_ir(f"开始推理 — {model_path}")

        cmd = [
            sys.executable, str(ROOT / "gui" / "infer_engine.py"),
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
        self.ir_progress.setFormat(f"Image %v / {total}")

    @Slot()
    def _on_stop_infer(self):
        if self._infer_worker and self._infer_worker.isRunning():
            self._log_append(self.ir_log, f'<span style="color:#ffb86c;">[warn]</span>  正在停止推理...')
            self._infer_worker.stop()

    @Slot(str)
    def _on_infer_failed(self, msg):
        self._log_append(self.ir_log, f'<span style="color:#ff5555;">[err!]</span>  推理失败')
        self._log_append(self.ir_log, f'<span style="color:#ff6e6e;">{msg[:1500]}</span>')
        self._set_infer_ui_state("idle")
        if not self._closing:
            QMessageBox.critical(self, "推理失败", msg[:2000])

    @Slot()
    def _on_infer_done(self):
        self._log_append(self.ir_log, f'<span style="color:#50fa7b;">[ ok ]</span>  推理完成')
        self._set_infer_ui_state("idle")
        if not self._closing:
            QMessageBox.information(self, "完成", "推理已结束。")

    @Slot()
    def _on_infer_stopped(self):
        self._log_append(self.ir_log, f'<span style="color:#ffb86c;">[warn]</span>  推理已停止')
        self._set_infer_ui_state("idle")

    @Slot()
    def _on_infer_thread_finished(self):
        if self._closing:
            QApplication.quit()


def main():
    app = QApplication(sys.argv)
    font = QFont()
    font.setFamilies(FONT_FAMILIES)
    font.setPixelSize(FONT_SIZE)
    app.setFont(font)
    w = MainWindow()
    w.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
