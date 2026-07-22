# YOLO-LAB-GUI 训练增强 & 数据转换 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 重构 main.py 架构并新增数据增强精细控制、高级超参数面板、实时训练曲线、模型导出四大功能。

**Architecture:** 将单体 main.py（1542 行）拆分为 gui/tabs/*.py 独立标签页模块，保持 core/gui 两层分离。新增 matplotlib 嵌入式图表、5 种格式导出子进程引擎。

**Tech Stack:** Python 3.10+, PySide6 >= 6.5.0, Ultralytics >= 8.0.0, matplotlib >= 3.5.0, PyYAML >= 6

## Global Constraints

- Python 版本：3.10+
- PySide6 >= 6.5.0
- 所有 UI 文本必须通过 `gui/i18n.py` 的 `tr()` 函数，标签页组件设置 `i18nKey` 属性
- 训练/推理/导出等计算密集型操作必须在子进程中运行（QThread + subprocess.Popen）
- 保持 `core/` 包零 GUI 依赖（不导入 PySide6）
- 亮色/暗色主题切换通过 `apply_theme_to_widgets()` 递归遍历 widget 树
- 预设文件 `gui/presets.json` 向后兼容（新字段有默认值兜底）
- commit 信息格式：`feat: <description>` 或 `refactor: <description>`，末尾追加 `Co-Authored-By: Claude <noreply@anthropic.com>`

---

## Phase 1: 架构重构 — 拆分 main.py 为独立标签页模块

此阶段为纯重构，不改变任何功能行为。目标：将 1542 行的 main.py 拆分为 ~200 行的窗口骨架 + 6 个 gui/tabs/*.py 文件。

### Task 1.1: 创建 gui/tabs 包和标签页骨架文件

**Files:**
- Create: `gui/tabs/__init__.py`
- Create: `gui/tabs/infer_tab.py`
- Create: `gui/tabs/logs_tab.py`
- Create: `gui/tabs/tools_tab.py`
- Create: `gui/tabs/settings_tab.py`

**Interfaces:**
- Consumes: `main.py` 中的 `MainWindow` 类（读取现有代码）
- Produces: 4 个 `QWidget` 子类，每个含 `build_*_tab()` 方法对应的 UI 构建逻辑

- [ ] **Step 1: 创建 gui/tabs/__init__.py**

```python
"""YOLO-LAB-GUI tab modules — each tab is a standalone QWidget subclass."""
```

- [ ] **Step 2: 创建 gui/tabs/infer_tab.py — 从 main.py 提取推理页代码**

从 `main.py` 的 `_build_infer_tab()` 方法（第 1254-1336 行）及相关方法提取：

```python
"""Inference tab — model prediction on images/video."""
from __future__ import annotations

import time
from pathlib import Path

from PySide6.QtCore import Qt, Slot
from PySide6.QtWidgets import (
    QFileDialog, QHBoxLayout, QLabel, QMessageBox, QVBoxLayout, QWidget,
)

from core.config import TrainConfig
from gui.paths import BEST_SEG_MODEL, PREDICT_DIR, TEST_IMAGES_DIR
from gui.styles import SPINNER_STYLE
from gui.widgets import (
    btn, card, danger_btn, field_label, input_, log_area,
    path_combo, path_combo_get, progress_bar, scroll_area,
    section_label, spinner,
)
from gui.workers import InferWorker
from gui.i18n import tr


class InferTab(QWidget):
    """Inference configuration and execution tab."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._infer_worker: InferWorker | None = None
        self._infer_defaults_done = False
        self._path_history: dict[str, list[str]] = {}
        self._build_ui()

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

    # All slot methods copied from MainWindow:
    # _browse, _add_to_history, _refresh_combo_history,
    # _log_append, _log_info_ir, _set_infer_ui_state,
    # _on_start_infer, _append_infer_log, _on_infer_progress,
    # _on_stop_infer, _on_infer_failed, _on_infer_done,
    # _on_infer_stopped, _on_infer_thread_finished,
    # _model_file_ok, showEvent
```

- [ ] **Step 3: 创建 gui/tabs/logs_tab.py — 从 main.py 提取日志页代码**

从 `main.py` 的 `_build_log_viewer_tab()`（第 620-716 行）及相关方法提取。

- [ ] **Step 4: 创建 gui/tabs/tools_tab.py — 从 main.py 提取工具页代码**

从 `main.py` 的 `_build_tools_tab()`（第 376-487 行）及相关方法提取。

- [ ] **Step 5: 创建 gui/tabs/settings_tab.py — 从 main.py 提取设置页代码**

从 `main.py` 的 `_build_settings_tab()`（第 590-614 行）提取。

- [ ] **Step 6: Commit**

```bash
git add gui/tabs/
git commit -m "refactor: extract infer/logs/tools/settings tabs into gui/tabs/ modules

Co-Authored-By: Claude <noreply@anthropic.com>"
```

### Task 1.2: 创建 gui/tabs/train_tab.py — 提取训练页（最大模块）

**Files:**
- Create: `gui/tabs/train_tab.py`

**Interfaces:**
- Consumes: `main.py` 中 `MainWindow` 类的训练页所有方法（第 164-370 行 + 第 876-1249 行）
- Produces: `TrainTab(QWidget)` — 含完整训练页 UI、预设管理、训练启停逻辑

- [ ] **Step 1: 创建 gui/tabs/train_tab.py**

从 `main.py` 提取以下方法到 `TrainTab` 类：
- `_build_train_tab()` → `_build_ui()`
- `_load_train_defaults()`, `_refresh_devices()`, `_apply_config()`
- `_scan_trained_models()`, `_reset_train_defaults()`, `_refresh_history()`
- `_get_current_config_dict()`, `_apply_config_dict()`
- `_refresh_preset_combo()`, `_on_preset_selected()`, `_save_preset()`, `_delete_preset()`
- `_build_config_from_train_ui()`, `_on_start_train()`
- `_append_train_log()`, `_on_train_progress()`, `_on_stop_train()`
- `_on_train_failed()`, `_on_train_done()`, `_on_train_stopped()`, `_on_end_train()`
- `_on_train_thread_finished()`, `_set_train_ui_state()`
- `_open_data_yaml()`, `_browse()`, `_add_to_history()`, `_refresh_combo_history()`
- `_model_file_ok()`, `_log_append()`, `_log_info()`, `_log_good()`, `_log_warn()`, `_log_err()`
- `_open_file_with_default_app()`, `_open_dir_safe()`, `_load_csv_log()`

保留 `self.tr_*` 控件引用、`self._train_worker`、`self._presets`、`self._path_history`。

`TrainTab.__init__` 参数需接收从 `MainWindow` 传入的共享依赖：
```python
class TrainTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._train_worker: TrainWorker | None = None
        self._presets: dict = {}
        self._path_history: dict[str, list[str]] = {}
        self._build_ui()
        self._load_train_defaults()
```

- [ ] **Step 2: Commit**

```bash
git add gui/tabs/train_tab.py
git commit -m "refactor: extract train tab into gui/tabs/train_tab.py

Co-Authored-By: Claude <noreply@anthropic.com>"
```

### Task 1.3: 精简 main.py — 组装标签页

**Files:**
- Modify: `main.py` — 从 ~1542 行精简为 ~200 行窗口骨架

**Interfaces:**
- Consumes: 所有 6 个标签页模块 + 共享组件（ModelSelector、styles、widgets、i18n）
- Produces: `MainWindow(QWidget)` — 组装标签页、主题/语言切换、Ctrl+Enter 快捷键、closeEvent

- [ ] **Step 1: 重写 main.py**

```python
"""
YOLO 分割训练 / 推理桌面界面 — Apple 风格简约设计
启动：在项目根目录执行  python main.py
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

PRESET_FILE = ROOT / "gui" / "presets.json"

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QApplication, QComboBox, QHBoxLayout, QPushButton,
    QTabWidget, QVBoxLayout, QWidget,
)

from gui.styles import (
    COMBO_STYLE, DARK_TOGGLE_STYLE, FONT_FAMILIES, FONT_SIZE,
    TAB_WIDGET_STYLE, apply_theme_to_widgets,
)
from gui.i18n import tr, set_language, apply_language, current_lang, AVAILABLE_LANGS
from gui.tabs.train_tab import TrainTab
from gui.tabs.infer_tab import InferTab
from gui.tabs.logs_tab import LogsTab
from gui.tabs.tools_tab import ToolsTab
from gui.tabs.settings_tab import SettingsTab


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


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(tr("app.title"))
        self._closing = False
        screen_h = QApplication.primaryScreen().availableGeometry().height()
        self.resize(820, int(screen_h * 0.75))
        self.setMinimumSize(720, 520)

        self._presets = load_presets()

        # ── 标签页 ──
        self._tabs = QTabWidget()
        self._tabs.setProperty("themeClass", "tab_widget")
        self._tabs.setStyleSheet(TAB_WIDGET_STYLE)

        self._train_tab = TrainTab()
        self._infer_tab = InferTab()
        self._logs_tab = LogsTab()
        self._tools_tab = ToolsTab()
        self._settings_tab = SettingsTab()

        tab_defs = [
            (self._train_tab,    "tab.train"),
            (self._infer_tab,    "tab.infer"),
            (self._logs_tab,     "tab.logs"),
            (self._tools_tab,    "tab.tools"),
            (self._settings_tab, "tab.settings"),
        ]
        for i, (widget, key) in enumerate(tab_defs):
            self._tabs.addTab(widget, tr(key))
            self._tabs.tabBar().setTabData(i, key)

        # ── 角落控件 ──
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

        # ── 快捷键 ──
        QShortcut(QKeySequence("Ctrl+Return"), self, self._on_ctrl_enter)

    # ── 主题 / 语言 ──

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
            self._train_tab._on_start_train()
        elif idx == 1:
            self._infer_tab._on_start_infer()

    # ── 关闭 ──

    def closeEvent(self, event):
        if self._closing:
            event.accept()
            return
        self._closing = True
        self.hide()
        workers_running = False
        if self._train_tab._train_worker and self._train_tab._train_worker.isRunning():
            self._train_tab._train_worker.stop()
            workers_running = True
        if self._infer_tab._infer_worker and self._infer_tab._infer_worker.isRunning():
            self._infer_tab._infer_worker.stop()
            workers_running = True
        if self._tools_tab._tool_worker and self._tools_tab._tool_worker.isRunning():
            self._tools_tab._tool_worker.stop()
            workers_running = True
        if not workers_running:
            QApplication.quit()
        event.ignore()


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
```

- [ ] **Step 2: 验证重构后应用正常启动**

```bash
cd ~/YOLO-LAB-GUI && python -c "from gui.tabs.train_tab import TrainTab; from gui.tabs.infer_tab import InferTab; from gui.tabs.logs_tab import LogsTab; from gui.tabs.tools_tab import ToolsTab; from gui.tabs.settings_tab import SettingsTab; print('All tab imports OK')"
```

- [ ] **Step 3: Commit**

```bash
git add main.py
git commit -m "refactor: shrink main.py to ~200-line skeleton, delegate to gui/tabs/

Co-Authored-By: Claude <noreply@anthropic.com>"
```

### Task 1.4: 路径历史 & 预设管理集中化

**Files:**
- Modify: `main.py`
- Modify: `gui/tabs/train_tab.py`

**Interfaces:**
- Consumes: 分散在各标签页的 `_path_history` 字典
- Produces: `MainWindow` 持有集中的 `_path_history`，标签页通过构造函数接收引用

- [ ] **Step 1: 将路径历史集中到 MainWindow**

在 `MainWindow.__init__` 中初始化 `self._path_history: dict[str, list[str]] = {}`，并在创建 TrainTab 时传入：

```python
# In MainWindow.__init__:
self._path_history: dict[str, list[str]] = {}
self._train_tab = TrainTab(path_history=self._path_history)
# similarly for other tabs
```

- [ ] **Step 2: 修改 TrainTab 构造函数**

```python
class TrainTab(QWidget):
    def __init__(self, parent=None, path_history: dict[str, list[str]] | None = None):
        super().__init__(parent)
        self._path_history = path_history if path_history is not None else {}
```

- [ ] **Step 3: 运行并确认无回归**

```bash
cd ~/YOLO-LAB-GUI && timeout 3 python main.py 2>&1 || true
```

- [ ] **Step 4: Commit**

```bash
git add main.py gui/tabs/train_tab.py
git commit -m "refactor: centralize path history in MainWindow

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## Phase 2: TrainConfig + build_train_kwargs 扩展

### Task 2.1: 扩展 TrainConfig 数据类

**Files:**
- Modify: `core/config.py` — 新增 9 个字段

**Interfaces:**
- Produces: `TrainConfig` 新增字段供后续 Phase 使用
- 向后兼容：所有新字段有默认值，旧 preset.json 加载不报错

- [ ] **Step 1: 在 TrainConfig 中添加新字段**

在 `core/config.py` 的 `TrainConfig` dataclass 中，`multi_scale` 行之后添加：

```python
    # === optimization & learning rate schedule ===
    optimizer: str = "AdamW"        # SGD / Adam / AdamW / RMSProp
    momentum: float = 0.937
    weight_decay: float = 0.0005
    lrf: float = 0.01               # final lr = lr0 * lrf
    cos_lr: bool = True             # cosine LR scheduler
    warmup_epochs: float = 3.0
    warmup_momentum: float = 0.8

    # === regularization ===
    dropout: float = 0.0            # classification head dropout
    label_smoothing: float = 0.0
```

- [ ] **Step 2: 验证导入和数据类实例化**

```bash
cd ~/YOLO-LAB-GUI && python -c "
from core.config import TrainConfig
c = TrainConfig()
print(f'optimizer={c.optimizer}, lr0={c.lr0}, cos_lr={c.cos_lr}')
print('TrainConfig OK')
"
```

- [ ] **Step 3: Commit**

```bash
git add core/config.py
git commit -m "feat: add optimizer/lr-schedule/regularization fields to TrainConfig

Co-Authored-By: Claude <noreply@anthropic.com>"
```

### Task 2.2: 扩展 build_train_kwargs

**Files:**
- Modify: `core/training.py` — `build_train_kwargs()` 函数添加新 kwargs 键

**Interfaces:**
- Consumes: `TrainConfig` 新字段
- Produces: `model.train()` 接收的新 kwargs

- [ ] **Step 1: 在 build_train_kwargs 中添加新参数**

在 `core/training.py` 的 `build_train_kwargs()` 函数中，`"multi_scale": config.multi_scale,` 之后添加：

```python
        "optimizer": config.optimizer,
        "momentum": config.momentum,
        "weight_decay": config.weight_decay,
        "lrf": config.lrf,
        "cos_lr": config.cos_lr,
        "warmup_epochs": config.warmup_epochs,
        "warmup_momentum": config.warmup_momentum,
        "dropout": config.dropout,
        "label_smoothing": config.label_smoothing,
```

- [ ] **Step 2: 验证 build_train_kwargs 返回完整字典**

```bash
cd ~/YOLO-LAB-GUI && python -c "
from core.config import TrainConfig
from core.training import build_train_kwargs
c = TrainConfig()
c.data_yaml = '/tmp/test.yaml'
kwargs = build_train_kwargs(c, use_augment=False)
assert 'optimizer' in kwargs
assert 'cos_lr' in kwargs
assert 'dropout' in kwargs
print(f'Total kwargs: {len(kwargs)} keys')
print('build_train_kwargs OK')
"
```

- [ ] **Step 3: Commit**

```bash
git add core/training.py
git commit -m "feat: pass new optimizer/regularization params to model.train()

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## Phase 3: 数据增强面板

### Task 3.1: 在 TrainTab 中添加数据增强面板

**Files:**
- Modify: `gui/tabs/train_tab.py` — 在 QSplitter 中插入新卡片面板

**Interfaces:**
- Consumes: 现有的 `resizable_card`, `spinner`, `field_label` 工厂函数
- Produces: 第 3 个 QSplitter 面板（在超参数和训练模式之间）—— 数据增强区域

- [ ] **Step 1: 在 TrainTab._build_ui() 中添加增强面板**

在超参数卡片之后、训练模式卡片之前插入以下代码：

```python
        # ── Panel 3: 数据增强 ──
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
```

需要在 `_build_train_tab` 方法开头定义辅助函数：

```python
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
```

- [ ] **Step 2: 添加 _on_augment_toggled 方法**

```python
    def _on_augment_toggled(self, checked: bool):
        """启用/禁用数据增强时切换参数区域可用性。"""
        for attr_name in [
            "aug_hsv_h", "aug_hsv_s", "aug_hsv_v",
            "aug_degrees", "aug_translate", "aug_scale", "aug_shear",
            "aug_perspective", "aug_flipud", "aug_fliplr",
            "aug_mosaic", "aug_mixup", "aug_copy_paste",
        ]:
            getattr(self, attr_name).setEnabled(checked)
```

- [ ] **Step 3: 更新 _get_current_config_dict() 和 _apply_config_dict()**

`_get_current_config_dict()` 新增增强参数：
```python
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
```

`_apply_config_dict()` 对应读取这些键（使用 `d.get(key, default)` 兜底）。

- [ ] **Step 4: 更新 _build_config_from_train_ui()**

在返回 `cfg` 之前赋值所有增强字段：
```python
    cfg.hsv_h = self.aug_hsv_h.value()
    cfg.hsv_s = self.aug_hsv_s.value()
    # ... etc for all 12 params
```

- [ ] **Step 5: 确认 QSplitter 面板数量调整**

训练页 QSplitter 从 4 个面板变为 5 个，默认 sizes 更新：
```python
splitter.setSizes([200, 180, 170, 130, 220])  # paths, hyperparams, augment, mode, monitor
```

- [ ] **Step 6: Commit**

```bash
git add gui/tabs/train_tab.py
git commit -m "feat: add data augmentation panel with all 12 params to train tab

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## Phase 4: 高级超参数面板

### Task 4.1: 添加可折叠高级超参数区域

**Files:**
- Modify: `gui/tabs/train_tab.py` — 在超参数卡片中添加可折叠区域
- Modify: `gui/widgets.py` — 新增 `collapsible_section()` 工厂函数

**Interfaces:**
- Consumes: 现有超参数面板卡片的 `lay2` 布局
- Produces: 可折叠的高级参数区域，带平滑动画

- [ ] **Step 1: 在 gui/widgets.py 添加可折叠组件函数**

```python
from PySide6.QtCore import QAbstractAnimation, QEasingCurve, QParallelAnimationGroup, QPropertyAnimation
from PySide6.QtWidgets import QSizePolicy, QToolButton


def collapsible_section(title: str, i18n_key: str = "",
                        parent: QWidget | None = None) -> tuple[QWidget, QToolButton, QWidget, QVBoxLayout]:
    """可折叠区域：点击标题按钮展开/收起内容区域。

    Returns (container, toggle_button, content_widget, content_layout)
    """
    container = QWidget(parent)
    container.setStyleSheet("background: transparent; border: none;")

    outer = QVBoxLayout(container)
    outer.setContentsMargins(0, 0, 0, 0)
    outer.setSpacing(0)

    # 切换按钮
    btn = QToolButton()
    display = tr(i18n_key) if i18n_key else title
    btn.setText(f"▸ {display}")
    btn.setProperty("i18nKey", i18n_key)
    btn.setToolButtonStyle(Qt.ToolButtonTextOnly)
    btn.setStyleSheet(
        "QToolButton { background: transparent; border: none; font-size: 12px; "
        "color: #6e6e73; font-weight: 500; padding: 4px 0; }"
        "QToolButton:hover { color: #0071e3; }"
    )
    btn.setCheckable(True)
    btn.setChecked(False)
    outer.addWidget(btn)

    # 内容区域
    content = QWidget()
    content.setStyleSheet("background: transparent; border: none;")
    content.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
    content.setMaximumHeight(0)
    content_layout = QVBoxLayout(content)
    content_layout.setContentsMargins(0, 8, 0, 4)
    content_layout.setSpacing(6)
    outer.addWidget(content)

    # 动画
    btn.toggled.connect(lambda checked: _animate_collapse(content, checked, btn))

    return container, btn, content, content_layout


def _animate_collapse(content: QWidget, expand: bool, btn: QToolButton) -> None:
    """展开/收起动画：通过 QPropertyAnimation 过渡 maxHeight。"""
    import math

    content.setUpdatesEnabled(False)

    # 计算内容实际高度
    content.setMaximumHeight(2000)  # 临时解除限制测量真实高度
    target_h = content.sizeHint().height() if expand else 0

    anim = QPropertyAnimation(content, b"maximumHeight")
    anim.setDuration(250)
    anim.setStartValue(content.maximumHeight() if not expand else 0)
    anim.setEndValue(target_h)
    anim.setEasingCurve(QEasingCurve.Type.OutCubic)

    # 更新按钮文本箭头
    display = btn.text()
    if expand:
        btn.setText(display.replace("▸", "▾"))
    else:
        btn.setText(display.replace("▾", "▸"))

    def on_finished():
        content.setUpdatesEnabled(True)
        if not expand:
            content.setMaximumHeight(0)

    anim.finished.connect(on_finished)
    anim.start()
```

- [ ] **Step 2: 在 TrainTab._build_ui 的超参数卡片中添加高级区域**

在 `lay2` 底部（实验名称行之后）插入：

```python
        lay2.addSpacing(6)
        coll, self._adv_toggle, self._adv_content, adv_lay = collapsible_section(
            "高级参数", i18n_key="train.adv.title")
        lay2.addWidget(coll)

        adv_grid = QHBoxLayout()
        adv_grid.setSpacing(20)

        # 学习率 & 优化器列
        col_lr = QVBoxLayout()
        col_lr.setSpacing(4)
        col_lr.addWidget(field_label("学习率 & 优化器", i18n_key="train.adv.lr_opt"))
        self.adv_lr0 = _adv_spin(0.0005, 0.0, 0.1, 0.0001, "train.adv.lr0")
        self.adv_lrf = _adv_spin(0.01, 0.0, 1.0, 0.001, "train.adv.lrf")
        self.adv_momentum = _adv_spin(0.937, 0.0, 1.0, 0.001, "train.adv.momentum")
        self.adv_weight_decay = _adv_spin(0.0005, 0.0, 0.1, 0.0001, "train.adv.weight_decay")

        self.adv_optimizer = simple_combo(min_width=120, font_size=13)
        self.adv_optimizer.addItems(["AdamW", "SGD", "Adam", "RMSProp"])
        self.adv_optimizer.setCurrentText("AdamW")
        self.adv_optimizer.setProperty("i18nKey", "train.adv.optimizer")

        self.adv_cos_lr = QCheckBox(tr("train.adv.cos_lr"))
        self.adv_cos_lr.setChecked(True)
        self.adv_cos_lr.setProperty("i18nKey", "train.adv.cos_lr")
        self.adv_cos_lr.setProperty("themeClass", "checkbox")
        self.adv_cos_lr.setStyleSheet(CHECKBOX_STYLE)

        for lbl_key, w in [
            ("train.adv.lr0", self.adv_lr0), ("train.adv.lrf", self.adv_lrf),
            ("train.adv.momentum", self.adv_momentum), ("train.adv.weight_decay", self.adv_weight_decay),
        ]:
            col_lr.addWidget(_adv_row(lbl_key, w))
        col_lr.addWidget(_adv_row("train.adv.optimizer", self.adv_optimizer))
        col_lr.addWidget(self.adv_cos_lr)
        col_lr.addStretch()
        adv_grid.addLayout(col_lr)

        # 正则化 & 策略列
        col_reg = QVBoxLayout()
        col_reg.setSpacing(4)
        col_reg.addWidget(field_label("正则化 & 策略", i18n_key="train.adv.reg_strategy"))
        self.adv_close_mosaic = _adv_spin(10, 0, 100, 1, "train.adv.close_mosaic")
        self.adv_multi_scale = _adv_spin(0.5, 0.0, 1.0, 0.1, "train.adv.multi_scale")
        self.adv_dropout = _adv_spin(0.0, 0.0, 0.5, 0.05, "train.adv.dropout")
        self.adv_label_smoothing = _adv_spin(0.0, 0.0, 0.2, 0.01, "train.adv.label_smoothing")
        self.adv_warmup_epochs = _adv_spin(3.0, 0.0, 50.0, 0.5, "train.adv.warmup_epochs")
        self.adv_warmup_momentum = _adv_spin(0.8, 0.0, 1.0, 0.05, "train.adv.warmup_momentum")

        for lbl_key, w in [
            ("train.adv.close_mosaic", self.adv_close_mosaic),
            ("train.adv.multi_scale", self.adv_multi_scale),
            ("train.adv.dropout", self.adv_dropout),
            ("train.adv.label_smoothing", self.adv_label_smoothing),
            ("train.adv.warmup_epochs", self.adv_warmup_epochs),
            ("train.adv.warmup_momentum", self.adv_warmup_momentum),
        ]:
            col_reg.addWidget(_adv_row(lbl_key, w))
        col_reg.addStretch()
        adv_grid.addLayout(col_reg)

        adv_lay.addLayout(adv_grid)
```

辅助函数（在 `_build_ui` 内部定义）：
```python
    def _adv_spin(default, min_v, max_v, step, i18n_key):
        s = QDoubleSpinBox()
        s.setRange(min_v, max_v)
        s.setValue(default)
        s.setSingleStep(step)
        s.setDecimals(4)
        s.setMinimumWidth(90)
        s.setProperty("i18nKey", i18n_key)
        s.setProperty("themeClass", "spinner")
        s.setStyleSheet(SPINNER_STYLE)
        return s

    def _adv_row(label_key, widget):
        row = QHBoxLayout()
        row.setSpacing(6)
        lbl = field_label("", i18n_key=label_key)
        lbl.setFixedWidth(90)
        row.addWidget(lbl)
        row.addWidget(widget)
        row.addStretch()
        return row
```

- [ ] **Step 3: 更新 _get_current_config_dict / _apply_config_dict / _build_config_from_train_ui**

在 `_get_current_config_dict()` 中添加高级参数字典：
```python
    "optimizer": self.adv_optimizer.currentText(),
    "lr0": self.adv_lr0.value(),
    "lrf": self.adv_lrf.value(),
    "momentum": self.adv_momentum.value(),
    "weight_decay": self.adv_weight_decay.value(),
    "cos_lr": self.adv_cos_lr.isChecked(),
    "warmup_epochs": self.adv_warmup_epochs.value(),
    "warmup_momentum": self.adv_warmup_momentum.value(),
    "close_mosaic": int(self.adv_close_mosaic.value()),
    "multi_scale": self.adv_multi_scale.value(),
    "dropout": self.adv_dropout.value(),
    "label_smoothing": self.adv_label_smoothing.value(),
```

对应更新 `_apply_config_dict()` 和 `_build_config_from_train_ui()`。

注意：`lr0` 现在由高级参数区域的 `adv_lr0` 控制，原有的基础参数区域的 `lr0` 不再单独存在（Ultralytics 默认值 0.01 vs 0.0005 需要统一）。当前的 `tr_epochs/imgsz/batch/device` 保持不变。

- [ ] **Step 4: Commit**

```bash
git add gui/tabs/train_tab.py gui/widgets.py
git commit -m "feat: add collapsible advanced hyperparameter panel

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## Phase 5: 实时训练曲线

### Task 5.1: 创建 TrainingChart 组件

**Files:**
- Create: `gui/charts/__init__.py`
- Create: `gui/charts/training_chart.py`

**Interfaces:**
- Consumes: `matplotlib.backends.backend_qtagg.FigureCanvasQTAgg`
- Produces: `TrainingChart(QWidget)` — 含上下两个子图（Loss + mAP），`append_metrics()` 方法，主题适配

- [ ] **Step 1: Create gui/charts/__init__.py**

```python
"""Real-time training charts using matplotlib embedded in Qt."""
from gui.charts.training_chart import TrainingChart
```

- [ ] **Step 2: Create gui/charts/training_chart.py**

```python
"""
Real-time training curves — embedded matplotlib FigureCanvas in a QWidget.
"""
from __future__ import annotations

import time
from collections import deque

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QSizePolicy, QVBoxLayout, QWidget

import matplotlib
matplotlib.use("QtAgg")

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

MAX_POINTS = 500  # keep at most N data points per curve
DRAW_INTERVAL_MS = 500  # throttle redraws


class TrainingChart(QWidget):
    """Real-time training metrics chart with loss and mAP subplots."""

    COLORS = {
        "box_loss": "#4da6ff",
        "seg_loss": "#50fa7b",
        "cls_loss": "#ffb86c",
        "dfl_loss": "#ff79c6",
        "mAP50": "#ff5555",
        "mAP50-95": "#f1fa8c",
    }

    def __init__(self, parent=None, dark_mode: bool = False):
        super().__init__(parent)
        self._dark = dark_mode
        self._epochs: list[int] = []
        self._data: dict[str, deque[tuple[int, float]]] = {
            "box_loss": deque(maxlen=MAX_POINTS),
            "seg_loss": deque(maxlen=MAX_POINTS),
            "cls_loss": deque(maxlen=MAX_POINTS),
            "dfl_loss": deque(maxlen=MAX_POINTS),
            "mAP50": deque(maxlen=MAX_POINTS),
            "mAP50-95": deque(maxlen=MAX_POINTS),
        }
        self._last_draw = 0.0

        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setMinimumSize(300, 240)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._fig = Figure(figsize=(5, 4), dpi=100)
        self._apply_bg_color()

        self._ax_loss = self._fig.add_subplot(211)
        self._ax_map = self._fig.add_subplot(212, sharex=self._ax_loss)

        self._init_axes()

        self._canvas = FigureCanvas(self._fig)
        self._canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        layout.addWidget(self._canvas)

        self._fig.tight_layout(pad=2.0)

        # 节流重绘定时器
        self._draw_timer = QTimer(self)
        self._draw_timer.setInterval(DRAW_INTERVAL_MS)
        self._draw_timer.timeout.connect(self._do_redraw)
        self._draw_timer.start()

    def _apply_bg_color(self):
        """Apply dark/light background colors."""
        if self._dark:
            self._fig.patch.set_facecolor("#1e1e1e")
        else:
            self._fig.patch.set_facecolor("#fafafa")

    def _init_axes(self):
        """Configure both subplots with legends."""
        fg = "#e0e0e0" if self._dark else "#333333"
        grid_c = "#444" if self._dark else "#ddd"
        bg = "#2d2d2d" if self._dark else "#ffffff"

        for ax in (self._ax_loss, self._ax_map):
            ax.set_facecolor(bg)
            ax.tick_params(colors=fg, labelsize=8)
            ax.spines["bottom"].set_color(grid_c)
            ax.spines["left"].set_color(grid_c)
            ax.spines["top"].set_visible(False)
            ax.spines["right"].set_visible(False)
            ax.grid(True, color=grid_c, linewidth=0.5, alpha=0.5)

        self._ax_loss.set_ylabel("Loss", color=fg, fontsize=9)
        self._ax_map.set_ylabel("mAP", color=fg, fontsize=9)
        self._ax_map.set_xlabel("Epoch", color=fg, fontsize=9)

        # 初始化空曲线
        self._lines: dict[str, object] = {}
        for key, color in self.COLORS.items():
            ax = self._ax_loss if "mAP" not in key else self._ax_map
            (line,) = ax.plot([], [], color=color, linewidth=1.2, label=key, alpha=0.85)
            self._lines[key] = line

        self._ax_loss.legend(
            loc="upper right", fontsize=7,
            facecolor=bg, edgecolor=grid_c,
            labelcolor=fg, framealpha=0.8,
        )
        self._ax_map.legend(
            loc="upper right", fontsize=7,
            facecolor=bg, edgecolor=grid_c,
            labelcolor=fg, framealpha=0.8,
        )

    def set_dark_mode(self, dark: bool):
        """Switch between dark and light theme."""
        self._dark = dark
        self._apply_bg_color()
        self._init_axes()
        self._do_redraw()

    def append_metrics(self, epoch: int, box_loss: float | None = None,
                       seg_loss: float | None = None, cls_loss: float | None = None,
                       dfl_loss: float | None = None, mAP50: float | None = None,
                       mAP50_95: float | None = None):
        """Add one epoch's metrics.  Only stores non-None values."""
        if box_loss is not None:
            self._data["box_loss"].append((epoch, box_loss))
        if seg_loss is not None:
            self._data["seg_loss"].append((epoch, seg_loss))
        if cls_loss is not None:
            self._data["cls_loss"].append((epoch, cls_loss))
        if dfl_loss is not None:
            self._data["dfl_loss"].append((epoch, dfl_loss))
        if mAP50 is not None:
            self._data["mAP50"].append((epoch, mAP50))
        if mAP50_95 is not None:
            self._data["mAP50-95"].append((epoch, mAP50_95))

    def _do_redraw(self):
        """Throttled redraw: update line data and refresh canvas."""
        now = time.monotonic()
        if now - self._last_draw < DRAW_INTERVAL_MS / 1500:
            return
        self._last_draw = now

        for key, line in self._lines.items():
            points = self._data[key]
            if points:
                xs, ys = zip(*points)
                line.set_data(xs, ys)
            else:
                line.set_data([], [])

        # 调整子图范围
        for ax in (self._ax_loss, self._ax_map):
            ax.relim()
            ax.autoscale_view(scalex=True, scaley=True)

        self._canvas.draw_idle()

    def reset(self):
        """Clear all data and reset chart."""
        for key in self._data:
            self._data[key].clear()
        for line in self._lines.values():
            line.set_data([], [])
        for ax in (self._ax_loss, self._ax_map):
            ax.relim()
            ax.autoscale_view()
        self._canvas.draw_idle()

    def closeEvent(self, event):
        self._draw_timer.stop()
        super().closeEvent(event)
```

- [ ] **Step 3: Verify chart module imports**

```bash
cd ~/YOLO-LAB-GUI && python -c "
from gui.charts.training_chart import TrainingChart
print('TrainingChart import OK')
"
```

- [ ] **Step 4: Commit**

```bash
git add gui/charts/
git commit -m "feat: add real-time matplotlib training chart component

Co-Authored-By: Claude <noreply@anthropic.com>"
```

### Task 5.2: 增强 TrainWorker 指标解析

**Files:**
- Modify: `gui/workers.py` — `TrainWorker._on_line()` 增加 metrics 行解析

**Interfaces:**
- Consumes: Ultralytics stdout epoch 行（`1/150  2.5G  1.234  1.567  ...`）
- Produces: 新信号 `metrics_update(dict)` — `{epoch: int, box_loss: float, ...}`

- [ ] **Step 1: 在 _BaseWorker 或 TrainWorker 中添加 metrics_update 信号**

在 `gui/workers.py` 的 `TrainWorker` 类中添加：

```python
class TrainWorker(_BaseWorker):
    progress = Signal(int)
    metrics_update = Signal(dict)  # 🆕 epoch metrics dict

    def _on_line(self, line: str) -> None:
        # 现有 progress 解析 ...
        m = re.search(r"\b(\d+)\s*/\s*(\d+)\b", line)
        # ... 现有逻辑 ...

        # 🆕 metrics 行解析
        self._parse_metrics_line(line)

    def _parse_metrics_line(self, line: str) -> None:
        """Parse Ultralytics per-epoch metrics from stdout table rows.

        Example line:
             1/150       2.5G      1.234      1.567     0.891      1.012         12        640
        """
        import re as _re

        m = _re.match(
            r"^\s*(\d+)\s*/\s*(\d+)\s+"    # epoch/total
            r"[\d.]+[GM]?\s+"               # GPU_mem
            r"([\d.]+)\s+"                  # box_loss
            r"([\d.]+)\s+"                  # seg_loss
            r"([\d.]+)\s+"                  # cls_loss
            r"([\d.]+)\s+"                  # dfl_loss
            r"\d+\s+"                       # Instances
            r"\d+",                         # Size
            line,
        )
        if not m:
            return

        try:
            epoch = int(m.group(1))
            total = int(m.group(2))
            metrics = {
                "epoch": epoch,
                "total_epochs": total,
                "box_loss": float(m.group(3)),
                "seg_loss": float(m.group(4)),
                "cls_loss": float(m.group(5)),
                "dfl_loss": float(m.group(6)),
            }
            self.metrics_update.emit(metrics)
        except (ValueError, IndexError):
            pass  # skip unparseable rows silently
