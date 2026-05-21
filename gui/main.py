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
from PySide6.QtGui import QFont, QKeySequence, QShortcut, QTextCursor
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QSpinBox,
    QStackedWidget,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from gui.config import TrainConfig
from gui.device import get_available_devices, get_default_device
from gui.train_engine import list_experiments

from gui.styles import (
    CHECKBOX_STYLE,
    COMBO_STYLE,
    DARK_TOGGLE_STYLE,
    FONT_FAMILIES,
    FONT_SIZE,
    RADIO_STYLE,
    SPINNER_STYLE,
    TAB_WIDGET_STYLE,
    apply_theme_to_widgets,
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
from gui.model_selector import ModelSelector
from gui.workers import InferWorker, ToolWorker, TrainWorker
from gui.i18n import tr, set_language, apply_language, current_lang, AVAILABLE_LANGS


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
        self.setWindowTitle(tr("app.title"))
        self._closing = False
        self.resize(820, 700)
        self.setMinimumSize(720, 520)

        self._train_worker: TrainWorker | None = None
        self._infer_worker: InferWorker | None = None
        self._tool_worker: ToolWorker | None = None
        self._infer_defaults_done = False
        self._presets = load_presets()
        self._path_history: dict[str, list[str]] = {}

        self._tabs = QTabWidget()
        self._tabs.setProperty("themeClass", "tab_widget")
        self._tabs.setStyleSheet(TAB_WIDGET_STYLE)
        tab_keys = ["tab.train", "tab.infer", "tab.logs", "tab.tools"]
        self._tabs.addTab(self._build_train_tab(), tr(tab_keys[0]))
        self._tabs.tabBar().setTabData(0, tab_keys[0])
        self._tabs.addTab(self._build_infer_tab(), tr(tab_keys[1]))
        self._tabs.tabBar().setTabData(1, tab_keys[1])
        self._tabs.addTab(self._build_log_viewer_tab(), tr(tab_keys[2]))
        self._tabs.tabBar().setTabData(2, tab_keys[2])
        self._tabs.addTab(self._build_tools_tab(), tr(tab_keys[3]))
        self._tabs.tabBar().setTabData(3, tab_keys[3])

        self._dark_mode = False
        self._dark_btn = QPushButton("☀")
        self._dark_btn.setProperty("themeClass", "tiny_btn")
        self._dark_btn.setStyleSheet(DARK_TOGGLE_STYLE)
        self._dark_btn.setFixedSize(32, 32)
        self._dark_btn.clicked.connect(self._toggle_dark_mode)

        self._lang_combo = QComboBox()
        self._lang_combo.setProperty("themeClass", "combo")
        self._lang_combo.setStyleSheet(COMBO_STYLE)
        self._lang_combo.setMaximumWidth(90)
        for code, name in AVAILABLE_LANGS.items():
            self._lang_combo.addItem(name, code)
        self._lang_combo.setCurrentIndex(0)
        self._lang_combo.currentIndexChanged.connect(self._on_lang_changed)

        corner = QWidget()
        cl = QHBoxLayout(corner)
        cl.setContentsMargins(0, 0, 8, 0)
        cl.setSpacing(6)
        cl.addWidget(self._lang_combo)
        cl.addWidget(self._dark_btn)
        self._tabs.setCornerWidget(corner)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.addWidget(self._tabs)

        self._load_train_defaults()

        QShortcut(QKeySequence("Ctrl+Return"), self, self._on_ctrl_enter)

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
        header1.addWidget(section_label("路径", i18n_key="train.card.paths"))
        header1.addStretch()
        scan_models_btn = tiny_btn("扫描模型", i18n_key="train.btn.scan")
        scan_models_btn.clicked.connect(self._scan_trained_models)
        header1.addWidget(scan_models_btn)
        edit_yaml_btn = tiny_btn("编辑 data.yaml", i18n_key="train.btn.edit_yaml")
        edit_yaml_btn.clicked.connect(self._open_data_yaml)
        header1.addWidget(edit_yaml_btn)
        lay1.addLayout(header1)
        lay1.addSpacing(14)

        for key in ["data_yaml", "model", "results", "logs"]:
            self._path_history.setdefault(key, [])

        self.tr_data_yaml = path_combo(default="", history=self._path_history["data_yaml"])
        self.tr_model = ModelSelector()
        self.tr_results   = path_combo(default="", history=self._path_history["results"])
        self.tr_logs      = path_combo(default="", history=self._path_history["logs"])

        rows_data = [
            ("data.yaml", self.tr_data_yaml, "data_yaml", False, "YAML (*.yaml *.yml)"),
            ("结果目录", self.tr_results,   "results",    True,  None),
            ("日志目录", self.tr_logs,      "logs",       True,  None),
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

        # 初始权重 — 模型选择器
        model_row = QHBoxLayout()
        model_row.setSpacing(10)
        model_lbl = field_label("初始权重", i18n_key="train.field.init_weights")
        model_lbl.setFixedWidth(72)
        model_row.addWidget(model_lbl)
        model_row.addWidget(self.tr_model, 1)
        lay1.addLayout(model_row)
        lay1.addSpacing(8)

        outer.addWidget(card1)

        # ── 超参数卡片 ──
        card2, lay2 = card()
        lay2.addWidget(section_label("超参数", i18n_key="train.card.hyperparams"))
        lay2.addSpacing(14)

        self.tr_epochs = spinner(1, 100000, 150, 100)
        self.tr_imgsz  = spinner(32, 4096, 640, 100)
        self.tr_batch  = spinner(1, 1024, 16, 100)
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
        lay2.addSpacing(12)

        exp_row = QHBoxLayout()
        exp_row.setSpacing(10)
        exp_row.addWidget(field_label("实验名称", i18n_key="train.field.exp_name"))
        self.tr_exp = input_(min_width=320)
        exp_row.addWidget(self.tr_exp, 1)
        lay2.addLayout(exp_row)
        outer.addWidget(card2)

        # ── 训练模式卡片 ──
        card3, lay3 = card()
        lay3.addWidget(section_label("训练模式", i18n_key="train.card.mode"))
        lay3.addSpacing(12)

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
        outer.addWidget(card3)

        # ── 数据增强 ──
        self.tr_augment = QCheckBox(tr("train.augment"))
        self.tr_augment.setProperty("i18nKey", "train.augment")
        self.tr_augment.setChecked(True)
        self.tr_augment.setProperty("themeClass", "checkbox")
        self.tr_augment.setStyleSheet(CHECKBOX_STYLE)
        outer.addWidget(self.tr_augment)

        # ── 操作按钮行 ──
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
        outer.addLayout(btn_row)

        # ── 进度条 ──
        outer.addSpacing(4)
        self.tr_progress = progress_bar(i18n_key="train.progress.format")
        outer.addWidget(self.tr_progress)

        # ── 日志 ──
        outer.addWidget(field_label("输出", i18n_key="train.log.output"))
        self.tr_log = log_area()
        outer.addWidget(self.tr_log, 1)

        return scroll_area(w)

    # ═══════════════════════════════════════════════════════
    #  工具页
    # ═══════════════════════════════════════════════════════

    def _build_tools_tab(self):
        w = QWidget()
        w.setMinimumSize(560, 580)
        outer = QVBoxLayout(w)
        outer.setContentsMargins(24, 16, 24, 24)
        outer.setSpacing(10)

        # ── 数据集目录卡片 ──
        card1, lay1 = card()
        lay1.addWidget(section_label("数据集目录", i18n_key="tools.card.dataset"))
        lay1.addSpacing(14)

        self._path_history.setdefault("tool_dataset", [])
        self.tool_dataset = path_combo(default=str(ROOT / "data" / "dataset"),
                                       history=self._path_history["tool_dataset"])
        row = QHBoxLayout()
        row.setSpacing(10)
        row.addWidget(self.tool_dataset, 1)
        b = btn("浏览", primary=False, i18n_key="train.btn.browse")
        b.setFixedWidth(60)
        b.clicked.connect(lambda: self._browse(self.tool_dataset, True, None, "tool_dataset"))
        row.addWidget(b)
        lay1.addLayout(row)
        outer.addWidget(card1)

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
        outer.addWidget(card2)

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
        outer.addLayout(btn_row)

        # ── 输出 ──
        outer.addWidget(field_label("输出", i18n_key="tools.log.output"))
        self.tool_log = log_area()
        outer.addWidget(self.tool_log, 1)

        return scroll_area(w)

    def _on_tool_changed(self, idx):
        self.tool_params.setCurrentIndex(idx)

    TOOL_SCRIPTS = [
        "create_empty_labels.py",
        "split_train_val/split_random_with_labels.py",
        "split_train_val_test/split_random_with_labels.py",
        "split_train_val/split_every_5th_with_labels.py",
        "split_images_only/split_random_images_only.py",
        "split_images_only/split_every_5th_images_only.py",
    ]

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
        script = str(ROOT / "tools" / "dataset_tools" / script_rel)

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

    # ═══════════════════════════════════════════════════════
    #  日志 & 结果 页
    # ═══════════════════════════════════════════════════════

    def _build_log_viewer_tab(self):
        from gui.paths import LOG_DIR, RESULTS_DIR, PREDICT_DIR
        w = QWidget()
        w.setMinimumSize(560, 520)
        outer = QVBoxLayout(w)
        outer.setContentsMargins(24, 16, 24, 24)
        outer.setSpacing(10)

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
        outer.addWidget(card1)

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
        outer.addWidget(card2)

        # ── 日志内容 ──
        self.lv_log = log_area()
        outer.addWidget(self.lv_log, 1)

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
        outer.addWidget(card3)

        # ── 快捷目录 ──
        card4, lay4 = card()
        lay4.addWidget(section_label("快捷目录", i18n_key="logs.card.quick"))
        lay4.addSpacing(14)
        quick_row = QHBoxLayout()
        quick_row.setSpacing(10)
        btn_specs = [
            ("训练结果", RESULTS_DIR, "logs.btn.results"),
            ("推理结果", str(Path(PREDICT_DIR) / "predict_result"), "logs.btn.predictions"),
            ("数据集", str(ROOT / "data" / "dataset"), "logs.btn.dataset"),
        ]
        for label, path, i18n_key in btn_specs:
            b = btn(label, primary=False, i18n_key=i18n_key)
            b.clicked.connect(lambda checked, p=path: self._open_dir_safe(p))
            quick_row.addWidget(b)
        quick_row.addStretch()
        lay4.addLayout(quick_row)
        outer.addWidget(card4)

        return scroll_area(w)

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
        from gui.paths import RESULTS_DIR
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
        pass  # handled by button clicks below

    def _lv_exp_path(self):
        from gui.paths import RESULTS_DIR
        name = self.lv_exp_combo.currentText()
        placeholder = tr("logs.combo.exp_placeholder")
        if not name or name == placeholder:
            QMessageBox.warning(self, tr("msg.title.hint"), tr("msg.select_experiment"))
            return None
        return Path(RESULTS_DIR) / name

    def _open_lv_exp_dir(self):
        p = self._lv_exp_path()
        if p and p.is_dir():
            self._open_file_with_default_app(str(p))

    def _open_lv_weights(self):
        p = self._lv_exp_path()
        if p:
            wp = p / "weights"
            if wp.is_dir():
                self._open_file_with_default_app(str(wp))
            else:
                QMessageBox.warning(self, tr("msg.title.hint"), f"{tr('msg.weights_dir_not_found')}\n{wp}")

    def _open_lv_plot(self):
        p = self._lv_exp_path()
        if p:
            rp = p / "results.png"
            if rp.is_file():
                self._open_file_with_default_app(str(rp))
            else:
                QMessageBox.warning(self, tr("msg.title.hint"), tr("msg.plot_not_found"))
                if p.is_dir():
                    self._open_file_with_default_app(str(p))

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
        if Path(path).is_file():
            return True
        if path and os.sep not in path and "/" not in path:
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
        """跨平台用默认程序打开文件。"""
        import platform
        system = platform.system()
        if system == "Windows":
            os.startfile(path)
        elif system == "Darwin":
            subprocess.Popen(["open", path])
        else:
            subprocess.Popen(["xdg-open", path])

    def _toggle_dark_mode(self):
        self._dark_mode = not self._dark_mode
        self._dark_btn.setText("🌙" if self._dark_mode else "☀")
        apply_theme_to_widgets(self, self._dark_mode)

    def _on_lang_changed(self, idx):
        lang = self._lang_combo.itemData(idx)
        if lang:
            set_language(lang)
            apply_language(self)

    def _on_ctrl_enter(self):
        idx = self._tabs.currentIndex()
        if idx == 0:
            self._on_start_train()
        elif idx == 1:
            self._on_start_infer()

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
        self.tr_data_yaml.setCurrentText(c.data_yaml)
        self.tr_model.set_model(c.model_file)
        self.tr_results.setCurrentText(c.results_dir)
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

    # ── 预设 ──

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
        self._log_append(self.tr_log, f'<span style="color:#6ec6ff;">{tr("log.info_prefix")}</span>  {msg}')

    def _log_good(self, msg):
        self._log_append(self.tr_log, f'<span style="color:#50fa7b;">{tr("log.ok_prefix")}</span>  {msg}')

    def _log_warn(self, msg):
        self._log_append(self.tr_log, f'<span style="color:#ffb86c;">{tr("log.warn_prefix")}</span>  {msg}')

    def _log_err(self, msg):
        self._log_append(self.tr_log, f'<span style="color:#ff5555;">{tr("log.err_prefix")}</span>  {msg}')

    # ── 训练 ──

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
        return c

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
            sys.executable, str(ROOT / "gui" / "train_engine.py"),
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
        lay1.addWidget(section_label("推理配置", i18n_key="infer.card.config"))
        lay1.addSpacing(14)

        for key in ["ir_model", "ir_source", "ir_save"]:
            self._path_history.setdefault(key, [])

        self.ir_model  = path_combo(default="", history=self._path_history["ir_model"])
        self.ir_source = path_combo(default="", history=self._path_history["ir_source"])
        self.ir_save   = path_combo(default="", history=self._path_history["ir_save"])
        self.ir_conf   = input_(default="0.406", min_width=96)
        self.ir_imgsz  = spinner(32, 4096, 640, 96)

        ir_rows = [
            ("模型 .pt", self.ir_model,  "ir_model",  False, "权重 (*.pt *.pth *.onnx)", "infer.field.model"),
            ("输入源",   self.ir_source, "ir_source", True,  None, "infer.field.source"),
            ("保存目录", self.ir_save,   "ir_save",   True,  None, "infer.field.save"),
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
        outer.addWidget(card1)

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
        outer.addLayout(ir_btn_row)

        # ── 进度条 ──
        outer.addSpacing(4)
        self.ir_progress = progress_bar(i18n_key="infer.progress.format")
        self.ir_progress.setFormat(tr("infer.progress.format"))
        self.ir_progress.setVisible(False)
        outer.addWidget(self.ir_progress)
        self.ir_eta_label = QLabel("")
        self.ir_eta_label.setStyleSheet("font-size:11px; color:#8e8e93;")
        self.ir_eta_label.setVisible(False)
        outer.addWidget(self.ir_eta_label)

        outer.addWidget(field_label("输出", i18n_key="infer.log.output"))
        self.ir_log = log_area()
        outer.addWidget(self.ir_log, 1)

        return scroll_area(w)

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
            self._infer_start_time = __import__("time").time()
        else:  # idle
            self.btn_infer.setVisible(True)
            self.btn_stop_ir.setVisible(False)
            self.ir_progress.setVisible(False)
            self.ir_eta_label.setVisible(False)

    def closeEvent(self, event):
        if self._closing:
            event.accept()
            return
        self._closing = True
        self.hide()
        self._log_info(tr("train.log.exiting"))
        workers_running = False
        if self._train_worker and self._train_worker.isRunning():
            self._train_worker.stop()
            workers_running = True
        if self._infer_worker and self._infer_worker.isRunning():
            self._infer_worker.stop()
            workers_running = True
        if self._tool_worker and self._tool_worker.isRunning():
            self._tool_worker.stop()
            workers_running = True
        if not workers_running:
            QApplication.quit()
        event.ignore()

    # ── 历史日志 & 结果查看 ──

    @staticmethod
    def _open_dir_safe(path_str: str) -> None:
        p = Path(path_str)
        if p.is_dir():
            MainWindow._open_file_with_default_app(str(p))
        elif p.parent.is_dir():
            MainWindow._open_file_with_default_app(str(p.parent))

    @staticmethod
    def _load_csv_log(log_widget, csv_path: Path):
        import csv
        log_widget.clear()
        with open(csv_path, encoding="utf-8-sig") as f:
            reader = csv.reader(f)
            rows = list(reader)
        if not rows:
            MainWindow._log_append(log_widget,
                f'<span style="color:#6ec6ff;">{tr("log.info_prefix")}</span>  {tr("msg.log_empty")}')
            return
        MainWindow._log_append(log_widget,
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
        MainWindow._log_append(log_widget, html)

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
            sys.executable, str(ROOT / "gui" / "infer_engine.py"),
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
        import time
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
