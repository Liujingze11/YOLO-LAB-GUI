"""
YOLO 分割训练 / 推理桌面界面 — Apple 风格简约设计
启动：在项目根目录执行  python gui/main.py
"""
from __future__ import annotations

import io
import json
import os
import subprocess
import sys
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

# 用户预设文件
PRESET_FILE = ROOT / "gui" / "presets.json"

from PySide6.QtCore import Qt, QThread, Signal, Slot
from PySide6.QtGui import QFont, QTextCursor
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QSizePolicy,
    QSpinBox,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from config import TrainConfig
from predict_test import InferConfig, YOLOInferencer
from train_segment import (
    execute_new_training,
    execute_resume_training,
    execute_train_from_previous_best,
    list_experiments,
)


class _TeeOut(io.TextIOBase):
    def __init__(self, original, emit_fn):
        super().__init__()
        self._original = original
        self._emit = emit_fn

    def write(self, s: str) -> int:
        try:
            self._original.write(s)
        except Exception:
            pass
        if s and s.strip():
            for line in s.rstrip("\n").split("\n"):
                if line.strip():
                    self._emit(line)
        return len(s)

    def flush(self) -> None:
        try:
            self._original.flush()
        except Exception:
            pass


class TrainWorker(QThread):
    log_line = Signal(str)
    failed = Signal(str)
    finished_ok = Signal()

    def __init__(self, config, mode, use_augment, selected_exp=None):
        super().__init__()
        self._config = config
        self._mode = mode
        self._use_augment = use_augment
        self._selected_exp = selected_exp or ""

    def run(self):
        old = sys.stdout
        sys.stdout = _TeeOut(old, self.log_line.emit)
        try:
            if self._mode == 1:
                execute_new_training(self._config, self._use_augment)
            elif self._mode == 2:
                execute_resume_training(self._config)
            elif self._mode == 3:
                if not self._selected_exp:
                    raise ValueError("请先选择历史实验目录。")
                execute_train_from_previous_best(
                    self._config, self._selected_exp, self._use_augment
                )
            self.finished_ok.emit()
        except Exception as e:
            self.failed.emit(f"{e}\n{traceback.format_exc()}")
        finally:
            sys.stdout = old


class InferWorker(QThread):
    log_line = Signal(str)
    failed = Signal(str)
    finished_ok = Signal()

    def __init__(self, cfg):
        super().__init__()
        self._cfg = cfg

    def run(self):
        old = sys.stdout
        sys.stdout = _TeeOut(old, self.log_line.emit)
        try:
            YOLOInferencer(self._cfg).run()
            self.finished_ok.emit()
        except Exception as e:
            self.failed.emit(f"{e}\n{traceback.format_exc()}")
        finally:
            sys.stdout = old


# ── 预设管理 ──────────────────────────────────────────────