```

- [ ] **Step 2: Commit**

```bash
git add gui/workers.py
git commit -m "feat: add metrics_update signal parsing to TrainWorker

Co-Authored-By: Claude <noreply@anthropic.com>"
```

### Task 5.3: 将曲线图表集成到 TrainTab 监控面板

**Files:**
- Modify: `gui/tabs/train_tab.py` — 监控面板底部改为 曲线/日志 左右分栏

**Interfaces:**
- Consumes: `TrainingChart`, `TrainWorker.metrics_update`
- Produces: QSplitter 水平分栏（曲线 | 日志）

- [ ] **Step 1: 导入 TrainingChart**

```python
from gui.charts.training_chart import TrainingChart
```

- [ ] **Step 2: 在 TrainTab._build_ui() 的监控面板中替换布局**

在进度条之后：

```python
        # ── 曲线 / 日志 水平分栏 ──
        self._chart_splitter = QSplitter(Qt.Horizontal)
        self._chart_splitter.setChildrenCollapsible(False)
        self._chart_splitter.setHandleWidth(4)
        self._chart_splitter.setStyleSheet("QSplitter::handle { background: #d0d0d0; }")

        self._train_chart = TrainingChart(dark_mode=False)
        self._chart_splitter.addWidget(self._train_chart)

        log_container = QWidget()
        log_layout = QVBoxLayout(log_container)
        log_layout.setContentsMargins(0, 0, 0, 0)
        self.tr_log = log_area()

        # 日志工具栏（清空/导出按钮可选）
        log_layout.addWidget(self.tr_log)

        self._chart_splitter.addWidget(log_container)
        self._chart_splitter.setSizes([400, 360])

        bottom_layout.addWidget(self._chart_splitter, 1)
