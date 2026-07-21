"""
Training tab — hyperparameters, preset management, and train lifecycle.
"""
from __future__ import annotations

import csv
import json
import os
import platform
import subprocess
import sys
from pathlib import Path

from PySide6.QtCore import Qt, Slot
from PySide6.QtGui import QTextCursor
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from core.config import TrainConfig
from core.device import get_available_devices, get_default_device
from gui.i18n import tr, current_lang
from gui.model_selector import ModelSelector
from gui.paths import REPO_ROOT, RESULTS_DIR, LOG_DIR
from gui.styles import (
    CHECKBOX_STYLE,
    COMBO_STYLE,
    RADIO_STYLE,
    SPINNER_STYLE,
)
from gui.train_engine import list_experiments
from gui.widgets import (
    btn,
    danger_btn,
    field_label,
    input_,
    log_area,
    path_combo,
    path_combo_get,
    progress_bar,
    resizable_card,
    scroll_area,
    simple_combo,
    spinner,
    tiny_btn,
)
from gui.workers import TrainWorker


# ── Preset persistence ─────────────────────────────────────

PRESET_FILE = REPO_ROOT / "gui" / "presets.json"


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


# ── TrainTab ────────────────────────────────────────────────

class TrainTab(QWidget):
    """Training configuration, execution and monitoring tab."""

    def __init__(self, parent=None, path_history: dict[str, list[str]] | None = None):
        super().__init__(parent)
        self._train_worker: TrainWorker | None = None
        self._presets: dict = {}
        self._path_history = path_history if path_history is not None else {}
        self._closing = False
        self._build_ui()
        self._load_train_defaults()

    # ── UI construction ─────────────────────────────────────

    def _build_ui(self):
        w = self
        outer = QVBoxLayout(w)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        inner = QWidget()
        inner.setMinimumSize(640, 920)
        il = QVBoxLayout(inner)
        il.setContentsMargins(24, 16, 24, 24)
        il.setSpacing(0)

        splitter = QSplitter(Qt.Vertical)
        splitter.setChildrenCollapsible(False)
        splitter.setHandleWidth(5)
        splitter.setStyleSheet("""
            QSplitter::handle:vertical {
                background: transparent;
            }
        """)
        self._splitter = splitter
        self._splitter_defaults = [200, 180, 170, 130, 220]

        # ── Panel 1: 路径 ──
        card1, header1, lay1 = resizable_card("路径", i18n_key="train.card.paths")

        scan_models_btn = tiny_btn("扫描模型", i18n_key="train.btn.scan")
        scan_models_btn.clicked.connect(self._scan_trained_models)
        header1.addWidget(scan_models_btn)
        edit_yaml_btn = tiny_btn("编辑 data.yaml", i18n_key="train.btn.edit_yaml")
        edit_yaml_btn.clicked.connect(self._open_data_yaml)
        header1.addWidget(edit_yaml_btn)

        for key in ["data_yaml", "model", "results", "logs"]:
            self._path_history.setdefault(key, [])

        self.tr_data_yaml = path_combo(default="", history=self._path_history["data_yaml"])
        self.tr_model = ModelSelector()
        self.tr_results = path_combo(default=RESULTS_DIR, history=self._path_history["results"])
        self.tr_logs = path_combo(default=LOG_DIR, history=self._path_history["logs"])

        rows_data = [
            ("data.yaml", self.tr_data_yaml, "data_yaml", False, "YAML (*.yaml *.yml)"),
            ("结果目录", self.tr_results, "results", True, None),
            ("日志目录", self.tr_logs, "logs", True, None),
        ]
        for label, cb, hist_key, is_dir, flt in rows_data:
            row = QHBoxLayout()
            row.setSpacing(10)
            lbl = field_label(label, i18n_key={
                "data.yaml": "train.data_yaml",
                "结果目录": "train.field.results_dir",
                "日志目录": "train.field.log_dir",
            }.get(label, ""))
            lbl.setFixedWidth(72)
            row.addWidget(lbl)
            row.addWidget(cb, 1)
            b = btn("浏览", primary=False, i18n_key="train.btn.browse")
            b.setFixedWidth(60)
            b.clicked.connect(lambda checked, c=cb, d=is_dir, f=flt, k=hist_key: self._browse(c, d, f, k))
            row.addWidget(b)
            lay1.addLayout(row)
            lay1.addSpacing(8)

        model_row = QHBoxLayout()
        model_row.setSpacing(10)
        model_lbl = field_label("初始权重", i18n_key="train.field.init_weights")
        model_lbl.setFixedWidth(72)
        model_row.addWidget(model_lbl)
        model_row.addWidget(self.tr_model, 1)
        lay1.addLayout(model_row)

        card1.setMinimumHeight(180)
        splitter.addWidget(self._wrap_card(card1))

        # ── Panel 2: 超参数 ──
        card2, header2, lay2 = resizable_card("超参数", i18n_key="train.card.hyperparams")

        self.tr_epochs = spinner(1, 100000, 150, 100)
        self.tr_imgsz = spinner(32, 4096, 640, 100)
        self.tr_batch = spinner(1, 1024, 16, 100)
        self.tr_device = QComboBox()
        self.tr_device.setMinimumWidth(100)
        self.tr_device.setProperty("themeClass", "combo")
        self.tr_device.setStyleSheet(COMBO_STYLE)

        grid = QHBoxLayout()
        grid.setSpacing(28)
        for lbl_text, i18n_key, wgt in [
            ("Epochs", "train.field.epochs", self.tr_epochs),
            ("Imgsz", "train.field.imgsz", self.tr_imgsz),
            ("Batch", "train.field.batch", self.tr_batch),
            ("Device", "train.field.device", self.tr_device),
        ]:
            col = QVBoxLayout()
            col.setSpacing(4)
            col.addWidget(field_label(lbl_text, i18n_key=i18n_key))
            col.addWidget(wgt)
            grid.addLayout(col)
        grid.addStretch()
        lay2.addLayout(grid)
        lay2.addSpacing(10)

        exp_row = QHBoxLayout()
        exp_row.setSpacing(10)
        exp_row.addWidget(field_label("实验名称", i18n_key="train.field.exp_name"))
        self.tr_exp = input_(min_width=320)
        exp_row.addWidget(self.tr_exp, 1)
        lay2.addLayout(exp_row)

        card2.setMinimumHeight(120)
        splitter.addWidget(self._wrap_card(card2))

        # ── Panel 3: 数据增强 ──

        def _aug_spin(default, min_v, max_v, step, i18n_key):
            """创建数据增强用的 DoubleSpinBox（步长更小，精度更高）。"""
            s = QDoubleSpinBox()
            s.setRange(min_v, max_v)
            s.setValue(default)
            s.setSingleStep(step)
            s.setDecimals(4)
            s.setMinimumWidth(80)
            s.setProperty("i18nKey", i18n_key)
            s.setProperty("themeClass", "spinner")
            s.setStyleSheet(SPINNER_STYLE)
            return s

        def _aug_row(label_key, widget):
            """数据增强参数行：标签 + 微调框。"""
            row = QHBoxLayout()
            row.setSpacing(6)
            lbl = field_label("", i18n_key=label_key)
            lbl.setFixedWidth(64)
            row.addWidget(lbl)
            row.addWidget(widget)
            row.addStretch()
            return row

        card_aug, header_aug, lay_aug = resizable_card("数据增强", i18n_key="train.card.augment")

        self.tr_augment = QCheckBox(tr("train.augment"))
        self.tr_augment.setProperty("i18nKey", "train.augment")
        self.tr_augment.setChecked(True)
        self.tr_augment.setProperty("themeClass", "checkbox")
        self.tr_augment.setStyleSheet(CHECKBOX_STYLE)
        self.tr_augment.toggled.connect(self._on_augment_toggled)
        header_aug.addWidget(self.tr_augment)

        aug_grid = QHBoxLayout()
        aug_grid.setSpacing(20)

        # 列1: 颜色抖动
        col1 = QVBoxLayout()
        col1.setSpacing(4)
        col1.addWidget(field_label("颜色抖动", i18n_key="train.aug.color"))
        self.aug_hsv_h = _aug_spin(0.015, 0.0, 1.0, 0.001, "train.aug.hsv_h")
        self.aug_hsv_s = _aug_spin(0.7, 0.0, 1.0, 0.1, "train.aug.hsv_s")
        self.aug_hsv_v = _aug_spin(0.4, 0.0, 1.0, 0.1, "train.aug.hsv_v")
        for lbl_key, w in [("train.aug.hsv_h", self.aug_hsv_h),
                           ("train.aug.hsv_s", self.aug_hsv_s),
                           ("train.aug.hsv_v", self.aug_hsv_v)]:
            col1.addWidget(_aug_row(lbl_key, w))
        col1.addStretch()
        aug_grid.addLayout(col1)

        # 列2: 几何变换
        col2 = QVBoxLayout()
        col2.setSpacing(4)
        col2.addWidget(field_label("几何变换", i18n_key="train.aug.geometry"))
        self.aug_degrees = _aug_spin(0.0, 0.0, 180.0, 1.0, "train.aug.degrees")
        self.aug_translate = _aug_spin(0.1, 0.0, 1.0, 0.1, "train.aug.translate")
        self.aug_scale = _aug_spin(0.5, 0.0, 2.0, 0.1, "train.aug.scale")
        self.aug_shear = _aug_spin(0.0, 0.0, 30.0, 1.0, "train.aug.shear")
        self.aug_perspective = _aug_spin(0.0, 0.0, 0.001, 0.0001, "train.aug.perspective")
        self.aug_flipud = _aug_spin(0.0, 0.0, 1.0, 0.1, "train.aug.flipud")
        self.aug_fliplr = _aug_spin(0.5, 0.0, 1.0, 0.1, "train.aug.fliplr")
        for lbl_key, w in [
            ("train.aug.degrees", self.aug_degrees),
            ("train.aug.translate", self.aug_translate),
            ("train.aug.scale", self.aug_scale),
            ("train.aug.shear", self.aug_shear),
            ("train.aug.perspective", self.aug_perspective),
            ("train.aug.flipud", self.aug_flipud),
            ("train.aug.fliplr", self.aug_fliplr),
        ]:
            col2.addWidget(_aug_row(lbl_key, w))
        col2.addStretch()
        aug_grid.addLayout(col2)

        # 列3: 混合策略
        col3 = QVBoxLayout()
        col3.setSpacing(4)
        col3.addWidget(field_label("混合策略", i18n_key="train.aug.mixing"))
        self.aug_mosaic = _aug_spin(1.0, 0.0, 1.0, 0.1, "train.aug.mosaic")
        self.aug_mixup = _aug_spin(0.0, 0.0, 1.0, 0.1, "train.aug.mixup")
        self.aug_copy_paste = _aug_spin(0.0, 0.0, 1.0, 0.1, "train.aug.copy_paste")
        for lbl_key, w in [
            ("train.aug.mosaic", self.aug_mosaic),
            ("train.aug.mixup", self.aug_mixup),
            ("train.aug.copy_paste", self.aug_copy_paste),
        ]:
            col3.addWidget(_aug_row(lbl_key, w))
        col3.addStretch()
        aug_grid.addLayout(col3)

        lay_aug.addLayout(aug_grid)

        card_aug.setMinimumHeight(160)
        splitter.addWidget(self._wrap_card(card_aug))

        # ── Panel 4: 训练模式 ──
        card3, header3, lay3 = resizable_card("训练模式", i18n_key="train.card.mode")

        self.rb_new = QRadioButton(tr("train.rb.new"))
        self.rb_new.setProperty("i18nKey", "train.rb.new")
        self.rb_new.setChecked(True)
        self.rb_new.setStyleSheet(RADIO_STYLE)
        self.rb_new.setProperty("themeClass", "radio")

        self.rb_resume = QRadioButton(tr("train.rb.resume"))
        self.rb_resume.setProperty("i18nKey", "train.rb.resume")
        self.rb_resume.setStyleSheet(RADIO_STYLE)
        self.rb_resume.setProperty("themeClass", "radio")

        self.rb_best = QRadioButton(tr("train.rb.finetune"))
        self.rb_best.setProperty("i18nKey", "train.rb.finetune")
        self.rb_best.setStyleSheet(RADIO_STYLE)
        self.rb_best.setProperty("themeClass", "radio")

        lay3.addWidget(self.rb_new)
        lay3.addWidget(self.rb_resume)
        lay3.addWidget(self.rb_best)

        hist_row = QHBoxLayout()
        hist_row.setSpacing(10)
        hist_row.addWidget(field_label("历史实验", i18n_key="train.field.history"))
        self.cb_history = simple_combo(min_width=300, font_size=13)
        hist_row.addWidget(self.cb_history, 1)
        refresh = btn("刷新", primary=False, i18n_key="train.btn.refresh")
        refresh.clicked.connect(self._refresh_history)
        hist_row.addWidget(refresh)
        lay3.addSpacing(8)
        lay3.addLayout(hist_row)

        card3.setMinimumHeight(130)
        splitter.addWidget(self._wrap_card(card3))

        # ── Panel 5: 底部面板（按钮 + 进度 + 日志）──
        bottom = QWidget()
        bottom_layout = QVBoxLayout(bottom)
        bottom_layout.setContentsMargins(0, 8, 0, 0)
        bottom_layout.setSpacing(6)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)

        self.btn_start = btn("开始训练", i18n_key="train.btn.start")
        self.btn_start.setFixedHeight(38)
        self.btn_start.clicked.connect(self._on_start_train)
        btn_row.addWidget(self.btn_start)

        self.btn_stop = danger_btn("停止训练", i18n_key="train.btn.stop")
        self.btn_stop.setFixedHeight(38)
        self.btn_stop.setEnabled(False)
        self.btn_stop.clicked.connect(self._on_stop_train)
        btn_row.addWidget(self.btn_stop)

        self.btn_reset = btn("恢复默认", primary=False, i18n_key="train.btn.reset")
        self.btn_reset.setFixedHeight(38)
        self.btn_reset.clicked.connect(self._reset_train_defaults)
        btn_row.addWidget(self.btn_reset)

        self.cb_presets = simple_combo(min_width=120)
        self._refresh_preset_combo()
        self.cb_presets.currentTextChanged.connect(self._on_preset_selected)
        btn_row.addWidget(self.cb_presets)

        save_btn = btn("保存预设", primary=False, i18n_key="train.btn.save_preset")
        save_btn.setFixedHeight(38)
        save_btn.clicked.connect(self._save_preset)
        btn_row.addWidget(save_btn)

        del_btn = btn("删除预设", primary=False, i18n_key="train.btn.delete_preset")
        del_btn.setFixedHeight(38)
        del_btn.clicked.connect(self._delete_preset)
        btn_row.addWidget(del_btn)

        btn_row.addStretch()
        bottom_layout.addLayout(btn_row)

        self.tr_progress = progress_bar(i18n_key="train.progress.format")
        bottom_layout.addWidget(self.tr_progress)

        self.tr_log = log_area()
        bottom_layout.addWidget(self.tr_log, 1)

        bottom.setMinimumHeight(180)
        splitter.addWidget(self._wrap_card(bottom))
        splitter.setSizes([200, 180, 170, 130, 220])
        il.addWidget(splitter)

        outer.addWidget(scroll_area(inner))

    # ── Shared utility methods ──────────────────────────────

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
        self._log_append(self.tr_log, f'<span style="color:#6ec6ff;">{tr("log.info_prefix")}</span>  {msg}')

    def _log_good(self, msg):
        self._log_append(self.tr_log, f'<span style="color:#50fa7b;">{tr("log.ok_prefix")}</span>  {msg}')

    def _log_warn(self, msg):
        self._log_append(self.tr_log, f'<span style="color:#ffb86c;">{tr("log.warn_prefix")}</span>  {msg}')

    def _log_err(self, msg):
        self._log_append(self.tr_log, f'<span style="color:#ff5555;">{tr("log.err_prefix")}</span>  {msg}')

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
            from gui.paths import PRETRAINED_DIR
            return (PRETRAINED_DIR / path).is_file()
        return False

    def _open_data_yaml(self):
        p = Path(path_combo_get(self.tr_data_yaml))
        if not p.is_file():
            QMessageBox.warning(self, tr("msg.title.hint"), f"{tr('msg.yaml_not_found')}\n{p}")
            return
        try:
            self._open_file_with_default_app(str(p))
        except Exception:
            QMessageBox.critical(self, tr("msg.title.error"), tr("msg.cannot_open_file"))

    @staticmethod
    def _open_file_with_default_app(path: str) -> None:
        system = platform.system()
        if system == "Windows":
            os.startfile(path)
        elif system == "Darwin":
            subprocess.Popen(["open", path])
        else:
            subprocess.Popen(["xdg-open", path])

    @staticmethod
    def _wrap_card(widget: QWidget) -> QWidget:
        container = QWidget()
        container.setStyleSheet("background: transparent;")
        lay = QVBoxLayout(container)
        lay.setContentsMargins(0, 6, 0, 6)
        lay.addWidget(widget)
        return container

    @staticmethod
    def _open_dir_safe(path_str: str) -> None:
        p = Path(path_str)
        if p.is_dir():
            TrainTab._open_file_with_default_app(str(p))
        elif p.parent.is_dir():
            TrainTab._open_file_with_default_app(str(p.parent))

    @staticmethod
    def _load_csv_log(log_widget, csv_path: Path):
        log_widget.clear()
        with open(csv_path, encoding="utf-8-sig") as f:
            reader = csv.reader(f)
            rows = list(reader)
        if not rows:
            TrainTab._log_append(log_widget,
                f'<span style="color:#6ec6ff;">{tr("log.info_prefix")}</span>  {tr("msg.log_empty")}')
            return
        TrainTab._log_append(log_widget,
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
        TrainTab._log_append(log_widget, html)

    # ── Defaults & config ──────────────────────────────────

    def _load_train_defaults(self):
        self._refresh_devices()
        self._apply_config(TrainConfig())

    def _refresh_devices(self):
        current = self.tr_device.currentData() or get_default_device()
        self.tr_device.clear()
        for dev_id, dev_name in get_available_devices():
            self.tr_device.addItem(dev_name, dev_id)
        idx = self.tr_device.findData(current)
        if idx >= 0:
            self.tr_device.setCurrentIndex(idx)
        else:
            self.tr_device.setCurrentIndex(0)

    def _apply_config(self, c):
        if c.data_yaml:
            self.tr_data_yaml.setCurrentText(c.data_yaml)
        self.tr_model.set_model(c.model_file)
        if c.results_dir:
            self.tr_results.setCurrentText(c.results_dir)
        if c.log_dir:
            self.tr_logs.setCurrentText(c.log_dir)
        self.tr_epochs.setValue(int(c.epochs))
        self.tr_imgsz.setValue(int(c.imgsz))
        self.tr_batch.setValue(int(c.batch))
        idx = self.tr_device.findData(str(c.device))
        if idx >= 0:
            self.tr_device.setCurrentIndex(idx)
        else:
            self.tr_device.setCurrentIndex(0)
        self.tr_exp.setText(c.experiment_name)
        self.tr_augment.setChecked(bool(c.use_augment))
        self.aug_hsv_h.setValue(c.hsv_h)
        self.aug_hsv_s.setValue(c.hsv_s)
        self.aug_hsv_v.setValue(c.hsv_v)
        self.aug_degrees.setValue(c.degrees)
        self.aug_translate.setValue(c.translate)
        self.aug_scale.setValue(c.scale)
        self.aug_shear.setValue(c.shear)
        self.aug_perspective.setValue(c.perspective)
        self.aug_flipud.setValue(c.flipud)
        self.aug_fliplr.setValue(c.fliplr)
        self.aug_mosaic.setValue(c.mosaic)
        self.aug_mixup.setValue(c.mixup)
        self.aug_copy_paste.setValue(c.copy_paste)
        self._refresh_history()

    def _scan_trained_models(self):
        results_dir = path_combo_get(self.tr_results)
        if not Path(results_dir).is_dir():
            return
        found = 0
        for exp in sorted(Path(results_dir).iterdir()):
            if exp.is_dir():
                best = exp / "weights" / "best.pt"
                if best.is_file():
                    self.tr_model.add_custom_path(str(best))
                    found += 1
        if found:
            self._log_info(tr("train.log.scan_found", count=found))
        else:
            self._log_warn(tr("train.log.scan_none"))

    def _reset_train_defaults(self):
        self._apply_config(TrainConfig())
        self._log_info(tr("train.log.defaults_reset"))

    def _refresh_history(self):
        self.cb_history.clear()
        res = Path(path_combo_get(self.tr_results) or ".")
        if not res.is_dir():
            return
        for name in sorted(list_experiments(str(res))):
            self.cb_history.addItem(name)

    def _on_augment_toggled(self, checked: bool):
        """启用/禁用数据增强时切换参数区域可用性。"""
        for attr_name in [
            "aug_hsv_h", "aug_hsv_s", "aug_hsv_v",
            "aug_degrees", "aug_translate", "aug_scale", "aug_shear",
            "aug_perspective", "aug_flipud", "aug_fliplr",
            "aug_mosaic", "aug_mixup", "aug_copy_paste",
        ]:
            getattr(self, attr_name).setEnabled(checked)

    # ── Presets ────────────────────────────────────────────

    def _get_current_config_dict(self):
        return {
            "data_yaml": path_combo_get(self.tr_data_yaml),
            "model_file": self.tr_model.current_model_path(),
            "results_dir": path_combo_get(self.tr_results),
            "log_dir": path_combo_get(self.tr_logs),
            "epochs": self.tr_epochs.value(),
            "imgsz": self.tr_imgsz.value(),
            "batch": self.tr_batch.value(),
            "device": self.tr_device.currentData() or get_default_device(),
            "experiment_name": self.tr_exp.text().strip(),
            "use_augment": self.tr_augment.isChecked(),
            "hsv_h": self.aug_hsv_h.value(),
            "hsv_s": self.aug_hsv_s.value(),
            "hsv_v": self.aug_hsv_v.value(),
            "degrees": self.aug_degrees.value(),
            "translate": self.aug_translate.value(),
            "scale": self.aug_scale.value(),
            "shear": self.aug_shear.value(),
            "perspective": self.aug_perspective.value(),
            "flipud": self.aug_flipud.value(),
            "fliplr": self.aug_fliplr.value(),
            "mosaic": self.aug_mosaic.value(),
            "mixup": self.aug_mixup.value(),
            "copy_paste": self.aug_copy_paste.value(),
        }

    def _apply_config_dict(self, d):
        self.tr_data_yaml.setCurrentText(d.get("data_yaml", ""))
        self.tr_model.set_model(d.get("model_file", ""))
        self.tr_results.setCurrentText(d.get("results_dir", ""))
        self.tr_logs.setCurrentText(d.get("log_dir", ""))
        self.tr_epochs.setValue(d.get("epochs", 150))
        self.tr_imgsz.setValue(d.get("imgsz", 640))
        self.tr_batch.setValue(d.get("batch", 16))
        dev = d.get("device", get_default_device())
        idx = self.tr_device.findData(dev)
        if idx >= 0:
            self.tr_device.setCurrentIndex(idx)
        else:
            self.tr_device.setCurrentIndex(0)
        self.tr_exp.setText(d.get("experiment_name", ""))
        self.tr_augment.setChecked(d.get("use_augment", True))
        self.aug_hsv_h.setValue(d.get("hsv_h", 0.015))
        self.aug_hsv_s.setValue(d.get("hsv_s", 0.7))
        self.aug_hsv_v.setValue(d.get("hsv_v", 0.4))
        self.aug_degrees.setValue(d.get("degrees", 0.0))
        self.aug_translate.setValue(d.get("translate", 0.1))
        self.aug_scale.setValue(d.get("scale", 0.5))
        self.aug_shear.setValue(d.get("shear", 0.0))
        self.aug_perspective.setValue(d.get("perspective", 0.0))
        self.aug_flipud.setValue(d.get("flipud", 0.0))
        self.aug_fliplr.setValue(d.get("fliplr", 0.5))
        self.aug_mosaic.setValue(d.get("mosaic", 1.0))
        self.aug_mixup.setValue(d.get("mixup", 0.0))
        self.aug_copy_paste.setValue(d.get("copy_paste", 0.0))
        self._refresh_history()

    def _refresh_preset_combo(self):
        self.cb_presets.blockSignals(True)
        self.cb_presets.clear()
        self.cb_presets.addItem(tr("train.combo.presets"))
        self._presets = load_presets()
        for name in sorted(self._presets.keys()):
            self.cb_presets.addItem(name)
        self.cb_presets.blockSignals(False)

    def _on_preset_selected(self, name):
        placeholder = tr("train.combo.presets")
        if not name or name == placeholder or name not in self._presets:
            return
        self._apply_config_dict(self._presets[name])
        self._log_info(tr("train.log.preset_loaded", name=name))

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
        self._log_info(tr("train.log.preset_saved", name=name))

    def _delete_preset(self):
        name = self.cb_presets.currentText()
        placeholder = tr("train.combo.presets")
        if not name or name == placeholder:
            QMessageBox.warning(self, tr("msg.title.hint"), tr("msg.select_experiment"))
            return
        if name in self._presets:
            del self._presets[name]
            save_presets(self._presets)
            self._refresh_preset_combo()
            self._log_info(tr("train.log.preset_deleted", name=name))

    # ── UI state ───────────────────────────────────────────

    def _set_train_ui_state(self, state: str) -> None:
        if state == "running":
            self.btn_start.setEnabled(False)
            self.btn_stop.setText(tr("train.btn.stop"))
            self.btn_stop.setProperty("i18nKey", "train.btn.stop")
            self.btn_stop.setEnabled(True)
            self.btn_stop.clicked.disconnect()
            self.btn_stop.clicked.connect(self._on_stop_train)
            self.tr_progress.setValue(0)
        elif state == "stopped":
            self.btn_start.setText(tr("train.btn.continue"))
            self.btn_start.setProperty("i18nKey", "train.btn.continue")
            self.btn_start.setEnabled(True)
            self.btn_stop.setText(tr("train.btn.end"))
            self.btn_stop.setProperty("i18nKey", "train.btn.end")
            self.btn_stop.setEnabled(True)
            self.rb_resume.setChecked(True)
            self.btn_stop.clicked.disconnect()
            self.btn_stop.clicked.connect(self._on_end_train)
        else:  # idle
            self.btn_start.setText(tr("train.btn.start"))
            self.btn_start.setProperty("i18nKey", "train.btn.start")
            self.btn_start.setEnabled(True)
            self.btn_stop.setText(tr("train.btn.stop"))
            self.btn_stop.setProperty("i18nKey", "train.btn.stop")
            self.btn_stop.setEnabled(False)
            self.rb_new.setChecked(True)
            self.btn_stop.clicked.disconnect()
            self.btn_stop.clicked.connect(self._on_stop_train)
            self.tr_progress.setRange(0, 100)
            self.tr_progress.setValue(0)
            self.tr_progress.setFormat(tr("train.progress.format"))

    # ── Config from UI ─────────────────────────────────────

    def _build_config_from_train_ui(self):
        c = TrainConfig()
        c.data_yaml = path_combo_get(self.tr_data_yaml)
        c.model_file = self.tr_model.current_model_path()
        c.results_dir = path_combo_get(self.tr_results)
        c.log_dir = path_combo_get(self.tr_logs)
        c.epochs = int(self.tr_epochs.value())
        c.imgsz = int(self.tr_imgsz.value())
        c.batch = int(self.tr_batch.value())
        c.device = self.tr_device.currentData() or get_default_device()
        c.experiment_name = self.tr_exp.text().strip() or c.experiment_name
        c.use_augment = self.tr_augment.isChecked()
        c.hsv_h = self.aug_hsv_h.value()
        c.hsv_s = self.aug_hsv_s.value()
        c.hsv_v = self.aug_hsv_v.value()
        c.degrees = self.aug_degrees.value()
        c.translate = self.aug_translate.value()
        c.scale = self.aug_scale.value()
        c.shear = self.aug_shear.value()
        c.perspective = self.aug_perspective.value()
        c.flipud = self.aug_flipud.value()
        c.fliplr = self.aug_fliplr.value()
        c.mosaic = self.aug_mosaic.value()
        c.mixup = self.aug_mixup.value()
        c.copy_paste = self.aug_copy_paste.value()
        return c

    # ── Train lifecycle ────────────────────────────────────

    @Slot()
    def _on_start_train(self):
        if self._train_worker and self._train_worker.isRunning():
            QMessageBox.warning(self, tr("msg.title.hint"), tr("msg.train_running"))
            return

        cfg = self._build_config_from_train_ui()
        use_aug = self.tr_augment.isChecked()

        if self.rb_new.isChecked():
            mode = 1
            mode_label = tr("train.msg.mode_new")
            if not self._model_file_ok(cfg.model_file):
                QMessageBox.critical(self, tr("msg.title.error"), f"{tr('msg.no_model')}\n{cfg.model_file}")
                return
            selected = None
            details = tr("train.msg.new_summary",
                         mode=mode_label, exp=cfg.experiment_name,
                         weights=cfg.model_file, data=cfg.data_yaml)
        elif self.rb_resume.isChecked():
            mode = 2
            mode_label = tr("train.msg.mode_resume")
            if not Path(cfg.last_pt).is_file():
                r = QMessageBox.question(
                    self, tr("msg.title.hint"),
                    f"{tr('msg.no_last_pt')}\n{cfg.last_pt}\n\n{tr('msg.fallback_new_train')}",
                    QMessageBox.Yes | QMessageBox.No,
                )
                if r != QMessageBox.Yes:
                    return
                mode = 1
                mode_label = tr("train.msg.mode_new_fallback")
                if not self._model_file_ok(cfg.model_file):
                    QMessageBox.critical(self, tr("msg.title.error"), f"{tr('msg.no_model')}\n{cfg.model_file}")
                    return
            selected = None
            weights_path = cfg.last_pt if mode == 2 else cfg.model_file
            details = tr("train.msg.resume_summary",
                         mode=mode_label, exp=cfg.experiment_name,
                         weights=weights_path, data=cfg.data_yaml)
        else:
            mode = 3
            mode_label = tr("train.msg.mode_finetune")
            selected = self.cb_history.currentText().strip()
            if not selected:
                QMessageBox.warning(self, tr("msg.title.hint"), tr("msg.no_history_selected"))
                return
            best = Path(cfg.results_dir) / selected / "weights" / "best.pt"
            if not best.is_file():
                QMessageBox.critical(self, tr("msg.title.error"), f"{tr('msg.no_best_pt')}\n{best}")
                return
            details = tr("train.msg.finetune_summary",
                         mode=mode_label, exp=cfg.experiment_name,
                         base=selected, weights=best, data=cfg.data_yaml)

        aug_status = tr("train.engine.augment_on") if use_aug else tr("train.engine.augment_off")
        summary = (
            f"{details}\n"
            f"{'─' * 40}\n"
            f"{tr('train.field.epochs')}:  {cfg.epochs:<6}  {tr('train.field.imgsz')}: {cfg.imgsz}\n"
            f"{tr('train.field.batch')}:   {cfg.batch:<6}  {tr('train.field.device')}: {cfg.device}\n"
            f"{aug_status}\n"
            f"{'─' * 40}\n"
            f"{tr('msg.title.confirm')}"
        )

        r = QMessageBox.question(
            self, tr("msg.title.confirm"), summary,
            QMessageBox.Yes | QMessageBox.No,
        )
        if r != QMessageBox.Yes:
            return

        self.tr_log.clear()
        self._log_info(tr("train.log.starting", name=cfg.experiment_name))
        self._log_info(tr("train.log.params", epochs=cfg.epochs, imgsz=cfg.imgsz, batch=cfg.batch, device=cfg.device))

        cmd = [
            sys.executable, str(REPO_ROOT / "gui" / "train_engine.py"),
            "--lang", current_lang(),
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
        self.tr_progress.setFormat(tr("train.progress.format"))

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
            self._log_warn(tr("train.log.stopping"))
            self._train_worker.stop()

    @Slot(str)
    def _on_train_failed(self, msg):
        self._log_err(tr("msg.title.failed"))
        self._log_append(self.tr_log, f'<span style="color:#ff6e6e;">{msg[:1500]}</span>')
        if not self._closing:
            QMessageBox.critical(self, tr("msg.title.failed"), msg[:2000])
        self._set_train_ui_state("idle")
        self._refresh_history()

    @Slot()
    def _on_train_done(self):
        self._log_good(tr("msg.train_done"))
        if not self._closing:
            QMessageBox.information(self, tr("msg.title.done"), tr("msg.train_done"))
        self._set_train_ui_state("idle")
        self._refresh_history()

    @Slot()
    def _on_train_stopped(self):
        self._log_warn(tr("train.log.paused"))
        self._set_train_ui_state("stopped")

    @Slot()
    def _on_end_train(self):
        self._log_info(tr("train.log.ended"))
        self._set_train_ui_state("idle")

    @Slot()
    def _on_train_thread_finished(self):
        if self._closing:
            QApplication.quit()