def load_presets():
    if PRESET_FILE.is_file():
        try:
            return json.loads(PRESET_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def save_presets(presets):
    PRESET_FILE.parent.mkdir(parents=True, exist_ok=True)
    PRESET_FILE.write_text(json.dumps(presets, ensure_ascii=False, indent=2), encoding="utf-8")


# ── 辅助控件 ──────────────────────────────────────────────

def _card():
    card = QWidget()
    card.setStyleSheet(
        "QWidget { background: #ffffff; border-radius: 12px; }"
    )
    shadow = QGraphicsDropShadowEffect()
    shadow.setBlurRadius(24)
    shadow.setColor(Qt.gray)
    shadow.setOffset(0, 1)
    card.setGraphicsEffect(shadow)
    lay = QVBoxLayout(card)
    lay.setContentsMargins(24, 20, 24, 20)
    lay.setSpacing(0)
    return card, lay


def _section_label(text):
    lbl = QLabel(text.upper())
    lbl.setStyleSheet(
        "font-size: 11px; font-weight: 600; color: #6e6e73; letter-spacing: 0.4px;"
    )
    lbl.setTextInteractionFlags(Qt.TextSelectableByMouse)
    return lbl


def _field_label(text):
    lbl = QLabel(text)
    lbl.setStyleSheet("font-size: 13px; color: #1d1d1f; font-weight: 400;")
    lbl.setTextInteractionFlags(Qt.TextSelectableByMouse)
    return lbl


def _input(placeholder="", default="", min_width=0):
    e = QLineEdit(default)
    e.setPlaceholderText(placeholder)
    e.setStyleSheet(
        "QLineEdit { background: #ffffff; border: 1px solid #c7c7cc; border-radius: 6px; "
        "padding: 7px 10px; font-size: 13px; color: #1d1d1f; }"
        "QLineEdit:focus { border: 1px solid #0071e3; }"
    )
    if min_width:
        e.setMinimumWidth(min_width)
    return e


def _path_combo(default="", history=None):
    """可编辑路径下拉框：输入框 + 下拉历史记录。"""
    cb = QComboBox()
    cb.setEditable(True)
    cb.setInsertPolicy(QComboBox.NoInsert)
    cb.setMinimumWidth(280)
    cb.setStyleSheet(
        "QComboBox { background: #ffffff; border: 1px solid #c7c7cc; border-radius: 6px; "
        "padding: 7px 10px; font-size: 13px; color: #1d1d1f; min-height: 20px; }"
        "QComboBox:hover { border: 1px solid #999; }"
        "QComboBox:focus { border: 1px solid #0071e3; }"
        "QComboBox::drop-down { border: none; width: 22px; }"
        "QComboBox::down-arrow { image: none; border: none; }"
        "QComboBox QAbstractItemView { background: #ffffff; border: 1px solid #c7c7cc; "
        "border-radius: 6px; padding: 4px; selection-background-color: #e8e8ed; "
        "font-size: 13px; outline: none; }"
    )
    if history:
        cb.addItems(history)
    cb.setCurrentText(default)
    cb.setSizePolicy(cb.sizePolicy().horizontalPolicy(), cb.sizePolicy().verticalPolicy())
    return cb


def _path_combo_get(cb):
    """从路径下拉框获取当前文本。"""
    return cb.currentText().strip()


def _spinner(mn, mx, default, min_width=96):
    s = QSpinBox()
    s.setRange(mn, mx)
    s.setValue(default)
    s.setMinimumWidth(min_width)
    s.setStyleSheet(
        "QSpinBox { background: #ffffff; border: 1px solid #c7c7cc; border-radius: 6px; "
        "padding: 7px 10px; font-size: 13px; }"
        "QSpinBox:focus { border: 1px solid #0071e3; }"
    )
    return s


def _btn(text, primary=True):
    b = QPushButton(text)
    if primary:
        b.setStyleSheet(
            "QPushButton { background: #0071e3; color: #fff; border: none; "
            "border-radius: 6px; padding: 8px 20px; font-size: 13px; font-weight: 500; }"
            "QPushButton:hover { background: #0077ed; }"
            "QPushButton:pressed { background: #006edb; }"
            "QPushButton:disabled { background: #aeaeb2; }"
        )
    else:
        b.setStyleSheet(
            "QPushButton { background: #e8e8ed; color: #1d1d1f; border: none; "
            "border-radius: 6px; padding: 8px 20px; font-size: 13px; font-weight: 400; }"
            "QPushButton:hover { background: #dedee3; }"
            "QPushButton:pressed { background: #d4d4d9; }"
        )
    return b


def _tiny_btn(text):
    b = QPushButton(text)
    b.setStyleSheet(
        "QPushButton { background: transparent; color: #0071e3; border: none; "
        "padding: 2px 6px; font-size: 12px; }"
        "QPushButton:hover { color: #0077ed; text-decoration: underline; }"
    )
    return b


def _log_area():
    e = QTextEdit()
    e.setReadOnly(True)
    e.setStyleSheet(
        "QTextEdit { background: #1e1e1e; border: none; border-radius: 10px; "
        "padding: 14px 16px; font-family: 'SF Mono', 'JetBrains Mono', 'Consolas', monospace; "
        "font-size: 12px; color: #e0e0e0; selection-background-color: #3a3a3a; }"
    )
    e.setMinimumHeight(160)
    return e


# ── 主窗口 ──────────────────────────────────────────────────

class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("YOLO Lab")
        self.resize(820, 700)
        self.setMinimumSize(480, 360)

        self._train_worker = None
        self._infer_worker = None
        self._infer_defaults_done = False
        self._presets = load_presets()
        self._path_history: dict[str, list[str]] = {}  # 各路径字段的历史记录

        tabs = QTabWidget()
        tabs.setStyleSheet(
            "QTabWidget::pane { border: none; background: #f5f5f7; padding: 20px 24px; }"
            "QTabBar::tab { background: transparent; color: #8e8e93; padding: 8px 16px; "
            "margin-right: 2px; border-bottom: 2px solid transparent; font-size: 14px; font-weight: 500; }"
            "QTabBar::tab:selected { color: #0071e3; border-bottom: 2px solid #0071e3; }"
            "QTabBar::tab:hover:!selected { color: #515154; }"
        )
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
        w.setMinimumSize(640, 780)
        outer = QVBoxLayout(w)
        outer.setContentsMargins(24, 16, 24, 24)
        outer.setSpacing(14)

        # ── 路径卡片 ──
        card1, lay1 = _card()
        header1 = QHBoxLayout()
        header1.addWidget(_section_label("路径"))
        header1.addStretch()
        edit_yaml_btn = _tiny_btn("编辑 data.yaml")
        edit_yaml_btn.clicked.connect(self._open_data_yaml)
        header1.addWidget(edit_yaml_btn)
        lay1.addLayout(header1)
        lay1.addSpacing(14)

        # 路径历史
        for key in ["data_yaml", "model", "results", "logs"]:
            self._path_history.setdefault(key, [])

        self.tr_data_yaml = _path_combo(default="", history=self._path_history["data_yaml"])
        self.tr_model     = _path_combo(default="", history=self._path_history["model"])
        self.tr_results   = _path_combo(default="", history=self._path_history["results"])
        self.tr_logs      = _path_combo(default="", history=self._path_history["logs"])

        rows_data = [
            ("data.yaml", self.tr_data_yaml, "data_yaml", False, "YAML (*.yaml *.yml)"),
            ("初始权重", self.tr_model,     "model",      False, "权重 (*.pt *.pth *.onnx)"),
            ("结果目录", self.tr_results,   "results",    True,  None),
            ("日志目录", self.tr_logs,      "logs",       True,  None),
        ]
        for label, cb, hist_key, is_dir, flt in rows_data:
            row = QHBoxLayout()
            row.setSpacing(10)
            lbl = _field_label(label)
            lbl.setFixedWidth(72)
            row.addWidget(lbl)
            row.addWidget(cb, 1)
            b = _btn("浏览", primary=False)
            b.setFixedWidth(60)
            b.clicked.connect(lambda checked, c=cb, d=is_dir, f=flt, k=hist_key: self._browse(c, d, f, k))
            row.addWidget(b)
            lay1.addLayout(row)
            lay1.addSpacing(8)

        outer.addWidget(card1)

        # ── 超参数卡片 ──
        card2, lay2 = _card()
        lay2.addWidget(_section_label("超参数"))
        lay2.addSpacing(14)

        self.tr_epochs = _spinner(1, 100000, 150, 100)
        self.tr_imgsz = _spinner(32, 4096, 640, 100)
        self.tr_batch = _spinner(1, 1024, 16, 100)
        self.tr_device = _input(default="0", min_width=100)

        grid = QHBoxLayout()
        grid.setSpacing(28)
        for lbl, wgt in [
            ("Epochs", self.tr_epochs), ("Imgsz", self.tr_imgsz),
            ("Batch", self.tr_batch), ("Device", self.tr_device),
        ]:
            col = QVBoxLayout()
            col.setSpacing(4)
            col.addWidget(_field_label(lbl))
            col.addWidget(wgt)
            grid.addLayout(col)
        grid.addStretch()
        lay2.addLayout(grid)
        lay2.addSpacing(12)

        exp_row = QHBoxLayout()
        exp_row.setSpacing(10)
        exp_row.addWidget(_field_label("实验名称"))
        self.tr_exp = _input(min_width=320)
        exp_row.addWidget(self.tr_exp, 1)
        lay2.addLayout(exp_row)
        outer.addWidget(card2)

        # ── 训练模式卡片 ──
        card3, lay3 = _card()
        lay3.addWidget(_section_label("训练模式"))
        lay3.addSpacing(12)

        self.rb_new = QRadioButton("新训练 — 从初始权重开始")
        self.rb_resume = QRadioButton("续训 — 从上一次 last.pt 继续")
        self.rb_best = QRadioButton("微调 — 基于历史实验的 best.pt")
        self.rb_new.setChecked(True)
        for rb in [self.rb_new, self.rb_resume, self.rb_best]:
            rb.setStyleSheet("QRadioButton { spacing: 6px; padding: 4px 0; font-size: 13px; }")
            lay3.addWidget(rb)

        hist_row = QHBoxLayout()
        hist_row.setSpacing(10)
        hist_row.addWidget(_field_label("历史实验"))
        self.cb_history = QComboBox()
        self.cb_history.setMinimumWidth(300)
        self.cb_history.setStyleSheet(
            "QComboBox { background: #ffffff; border: 1px solid #c7c7cc; border-radius: 6px; "
            "padding: 7px 10px; font-size: 13px; min-height: 20px; }"
            "QComboBox:hover { border: 1px solid #999; }"
            "QComboBox::drop-down { border: none; width: 20px; }"
            "QComboBox QAbstractItemView { background: #ffffff; border: 1px solid #c7c7cc; "
            "border-radius: 6px; padding: 4px; selection-background-color: #e8e8ed; }"
        )
        hist_row.addWidget(self.cb_history, 1)
        refresh = _btn("刷新", primary=False)
        refresh.clicked.connect(self._refresh_history)
        hist_row.addWidget(refresh)
        lay3.addSpacing(8)
        lay3.addLayout(hist_row)
        outer.addWidget(card3)

        # ── 数据增强 ──
        self.tr_augment = QCheckBox("启用数据增强")
        self.tr_augment.setChecked(True)
        self.tr_augment.setStyleSheet("QCheckBox { spacing: 8px; font-size: 13px; }")
        outer.addWidget(self.tr_augment)

        # ── 操作按钮行 ──
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)

        self.btn_start = _btn("开始训练")
        self.btn_start.setFixedHeight(38)
        self.btn_start.clicked.connect(self._on_start_train)
        btn_row.addWidget(self.btn_start)

        self.btn_reset = _btn("恢复默认", primary=False)
        self.btn_reset.setFixedHeight(38)
        self.btn_reset.clicked.connect(self._reset_train_defaults)
        btn_row.addWidget(self.btn_reset)

        # 预设下拉
        self.cb_presets = QComboBox()
        self.cb_presets.setMinimumWidth(120)
        self.cb_presets.setStyleSheet(
            "QComboBox { background: #ffffff; border: 1px solid #c7c7cc; border-radius: 6px; "
            "padding: 7px 10px; font-size: 12px; min-height: 20px; }"
            "QComboBox:hover { border: 1px solid #999; }"
            "QComboBox::drop-down { border: none; width: 20px; }"
            "QComboBox QAbstractItemView { background: #ffffff; border: 1px solid #c7c7cc; "
            "border-radius: 6px; padding: 4px; selection-background-color: #e8e8ed; }"
        )
        self._refresh_preset_combo()
        self.cb_presets.currentTextChanged.connect(self._on_preset_selected)
        btn_row.addWidget(self.cb_presets)

        save_btn = _btn("保存预设", primary=False)
        save_btn.setFixedHeight(38)
        save_btn.clicked.connect(self._save_preset)
        btn_row.addWidget(save_btn)

        del_btn = _btn("删除预设", primary=False)
        del_btn.setFixedHeight(38)
        del_btn.clicked.connect(self._delete_preset)
        btn_row.addWidget(del_btn)

        btn_row.addStretch()
        outer.addLayout(btn_row)

        # ── 日志 ──
        outer.addWidget(_field_label("输出"))
        self.tr_log = _log_area()
        outer.addWidget(self.tr_log, 1)

        scroll = QScrollArea()
        scroll.setWidgetResizable(False)
        scroll.setWidget(w)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setStyleSheet(
            "QScrollArea { border: none; background: #f5f5f7; }"
            "QScrollBar:vertical { background: transparent; width: 8px; margin: 0; }"
            "QScrollBar::handle:vertical { background: #c0c0c0; border-radius: 4px; min-height: 30px; }"
            "QScrollBar::handle:vertical:hover { background: #a0a0a0; }"
            "QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }"
            "QScrollBar:horizontal { background: transparent; height: 8px; margin: 0; }"
            "QScrollBar::handle:horizontal { background: #c0c0c0; border-radius: 4px; min-width: 30px; }"
            "QScrollBar::handle:horizontal:hover { background: #a0a0a0; }"
            "QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0; }"
        )
        return scroll

    def _add_to_history(self, key, value):
        """将路径加入对应历史记录（去重，最新在前）。"""
        if not value:
            return
        hist = self._path_history.setdefault(key, [])
        if value in hist:
            hist.remove(value)
        hist.insert(0, value)
        if len(hist) > 20:
            hist.pop()

    def _browse(self, combo, directory, filter_str, hist_key):
        start = Path(_path_combo_get(combo) or str(ROOT)).resolve()
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

    def _open_data_yaml(self):
        p = Path(_path_combo_get(self.tr_data_yaml))
        if not p.is_file():
            QMessageBox.warning(self, "提示", f"文件不存在：\n{p}")
            return
        try:
            os.startfile(str(p))
        except Exception:
            try:
                subprocess.Popen(["xdg-open", str(p)])
            except Exception:
                QMessageBox.critical(self, "错误", "无法打开文件，请手动打开。")

    def _load_train_defaults(self):
        c = TrainConfig()
        self._apply_config(c)

    def _apply_config(self, c):
        self.tr_data_yaml.setCurrentText(c.data_yaml)
        self.tr_model.setCurrentText(c.model_file)
        self.tr_results.setCurrentText(c.results_dir)
        self.tr_logs.setCurrentText(c.log_dir)
        self.tr_epochs.setValue(int(c.epochs))
        self.tr_imgsz.setValue(int(c.imgsz))
        self.tr_batch.setValue(int(c.batch))
        self.tr_device.setText(str(c.device))
        self.tr_exp.setText(c.experiment_name)
        self.tr_augment.setChecked(bool(c.use_augment))
        self._refresh_history()

    def _reset_train_defaults(self):
        c = TrainConfig()
        self._apply_config(c)
        self._log_info("已恢复默认配置")

    def _refresh_history(self):
        self.cb_history.clear()
        res = Path(_path_combo_get(self.tr_results) or ".")
        if not res.is_dir():
            return
        for name in sorted(list_experiments(str(res))):
            self.cb_history.addItem(name)

    # ── 预设 ──

    def _get_current_config_dict(self):
        return {
            "data_yaml": _path_combo_get(self.tr_data_yaml),
            "model_file": _path_combo_get(self.tr_model),
            "results_dir": _path_combo_get(self.tr_results),
            "log_dir": _path_combo_get(self.tr_logs),
            "epochs": self.tr_epochs.value(),
            "imgsz": self.tr_imgsz.value(),
            "batch": self.tr_batch.value(),
            "device": self.tr_device.text().strip(),
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
        self.tr_device.setText(d.get("device", "0"))
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

    def _log_info(self, msg):
        self.tr_log.append(f'<span style="color:#6ec6ff;">[info]</span>  {msg}')

    def _log_good(self, msg):
        self.tr_log.append(f'<span style="color:#50fa7b;">[ ok ]</span>  {msg}')

    def _log_warn(self, msg):
        self.tr_log.append(f'<span style="color:#ffb86c;">[warn]</span>  {msg}')

    def _log_err(self, msg):
        self.tr_log.append(f'<span style="color:#ff5555;">[err!]</span>  {msg}')

    # ── 训练 ──

    def _build_config_from_train_ui(self):
        c = TrainConfig()
        c.data_yaml = _path_combo_get(self.tr_data_yaml)
        c.model_file = _path_combo_get(self.tr_model)
        c.results_dir = _path_combo_get(self.tr_results)
        c.log_dir = _path_combo_get(self.tr_logs)
        c.epochs = int(self.tr_epochs.value())
        c.imgsz = int(self.tr_imgsz.value())
        c.batch = int(self.tr_batch.value())
        c.device = self.tr_device.text().strip() or "0"
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
            if not Path(cfg.model_file).is_file():
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
                if not Path(cfg.model_file).is_file():
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
        self.btn_start.setEnabled(False)

        self._train_worker = TrainWorker(cfg, mode, use_aug, selected if mode == 3 else None)
        self._train_worker.log_line.connect(self._append_train_log)
        self._train_worker.failed.connect(self._on_train_failed)
        self._train_worker.finished_ok.connect(self._on_train_done)
        self._train_worker.finished.connect(self._on_train_thread_finished)
        self._train_worker.start()

    @Slot(str)
    def _append_train_log(self, line):
        self.tr_log.append(f'<span style="color:#c0c0c0;">{line}</span>')

    @Slot(str)
    def _on_train_failed(self, msg):
        self._log_err("训练失败")
        self.tr_log.append(f'<span style="color:#ff6e6e;">{msg[:1500]}</span>')
        QMessageBox.critical(self, "训练失败", msg[:2000])

    @Slot()
    def _on_train_done(self):
        self._log_good("训练完成")
        QMessageBox.information(self, "完成", "训练流程已结束。")
        self._refresh_history()

    @Slot()
    def _on_train_thread_finished(self):
        self.btn_start.setEnabled(True)

    # ═══════════════════════════════════════════════════════
    #  推理页
    # ═══════════════════════════════════════════════════════

    def _build_infer_tab(self):
        w = QWidget()
        w.setMinimumSize(560, 460)
        outer = QVBoxLayout(w)
        outer.setContentsMargins(24, 16, 24, 24)
        outer.setSpacing(14)

        card1, lay1 = _card()
        lay1.addWidget(_section_label("推理配置"))
        lay1.addSpacing(14)

        for key in ["ir_model", "ir_source", "ir_save"]:
            self._path_history.setdefault(key, [])

        self.ir_model  = _path_combo(default="", history=self._path_history["ir_model"])
        self.ir_source = _path_combo(default="", history=self._path_history["ir_source"])
        self.ir_save   = _path_combo(default="", history=self._path_history["ir_save"])
        self.ir_conf = _input(default="0.406", min_width=96)
        self.ir_imgsz = _spinner(32, 4096, 640, 96)

        ir_rows = [
            ("模型 .pt", self.ir_model,  "ir_model",  False, "权重 (*.pt *.pth *.onnx)"),
            ("输入源",   self.ir_source, "ir_source", True,  None),
            ("保存目录", self.ir_save,   "ir_save",   True,  None),
        ]
        for label, cb, hist_key, is_dir, flt in ir_rows:
            row = QHBoxLayout()
            row.setSpacing(10)
            lbl = _field_label(label)
            lbl.setFixedWidth(72)
            row.addWidget(lbl)
            row.addWidget(cb, 1)
            b = _btn("浏览", primary=False)
            b.setFixedWidth(60)
            b.clicked.connect(lambda checked, c=cb, d=is_dir, f=flt, k=hist_key: self._browse(c, d, f, k))
            row.addWidget(b)
            lay1.addLayout(row)
            lay1.addSpacing(8)

        conf_row = QHBoxLayout()
        conf_row.setSpacing(10)
        conf_row.addWidget(_field_label("Conf"))
        conf_row.addWidget(self.ir_conf)
        conf_row.addSpacing(24)
        conf_row.addWidget(_field_label("Imgsz"))
        conf_row.addWidget(self.ir_imgsz)
        conf_row.addStretch()
        lay1.addLayout(conf_row)
        outer.addWidget(card1)

        self.btn_infer = _btn("开始推理")
        self.btn_infer.setFixedHeight(38)
        self.btn_infer.clicked.connect(self._on_start_infer)
        outer.addWidget(self.btn_infer)

        outer.addWidget(_field_label("输出"))
        self.ir_log = _log_area()
        outer.addWidget(self.ir_log, 1)

        scroll = QScrollArea()
        scroll.setWidgetResizable(False)
        scroll.setWidget(w)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setStyleSheet(
            "QScrollArea { border: none; background: #f5f5f7; }"
            "QScrollBar:vertical { background: transparent; width: 8px; margin: 0; }"
            "QScrollBar::handle:vertical { background: #c0c0c0; border-radius: 4px; min-height: 30px; }"
            "QScrollBar::handle:vertical:hover { background: #a0a0a0; }"
            "QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }"
            "QScrollBar:horizontal { background: transparent; height: 8px; margin: 0; }"
            "QScrollBar::handle:horizontal { background: #c0c0c0; border-radius: 4px; min-width: 30px; }"
            "QScrollBar::handle:horizontal:hover { background: #a0a0a0; }"
            "QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0; }"
        )
        return scroll

    def _log_info_ir(self, msg):
        self.ir_log.append(f'<span style="color:#6ec6ff;">[info]</span>  {msg}')

    def showEvent(self, e):
        super().showEvent(e)
        if self._infer_defaults_done:
            return
        self._infer_defaults_done = True
        from paths import BEST_SEG_MODEL, PREDICT_DIR, TEST_IMAGES_DIR
        self.ir_model.setCurrentText(BEST_SEG_MODEL)
        self.ir_source.setCurrentText(TEST_IMAGES_DIR)
        self.ir_save.setCurrentText(str(Path(PREDICT_DIR) / "predict_result"))

    @Slot()
    def _on_start_infer(self):
        if self._infer_worker and self._infer_worker.isRunning():
            QMessageBox.warning(self, "提示", "推理正在进行中。")
            return
        cfg = InferConfig(
            model_path=_path_combo_get(self.ir_model),
            source=_path_combo_get(self.ir_source),
            save_dir=_path_combo_get(self.ir_save),
            conf=float(self.ir_conf.text().strip() or "0.25"),
            imgsz=int(self.ir_imgsz.value()),
            task_param_file=str(SCRIPTS / "infer_task_params.json"),
        )
        if not Path(cfg.model_path).is_file():
            QMessageBox.critical(self, "错误", f"找不到模型：\n{cfg.model_path}")
            return
        if not Path(cfg.source).exists():
            QMessageBox.critical(self, "错误", f"找不到输入：\n{cfg.source}")
            return

        self.ir_log.clear()
        self._log_info_ir(f"开始推理 — {cfg.model_path}")
        self.btn_infer.setEnabled(False)
        self._infer_worker = InferWorker(cfg)
        self._infer_worker.log_line.connect(
            lambda line: self.ir_log.append(f'<span style="color:#c0c0c0;">{line}</span>')
        )
        self._infer_worker.failed.connect(self._on_infer_failed)
        self._infer_worker.finished_ok.connect(self._on_infer_done)
        self._infer_worker.finished.connect(self._on_infer_thread_finished)
        self._infer_worker.start()

    @Slot(str)
    def _on_infer_failed(self, msg):
        self.ir_log.append(f'<span style="color:#ff5555;">[err!]</span>  推理失败')
        self.ir_log.append(f'<span style="color:#ff6e6e;">{msg[:1500]}</span>')
        QMessageBox.critical(self, "推理失败", msg[:2000])

    @Slot()
    def _on_infer_done(self):
        self.ir_log.append(f'<span style="color:#50fa7b;">[ ok ]</span>  推理完成')
        QMessageBox.information(self, "完成", "推理已结束。")

    @Slot()
    def _on_infer_thread_finished(self):
        self.btn_infer.setEnabled(True)


def main():
    app = QApplication(sys.argv)
    font = QFont()
    font.setFamilies(["-apple-system", "Segoe UI", "Noto Sans CJK SC", "sans-serif"])
    font.setPixelSize(13)
    app.setFont(font)
    w = MainWindow()
    w.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