```

- [ ] **Step 3: 在 _on_start_train 中连接 metrics_update 信号**

```python
    self._train_worker = TrainWorker(cmd)
    self._train_worker.log_line.connect(self._append_train_log)
    self._train_worker.progress.connect(self._on_train_progress)
    self._train_worker.metrics_update.connect(self._on_train_metrics)  # 🆕
    # ...
```

- [ ] **Step 4: 添加 _on_train_metrics slot**

```python
    @Slot(dict)
    def _on_train_metrics(self, metrics: dict):
        """Update real-time training chart with new epoch metrics."""
        self._train_chart.append_metrics(
            epoch=metrics.get("epoch", 0),
            box_loss=metrics.get("box_loss"),
            seg_loss=metrics.get("seg_loss"),
            cls_loss=metrics.get("cls_loss"),
            dfl_loss=metrics.get("dfl_loss"),
        )
```

- [ ] **Step 5: 训练开始/结束时重置图表**

在 `_set_train_ui_state("running")` 中添加 `self._train_chart.reset()`。
在 `_set_train_ui_state("idle")` 中不做操作（保留图表供复查）。

- [ ] **Step 6: 主题切换时更新图表**

TrainTab 需暴露 `set_dark_mode()` 方法供 MainWindow 调用：

```python
    def set_dark_mode(self, dark: bool):
        if hasattr(self, '_train_chart'):
            self._train_chart.set_dark_mode(dark)
