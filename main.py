"""
YOLO 分割训练 / 推理桌面界面 — Apple 风格简约设计
启动：在项目根目录执行  python main.py
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

PRESET_FILE = ROOT / "gui" / "presets.json"

from PySide6.QtGui import QFont, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QApplication, QComboBox, QHBoxLayout, QPushButton,
    QTabWidget, QVBoxLayout, QWidget,
)

from gui.styles import (
    COMBO_STYLE, DARK_TOGGLE_STYLE, FONT_FAMILIES, FONT_SIZE,
    TAB_WIDGET_STYLE, apply_theme_to_widgets,
)
from gui.i18n import tr, set_language, apply_language, AVAILABLE_LANGS
from gui.tabs.train_tab import TrainTab
from gui.tabs.infer_tab import InferTab
from gui.tabs.export_tab import ExportTab
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
        self._path_history: dict[str, list[str]] = {}

        # ── 标签页 ──
        self._tabs = QTabWidget()
        self._tabs.setProperty("themeClass", "tab_widget")
        self._tabs.setStyleSheet(TAB_WIDGET_STYLE)

        self._train_tab = TrainTab(path_history=self._path_history)
        self._infer_tab = InferTab(path_history=self._path_history)
        self._export_tab = ExportTab(path_history=self._path_history)
        self._logs_tab = LogsTab(path_history=self._path_history)
        self._tools_tab = ToolsTab(path_history=self._path_history)
        self._settings_tab = SettingsTab()

        tab_defs = [
            (self._train_tab,    "tab.train"),
            (self._infer_tab,    "tab.infer"),
            (self._export_tab,   "tab.export"),
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
        if hasattr(self._train_tab, 'set_dark_mode'):
            self._train_tab.set_dark_mode(self._dark_mode)

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
        for tab, attr in [
            (self._train_tab, "_train_worker"),
            (self._infer_tab, "_infer_worker"),
            (self._tools_tab, "_tool_worker"),
            (self._export_tab, "_export_worker"),
        ]:
            worker = getattr(tab, attr, None)
            if worker and worker.isRunning():
                worker.finished.connect(QApplication.quit)
                worker.stop()
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