```

MainWindow 的 `_toggle_dark_mode()` 中追加：
```python
    self._train_tab.set_dark_mode(self._dark_mode)
```

- [ ] **Step 7: Commit**

```bash
git add gui/tabs/train_tab.py main.py
git commit -m "feat: integrate real-time training chart into monitor panel

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## Phase 6: 数据转换页（模型导出）

### Task 6.1: 创建 core/export.py

**Files:**
- Create: `core/export.py`

**Interfaces:**
- Produces: `ExportConfig` dataclass, `EXPORT_FORMATS` 元数据字典

- [ ] **Step 1: 创建 core/export.py**

```python
"""Model export logic — format-agnostic, shared across repos."""
from dataclasses import dataclass, field


# Format metadata: (display_name, emoji, description, ultralytics_format_key)
EXPORT_FORMATS: dict[str, dict] = {
    "onnx": {
        "key": "onnx",
        "emoji": "⚡",
        "desc_key": "export.format.onnx_desc",
        "suffix": ".onnx",
    },
    "engine": {
        "key": "engine",
        "emoji": "🚀",
        "desc_key": "export.format.engine_desc",
        "suffix": ".engine",
    },
    "openvino": {
        "key": "openvino",
        "emoji": "🔵",
        "desc_key": "export.format.openvino_desc",
        "suffix": "_openvino_model/",
    },
    "coreml": {
        "key": "coreml",
        "emoji": "🍎",
        "desc_key": "export.format.coreml_desc",
        "suffix": ".mlpackage",
    },
    "tflite": {
        "key": "tflite",
        "emoji": "📱",
        "desc_key": "export.format.tflite_desc",
        "suffix": ".tflite",
    },
}


@dataclass
class ExportConfig:
    model_path: str = ""
    format: str = "onnx"                # onnx / engine / openvino / coreml / tflite
    imgsz: int = 640
    output_dir: str = ""

    # ONNX options
    opset: int = 12
    dynamic: bool = True
    simplify: bool = True
    nms: bool = False

    # TensorRT options
    fp16: bool = False
    int8: bool = False
    workspace: float = 4.0              # GB


def build_export_kwargs(cfg: ExportConfig) -> dict:
    """Build kwargs dict for model.export() from ExportConfig."""
    kwargs: dict = {
        "format": cfg.format,
        "imgsz": cfg.imgsz,
    }
    if cfg.format == "onnx":
        kwargs["opset"] = cfg.opset
        kwargs["dynamic"] = cfg.dynamic
        kwargs["simplify"] = cfg.simplify
        if cfg.nms:
            kwargs["nms"] = True
    elif cfg.format == "engine":
        kwargs["half"] = cfg.fp16
        kwargs["int8"] = cfg.int8
        kwargs["workspace"] = cfg.workspace
    elif cfg.format == "openvino":
        kwargs["int8"] = cfg.int8
        if hasattr(cfg, "dynamic"):
            kwargs["dynamic"] = cfg.dynamic
    elif cfg.format == "coreml":
        if cfg.nms:
            kwargs["nms"] = True
    elif cfg.format == "tflite":
        kwargs["int8"] = cfg.int8
        if cfg.fp16:
            kwargs["half"] = True
    return kwargs
```

- [ ] **Step 2: Commit**

```bash
git add core/export.py
git commit -m "feat: add core/export.py with ExportConfig and format definitions

Co-Authored-By: Claude <noreply@anthropic.com>"
```

### Task 6.2: 创建 gui/export_engine.py

**Files:**
- Create: `gui/export_engine.py`

**Interfaces:**
- Consumes: CLI 参数（`--model`, `--format`, `--imgsz`, ...）
- Produces: 子进程脚本，调用 `model.export()` 并输出日志

- [ ] **Step 1: 创建 gui/export_engine.py**

```python
"""
Model export engine — subprocess entry point for model format conversion.

Usage: python gui/export_engine.py --model best.pt --format onnx --imgsz 640 --output-dir ./exports
"""
import sys
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ultralytics import YOLO
from core.export import ExportConfig, build_export_kwargs


def parse_args():
    p = argparse.ArgumentParser(description="YOLO model export engine")
    p.add_argument("--model", required=True)
    p.add_argument("--format", default="onnx", choices=["onnx", "engine", "openvino", "coreml", "tflite"])
    p.add_argument("--imgsz", type=int, default=640)
    p.add_argument("--output-dir", default="")
    p.add_argument("--opset", type=int, default=12)
    p.add_argument("--dynamic", action="store_true", default=True)
    p.add_argument("--no-dynamic", action="store_false", dest="dynamic")
    p.add_argument("--simplify", action="store_true", default=True)
    p.add_argument("--no-simplify", action="store_false", dest="simplify")
    p.add_argument("--nms", action="store_true", default=False)
    p.add_argument("--fp16", action="store_true", default=False)
    p.add_argument("--int8", action="store_true", default=False)
    p.add_argument("--workspace", type=float, default=4.0)
    p.add_argument("--lang", default="zh")
    return p.parse_args()


def main():
    args = parse_args()

    # i18n
    _locale_dir = Path(__file__).resolve().parent.parent / "locales"
    from core.i18n import load_locale, t as _t
    loc = load_locale(_locale_dir, args.lang)

    cfg = ExportConfig(
        model_path=args.model,
        format=args.format,
        imgsz=args.imgsz,
        output_dir=args.output_dir,
        opset=args.opset,
        dynamic=args.dynamic,
        simplify=args.simplify,
        nms=args.nms,
        fp16=args.fp16,
        int8=args.int8,
        workspace=args.workspace,
    )

    print(_t(loc, "export.engine.loading", model=cfg.model_path))
    model = YOLO(cfg.model_path)

    task = getattr(model, "task", "detect")
    print(_t(loc, "export.engine.task", task=task))

    if cfg.output_dir:
        Path(cfg.output_dir).mkdir(parents=True, exist_ok=True)

    kwargs = build_export_kwargs(cfg)

    print(_t(loc, "export.engine.exporting", format=cfg.format, imgsz=cfg.imgsz))
    try:
        result_path = model.export(**kwargs)
        print(_t(loc, "export.engine.done", path=result_path))
    except Exception as e:
        print(_t(loc, "export.engine.failed", err=str(e)))
        sys.exit(1)


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Commit**

```bash
git add gui/export_engine.py
git commit -m "feat: add model export engine subprocess script

Co-Authored-By: Claude <noreply@anthropic.com>"
```

### Task 6.3: 创建 ExportWorker

**Files:**
- Modify: `gui/workers.py` — 添加 `ExportWorker` 类

**Interfaces:**
- Consumes: `_BaseWorker`
- Produces: `ExportWorker` — 纯日志输出的子进程 worker

- [ ] **Step 1: 添加 ExportWorker**

```python
class ExportWorker(_BaseWorker):
    """在子进程中运行模型导出脚本，仅输出日志。"""
```

`ExportWorker` 继承 `_BaseWorker`，无需额外逻辑（导出无进度百分比解析，纯文本日志即可）。

- [ ] **Step 2: Commit**

```bash
git add gui/workers.py
git commit -m "feat: add ExportWorker for model export subprocess

Co-Authored-By: Claude <noreply@anthropic.com>"
```

### Task 6.4: 创建 gui/tabs/export_tab.py

**Files:**
- Create: `gui/tabs/export_tab.py`
- Modify: `gui/widgets.py` — 添加 `export_format_card()` 工厂函数
- Modify: `gui/styles.py` — 添加导出卡片选中样式

- [ ] **Step 1: 在 gui/styles.py 添加导出卡片样式**

```python
# 在 COMBO_SIMPLE_STYLE 之后添加
EXPORT_CARD_STYLE = (
    "QFrame { background: #ffffff; border: 1px solid #d0d0d0; border-radius: 8px; }"
    "QFrame:hover { border: 1px solid #0071e3; }"
)

EXPORT_CARD_SELECTED_STYLE = (
    "QFrame { background: rgba(0,113,227,0.08); border: 2px solid #0071e3; border-radius: 8px; }"
)
```

- [ ] **Step 2: 在 gui/widgets.py 添加 export_format_card()**

```python
def export_format_card(format_key: str, emoji: str, name: str, desc: str,
                       parent: QWidget | None = None) -> QFrame:
    """Clickable export format card — styled for Apple-like selection UI."""
    card_w = QFrame(parent)
    card_w.setProperty("format_key", format_key)
    card_w.setFixedSize(140, 80)
    card_w.setCursor(Qt.PointingHandCursor)
    card_w.setStyleSheet(
        "QFrame { background: #ffffff; border: 1px solid #d0d0d0; border-radius: 10px; }"
        "QFrame:hover { border: 1px solid #0071e3; }"
    )

    layout = QVBoxLayout(card_w)
    layout.setContentsMargins(12, 10, 12, 10)
    layout.setSpacing(4)

    emoji_lbl = QLabel(f"{emoji}")
    emoji_lbl.setStyleSheet("font-size: 22px; border: none; background: transparent;")
    layout.addWidget(emoji_lbl)

    name_lbl = QLabel(name)
    name_lbl.setStyleSheet("font-size: 13px; font-weight: 600; color: #1d1d1f; border: none; background: transparent;")
    layout.addWidget(name_lbl)

    desc_lbl = QLabel(desc)
    desc_lbl.setStyleSheet("font-size: 10px; color: #8e8e93; border: none; background: transparent;")
    desc_lbl.setWordWrap(True)
    layout.addWidget(desc_lbl)

    layout.addStretch()
    return card_w
```

- [ ] **Step 3: 创建 gui/tabs/export_tab.py**

```python
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

    def __init__(self, parent=None):
        super().__init__(parent)
        self._export_worker: ExportWorker | None = None
        self._selected_format: str = "onnx"
        self._path_history: dict[str, list[str]] = {}
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
```

- [ ] **Step 2: 在 main.py 中注册导出标签页**

```python
# 在 MainWindow.__init__ 中添加：
from gui.tabs.export_tab import ExportTab

self._export_tab = ExportTab()
tab_defs = [
    (self._train_tab,    "tab.train"),
    (self._infer_tab,    "tab.infer"),
    (self._export_tab,   "tab.export"),  # 🆕 在第 3 位
    (self._logs_tab,     "tab.logs"),
    (self._tools_tab,    "tab.tools"),
    (self._settings_tab, "tab.settings"),
]
```

同时更新 `closeEvent` 添加 `self._export_tab._export_worker` 的停止逻辑。

- [ ] **Step 3: 验证导入**

```bash
cd ~/YOLO-LAB-GUI && python -c "
from gui.tabs.export_tab import ExportTab
from gui.export_engine import main as export_main
from core.export import ExportConfig, EXPORT_FORMATS
print('Export module chain OK')
"
```

- [ ] **Step 4: Commit**

```bash
git add gui/tabs/export_tab.py gui/widgets.py gui/styles.py main.py
git commit -m "feat: add model export tab with 5 format support

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## Phase 7: 国际化翻译补充

### Task 7.1: 补充所有 locale 文件的新增翻译键

**Files:**
- Modify: `locales/zh.json`
- Modify: `locales/en.json`
- Modify: `locales/fr.json`
- Modify: `locales/es.json`

**Interfaces:**
- Consumes: 所有新增 UI 文本的翻译键
- Produces: 4 种语言完整覆盖

- [ ] **Step 1: 在 zh.json 中添加新键（插入到文件末尾的 `}` 之前）**

```json
  "tab.export": "数据转换",

  "train.card.augment": "数据增强",
  "train.aug.color": "颜色抖动",
  "train.aug.geometry": "几何变换",
  "train.aug.mixing": "混合策略",
  "train.aug.hsv_h": "HSV-H",
  "train.aug.hsv_s": "HSV-S",
  "train.aug.hsv_v": "HSV-V",
  "train.aug.degrees": "旋转°",
  "train.aug.translate": "平移",
  "train.aug.scale": "缩放",
  "train.aug.shear": "剪切",
  "train.aug.perspective": "透视",
  "train.aug.flipud": "上下翻转",
  "train.aug.fliplr": "左右翻转",
  "train.aug.mosaic": "Mosaic",
  "train.aug.mixup": "MixUp",
  "train.aug.copy_paste": "复制粘贴",

  "train.adv.title": "高级参数",
  "train.adv.lr_opt": "学习率 & 优化器",
  "train.adv.reg_strategy": "正则化 & 策略",
  "train.adv.lr0": "LR0",
  "train.adv.lrf": "LRF",
  "train.adv.momentum": "Momentum",
  "train.adv.weight_decay": "Weight Decay",
  "train.adv.optimizer": "Optimizer",
  "train.adv.cos_lr": "余弦退火",
  "train.adv.close_mosaic": "关闭 Mosaic",
  "train.adv.multi_scale": "多尺度",
  "train.adv.dropout": "Dropout",
  "train.adv.label_smoothing": "标签平滑",
  "train.adv.warmup_epochs": "Warmup Epochs",
  "train.adv.warmup_momentum": "Warmup Momentum",

  "train.chart.title": "训练曲线",
  "train.chart.loss": "Loss 曲线",
  "train.chart.map": "mAP 曲线",

  "export.card.source": "源模型",
  "export.card.format": "导出格式",
  "export.card.options": "导出选项",
  "export.card.output": "输出目录",
  "export.field.model": "模型文件",
  "export.btn.start": "导出模型",
  "export.btn.stop": "取消",
  "export.opt.imgsz": "Imgsz",
  "export.opt.opset": "Opset",
  "export.opt.dynamic": "动态 Batch",
  "export.opt.simplify": "简化模型",
  "export.opt.nms": "NMS",
  "export.opt.workspace": "Workspace (GB)",

  "export.format.onnx_desc": "通用推理部署",
  "export.format.engine_desc": "NVIDIA GPU 最快推理",
  "export.format.openvino_desc": "Intel CPU/GPU 优化",
  "export.format.coreml_desc": "Apple 设备部署",
  "export.format.tflite_desc": "移动端 / 边缘设备",

  "export.engine.loading": "加载模型: {model}",
  "export.engine.task": "检测到任务类型: {task}",
  "export.engine.exporting": "正在导出 {format} (imgsz={imgsz})…",
  "export.engine.done": "导出完成: {path}",
  "export.engine.failed": "导出失败: {err}"
```

- [ ] **Step 2: 在 en.json 中添加对应英文翻译**

```json
  "tab.export": "Export",

  "train.card.augment": "Augmentation",
  "train.aug.color": "Color Jitter",
  "train.aug.geometry": "Geometric",
  "train.aug.mixing": "Mixing",
  "train.aug.hsv_h": "HSV-H",
  "train.aug.hsv_s": "HSV-S",
  "train.aug.hsv_v": "HSV-V",
  "train.aug.degrees": "Rotate°",
  "train.aug.translate": "Translate",
  "train.aug.scale": "Scale",
  "train.aug.shear": "Shear",
  "train.aug.perspective": "Perspective",
  "train.aug.flipud": "Flip U-D",
  "train.aug.fliplr": "Flip L-R",
  "train.aug.mosaic": "Mosaic",
  "train.aug.mixup": "MixUp",
  "train.aug.copy_paste": "Copy-Paste",

  "train.adv.title": "Advanced",
  "train.adv.lr_opt": "LR & Optimizer",
  "train.adv.reg_strategy": "Regularization & Strategy",
  "train.adv.lr0": "LR0",
  "train.adv.lrf": "LRF",
  "train.adv.momentum": "Momentum",
  "train.adv.weight_decay": "Weight Decay",
  "train.adv.optimizer": "Optimizer",
  "train.adv.cos_lr": "Cosine LR",
  "train.adv.close_mosaic": "Close Mosaic",
  "train.adv.multi_scale": "Multi-Scale",
  "train.adv.dropout": "Dropout",
  "train.adv.label_smoothing": "Label Smooth",
  "train.adv.warmup_epochs": "Warmup Epochs",
  "train.adv.warmup_momentum": "Warmup Momentum",

  "train.chart.title": "Curves",
  "train.chart.loss": "Loss",
  "train.chart.map": "mAP",

  "export.card.source": "Source Model",
  "export.card.format": "Export Format",
  "export.card.options": "Export Options",
  "export.card.output": "Output Directory",
  "export.field.model": "Model File",
  "export.btn.start": "Export Model",
  "export.btn.stop": "Cancel",
  "export.opt.imgsz": "Imgsz",
  "export.opt.opset": "Opset",
  "export.opt.dynamic": "Dynamic Batch",
  "export.opt.simplify": "Simplify",
  "export.opt.nms": "NMS",
  "export.opt.workspace": "Workspace (GB)",

  "export.format.onnx_desc": "Universal inference",
  "export.format.engine_desc": "NVIDIA GPU fastest",
  "export.format.openvino_desc": "Intel CPU/GPU optimized",
  "export.format.coreml_desc": "Apple device deployment",
  "export.format.tflite_desc": "Mobile / Edge devices",

  "export.engine.loading": "Loading model: {model}",
  "export.engine.task": "Detected task: {task}",
  "export.engine.exporting": "Exporting {format} (imgsz={imgsz})...",
  "export.engine.done": "Export done: {path}",
  "export.engine.failed": "Export failed: {err}"
```

- [ ] **Step 3: 在 fr.json 中添加对应翻译**

```json
  "tab.export": "Conversion",
  "train.card.augment": "Augmentation",
  "train.aug.color": "Couleur",
  "train.aug.geometry": "Géométrie",
  "train.aug.mixing": "Mélange",
  "train.aug.hsv_h": "HSV-H",
  "train.aug.hsv_s": "HSV-S",
  "train.aug.hsv_v": "HSV-V",
  "train.aug.degrees": "Rotation°",
  "train.aug.translate": "Translation",
  "train.aug.scale": "Échelle",
  "train.aug.shear": "Cisaillement",
  "train.aug.perspective": "Perspective",
  "train.aug.flipud": "Flip H-B",
  "train.aug.fliplr": "Flip G-D",
  "train.aug.mosaic": "Mosaic",
  "train.aug.mixup": "MixUp",
  "train.aug.copy_paste": "Copier-Coller",
  "train.adv.title": "Avancé",
  "train.adv.lr_opt": "LR & Optimiseur",
  "train.adv.reg_strategy": "Régularisation",
  "train.adv.lr0": "LR0",
  "train.adv.lrf": "LRF",
  "train.adv.momentum": "Momentum",
  "train.adv.weight_decay": "Weight Decay",
  "train.adv.optimizer": "Optimiseur",
  "train.adv.cos_lr": "Cosinus LR",
  "train.adv.close_mosaic": "Fermer Mosaic",
  "train.adv.multi_scale": "Multi-Échelle",
  "train.adv.dropout": "Dropout",
  "train.adv.label_smoothing": "Label Smooth",
  "train.adv.warmup_epochs": "Warmup Epochs",
  "train.adv.warmup_momentum": "Warmup Mom.",
  "export.card.source": "Modèle Source",
  "export.card.format": "Format d'Export",
  "export.card.options": "Options",
  "export.card.output": "Dossier de Sortie",
  "export.field.model": "Fichier Modèle",
  "export.btn.start": "Exporter",
  "export.btn.stop": "Annuler",
  "export.opt.imgsz": "Imgsz",
  "export.opt.opset": "Opset",
  "export.opt.dynamic": "Batch Dynamique",
  "export.opt.simplify": "Simplifier",
  "export.opt.nms": "NMS",
  "export.format.onnx_desc": "Inférence universelle",
  "export.format.engine_desc": "NVIDIA GPU le plus rapide",
  "export.format.openvino_desc": "Optimisé Intel CPU/GPU",
  "export.format.coreml_desc": "Déploiement Apple",
  "export.format.tflite_desc": "Mobile / Edge",
  "export.engine.loading": "Chargement: {model}",
  "export.engine.task": "Tâche détectée: {task}",
  "export.engine.exporting": "Export {format} (imgsz={imgsz})...",
  "export.engine.done": "Export terminé: {path}",
  "export.engine.failed": "Échec: {err}"
```

- [ ] **Step 4: 在 es.json 中添加对应翻译**

```json
  "tab.export": "Conversión",
  "train.card.augment": "Aumento",
  "train.aug.color": "Color",
  "train.aug.geometry": "Geometría",
  "train.aug.mixing": "Mezcla",
  "train.aug.hsv_h": "HSV-H",
  "train.aug.hsv_s": "HSV-S",
  "train.aug.hsv_v": "HSV-V",
  "train.aug.degrees": "Rotación°",
  "train.aug.translate": "Traslación",
  "train.aug.scale": "Escala",
  "train.aug.shear": "Cizalla",
  "train.aug.perspective": "Perspectiva",
  "train.aug.flipud": "Volteo V",
  "train.aug.fliplr": "Volteo H",
  "train.aug.mosaic": "Mosaic",
  "train.aug.mixup": "MixUp",
  "train.aug.copy_paste": "Copiar-Pegar",
  "train.adv.title": "Avanzado",
  "train.adv.lr_opt": "LR y Optimizador",
  "train.adv.reg_strategy": "Regularización",
  "train.adv.lr0": "LR0",
  "train.adv.lrf": "LRF",
  "train.adv.momentum": "Momentum",
  "train.adv.weight_decay": "Weight Decay",
  "train.adv.optimizer": "Optimizador",
  "train.adv.cos_lr": "LR Coseno",
  "train.adv.close_mosaic": "Cerrar Mosaic",
  "train.adv.multi_scale": "Multi-Escala",
  "train.adv.dropout": "Dropout",
  "train.adv.label_smoothing": "Suavizado Etq.",
  "train.adv.warmup_epochs": "Épocas Calent.",
  "train.adv.warmup_momentum": "Mom. Calent.",
  "export.card.source": "Modelo Fuente",
  "export.card.format": "Formato Exportación",
  "export.card.options": "Opciones",
  "export.card.output": "Directorio Salida",
  "export.field.model": "Archivo Modelo",
  "export.btn.start": "Exportar",
  "export.btn.stop": "Cancelar",
  "export.opt.imgsz": "Imgsz",
  "export.opt.opset": "Opset",
  "export.opt.dynamic": "Batch Dinámico",
  "export.opt.simplify": "Simplificar",
  "export.opt.nms": "NMS",
  "export.format.onnx_desc": "Inferencia universal",
  "export.format.engine_desc": "NVIDIA GPU más rápido",
  "export.format.openvino_desc": "Optimizado Intel CPU/GPU",
  "export.format.coreml_desc": "Despliegue Apple",
  "export.format.tflite_desc": "Móvil / Edge",
  "export.engine.loading": "Cargando: {model}",
  "export.engine.task": "Tarea detectada: {task}",
  "export.engine.exporting": "Exportando {format} (imgsz={imgsz})...",
  "export.engine.done": "Exportación completa: {path}",
  "export.engine.failed": "Error: {err}"
```

- [ ] **Step 4: 验证 JSON 文件格式正确**

```bash
cd ~/YOLO-LAB-GUI && python -c "
import json
for lang in ['zh', 'en', 'fr', 'es']:
    with open(f'locales/{lang}.json', 'r') as f:
        data = json.load(f)
    print(f'{lang}: {len(data)} keys')
"
```

- [ ] **Step 5: Commit**

```bash
git add locales/
git commit -m "feat: add i18n keys for augmentation, advanced params, export tab

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## Phase 8: 设置页扩展（可选）

### Task 8.1: 扩展设置页

**Files:**
- Modify: `gui/tabs/settings_tab.py` — 添加更多设置选项

**Interfaces:**
- Consumes: `MainWindow._dark_mode`, `MainWindow._splitter`
- Produces: 设置页包含默认路径配置、面板重置

- [ ] **Step 1: 在 SettingsTab 中添加默认路径配置**

在现有面板重置按钮基础上，添加：

```python
    # ── 默认路径 ──
    card2, lay2 = card()
    lay2.addWidget(section_label("默认路径", i18n_key="settings.card.defaults"))
    lay2.addSpacing(12)

    # 数据集默认目录
    ds_row = QHBoxLayout()
    ds_row.setSpacing(10)
    ds_row.addWidget(field_label("数据集", i18n_key="settings.field.dataset_dir"))
    self.default_dataset = path_combo(default=str(ROOT / "data" / "dataset"))
    ds_row.addWidget(self.default_dataset, 1)
    lay2.addLayout(ds_row)

    # 模型缓存目录
    model_row = QHBoxLayout()
    model_row.setSpacing(10)
    model_row.addWidget(field_label("模型缓存", i18n_key="settings.field.model_dir"))
    self.default_model_dir = path_combo(default=str(ROOT / "pretrained_models"))
    model_row.addWidget(self.default_model_dir, 1)
    lay2.addLayout(model_row)

    lay2.addSpacing(12)
    save_defaults_btn = btn("保存默认值", primary=False, i18n_key="settings.btn.save_defaults")
    save_defaults_btn.clicked.connect(self._save_defaults)
    lay2.addWidget(save_defaults_btn)

    outer.addWidget(card2)
```

- [ ] **Step 2: Commit**

```bash
git add gui/tabs/settings_tab.py
git commit -m "feat: expand settings tab with default path configuration

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## Post-Implementation Validation

完成所有 8 个 Phase 后，执行以下集成验证：

- [ ] **启动验证**: `timeout 5 python main.py 2>&1` — 窗口正常出现，无 crash
- [ ] **导入验证**: 所有 6 个标签页可独立导入
- [ ] **训练页面板拖拽**: QSplitter 5 个面板可拖拽调整比例
- [ ] **高级参数折叠**: 点击展开/收起有动画效果
- [ ] **增强开关**: 关闭后参数区域 disabled
- [ ] **实时曲线**: 嵌入在训练页底部，左右分栏可拖拽
- [ ] **导出页**: 5 张格式卡片可点击切换，参数面板跟随变化
- [ ] **语言切换**: 中英法西切换后所有新文本正确
- [ ] **暗色模式**: 切换后曲线图背景跟随
- [ ] **preset 兼容**: 旧 preset.json 加载不报错
- [ ] **Ctrl+Enter**: 训练页和推理页快捷键正常
